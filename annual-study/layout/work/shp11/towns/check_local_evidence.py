"""Validate local ER accounting and register independent 2017–2025 built-cover comparisons."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio

w=Path(__file__).resolve().parent
src=Path('D:/ER219_work/annual_actual')
sys.path.insert(0,str(src/'analysis/geo'))
from exactextract import exact_extract

p=gpd.read_file(w/'case_hotspots.gpkg',layer='patches')
sites=pd.read_csv(w/'case_hotspots.csv')
c=pd.read_csv(w/'patch_grid_contributions.csv')
t=pd.read_csv(w/'patch_land_transitions.csv')
v=pd.read_csv(w/'quadrants.csv')
town=pd.read_csv(w/'四类入选镇街指标与增减地段强度.csv')
for grp, sub in v.groupby(['seq','up']):
    expected=town[town.town_seq==grp[0]].iloc[0]
    assert abs(sub.km2.sum()-expected['up_km2' if grp[1] else 'down_km2'])<1e-7
    assert abs(np.average(sub.delta,weights=sub.km2)-expected['up_mean' if grp[1] else 'down_mean'])<1e-7
for r in sites.itertuples():
    co=c[c.code==r.code]
    assert abs(r.area_km2-co.area_km2.sum())<1e-7
    assert abs(r.delta-np.average(co.delta,weights=co.area_km2))<1e-8
    assert abs(r.delta-sum(getattr(r,col) for col in co.columns if col.startswith('delta_')))<1e-9
    assert abs(r.area_km2-t[t.code==r.code].ha.sum()/100)<1e-5

types=['CLCD','Esri']
source_files={
    (a,y): (src/f'years/model/CLCD_{y}.tif' if a=='CLCD' else src/f'product_check/Esri_native_code_on30_{y}.tif')
    for y in [2017,2025] for a in types
}
raster_data={}
for key,fn in source_files.items():
    with rasterio.open(fn) as ds:
        if not raster_data:
            shape,trans,crs=ds.shape,ds.transform,ds.crs
            weights=exact_extract(ds,p,['cell_id','coverage'],include_cols=['code'],output='pandas')
        assert ds.shape==shape and ds.transform==trans and ds.crs==crs
        raster_data[key]=ds.read(1).ravel()
results=[]
for rr in weights.itertuples():
    cells=np.asarray(rr.cell_id,int)
    ha=np.asarray(rr.coverage,float)*0.09
    raw={k:v[cells] for k,v in raster_data.items()}
    valid=np.ones(len(cells),bool)
    for (prod,y),vals in raw.items():
        codes=range(1,10) if prod=='CLCD' else (1,2,4,5,7,8,9,11)
        valid&=np.isin(vals,codes)
    result={'code':rr.code,'valid_ha':ha[valid].sum(),'valid_fraction':ha[valid].sum()/ha.sum()}
    for a in types:
        idx=8 if a=='CLCD' else 7
        for year in [2017,2025]:
            result[f'{a}_{year}']=np.average(raw[a,year][valid]==idx,weights=ha[valid])*100
        result[f'{a}_delta_pp']=result[f'{a}_2025']-result[f'{a}_2017']
    results.append(result)
tcheck=pd.DataFrame(results)
tcheck.to_csv(w/'patch_built_cover_comparison_2017_2025.csv',index=False,encoding='utf-8-sig')
print(tcheck.round(3).to_string(index=False))
print('All patch sums, sign-region quadrant sums and component sums checked.')
