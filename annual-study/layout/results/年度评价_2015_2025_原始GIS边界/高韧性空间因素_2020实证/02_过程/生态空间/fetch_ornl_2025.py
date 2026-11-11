"""NASA ORNL TESViS MOD13Q1 V061: same native archive, not a new product. Validate exact pixel values against local Azure windows for a 2020 holdback date before using 2025."""
import requests,gzip,hashlib,json,sys,math,datetime,time,concurrent.futures,numpy as np,rasterio
from rasterio.transform import Affine
from pathlib import Path
here=Path(__file__).resolve().parent; rawbase=here.parents[1]/'01_原始数据'
BANDS={'NDVI':'250m_16_days_NDVI','QA':'250m_16_days_pixel_reliability','VIQ':'250m_16_days_VI_Quality'}
url='https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset'
tmpl=next((rawbase/'MOD13Q1_2020_生长季').glob('*NDVI.tif'))
with rasterio.open(tmpl) as src:crs=src.crs
def get(year,d,k):
    dr=rawbase/('MOD13Q1_2025_生长季' if year==2025 else 'MOD13Q1_ORNL渠道验证');dr.mkdir(parents=True,exist_ok=True)
    name=f'MOD13Q1.A{year}{d:03d}.mosaic.061.ORNL_{k}';dst=dr/(name+'.tif');srcjson=dr/(name+'.json.gz');meta=dr/(name+'.json')
    if dst.exists() and meta.exists() and hashlib.sha256(dst.read_bytes()).hexdigest()==json.loads(meta.read_text('utf8'))['sha256']:return dst
    date=f'A{year}{d:03d}';params={'latitude':39.934007,'longitude':116.322900,'startDate':date,'endDate':date,'kmAboveBelow':34,'kmLeftRight':56,'band':BANDS[k]}
    if srcjson.exists():j=json.loads(gzip.decompress(srcjson.read_bytes()))
    else:
        for t in range(3):
            try:
                resp=requests.get(url,params=params,timeout=(15,100));resp.raise_for_status();j=resp.json()
                assert 'subset' in j,(resp.status_code,j);srcjson.write_bytes(gzip.compress(resp.content));break
            except Exception:
                if t==2:raise
                time.sleep(1+t)
    assert len(j['subset'])==1 and j['subset'][0]['modis_date']==date
    sub=j['subset'][0];nr=int(j['nrows']);nc=int(j['ncols']);res=float(j['cellsize']);ox=float(j['xllcorner']);oy=float(j['yllcorner'])
    # Published REST coordinates rounded to centimetres; snap to the source projection's native lattice.
    with rasterio.open(tmpl) as ref:
        tf=ref.transform;px=round((ox-tf.c)/tf.a);py=round((oy+nr*res-tf.f)/tf.e)
        aff=tf*Affine.translation(px,py)
        assert max(abs(aff.c-ox),abs(aff.f-oy-nr*res))<.1
    dtype={'QA':'int16','NDVI':'int16','VIQ':'uint16'}[k];fill={'QA':-1,'NDVI':-3000,'VIQ':65535}[k]
    arr=np.asarray(sub['data']).astype('int64').reshape(nr,nc);arr[arr<0 if k=='VIQ' else arr<-10000]=fill
    with rasterio.open(dst,'w',driver='GTiff',height=nr,width=nc,count=1,dtype=dtype,nodata=fill,transform=aff,crs=crs,compress='deflate',tiled=True) as f:f.write(arr.astype(dtype),1)
    meta.write_text(json.dumps({'source_url':j.get('header',url),'date':date,'proc_date':sub.get('proc_date'),'product':'MOD13Q1 V061 (NASA ORNL TESViS original raw data, no quality filtering)','tile_returned':sub.get('tile'),'returned_shape':[nr,nc],'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'json_gz_sha256':hashlib.sha256(srcjson.read_bytes()).hexdigest()},indent=2),encoding='utf8')
    print('ORNL ready',date,k,nr,nc,flush=True);return dst
def validate():
    rec=[]
    from rasterio.windows import from_bounds,Window,intersection
    for k in BANDS:
        f=get(2020,161,k)
        with rasterio.open(f) as z:
            for a in sorted((rawbase/'MOD13Q1_2020_生长季').glob(f'MOD13Q1.A2020161.*_{k}.tif')):
                with rasterio.open(a) as v:
                    b=(max(z.bounds.left,v.bounds.left),max(z.bounds.bottom,v.bounds.bottom),min(z.bounds.right,v.bounds.right),min(z.bounds.top,v.bounds.top))
                    w1=from_bounds(*b,z.transform).round_offsets().round_lengths();w2=from_bounds(*b,v.transform).round_offsets().round_lengths()
                    x=z.read(1,window=w1);y=v.read(1,window=w2)
                    # ESA/NASA archives can code nodata for summary QA with signed or unsigned bytes.
                    if k=='QA':
                        x=x.astype('i4');y=y.astype('i4');x=np.where(x==255,-1,x);y=np.where(y==255,-1,y)
                    if k=='VIQ':x=x.astype('uint16');y=y.astype('uint16')
                    assert x.shape==y.shape
                    rec.append({'product':v.name,'n':x.size,'equal':int((x==y).sum()),'fraction':float((x==y).mean())})
    print('channel equivalence',rec,flush=True)
    (here/'ORNL_2020渠道交叉核验.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf8')
    assert min(z['fraction'] for z in rec)>.995
def batch(days,k):
    dr=rawbase/'MOD13Q1_2025_生长季';dr.mkdir(parents=True,exist_ok=True)
    needed=[d for d in days if not (dr/f'MOD13Q1.A2025{d:03d}.mosaic.061.ORNL_{k}.tif').exists()]
    if needed:
        dates=[f'A2025{d:03d}' for d in days]
        p={'latitude':39.934007,'longitude':116.322900,'startDate':dates[0],'endDate':dates[-1],'kmAboveBelow':34,'kmLeftRight':56,'band':BANDS[k]}
        arc=dr/'ORNL_original_batch';arc.mkdir(exist_ok=True)
        f=arc/(dates[0]+'_'+dates[-1]+'_'+k+'.json.gz')
        if f.exists():j=json.loads(gzip.decompress(f.read_bytes()))
        else:
            try:
                rr=requests.get(url,params=p,timeout=(15,120));rr.raise_for_status();j=rr.json();assert set(z['modis_date'] for z in j['subset'])==set(dates)
                f.write_bytes(gzip.compress(rr.content))
            except Exception:
                for d in needed:get(2025,d,k)
                return
        for sub in j['subset']:
            if int(sub['modis_date'][-3:]) not in needed:continue
            pth=dr/(f'MOD13Q1.{sub["modis_date"]}.mosaic.061.ORNL_{k}.json.gz')
            pth.write_bytes(gzip.compress(json.dumps({**j,'subset':[sub]}).encode()))
    for d in days:get(2025,d,k)
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(3) as e:
        for r in e.map(lambda k:get(2020,161,k),BANDS):pass
    validate()
    days=list(range(97,290,16))
    with concurrent.futures.ThreadPoolExecutor(6) as e:
        fs=[e.submit(batch,days[i:i+3],k) for i in range(0,len(days),3) for k in BANDS]
        for f in concurrent.futures.as_completed(fs):f.result()
    (rawbase/'MOD13Q1_2025_生长季'/'ORNL完整原生窗.txt').write_text('13 Terra 16d dates, native SIN mosaic via ORNL DAAC',encoding='utf8')
