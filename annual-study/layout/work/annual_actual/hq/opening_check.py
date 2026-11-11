from pathlib import Path
import json, hashlib, time
import requests
import numpy as np,pandas as pd,geopandas as gpd,shapely
from shapely.geometry import box
from fetch_annual_roads import ROOT,VECTORS,RAW,dump
refs={'京台北京段':'https://jtw.beijing.gov.cn/xxgk/ndzdgz/201912/t20191210_1018028.html','京雄五六环':'https://jtw.beijing.gov.cn/xxgk/xwfbh/202312/t20231228_3516785.html','京雄六环市界':'https://www.beijing.gov.cn/ywdt/gzdt/202303/t20230331_2948699.html'}
dir_=RAW/'通车核查';dir_.mkdir(exist_ok=True)
for key,uri in refs.items():
 path=dir_/(key+'.html')
 if not path.exists():
  try:
   r=requests.get(uri,timeout=18);r.raise_for_status();path.write_bytes(r.content)
  except requests.RequestException as ex:print(key,str(ex)[:100])
g=gpd.read_file(VECTORS/'OSM_major_2025.gpkg');prj=g.crs
samples={}
specs=[('京台北京段','G3',(116.43,39.61,116.59,39.74),2016),('京雄五六环','S3601',(116.1,39.715,116.28,39.77),2023),('京雄六环市界','S3601',(116.1,39.64,116.27,39.676),2022)]
for key,ref,bounds,year in specs:
 corr=g[(g.ref==ref)&(g.highway=='motorway')]
 extent=gpd.GeoSeries([box(*bounds)],crs=4326).to_crs(prj)[0]
 lines=shapely.get_parts(shapely.intersection(corr.geometry.to_numpy(),extent));lines=lines[shapely.get_type_id(lines)==1]
 pts=[]
 for line in lines:
  n=int(line.length//30); 
  for j in range(n):pts.append(line.interpolate((j+.5)*30))
 samples[key]=np.asarray(pts,dtype=object)
rows=[]
for y in range(2015,2026):
 v=gpd.read_file(VECTORS/f'OSM_major_{y}.gpkg')
 idx=shapely.STRtree(v.geometry)
 for key,ref,bounds,opening in specs:
  pts=samples[key];hit=idx.query(pts,predicate='dwithin',distance=60)
  h=np.zeros(len(pts),bool);h[hit[0]]=True
  rows.append(dict(year=y,route=key,opening_year=opening,points=len(h),within_60m=int(h.sum()),fraction=float(h.mean())))
pd.DataFrame(rows).to_csv(ROOT/'官方通车与快照局部空间核验.csv',encoding='utf-8-sig',index=False)
dump(ROOT/'official_road_check_design.json',dict(official_sources=refs,corridors=specs,construction_notice='Opening year comes from the government reference for the named segment. Restricted windows are internal check locations on its 2025 route; statistics are geometry overlap not a binary claim about operating status of an OSM way.',method='Sample lane road centerlines in 2025 every 30 m along selected inner portions. For each annual snapshot match any major road geometry within 60 m (two raster pixels). Nearby co-located/parallel roads detectable before actual opening; labels are not the criterion.'))
print(pd.DataFrame(rows).pivot(index='year',columns='route',values='fraction').round(3).to_string())
