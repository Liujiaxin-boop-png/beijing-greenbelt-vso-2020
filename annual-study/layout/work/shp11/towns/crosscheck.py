from pathlib import Path
import sys,json,gzip
import pandas as pd, numpy as np, geopandas as gp, shapely, rasterio
from shapely.geometry import box
out=Path(__file__).resolve().parent
base=Path('D:/ER219_work/annual_actual')
sys.path.insert(0,str(base/'analysis/geo'))
from exactextract import exact_extract
grid=pd.read_csv(out.parent/'core/六项格网十年变化.csv')
towns=gp.read_file(out/'planning_towns.gpkg',layer='towns')
pieces=pd.read_csv(out/'pieces_full.csv').drop(columns='grid_id')
sels=pd.read_csv(out/'四类入选镇街指标与增减地段强度.csv')
names={r.town_seq:{'长辛店镇':'原长辛店镇'}.get(r.display_name,r.display_name) for r in sels.itertuples()}
g=pieces[pieces.town_seq.isin(names)].merge(grid,on=['ix','iy'],validate='m:1')
full=shapely.box(g.ix*500,g.iy*500,(g.ix+1)*500,(g.iy+1)*500)
def subset(geom):
    return gp.GeoDataFrame({'id':np.arange(len(g)),'geometry':geom},crs=towns.crs)
cuts=subset(shapely.intersection(full,towns.geometry.values[g.town_seq.to_numpy()]))
whole=subset(full)
g['town']=g.town_seq.map(names)
g['full_inside']=cuts.area/250000
assert np.allclose(cuts.area,g.poly_area)
g['km2']=cuts.area/1e6
g.reset_index(drop=True,inplace=True)
for domain,geo in [('cut',cuts),('whole',whole)]:
    arrays={}
    for yy in [2015,2025]:
        with rasterio.open(base/f'years/model/CLCD_{yy}.tif') as ds:
            if not arrays: ex=exact_extract(ds,geo,['cell_id','coverage'],include_cols=['id'],output='pandas')
            arrays[yy]=ds.read(1).ravel()
    for row in ex.itertuples():
        cells=np.array(row.cell_id,int);wt=np.array(row.coverage)*0.09
        a,b=arrays[2015][cells],arrays[2025][cells]
        assert np.isin(np.r_[a,b],range(1,10)).all()
        for k,v in [('veg',(2,3,4)),('forest',(2,3)),('bg',(2,3,4,5,9)),('built',(8,)),('water',(5,9))]:
            x=np.isin(a,v);y=np.isin(b,v)
            g.loc[int(row.id),f'{domain}_{k}_ha']=np.sum(wt*y)-np.sum(wt*x)
        g.loc[int(row.id),f'{domain}_crop_to_forest_ha']=np.sum(wt[((a==1)&(b==2))])
assert len(g)==len(cuts) and g['cut_bg_ha'].notna().all()
g['same']=(g.delta_HQI>0)&(g.delta_MCR>0)
g['net_green']=(g.cut_veg_ha>1e-5)&(g.whole_veg_ha>1e-5)
g['net_bluegreen']=(g.cut_bg_ha>1e-5)&(g.whole_bg_ha>1e-5)
g['grid100']=(g.full_inside>0.99999)
g['positive_er']=g.delta>0
g['large_green']=(g.cut_veg_ha>=.9)
geo=cuts.copy()
hot=gp.read_file(out/'case_hotspots.gpkg',layer='patches')
roads_file=next(Path('D:/ER219_raw/年度分析_2015_2025/OSM年末主要道路').glob('ohsome_2025*.geojson.gz'))
roads=gp.GeoDataFrame.from_features(json.load(gzip.open(roads_file,'rt',encoding='utf-8'))['features'],crs='EPSG:4326').to_crs(towns.crs)
roads=roads.loc[roads.name.notna() & ~roads.highway.astype(str).str.endswith('_link') & roads.name.astype(str).str.contains(r'[\u4e00-\u9fff]',regex=True)]
for i,c in geo.iterrows():
    town=towns.geometry.iloc[int(g.loc[i,'town_seq'])]
    p=c.geometry.representative_point();xmin,ymin,xmax,ymax=town.bounds
    g.loc[i,'quad']=('西' if p.x<(xmin+xmax)/2 else '东')+('北' if p.y>(ymin+ymax)/2 else '南')
    h=hot[hot.seq==g.loc[i,'town_seq']].copy()
    dist=h.distance(p)
    g.loc[i,'patch']=h.loc[dist.idxmin(),'code'];g.loc[i,'patch_dist_m']=dist.min()
    dis=roads.distance(p)
    g.loc[i,'near_road']=roads.loc[dis.idxmin(),'name']
    g.loc[i,'road_centre_m']=dis.min()
    record=g.loc[i]
    g.loc[i,'near_road_intersects']=c.geometry.intersects(roads.loc[dis.idxmin(),'geometry'])
cols=['town','grid_id','quad','patch','patch_dist_m','near_road','road_centre_m','near_road_intersects','full_inside','km2','delta','delta_HQI','delta_MCR','delta_LRI','delta_LDI','delta_LBI','delta_ALLDIST','net_green','same','positive_er','grid100','cut_veg_ha','whole_veg_ha','cut_bg_ha','whole_bg_ha','cut_forest_ha','cut_built_ha','cut_water_ha','cut_crop_to_forest_ha']
g[cols].to_csv(out/'四镇每格蓝绿面积净变与两项条件.csv',index=False,encoding='utf-8-sig')
print(g.groupby('town').agg(total=('grid_id','size'),ngreen=('net_green','sum'),same=('same','sum')))
v=g[g.same & (g.net_green | g.net_bluegreen)]
print(v[cols[:14]+cols[-8:]].round(5).to_string(index=False))
print('any green by HQ and contact direction')
print(g[g.net_green].groupby(['town',g.delta_HQI>0,g.delta_MCR>0]).agg(n=('grid_id','size'),area=('km2','sum'),netveg=('cut_veg_ha','sum')))
