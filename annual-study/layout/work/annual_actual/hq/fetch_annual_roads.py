import concurrent.futures, datetime, gzip, json, hashlib, os, pathlib, time
import geopandas as gpd
import pandas as pd
import requests
import shapely
from shapely.geometry import shape
import rasterio
ROOT=pathlib.Path(os.environ.get('ER219_ANNUAL_WORK','D:/ER219_work/annual_actual'))/'hq'
ROOT.mkdir(parents=True,exist_ok=True)
RAW=pathlib.Path(r'D:\ER219_raw\年度分析_2015_2025\OSM年末主要道路')
RAW.mkdir(parents=True,exist_ok=True)
VECTORS=ROOT/'vectors'; VECTORS.mkdir(exist_ok=True)
URL='https://api.ohsome.org/v1'
BBOX='115.54,39.24,117.31,40.61'
TAGS=['motorway','trunk','primary','motorway_link','trunk_link','primary_link']
FILTER='type:way and highway in ('+','.join(TAGS)+')'
def dump(path,o):
 tmp=path.with_suffix('.new')
 tmp.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding='utf-8')
 os.replace(tmp,path)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for k in iter(lambda:f.read(1<<20),b''):h.update(k)
 return h.hexdigest()
def request(endpoint,p,save=None):
 for i in range(4):
  try:
   with requests.get(URL+endpoint,params=p,timeout=(20,150),stream=True,headers={'User-Agent':'academic-spatial-analysis/1.0','Accept':'application/geo+json, application/json','Accept-Encoding':'gzip'}) as r:
    r.raise_for_status()
    if not save:return r.json()
    temp=save.with_suffix('.part')
    with gzip.open(temp,'wb',compresslevel=3) as out:
     for b in r.iter_content(262144):
      if b:out.write(b)
    with gzip.open(temp,'rb') as f:
     j=json.load(f)
    assert isinstance(j.get('features'),list) and j['features']
    os.replace(temp,save)
    return j
  except Exception as ex:
   print('download retry',endpoint,i,str(ex)[:300],flush=True)
   if i==3: raise
   time.sleep(3+i*3)
def annual(year):
 moment=f'{year}-12-31T15:59:59Z'
 params=dict(bboxes=BBOX,time=f'{year}-12-31T15:59:58Z,{year}-12-31T16:00:00Z',filter=FILTER,properties='tags,metadata')
 raw=RAW/f'ohsome_{year}_Beijing_clock_235959.geojson.gz'
 vp=VECTORS/f'OSM_major_{year}.gpkg'
 rec=RAW/f'ohsome_{year}_provenance.json'
 if vp.exists() and rec.exists():
  return json.loads(rec.read_text(encoding='utf8'))
 if raw.exists():
  with gzip.open(raw,'rb') as f:j=json.load(f)
 else:
  print('fetch',year,flush=True);j=request('/elementsFullHistory/geometry',params,raw)
 count=request('/elements/count',dict(bboxes=BBOX,time=moment,filter=FILTER))
 expected=int(count['result'][0]['value'])
 assert count['result'][0]['timestamp']==moment
 rows=[]
 for feat in j['features']:
  a=feat['properties']
  if not (a['@validFrom']<=moment<a['@validTo']):continue
  assert a['highway'] in TAGS
  geom=shape(feat['geometry'])
  if geom.geom_type not in ('LineString','MultiLineString'):continue
  if geom.is_empty or geom.length==0:continue
  row={k:str(a[k]) if k in a else None for k in ['highway','name','name:zh','ref','opening_date','start_date','bridge','tunnel','source','source:date']}
  row.update(osm_id=a['@osmId'],version=a.get('@version'),geometry=geom)
  rows.append(row)
 gf=gpd.GeoDataFrame(rows,crs=4326); assert len(gf.osm_id.unique())==len(gf)
 # Full AOI may include a tangency whose clipped geometry is a point; log any count mismatch.
 assert abs(len(gf)-expected)<=max(5,expected*.0002),(year,len(gf),expected)
 gf=gf.rename(columns={'name:zh':'name_zh','source:date':'source_date'})
 with rasterio.open(r'D:\ER219_work\spatial\clcd2020.tif') as r:
  gfp=gf.to_crs(r.crs)
 gfp.to_file(vp,layer='major_roads',driver='GPKG',engine='pyogrio')
 prov=dict(year=year,snapshot_local=f'{year}-12-31T23:59:59+08:00',snapshot_utc=moment,
    source=URL+'/elementsFullHistory/geometry',method='GET',parameters=params,licence='© OpenStreetMap contributors, ODbL 1.0; extraction: HeiGIT ohsome API',
    validity='validFrom<=snapshot<validTo; 2-second request interval around snapshot; properties trimmed to specified timestamp.',
    extract_version=j.get('apiVersion'),count_endpoint=URL+'/elements/count',independent_count=expected,unique_line_features=len(gfp),linear_exclusions=expected-len(gfp),
    full_download_sha256=sha(raw),full_download=raw.name,raw_file_bytes=raw.stat().st_size,vector=str(vp),vector_sha256=sha(vp),classes=gfp.highway.value_counts().to_dict(),
    mapped_km_whole_bbox=float(gfp.length.sum()/1000),tagged_opening_date=int(gfp.opening_date.notna().sum()),tagged_start_date=int(gfp.start_date.notna().sum()))
 dump(rec,prov)
 print('DONE',year,expected,len(gfp),round(prov['mapped_km_whole_bbox']),flush=True)
 return prov
def main():
 dump(RAW/'api_metadata.json',request('/metadata',{}))
 with concurrent.futures.ThreadPoolExecutor(2) as ex:
  results=list(ex.map(annual,range(2015,2026)))
 dump(ROOT/'roads_download_manifest.json',results)
if __name__=='__main__':main()