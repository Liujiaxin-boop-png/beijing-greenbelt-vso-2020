"""Read the original LZW tile ranges of the annual national 1.0.5 COGs. No resampling.
All local extents and native Albers CRS are read from the verified 2020 full file.
An offline Pillow/libtiff decoder handles each untouched compressed tile."""
from pathlib import Path
import json,hashlib,struct,io,sys,math,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from threading import Lock
from datetime import datetime,timezone
import requests,numpy as np,rasterio as rio,tifffile
from PIL import Image
from rasterio.transform import Affine
from rasterio.windows import Window
from rasterio.warp import transform_bounds
import pandas as pd
work=Path(__file__).resolve().parent
root=Path(r'D:\ER219_raw\CLCD_v105_2015_2025');root.mkdir(exist_ok=True)
localfull=Path(r'D:\ER219_raw\CLCD2020\CLCD_v01_2020_albert.tif')
old=Path(r'D:\ER219_work\spatial\clcd2020.tif')
manifest=pd.read_csv(next(Path(r'D:\ER219_work\indicator_rebuild_20261107').glob('CLCD2015*csv'))).set_index('year')
with rio.open(localfull) as src,rio.open(old) as og:
 numwidth,numheight=src.width,src.height
 tr,cr=src.transform,src.crs
 original_model=src.window(*og.bounds).round_offsets().round_lengths()
 model_cols,model_rows=og.width,og.height
 bbox=src.window(*transform_bounds('EPSG:4326',cr,115.2,39.25,117.7,41.15,densify_pts=40))
 p0r,p0c=math.floor(bbox.row_off/512),math.floor(bbox.col_off/512)
 p1r,p1c=math.ceil((bbox.row_off+bbox.height)/512),math.ceil((bbox.col_off+bbox.width)/512)
 nr,nc=p1r-p0r,p1c-p0c
 wide=Window(p0c*512,p0r*512,nc*512,nr*512)
