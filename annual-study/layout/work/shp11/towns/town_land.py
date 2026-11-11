from pathlib import Path
import pandas as pd, numpy as np, geopandas as gp, rasterio as rio, sys,json
w=Path(__file__).resolve().parent
src=Path('D:/ER219_work/annual_actual')
sys.path.insert(0,str(src/'analysis/geo'))
from exactextract import exact_extract
towns=gp.read_file(w/'planning_towns.gpkg',layer='towns')
def save(df,f): df.to_csv(w/f,index=False,encoding='utf-8-sig',float_format='%.12g')
def read(name):
    with rio.open(name) as ds:return ds.read(1).ravel(),ds.shape,ds.transform
layers={}; namelist=['缺失','耕地','林地','灌丛','草地','水体','冰雪','裸地','不透水面','湿地']
with rio.open(src/'years/model/CLCD_2015.tif') as ds:
    cells=exact_extract(ds,towns,['cell_id','coverage'],include_cols=['town_seq'],output='pandas')
    shape=ds.shape;aff=ds.transform;assert abs(aff.a*aff.e)==900
for year in range(2015,2026):
    layers['CLCD',year],s,t=read(src/f'years/model/CLCD_{year}.tif'); assert s==shape and t==aff
for y in (2017,2025):
    layers['Esri',y],s,t=read(src/f'product_check/Esri_native_code_on30_{y}.tif');assert s==shape and t==aff
yearrows=[];tran=[];prod=[];changes=[]
for rr in cells.itertuples():
    town=towns.iloc[rr.town_seq]; assert town.town_seq==rr.town_seq
    ar=np.asarray(rr.coverage,'float64')*.09; idx=np.asarray(rr.cell_id,int)
    # Tiny territories may intersect a subpixel in less than single-precision geometric tolerance.
    assert abs(ar.sum()-town.area_km2*100)<.01,(rr.town_seq,ar.sum(),town.area_km2*100)
    info={'town_seq':rr.town_seq,'display_name':town.display_name,'town_id':town.town_id}
    if not len(idx) or not ar.sum():
        continue
    for year in range(2015,2026):
        v=layers['CLCD',year][idx]
        assert np.isin(v,range(1,10)).all()
        areas=np.bincount(v,weights=ar,minlength=10);row={**info,'year':year,'area_ha':ar.sum()}
        for i in range(1,10): row[namelist[i]]=areas[i]
        row['林灌草']=sum(areas[[2,3,4]]);row['水湿']=sum(areas[[5,9]]);row['蓝绿']=sum(areas[[2,3,4,5,9]])
        yearrows.append(row)
    a=layers['CLCD',2015][idx].astype(int);b=layers['CLCD',2025][idx].astype(int)
    mat=np.bincount(a*10+b,weights=ar,minlength=100).reshape(10,10)
    for i,j in zip(*np.nonzero(mat)):
        tran.append({**info,'from':namelist[i],'to':namelist[j],'ha':mat[i,j]})
    vals={k:v[idx] for k,v in layers.items() if k[1] in (2017,2025)}
    valid=np.ones(len(ar),bool)
    for (p,y),v in vals.items():valid&=np.isin(v,range(1,10) if p=='CLCD' else [1,2,4,5,7,8,9,11])
    row={**info,'valid_ha':ar[valid].sum(),'valid_fraction':ar[valid].sum()/ar.sum()}
    for p in ('CLCD','Esri'):
        for cls,codes in [('built',(8,) if p=='CLCD' else (7,)),('wood',(2,3) if p=='CLCD' else (2,)),('water',(5,9) if p=='CLCD' else (1,4))]:
            for y in (2017,2025):row[f'{p}_{cls}_{y}']=100*np.average(np.isin(vals[p,y][valid],codes),weights=ar[valid]) if ar[valid].sum() else np.nan
            row[f'{p}_{cls}_delta_pp']=row[f'{p}_{cls}_2025']-row[f'{p}_{cls}_2017']
    prod.append(row)
rows=pd.DataFrame(yearrows)
save(rows,'全镇街CLCD逐年地类面积_公顷.csv');save(pd.DataFrame(tran),'全镇街2015至2025地类转移面积_公顷.csv');save(pd.DataFrame(prod),'全镇街两套产品2017至2025建成林木水湿变化.csv')
print(len(prod),len(rows),len(tran))
