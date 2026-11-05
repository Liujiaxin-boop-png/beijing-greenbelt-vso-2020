from pathlib import Path
import requests, json, hashlib, time, datetime
import rasterio
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/'01_原始数据/WorldCover2020官方整幅'
AUDIT=ROOT/'02_过程文件/数据审计'
RAW.mkdir(parents=True,exist_ok=True)

def get_tile(tile):
    name='ESA_WorldCover_10m_2020_v100_'+tile+'_Map.tif'
    url='https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/map/'+name
    dst=RAW/name; part=dst.with_suffix('.tif.partial')
    start=time.time()
    rec={'url':url,'source_page':'https://esa-worldcover.org/en/data-access','tile':tile,'version':'v100','year':2020,'license':'CC-BY-4.0','raw_file':str(dst),'retrieval':'complete original official GeoTIFF bytes; no raster transformation'}
    if not dst.exists():
        with requests.get(url,stream=True,timeout=(20,120)) as r:
            r.raise_for_status(); rec['headers']={k:r.headers.get(k) for k in ['Content-Length','ETag','Last-Modified','Content-Type']}
            with part.open('wb') as f:
                for b in r.iter_content(8*1024*1024):f.write(b)
            if r.headers.get('Content-Length'):assert part.stat().st_size==int(r.headers['Content-Length'])
        part.rename(dst)
    h=hashlib.sha256()
    with dst.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    rec.update(sha256=h.hexdigest(),bytes=dst.stat().st_size,elapsed_seconds=round(time.time()-start,1))
    with rasterio.open(dst) as ds:
        rec.update(crs=str(ds.crs),shape=list(ds.shape),bounds=list(ds.bounds),resolution=list(ds.res),nodata=ds.nodata)
        ds.read(1,window=rasterio.windows.Window(0,0,128,128))
    rec['status']='COMPLETE_ORIGINAL_TILE_DOWNLOADED_AND_OPENED'
    (RAW/(name+'.metadata.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(rec,ensure_ascii=False),flush=True)
    return rec

with ThreadPoolExecutor(2) as pool: results=list(pool.map(get_tile,['N39E114','N39E117']))
(AUDIT/'219_worldcover_original_download.json').write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':results},ensure_ascii=False,indent=2),encoding='utf-8')
