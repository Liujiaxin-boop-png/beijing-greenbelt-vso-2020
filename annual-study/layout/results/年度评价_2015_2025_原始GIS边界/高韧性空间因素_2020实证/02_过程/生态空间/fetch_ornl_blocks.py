"""Read missing 2025 NDVI values via native non-resampled ORNL subsets. Subdivide native rectangle so a truncated HTTP payload never produces false zeros."""
from fetch_ornl_2025 import here,rawbase,BANDS,url,validate
from pathlib import Path
import time,math,json,gzip,hashlib,concurrent.futures,requests
import numpy as np,rasterio
from pyproj import Transformer
from rasterio.transform import Affine
D=rawbase/'MOD13Q1_2025_生长季';S=D/'ORNL原生分块';S.mkdir(exist_ok=True)
ref=next(D.glob('*_QA.tif'))
with rasterio.open(ref) as r:tf,crs,nrow,ncol=r.transform,r.crs,r.height,r.width
to_geo=Transformer.from_crs(crs,'EPSG:4326',always_xy=True)
def chunk(task):
    year,day,y0,y1,x0,x1=task; date=f'A{year}{day:03d}';p=S/f'{date}_NDVI_{y0}_{x0}.json.gz'
    cx,cy=tf*((x0+x1)/2,(y0+y1)/2);lon,lat=to_geo.transform(cx,cy)
    params=dict(latitude=round(lat,7),longitude=round(lon,7),startDate=date,endDate=date,kmAboveBelow=math.ceil((y1-y0+4)/8),kmLeftRight=math.ceil((x1-x0+4)/8),band=BANDS['NDVI'])
    if p.exists():j=json.loads(gzip.decompress(p.read_bytes()))
    else:
        for attempt in range(5):
            try:
                # Using a new query shape subdivides the transfer while native pixel addresses remain identical.
                rr=requests.get(url,params=params,timeout=(8,30))
                rr.raise_for_status();j=rr.json();sub=j['subset'];assert len(sub)==1 and sub[0]['modis_date']==date and len(sub[0]['data'])==int(j['nrows'])*int(j['ncols'])
                gg=gzip.compress(rr.content); tmp=p.with_suffix('.tmp');tmp.write_bytes(gg);tmp.replace(p);break
            except Exception as ex:
                if attempt==4:raise
                time.sleep(.3+attempt)
    n,m=int(j['nrows']),int(j['ncols']);res=float(j['cellsize']);left=float(j['xllcorner']);top=float(j['yllcorner'])+n*res
    col=(left-tf.c)/tf.a;row=(top-tf.f)/tf.e;assert abs(col-round(col))<.001 and abs(row-round(row))<.001
    oy,ox=int(round(row)),int(round(col));assert oy<=y0 and ox<=x0 and oy+n>=y1 and ox+m>=x1
    a=np.asarray(j['subset'][0]['data'],dtype=np.int16).reshape(n,m)
    return (year,day,y0,y1,x0,x1,a[y0-oy:y1-oy,x0-ox:x1-ox],p)
def blocks(year,d):
    return [(year,d,y,min(y+92,nrow),x,min(x+150,ncol)) for y in range(0,nrow,92) for x in range(0,ncol,150)]
if __name__=='__main__':
    validate()
    with rasterio.open(next((rawbase/'MOD13Q1_ORNL渠道验证').glob('*NDVI.tif'))) as r:
        b=blocks(2020,161)[4]; *_,chk,p=chunk(b); np.testing.assert_array_equal(chk,r.read(1)[b[2]:b[3],b[4]:b[5]])
    todo=[];arrays={};filled={};files={}
    for d in range(97,290,16):
        if (D/f'MOD13Q1.A2025{d:03d}.mosaic.061.ORNL_NDVI.tif').exists():continue
        arrays[d]=np.zeros((nrow,ncol),dtype='int16');filled[d]=np.zeros((nrow,ncol),dtype='uint8');files[d]=[];todo+=blocks(2025,d)
    completed=0
    with concurrent.futures.ThreadPoolExecutor(10) as e:
        futs=[e.submit(chunk,t) for t in todo]
        for f in concurrent.futures.as_completed(futs):
            year,d,y0,y1,x0,x1,a,p=f.result();arrays[d][y0:y1,x0:x1]=a;filled[d][y0:y1,x0:x1]+=1;files[d].append(p.name);completed+=1
            if completed%10==0:print('native chunks',completed,'/',len(todo),flush=True)
            if filled[d].min()==1:
                assert filled[d].max()==1
                dest=D/f'MOD13Q1.A2025{d:03d}.mosaic.061.ORNL_NDVI.tif'
                with rasterio.open(dest,'w',driver='GTiff',count=1,crs=crs,transform=tf,height=nrow,width=ncol,compress='deflate',tiled=True,nodata=-3000,dtype='int16') as r:r.write(arrays[d],1)
                dest.with_suffix('.json').write_text(json.dumps({'source_url':url,'date':f'A2025{d:03d}','product':'MOD13Q1 v061, native ORNL DAAC subsetting','shape':[nrow,ncol],'method':'Exact native row/column clipping; all output pixels allocated once. Source blocks stored as full raw JSON gzip including request URLs and production date. Middle validation block reproduced 2020 native pixel values exactly.','blocks':sorted(files[d]),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},indent=2),encoding='utf8');print('native mosaic',d,flush=True)
    assert len(list(D.glob('*_NDVI.tif')))==13
    (D/'ORNL完整原生窗.txt').write_text('13 Terra 16d dates, native SIN mosaic via ORNL DAAC',encoding='utf8')
