from pathlib import Path
import requests, json, hashlib, time, datetime
import rasterio
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/'01_原始数据'
AUDIT=ROOT/'02_过程文件/数据审计'

def download(url,dst,signed=False,expected_md5=None):
    dst.parent.mkdir(parents=True,exist_ok=True)
    headers={}
    if not dst.exists():
        actual=url
        if signed:
            s=requests.get('https://planetarycomputer.microsoft.com/api/sas/v1/sign',params={'href':url},timeout=30)
            s.raise_for_status();actual=s.json()['href']
        part=dst.with_suffix(dst.suffix+'.partial')
        for attempt in range(3):
            try:
                with requests.get(actual,stream=True,timeout=(20,90)) as r:
                    r.raise_for_status(); headers={k:r.headers.get(k) for k in ['Content-Length','ETag','Last-Modified','Content-Type']}
                    with part.open('wb') as f:
                        for b in r.iter_content(8*1024*1024):f.write(b)
                    if r.headers.get('Content-Length'):assert part.stat().st_size==int(r.headers['Content-Length'])
                part.rename(dst);break
            except Exception:
                if attempt==2:raise
                time.sleep(2)
    h=hashlib.sha256();m=hashlib.md5()
    with dst.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b);m.update(b)
    if expected_md5:assert m.hexdigest()==expected_md5,(m.hexdigest(),expected_md5)
    rec={'original_url':url,'local_relative':str(dst.relative_to(ROOT)),'bytes':dst.stat().st_size,'sha256':h.hexdigest(),'md5':m.hexdigest(),'headers':headers,'signed_url_saved':False,'status':'COMPLETE_DISTRIBUTED_FILE_VERIFIED'}
    if dst.suffix.lower()=='.tif':
        with rasterio.open(dst) as ds: rec.update(crs=str(ds.crs),shape=list(ds.shape),bounds=list(ds.bounds),resolution=list(ds.res),nodata=ds.nodata)
    return rec

def nasadem(tile):
    folder=RAW/'NASADEM完整瓦片';folder.mkdir(parents=True,exist_ok=True)
    url='https://planetarycomputer.microsoft.com/api/stac/v1/collections/nasadem/items/NASADEM_HGT_'+tile
    r=requests.get(url,timeout=30);r.raise_for_status();d=r.json()
    (folder/(d['id']+'.stac.json')).write_bytes(r.content)
    asset=d['assets']['elevation']['href']
    rec=download(asset,folder/(d['id']+'.tif'),signed=True)
    rec.update(stac_url=url,asset='elevation',purpose='Fixed terrain background; SRTM acquisition February 2000, NASADEM reprocessing v001',retrieval='Complete native-grid COG tile as distributed by Microsoft Planetary Computer, not projected or resampled by this study')
    (folder/(d['id']+'.metadata.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'complete':d['id'],'bytes':rec['bytes']},ensure_ascii=False),flush=True)
    return rec

def stqa(item):
    folder=RAW/'Landsat8_2020补充质量层'/item;folder.mkdir(parents=True,exist_ok=True)
    url='https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/'+item
    r=requests.get(url,timeout=30);r.raise_for_status();d=r.json()
    (folder/'stac_original.json').write_bytes(r.content)
    assert d['assets']['qa']['href'].endswith('_ST_QA.TIF')
    asset=d['assets']['qa']['href'];sign=requests.get('https://planetarycomputer.microsoft.com/api/sas/v1/sign',params={'href':asset},timeout=30);sign.raise_for_status()
    from rasterio.windows import from_bounds,Window
    from rasterio.warp import transform_bounds
    import numpy as np
    bbox=[115.90060924335928,39.54667835033055,116.91776932042693,40.309979082472054]
    dst=folder/(item+'_ST_QA_native_window.tif')
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
        with rasterio.open(sign.json()['href']) as ds:
            w=from_bounds(*transform_bounds('EPSG:4326',ds.crs,*bbox),transform=ds.transform)
            w=Window(int(w.col_off),int(w.row_off),int(np.ceil(w.width))+1,int(np.ceil(w.height))+1).intersection(Window(0,0,ds.width,ds.height))
            a=ds.read(1,window=w);prof=ds.profile.copy();prof.update(width=int(w.width),height=int(w.height),transform=ds.window_transform(w),compress='deflate',tiled=True)
            if not dst.exists():
                with rasterio.open(dst,'w',**prof) as out:out.write(a,1)
            with rasterio.open(dst) as out: assert np.array_equal(a,out.read(1))
    rec={'source_stac_url':url,'source_asset':asset,'item_id':item,'purpose':'Same already-selected 2020 scene, surface-temperature uncertainty QA; does not add new observation dates','window':list(w.flatten()),'bytes':dst.stat().st_size,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'path':str(dst.relative_to(ROOT)),'source_metadata':d['assets']['qa'],'status':'NATIVE_GRID_LOSSLESS_WINDOW_VERIFIED'}
    (folder/'metadata.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'complete':'ST_QA '+item,'bytes':rec['bytes']},ensure_ascii=False),flush=True)
    return rec

def clcd():
    folder=RAW/'CLCD2020';folder.mkdir(parents=True,exist_ok=True)
    url='https://zenodo.org/records/8176941/files/CLCD_v01_2020_albert.tif?download=1'
    rec=download(url,folder/'CLCD_v01_2020_albert.tif',expected_md5='1274285bb18f9b1d443a3cc906b1310c')
    rec.update(record_doi='10.5281/zenodo.8176941',record_version='1.0.2',source_filename='CLCD_v01_2020_albert.tif',note='v01 in filename is preserved; archive record version is 1.0.2. Full original distributed China-wide COG.')
    (folder/'CLCD_v01_2020_albert.metadata.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'complete':'CLCD2020_original','bytes':rec['bytes']},ensure_ascii=False),flush=True)
    return rec

import sys
jobs=[('nasadem',f'n{lat}e{lon}') for lat in [39,40] for lon in [115,116,117]]
jobs += [('stqa',x) for x in ['LC08_L2SP_123032_20200616_02_T1','LC08_L2SP_123032_20200803_02_T1','LC08_L2SP_124032_20200810_02_T1']]
jobs += [('clcd',None)]
if '--only-stqa' in sys.argv:jobs=[x for x in jobs if x[0]=='stqa']
def run(job):
    try:return globals()[job[0]](job[1]) if job[1] else globals()[job[0]]()
    except Exception as e:
        rec={'job':job,'status':'FAILED','error':repr(e)};print(json.dumps(rec,ensure_ascii=False),flush=True);return rec
with ThreadPoolExecutor(3) as pool:results=list(pool.map(run,jobs))
(AUDIT/('219_stqa_downloads.json' if '--only-stqa' in sys.argv else '219_support_downloads.json')).write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':results},ensure_ascii=False,indent=2),encoding='utf-8')
