import requests,numpy as np,rasterio as rio,tifffile,io,os,time,json,sys,hashlib,concurrent.futures as cf
from pathlib import Path
from rasterio.windows import from_bounds, Window, transform
from rasterio.io import MemoryFile
import pyogrio
W=Path(__file__).resolve().parent; P=W/'发布者COG的北京范围'; P.mkdir(exist_ok=True)
grid=pyogrio.read_dataframe('D:/ER219_work/shp11/core/annual_grid_500.gpkg').to_crs(4326); x0,y0,x1,y1=grid.total_bounds
M=json.loads((W/'OpenGeoHub_meta.json').read_text(encoding='utf8'))
def fetch(url,a,b):
    for i in range(3):
        try:
            r=requests.get(url,headers={'Range':f'bytes={a}-{b}','Accept-Encoding':'identity'},params={'subregion_part':f'{a}-{b}'},timeout=(8,22));r.raise_for_status()
            assert r.headers.get('Content-Range','').startswith(f'bytes {a}-{b}/'),(r.status_code,r.headers.get('Content-Range'),len(r.content))
            return r.content
        except Exception as e:
            if i==2:raise
            time.sleep(1.5+i)
def get(year):
  fn=f'nightlights.average_viirs.v21_m_500m_s_{year}0101_{year}1231_go_epsg4326_v20250904.tif'
  E=next(e for e in M['files'] if e['key']==fn); url='https://zenodo.org/api/records/17294744/files/'+fn+'/content'
  tmp=P/f'{year}.part'; out=P/f'OpenGeoHub_average_{year}_北京.tif'; meta=P/f'{year}_源与窗口.json'
  if out.exists() and meta.exists():return
  header=fetch(url,0,524287)
  with tmp.open('wb') as f: f.write(header);f.truncate(E['size'])
  with rio.open(tmp) as ds:
    b=from_bounds(x0-.005,y0-.005,x1+.005,y1+.005,ds.transform);b=Window(int(np.floor(b.col_off)),int(np.floor(b.row_off)),int(np.ceil(b.width))+2,int(np.ceil(b.height))+2)
    tileh,tilew=ds.block_shapes[0]; ar=np.arange
    ix=(int(b.col_off)//tilew,int(b.col_off+b.width-1)//tilew)
    iy=(int(b.row_off)//tileh,int(b.row_off+b.height-1)//tileh)
    nr=int(np.ceil(ds.width/tilew))
  with tifffile.TiffFile(tmp) as tf:
    pg=tf.pages[0];offs=pg.dataoffsets;bs=pg.databytecounts
    requests_needed=[]
    for row in range(iy[0],iy[1]+1):
        for col in range(ix[0],ix[1]+1):
            val=row*nr+col; off,size=offs[val],bs[val]
            if size>0:
                assert off>0
                requests_needed.append((off,size))
  with tmp.open('r+b') as f:
    for a,k in requests_needed: f.seek(a); f.write(fetch(url,a,a+k-1))
  with rio.open(tmp) as ds:
    arr=ds.read(1,window=b); aff=transform(b,ds.transform)
    with rio.open(out,'w',driver='GTiff',width=arr.shape[1],height=arr.shape[0],count=1,dtype=arr.dtype,transform=aff,crs=ds.crs,nodata=ds.nodata,compress='deflate') as oo:
        oo.write(arr,1);oo.scales=ds.scales;oo.offsets=ds.offsets;oo.update_tags(radiance_conversion='(raw * source TIFF scale) / 10; see publisher documentation')
    rec={'year':year,'url':url,'source_file':fn,'registry_checksum':E['checksum'],'content_total_bytes':E['size'],'tiff_dtype':str(arr.dtype),'nodata':ds.nodata,'local_min':float(arr.min()),'local_max':float(arr.max()),'n_values':int(np.unique(arr).size),'source_affine':list(ds.transform),'source_scale':ds.scales,'tile_ranges':requests_needed,'window':list(b.flatten()),'sha256_clipped':hashlib.sha256(out.read_bytes()).hexdigest()}
    assert rec['n_values']>5,rec
  tmp.unlink();meta.write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf8');print(year,rec['n_values'],rec['local_min'],rec['local_max'],flush=True)
ys=list(map(int,sys.argv[1:])) or [2019,2020,2021,2015,2016,2017,2018,2022,2023,2024]
with cf.ThreadPoolExecutor(3) as p:
 for f in cf.as_completed({p.submit(get,y):y for y in ys}):
    try:f.result()
    except Exception as e:print('FAILED',str(e)[:290],flush=True)
