import re,hashlib,math,json,shutil,os,threading,concurrent.futures,time
from pathlib import Path
import requests,numpy as np,rasterio,tifffile
from rasterio.windows import Window
from rasterio.warp import transform_bounds,reproject,Resampling
from rasterio.merge import merge
from compare_landcover import P,A
raw=Path(r'D:\ER219_raw\年度分析_2015_2025\Esri_2017_2025');raw.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def tile(yt):
 y,t=yt;tag=f'{t}_{y}0101-'+(f'{y}1231' if y==2025 else f'{y+1}0101')+'.tif';url=f'https://lulctimeseries.blob.core.windows.net/lulctimeseriesv003/lc{y}/{tag}';rang=raw/(tag+'_原始字节段');rang.mkdir(exist_ok=True)
 pr=raw/(tag[:-4]+'_北京绿隔原网格窗口.tif');manifest=raw/(tag+'.source.json')
 if pr.exists() and manifest.exists():return pr
 r=requests.head(url,timeout=20);r.raise_for_status();sz=int(r.headers['Content-Length']);etag=r.headers['ETag'];rl=[]
 def get(az):
  left,right=az;dst=rang/f'{left}_{right}.bin'
  if not dst.exists() or dst.stat().st_size!=right-left+1:
   for i in range(4):
    try:
     rr=requests.get(url+f'?window={left}-{right}',headers={'Range':f'bytes={left}-{right}','Accept-Encoding':'identity'},timeout=(12,45))
     assert rr.status_code==206 and rr.headers['Content-Range']==f'bytes {left}-{right}/{sz}'
     assert rr.headers['ETag']==etag and len(rr.content)==right-left+1
     tmp=dst.with_suffix('.part');tmp.write_bytes(rr.content);os.replace(tmp,dst);break
    except Exception as ex:
     if i==3:raise
     print(tag,'retry',az,repr(ex)[:130],flush=True);time.sleep(1)
  return (left,right,dst)
 head=get((0,1199999));sparse=P/(tag+'.working.partial')
 with sparse.open('wb') as fp:fp.truncate(sz);fp.seek(0);fp.write(head[2].read_bytes())
 with tifffile.TiffFile(sparse) as td:
  pg=td.pages[0];tw,th=pg.tilewidth,pg.tilelength;w,h=pg.imagewidth,pg.imagelength
  of,bc=np.array(pg.dataoffsets),np.array(pg.databytecounts)
 with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
  with rasterio.open(sparse) as ss:
   tgt=transform_bounds('EPSG:4326',ss.crs,116.03,39.64,116.76,40.23,densify_pts=50)
   bb=ss.window(*tgt);r0=max(0,math.floor(bb.row_off)-2);c0=max(0,math.floor(bb.col_off)-2);r1=min(h,math.ceil(bb.row_off+bb.height)+2);c1=min(w,math.ceil(bb.col_off+bb.width)+2)
   assert r1>r0 and c1>c0;win=Window(c0,r0,c1-c0,r1-r0);xx=ss.window_transform(win);srccrs=ss.crs
 ntx=math.ceil(w/tw);ranges=[]
 for ry in range(r0//th,(r1-1)//th+1):
  ids=ry*ntx+np.arange(c0//tw,(c1-1)//tw+1)
  ids=ids[bc[ids]>0]
  if len(ids):ranges.append((int(min(of[ids])),int(max(of[ids]+bc[ids])-1)))
 with concurrent.futures.ThreadPoolExecutor(5) as ex:bits=list(ex.map(get,ranges))
 with sparse.open('r+b') as fp:
  for a,b,f in bits:fp.seek(a);fp.write(f.read_bytes())
 with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
  with rasterio.open(sparse) as s:
   vals=s.read(1,window=win,masked=False);codes=np.unique(vals).tolist()
   assert np.isin(vals,[0,1,2,4,5,7,8,9,10,11]).all(),codes
   tmp=pr.with_suffix('.partial.tif')
   with rasterio.open(tmp,'w',driver='GTiff',width=int(win.width),height=int(win.height),count=1,dtype='uint8',nodata=0,tiled=True,compress='deflate',transform=xx,crs=srccrs) as f:f.write(vals,1)
   os.replace(tmp,pr)
 meta=dict(url=url,year=y,source_tile=t,provider='Impact Observatory / Esri, imaged by Sentinel-2; current Esri Living Atlas landcoverexplorer download URL pattern as distributed by the app',source_byte_length=sz,etag=etag,licence='CC BY 4.0',original_window=[c0,r0,c1-c0,r1-r0],classes=codes,scheme='1 water 2 trees 4 flooded vegetation 5 cropland 7 built 8 bare 9 snow 10 cloud 11 rangeland (grass/shrub incl sparse natural open vegetation)',native_window_sha=sha(pr),ranges=[dict(first=a,last=z,sha=sha(f)) for a,z,f in [head]+bits])
 manifest.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
 sparse.unlink()
 print('NATIVE',y,t,len(bits),vals.shape,flush=True);return pr
def annual(y,files):
 with rasterio.open(files[0]) as a,rasterio.open(files[1]) as b:
  assert a.crs==b.crs
  rawarr,aff=merge([a,b],nodata=0,method='first');crs=a.crs
 with rasterio.open(A/'years/model'/f'CLCD_{y}.tif') as ref:
  ar=np.zeros(ref.shape,'uint8')
  reproject(rawarr[0],ar,src_transform=aff,src_crs=crs,src_nodata=0,dst_transform=ref.transform,dst_crs=ref.crs,dst_nodata=0,resampling=Resampling.mode,num_threads=3)
  to=P/f'Esri_native_code_on30_{y}.tif';m=ref.profile;m.update(nodata=0,compress='deflate',dtype='uint8')
  with rasterio.open(to,'w',**m) as d:d.write(ar,1);d.update_tags(source='Esri/Impact Observatory v003 annual, original codes; 10m mosaic common src then mode to30m',year=str(y))
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(4) as ex:
  futures={(y,t):ex.submit(tile,(y,t)) for y in (2017,2025) for t in ('50S','50T')}
  for y in (2017,2025):annual(y,[futures[(y,t)].result() for t in ('50S','50T')])
