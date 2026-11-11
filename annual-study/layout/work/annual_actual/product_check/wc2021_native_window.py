import re,hashlib,math,json,shutil,os,threading,concurrent.futures,time
from pathlib import Path
import requests,numpy as np,rasterio,tifffile
from rasterio.windows import Window
from rasterio.warp import transform_bounds,reproject,Resampling
from rasterio.merge import merge
from compare_landcover import P,A
raw=Path(r'D:\ER219_raw\年度分析_2015_2025\WorldCover2021');raw.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def tile(yt):
 y,t=yt;tag='ESA_WorldCover_10m_2021_v200_N39E114_Map.tif';url=f'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/{tag}';rang=raw/(tag+'_原始字节段');rang.mkdir(exist_ok=True)
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
   assert np.isin(vals,[0,10,20,30,40,50,60,70,80,90,95,100]).all(),codes
   tmp=pr.with_suffix('.partial.tif')
   with rasterio.open(tmp,'w',driver='GTiff',width=int(win.width),height=int(win.height),count=1,dtype='uint8',nodata=0,tiled=True,compress='deflate',transform=xx,crs=srccrs) as f:f.write(vals,1)
   os.replace(tmp,pr)
 meta=dict(url=url,year=y,source_tile=t,provider='ESA WorldCover 10m v200 2021 official map tiles',source_byte_length=sz,etag=etag,licence='CC BY 4.0',original_window=[c0,r0,c1-c0,r1-r0],classes=codes,scheme='WorldCover native codes; 10 trees, 20 shrub, 30 grass, 40 crop, 50 built, 60 bare, 70 snow, 80 water, 90 wetland',native_window_sha=sha(pr),ranges=[dict(first=a,last=z,sha=sha(f)) for a,z,f in [head]+bits])
 manifest.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
 sparse.unlink()
 print('NATIVE',y,t,len(bits),vals.shape,flush=True);return pr
if __name__=='__main__':
 filepath=tile((2021,'N39E114'))
 with rasterio.open(filepath) as rawds,rasterio.open(A/'years/model/CLCD_2021.tif') as ref:
  ar=np.zeros(ref.shape,'uint8')
  reproject(rasterio.band(rawds,1),ar,src_transform=rawds.transform,src_crs=rawds.crs,src_nodata=0,dst_transform=ref.transform,dst_crs=ref.crs,dst_nodata=0,resampling=Resampling.mode,num_threads=3)
  lookup=np.zeros(256,'uint8');lookup[[10,20,30,40,50,60,70,80,90]]=[2,3,4,1,8,7,6,5,9];p=P/'WC2021_harmonized_scopebuffer.tif';meta=ref.profile;meta.update(dtype='uint8',nodata=0,compress='deflate')
  with rasterio.open(p,'w',**meta) as out:out.write(lookup[ar],1);out.update_tags(Resampling='Mode, original 10m native window over full planning AOI and buffer, transform fixed to CLCD. WorldCover source codes 10:2 20:3 30:4 40:1 50:8 60:7 70:6 80:5 90:9')
 from compare_landcover import run
 run(2021,p,'WorldCover_v200')
