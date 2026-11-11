from pathlib import Path
import pandas as pd,numpy as np,geopandas as gp,shapely,exactextract as ex,rasterio
B=Path(__file__).resolve().parent;d=B.parent.parent;tdir=d/'计算结果与核验'/'02_镇街与案例';gdir=d/'计算结果与核验'/'01_全区与格网';src=d/'高韧性空间因素_2020实证'/'02_过程'/'生态空间'
town=gp.read_file(tdir/'planning_towns.gpkg',layer='towns');town=town[town.display_name.isin(['黄村地区','宛平城地区','宋庄镇'])].copy();town['unit']=town.display_name
grid=gp.read_file(gdir/'annual_grid_500.gpkg',layer='grid500');ids=['500_1890_8661','500_1890_8662','500_1955_8706'];grid=grid[grid.grid_id.isin(ids)].copy();grid['unit']=grid.grid_id;grid.geometry=shapely.box(grid.ix*500,grid.iy*500,(grid.ix+1)*500,(grid.iy+1)*500)
geo=pd.concat([town[['unit','geometry']],grid[['unit','geometry']]],ignore_index=True);geo['ha']=geo.area/1e4;geo.geometry=geo.geometry.segmentize(25)
rows=[]
for y in [2017,2019,2020,2021,2025]:
 f=src/f'Esri{y}_mosaic.tif'
 with rasterio.open(f) as r: crs=r.crs;pixel_area=abs(r.transform.a*r.transform.e)
 v=geo.to_crs(crs);t=ex.exact_extract(str(f),v,['unique','frac','count'],include_cols=['unit'],output='pandas');t=t.merge(pd.DataFrame({'unit':v.unit,'utm_ha':v.area/1e4,'ha':v.ha}),on='unit')
 for rr in t.itertuples():
  fr=dict(zip(rr.unique,rr.frac)); frac=rr.count*pixel_area/1e4/rr.utm_ha;assert abs(frac-1)<.002,(y,rr.unit,frac);frac=min(1.,frac)
  rows.append([rr.unit,y,'Esri 10 m',rr.ha,frac*100,rr.ha*frac*fr.get(1,0.),rr.ha*frac*fr.get(7,0.)])
ct=pd.read_csv(tdir/'全镇街CLCD逐年地类面积_公顷.csv');ct=ct[ct.display_name.isin(town.unit)]
for _,r in ct.iterrows():rows.append([r['display_name'],r['year'],'CLCD 30 m',r['area_ha'],100.,r['水体'],r['不透水面']])
cg=pd.read_csv(d/'计算结果与核验'/'03_检验与溯源'/'02_指标和底图检验'/'宋庄及两永定河格网逐年水面复核.csv');cg=cg[cg['product']=='CLCD']
for rr in cg.itertuples():rows.append([rr.grid_id,rr.year,'CLCD 30 m',25.,min(100.,rr.valid_ha/25*100),rr.water_ha,np.nan])
z=pd.DataFrame(rows,columns=['位置','年','土地覆盖产品','界内面积或完整格面积_ha','有效覆盖率_pct','水面面积_ha','建成或不透水面_ha']);z.to_csv(B/'贡献较大镇街与三个复核格_两产品分期水面.csv',index=False,encoding='utf-8-sig')
print(z[z.年.isin([2019,2021,2025])].pivot(index=['位置','年'],columns='土地覆盖产品',values='水面面积_ha').round(2).to_string())
print(z[z.年.isin([2019,2021,2025])].pivot(index=['位置','年'],columns='土地覆盖产品',values='建成或不透水面_ha').round(2).to_string())

