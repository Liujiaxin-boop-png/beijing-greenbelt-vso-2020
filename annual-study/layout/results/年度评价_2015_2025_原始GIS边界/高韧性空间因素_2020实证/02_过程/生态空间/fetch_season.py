"""Download native 2020 MOD13Q1 v061 COG windows for all full 16-day periods April–October; no GEE; both tiles; input requests and window integrity archived."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from io import BytesIO
import json,time,math,hashlib,shutil,datetime,threading,sys
import requests,numpy as np,rasterio,tifffile,geopandas as gp
from rasterio.windows import Window
from rasterio.warp import transform_bounds
here=Path(__file__).resolve().parent
year=int(sys.argv[1]) if len(sys.argv)>1 else 2020
root=here.parents[1]
raw=root/'01_原始数据'/f'MOD13Q1_{year}_生长季'
raw.mkdir(parents=True,exist_ok=True)
olds=Path('D:/ER219_raw/年度分析_2015_2025/MOD13Q1_2020_夏季独立观测')
grid=gp.read_file(next(Path('D:/ER219_results/年度评价_2015_2025_原始GIS边界/计算结果与核验').rglob('annual_grid_500.gpkg')))
bounds=(grid.ix.min()*500,grid.iy.min()*500,(grid.ix.max()+1)*500,(grid.iy.max()+1)*500)
def req(url,**kw):
    for retry in range(4):
        try:
            a=requests.get(url,timeout=(8,35),**kw);a.raise_for_status();return a
        except Exception:
            if retry==3:raise
            time.sleep(.3)
catalog=here/('season_stac.json' if year==2020 else f'season_stac_{year}.json')
if not catalog.exists():
    params={'collections':'modis-13Q1-061','bbox':'116.38,39.96,116.43,40.04','datetime':f'{year}-04-01T00:00:00Z/{year}-10-31T23:59:59Z','limit':100}
    a=req('https://planetarycomputer.microsoft.com/api/stac/v1/search',params=params);catalog.write_bytes(a.content)
features=json.loads(catalog.read_text('utf8'))['features'];features=[f for f in features if f['id'].startswith('MOD13Q1') and ('.h26v04.' in f['id'] or '.h26v05.' in f['id']) and 97<=int(f['id'].split('.')[1][-3:])<=289]
# Some acquisitions were reprocessed. Keep the latest production timestamp for each sensor/date/tile/collection.
features=list({'.'.join(f['id'].split('.')[:4]):f for f in sorted(features,key=lambda f:f['id'])}.values())
print('n',len(features),flush=True);assert len(features)==26
(raw/'stac_26.json').write_text(json.dumps(features),encoding='utf8')
keys={'NDVI':'250m_16_days_NDVI','QA':'250m_16_days_pixel_reliability','VIQ':'250m_16_days_VI_Quality'}
token=req('https://planetarycomputer.microsoft.com/api/sas/v1/token/modiseuwest/modis-061-cogs',params={'cache':int(time.time())}).json()['token']
def download(f,k):
    item=f['id'];href=f['assets'][keys[k]]['href'];dest=raw/(item+'_'+k+'.tif');rec=dest.with_suffix('.json')
    ready=lambda d,r:d.exists() and r.exists() and hashlib.sha256(d.read_bytes()).hexdigest()==json.loads(r.read_text('utf8'))['window_sha256']
    if ready(dest,rec):return
    prior=olds/dest.name
    if ready(prior,prior.with_suffix('.json')):
        shutil.copy2(prior,dest);shutil.copy2(prior.with_suffix('.json'),rec);return
    def rng(i,j):
        for t in range(3):
            rr=req(href+'?'+token,headers={'Range':f'bytes={i}-{j}','Accept-Encoding':'identity'})
            if rr.status_code==206 and len(rr.content)==j-i+1:return rr
        raise RuntimeError((rr.status_code,len(rr.content),i,j))
    hdr=rng(0,100000)
    size=int(hdr.headers['Content-Range'].split('/')[-1]);etag=hdr.headers['ETag']
    with tifffile.TiffFile(BytesIO(hdr.content)) as tf:
        pg=tf.pages[0];tw,th,w,h=pg.tilewidth,pg.tilelength,pg.imagewidth,pg.imagelength;offsets=np.asarray(pg.dataoffsets);sizes=np.asarray(pg.databytecounts)
    temp=raw/(item+'_'+k+'.partial')
    with temp.open('wb') as fd:fd.truncate(size);fd.seek(0);fd.write(hdr.content)
    with rasterio.open(temp) as z:
        box=transform_bounds(grid.crs,z.crs,*bounds,densify_pts=64);win=z.window(*box)
        x0=max(0,int(math.floor(win.col_off))-2);x1=min(w,int(math.ceil(win.col_off+win.width))+2)
        y0=max(0,int(math.floor(win.row_off))-2);y1=min(h,int(math.ceil(win.row_off+win.height))+2)
    assert x1>x0 and y1>y0; nt=math.ceil(w/tw)
    spans=[]
    for row in range(y0//th,(y1-1)//th+1):
        ids=np.arange(row*nt+x0//tw,row*nt+(x1-1)//tw+1);spans.append((int(offsets[ids].min()),int((offsets[ids]+sizes[ids]).max()-1)))
    with temp.open('r+b') as fd:
        for i,j in spans:
            rr=rng(i,j);assert etag==rr.headers['ETag'];fd.seek(i);fd.write(rr.content)
    window=Window(x0,y0,x1-x0,y1-y0)
    with rasterio.open(temp) as z:
        v=z.read(1,window=window);aff=z.window_transform(window);crs=z.crs;nodata=z.nodata
    with rasterio.open(dest,'w',driver='GTiff',width=v.shape[1],height=v.shape[0],count=1,dtype=v.dtype,transform=aff,crs=crs,nodata=nodata,compress='deflate') as z:z.write(v,1)
    temp.unlink()
    rec.write_text(json.dumps({'item':item,'asset':keys[k],'href':href,'etag':etag,'source_size':size,'window':[x0,y0,x1-x0,y1-y0],'byte_ranges':spans,'window_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},indent=2),encoding='utf8')
todo=[(f,k) for k in ['QA','NDVI','VIQ'] for f in sorted(features,key=lambda f:f['id'])]
failed=[]
with ThreadPoolExecutor(16) as ex:
    fut={ex.submit(download,f,k):(f['id'],k) for f,k in todo}
    for future in as_completed(fut):
        tag=fut[future]
        try:future.result();print('ready',*tag,flush=True)
        except Exception as e:failed.append(tag);print('error',tag,type(e).__name__,flush=True)
print('failed',failed,flush=True);sys.exit(bool(failed))
