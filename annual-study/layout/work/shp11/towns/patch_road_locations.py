"""Named road landmarks within each mapped patch, recorded in the 2025 OSM snapshot."""
import gzip
import json
from pathlib import Path
import re

import geopandas as gpd
import pandas as pd
import shapely

w=Path(__file__).resolve().parent
f=next(Path('D:/ER219_raw/年度分析_2015_2025/OSM年末主要道路').glob('ohsome_2025*.geojson.gz'))
features=json.load(gzip.open(f,'rt',encoding='utf8'))['features']
roads=gpd.GeoDataFrame.from_features(features,crs='EPSG:4326')
roads=roads.loc[roads.name.notna() & ~roads.highway.astype(str).str.endswith('_link'),['name','highway','@osmId','geometry']].copy()
roads=roads[roads.name.astype(str).str.contains(r'[\u4e00-\u9fff]',regex=True)]
patch=gpd.read_file(w/'case_hotspots.gpkg',layer='patches')
mark=gpd.read_file(w/'case_hotspots.gpkg',layer='markers').set_index('code')
roads=roads.to_crs(patch.crs)
rows=[]
geom_rows=[]
for r in patch.itertuples():
    ids=roads.sindex.query(r.geometry,predicate='intersects')
    if len(ids)==0:continue
    nearby=roads.iloc[ids].copy()
    nearby.geometry=nearby.intersection(r.geometry)
    nearby=nearby[nearby.length>2]
    for name,g in nearby.groupby('name'):
        geo=shapely.union_all(g.geometry.values)
        rows.append({'code':r.code,'road':name,'mapped_line_km':geo.length/1000,'marker_distance_m':mark.loc[r.code].geometry.distance(geo),'osm_ids':'|'.join(map(str,g['@osmId'].tolist()))})
        geom_rows.append({'code':r.code,'road':name,'geometry':geo})
out=pd.DataFrame(rows).sort_values(['code','mapped_line_km'],ascending=[True,False])
out.to_csv(w/'patch_road_landmarks.csv',encoding='utf-8-sig',index=False)
print(out.groupby('code').head(3).drop(columns='osm_ids').round(2).to_string(index=False))
