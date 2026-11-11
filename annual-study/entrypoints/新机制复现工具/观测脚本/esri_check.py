"""Fetch native Sentinel-2 10m Land Use/Land Cover Time Series v003 for aligned 2019–2021 cross-date checks. No source reclassification except class 7 built; remove cloud (10) and NoData (0) from denominator."""
import json,hashlib,math,time,concurrent.futures,shutil,tempfile,sys
from pathlib import Path
import requests, numpy as np,pandas as pd, geopandas as gp,shapely,rasterio,tifffile,exactextract as ex
from rasterio.windows import Window
from rasterio.warp import transform_bounds
from rasterio.merge import merge
here=Path(__file__).resolve().parent;base=here.parents[1];raw=base/'01_原始数据'/'Esri_v003_2019_2020_2021';raw.mkdir(parents=True,exist_ok=True)
grid=gp.read_file(next(Path(r'D:/ER219_results/年度评价_2015_2025_原始GIS边界/计算结果与核验').rglob('annual_grid_500.gpkg')))
squares=grid.copy();squares.geometry=shapely.box(grid.ix*500,grid.iy*500,(grid.ix+1)*500,(grid.iy+1)*500);bb=squares.total_bounds
def tile(yt):
    year,t=yt;name=f'{t}_{year}0101-'+(f'{year}1231' if year==2025 else f'{year+1}0101');url=f'https://lulctimeseries.blob.core.windows.net/lulctimeseriesv003/lc{year}/{name}.tif';dst=raw/(name+'.tif');meta=dst.with_suffix('.json')
    if dst.exists() and meta.exists() and hashlib.sha256(dst.read_bytes()).hexdigest()==json.loads(meta.read_text('utf8'))['sha256']:return dst
    old=Path('D:/ER219_raw/年度分析_2015_2025/Esri_2017_2025')/(name+'_北京绿隔原网格窗口.tif')
    oldmeta=old.parent/(name+'.tif.source.json')
    if old.exists() and oldmeta.exists():
        m=json.loads(oldmeta.read_text('utf8'));sha=hashlib.sha256(old.read_bytes()).hexdigest()
        assert sha==m['native_window_sha'] and m['url']==url
        shutil.copy2(old,dst);meta.write_text(json.dumps({**m,'sha256':sha},ensure_ascii=False,indent=2),encoding='utf8');return dst
    def get(i,j):
        for att in range(3):
            try:
                r=requests.get(url+f'?window={i}-{j}',headers={'Range':f'bytes={i}-{j}','Accept-Encoding':'identity'},timeout=(10,45));r.raise_for_status()
                assert r.status_code==206 and len(r.content)==j-i+1 and r.headers['Content-Range'].startswith(f'bytes {i}-{j}/')
                return r
            except Exception:
                if att==2:raise
                time.sleep(.5)
    h=get(0,1199999);sz=int(h.headers['Content-Range'].split('/')[-1]);etag=h.headers['ETag'];p=raw/(name+'.partial')
    with p.open('wb') as fp:fp.truncate(sz);fp.seek(0);fp.write(h.content)
    with tifffile.TiffFile(p) as tf:
        f=tf.pages[0];tw,th,w,ht=f.tilewidth,f.tilelength,f.imagewidth,f.imagelength;o,b=np.array(f.dataoffsets),np.array(f.databytecounts)
    with rasterio.open(p) as src:
        ext=transform_bounds(squares.crs,src.crs,*bb,densify_pts=60);win=src.window(*ext)
        x0=max(0,math.floor(win.col_off)-2);y0=max(0,math.floor(win.row_off)-2);x1=min(w,math.ceil(win.col_off+win.width)+2);y1=min(ht,math.ceil(win.row_off+win.height)+2)
        nbx=math.ceil(w/tw);assert x1>x0 and y1>y0
    spans=[]
    for rr in range(y0//th,(y1-1)//th+1):
        ids=np.arange(rr*nbx+x0//tw,rr*nbx+(x1-1)//tw+1);ids=ids[b[ids]>0]
        if len(ids):spans.append((int(o[ids].min()),int((o[ids]+b[ids]).max()-1)))
    with concurrent.futures.ThreadPoolExecutor(6) as e, p.open('r+b') as fd:
        for (i,j),v in zip(spans,e.map(lambda ij:get(*ij),spans)):
            assert v.headers['ETag']==etag;fd.seek(i);fd.write(v.content)
    with rasterio.open(p) as src:
        win=Window(x0,y0,x1-x0,y1-y0);v=src.read(1,window=win);aff=src.window_transform(win);crs=src.crs
    assert np.isin(v,[0,1,2,4,5,7,8,9,10,11]).all(); assert v.max()>0
    with rasterio.open(dst,'w',driver='GTiff',height=v.shape[0],width=v.shape[1],transform=aff,crs=crs,count=1,nodata=0,dtype='uint8',tiled=True,compress='deflate') as f:f.write(v,1)
    p.unlink();meta.write_text(json.dumps({'source':url,'etag':etag,'source_bytes':sz,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'ranges':spans,'window':[x0,y0,x1-x0,y1-y0]},indent=2),encoding='utf8');print('ready',name,flush=True);return dst
def run(y,fn):
    with rasterio.open(fn[0]) as a,rasterio.open(fn[1]) as b:
        arr,aff=merge([a,b],nodata=0,method='first');crs=a.crs
    arr[arr==10]=0; dst=here/f'Esri{y}_mosaic.tif'
    with rasterio.open(dst,'w',driver='GTiff',width=arr.shape[2],height=arr.shape[1],count=1,dtype='uint8',nodata=0,crs=crs,transform=aff,tiled=True,compress='deflate') as f:f.write(arr)
    del arr
    geo=squares.copy();geo.geometry=geo.geometry.segmentize(25);geo=geo.to_crs(crs)
    r=ex.exact_extract(str(dst),geo,['unique','frac','count'],include_cols=['grid_id'],output='pandas')
    frac=[dict(zip(q.unique,q.frac)).get(7,0.) for q in r.itertuples(index=False)]
    coverage=np.clip(r['count'].values*abs(aff.a*aff.e)/geo.area.values,0,1)
    out=pd.DataFrame({'grid_id':r['grid_id'],'built_pct_full':np.where(coverage>=.8,frac,np.nan),'coverage':coverage})
    classes=[dict(zip(q.unique,q.frac)) for q in r.itertuples(index=False)]
    for name,codes in {'tree_frac':[2], 'crop_frac':[5], 'waterwet_frac':[1,4], 'rangeland_frac':[11]}.items():
        out[name]=[sum(m.get(c,0.) for c in codes) for m in classes]
    assert len(out)==4478 and out.grid_id.is_unique
    out.to_csv(here/f'esri_built_{y}.csv',index=False,encoding='utf-8-sig',float_format='%.9g')
    print('done',y,int((coverage>=.8).sum()),float(coverage.min()),float(out.built_pct_full.mean()),flush=True)
if __name__=='__main__':
    years=tuple(map(int,sys.argv[1:])) if len(sys.argv)>1 else (2017,2019,2020,2021,2025)
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        futures={yt:pool.submit(tile,yt) for yt in [(y,t) for y in years for t in ['50S','50T']]}
        for y in years:run(y,[futures[y,t].result() for t in ['50S','50T']])