model_rows_tiles=list(range(int(original_model.row_off)//512,math.ceil((original_model.row_off+original_model.height)/512)))
rdorder=model_rows_tiles+[i for i in range(p0r,p1r) if i not in model_rows_tiles]
loglock=Lock()
def log(*msg):
 with loglock:
  print(datetime.now().strftime('%H:%M:%S'),*msg,flush=True)
def sh(x):return hashlib.sha256(x).hexdigest()
def date():return datetime.now(timezone.utc).isoformat()
def getbytes(sess,year,a,z,expected,kind):
 d=work/'ranges'/str(year);d.mkdir(parents=True,exist_ok=True)
 path=d/f'{a}-{z}.bin'
 if path.exists() and path.stat().st_size==z-a+1:return path.read_bytes()
 u=manifest.loc[year].url
 for attempt in range(9):
  try:
   url=u+f'?window={a}-{z}' if attempt!=3 else f'https://zenodo.org/records/18180184/files/CLCD_v01_{year}_albert.tif?download=1&window={a}-{z}'
   with sess.get(url,headers={'Range':f'bytes={a}-{z}','Accept-Encoding':'identity'},stream=True,timeout=(10,65)) as rr:
    if rr.status_code in [403,429]:raise RuntimeError(f'HTTP {rr.status_code} Retry-After {rr.headers.get("Retry-After")}')
    assert rr.status_code==206,rr.status_code
    assert rr.headers.get('Content-Range','').lower()==f'bytes {a}-{z}/{expected}',(rr.headers.get('Content-Range'),year)
    b=rr.content
   assert len(b)==z-a+1
   tmp=path.with_suffix('.tmp');tmp.write_bytes(b);tmp.replace(path);return b
  except Exception as err:
   log(year,kind,'attempt',attempt+1,str(err));time.sleep(min(24,2**attempt))
 raise RuntimeError((year,a,z,'range failed'))
def decode(comp):
 seq=[(256,4,512),(257,4,512),(258,3,8),(259,3,5),(262,3,1),(273,4,8+2+10*12+4),(277,3,1),(278,4,512),(279,4,len(comp)),(284,3,1)]
 hdr=b'II'+struct.pack('<HIH',42,8,len(seq))
 for tag,ty,val in seq:hdr+=struct.pack('<HHII',tag,ty,1,val)
 hdr+=bytes(4)
 with Image.open(io.BytesIO(hdr+comp)) as im: a=np.asarray(im).copy()
 assert a.shape==(512,512)
 return a
def output(path,array,window,year):
 if path.is_file():
  with rio.open(path) as existing:
   assert existing.shape==array.shape and existing.crs==cr and existing.transform.almost_equals(rio.windows.transform(window,tr))
   assert np.array_equal(existing.read(1),array)
  return
 temp=path.with_suffix('.partial.tif');path.parent.mkdir(parents=True,exist_ok=True)
 with rio.open(temp,'w',driver='GTiff',width=array.shape[1],height=array.shape[0],count=1,dtype='uint8',crs=cr,transform=rio.windows.transform(window,tr),nodata=0,tiled=True,blockxsize=256,blockysize=256,compress='deflate') as ds:
  ds.write(array,1);ds.update_tags(zenodo_record='18180184',version='1.0.5',year=year,source_filename=manifest.loc[year].filename,subset='native integer pixel window; no interpolation')
 temp.replace(path)
def yearrun(year):
 wp=root/f'CLCD_{year}_Beijing_native.tif';mp=work/'model'/f'CLCD_{year}.tif'
 report=root/f'CLCD_{year}_source.json'
 if report.exists() and wp.exists() and mp.exists():return year
 sess=requests.Session();sess.headers['User-Agent']='Academic noncommercial Beijing landscape change study native COG subset/1.0'
 nbytes=int(manifest.loc[year].bytes)
 chunks=[]
 if year==2020:
  digest=hashlib.file_digest(open(localfull,'rb'),'md5').hexdigest();assert 'md5:'+digest==manifest.loc[year].provider_checksum
  with rio.open(localfull) as ds:aa=ds.read(1,window=wide);mm=ds.read(1,window=original_model)
  output(wp,aa,wide,year);output(mp,mm,original_model,year)
 else:
  header=getbytes(sess,year,0,799999,nbytes,'header');chunks.append({'range':[0,799999],'sha256':sh(header)})
  with tifffile.TiffFile(io.BytesIO(header)) as t:
   pg=t.pages[0]; assert (pg.tilelength,pg.tilewidth,int(pg.compression),pg.imagewidth,pg.imagelength)==(512,512,5,numwidth,numheight)
   assert not pg.tags.get(317) or int(pg.tags[317].value)==1
   assert np.allclose(pg.tags[33922].value[3:5],[tr.c,tr.f],rtol=0,atol=0.0001)
   assert np.allclose(pg.tags[33550].value[:2],[30,30],rtol=0,atol=0.000001)
   offsets,counts=pg.dataoffsets,pg.databytecounts
  aa=np.zeros((nr*512,nc*512),'uint8');tcols=math.ceil(numwidth/512)
  for iteration,j in enumerate(rdorder):
   tids=list(range(j*tcols+p0c,j*tcols+p1c));nz=[i for i in tids if counts[i]>0]
   if nz:
    a=min(offsets[i] for i in nz);z=max(offsets[i]+counts[i]-1 for i in nz)
    raw=getbytes(sess,year,a,z,nbytes,f'row{j}')
    chunks.append({'tile_row':j,'range':[a,z],'sha256':sh(raw)})
    for tid in nz:
     cdx=tid%tcols-p0c;lo=offsets[tid]-a;tile=decode(raw[lo:lo+counts[tid]])
     aa[(j-p0r)*512:(j-p0r+1)*512,cdx*512:(cdx+1)*512]=tile
   if iteration+1==len(model_rows_tiles):
    rr,cc=int(original_model.row_off-wide.row_off),int(original_model.col_off-wide.col_off);mm=aa[rr:rr+model_rows,cc:cc+model_cols]
    assert np.isin(mm,[1,2,3,4,5,6,7,8,9]).all();output(mp,mm,original_model,year);log(year,'MODEL READY')
  output(wp,aa,wide,year)
 wh=np.bincount(aa.ravel(),minlength=10);mh=np.bincount(mm.ravel(),minlength=10)
 assert len(wh)==10 and mh[0]==0
 profile={'year':year,'record':'https://zenodo.org/records/18180184','version':'1.0.5','source':manifest.loc[year].url,'national_file_md5':manifest.loc[year].provider_checksum,'national_file_bytes':nbytes,'download_time_utc':date(),'large_window_rcwh':[p0r*512,p0c*512,wide.width,wide.height],'model_window_colrowwh':list(original_model.flatten()),'model_native_pixel_sha256':sh(mm.tobytes()),'wide_native_pixel_sha256':sh(aa.tobytes()),'wide_code_counts_0_to_9':wh.tolist(),'model_code_counts_0_to_9':mh.tolist(),'response_ranges':chunks,'raw':str(wp),'model':str(mp),'model_shape':[model_rows,model_cols],'full_file_locally_md5_verified':year==2020,'window_source':'local national file' if year==2020 else 'full-resolution tier of national COG; HTTP Range; TIFF tile-specific LZW lossless decode; original cell values and Albers pixel alignment'}
 report.write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf8');log(year,'WIDE AND RECEIPT READY')
 return year
if __name__=='__main__':
 log('window tiles',p0r,p1r,p0c,p1c,'priority',rdorder)
 with ThreadPoolExecutor(max_workers=6) as pool:
  futs={pool.submit(yearrun,y):y for y in [2020,2015,2025,2016,2017,2018,2019,2021,2022,2023,2024]}
  failed=[]
  for f in as_completed(futs):
   try:f.result()
   except Exception:
    import traceback;log(futs[f],traceback.format_exc());failed.append(futs[f])
 if failed:raise SystemExit(failed)
