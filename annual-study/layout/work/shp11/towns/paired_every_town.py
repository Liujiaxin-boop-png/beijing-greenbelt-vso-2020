from pathlib import Path
import json,numpy as np,pandas as pd,geopandas as gp, shapely as sh,rasterio as rio,sys
w=Path(__file__).parent;src=Path('D:/ER219_work/annual_actual')
sys.path.insert(0,str(src/'analysis/geo'))
from exactextract import exact_extract
tr=pd.read_csv(w/'镇街格网CLCD2015至2025地类转移_公顷.csv.gz')
su=pd.read_csv(w/'82镇街首末年分型与敏感性.csv')
g=pd.read_csv(w.parent/'core/六项格网十年变化.csv')
info=pd.read_csv(w/'town_catalogue.csv')
for var,k in [('veg',(2,3,4)),('bluegreen',(2,3,4,5,9))]:
    tr[var]=tr.ha*(tr.to.isin(k).astype(int)-tr['from'].isin(k).astype(int))
pieces=tr.groupby(['town_seq','grid_id'],as_index=False)[['veg','bluegreen','ha']].sum()
with rio.open(src/'years/model/CLCD_2015.tif') as ds:
    geo=gp.GeoDataFrame({'grid_id':g.grid_id},geometry=sh.box(500*g.ix,500*g.iy,500*(g.ix+1),500*(g.iy+1)),crs=ds.crs)
    masks=exact_extract(ds,geo,['cell_id','coverage'],include_cols=['grid_id'],output='pandas')
    a=ds.read(1).ravel()
with rio.open(src/'years/model/CLCD_2025.tif') as ds:b=ds.read(1).ravel()
raw=[]
for row in masks.itertuples():
    idx=np.asarray(row.cell_id,int);ha=np.asarray(row.coverage,float)*.09
    r={'grid_id':row.grid_id}
    for key,cl in [('veg',(2,3,4)),('bluegreen',(2,3,4,5,9))]:
        r[key+'_whole']=ha[np.isin(b[idx],cl)].sum()-ha[np.isin(a[idx],cl)].sum()
    raw.append(r)
d=pieces.merge(g[['grid_id','delta_HQI','delta_MCR','delta']],validate='m:1').merge(pd.DataFrame(raw),validate='m:1')
d['both']=(d.delta_HQI>0)&(d.delta_MCR>0)
rows=[]
for seq,sub in d.groupby('town_seq'):
    rr={'town_seq':seq,'n_grids':len(sub),'sample_ha':sub.ha.sum()}
    for var in ('veg','bluegreen'):
        net=(sub[var]>1e-5)&(sub[var+'_whole']>1e-5)
        both=net&sub.both
        rr.update({var+'_gain_n':net.sum(),var+'_coimprove_n':both.sum(),var+'_gain_clipped_ha':sub.loc[net,'ha'].sum(),var+'_coimprove_clipped_ha':sub.loc[both,'ha'].sum(),var+'_gain_ha':sub.loc[net,var].sum(),var+'_coimprove_gain_ha':sub.loc[both,var].sum()})
    rows.append(rr)
s=pd.DataFrame(rows).merge(info,on='town_seq',validate='1:1').merge(su[['town_seq','base_type','delta','delta_HQI','delta_MCR','nominated_1km2']],on='town_seq',how='left',validate='1:1')
s.to_csv(w/'镇街内增绿与质量联系同步格网对照.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
res=s[s.nominated_1km2.eq(True)]
print(res[['display_name','n_grids','veg_gain_n','veg_coimprove_n','bluegreen_gain_n','bluegreen_coimprove_n']].to_string(index=False))
assert set(res.bluegreen_coimprove_n)=={0,4} and res.veg_coimprove_n.sum()==0
print(s[s.veg_coimprove_n>0][['display_name','veg_gain_n','veg_coimprove_n']].sort_values('veg_coimprove_n',ascending=False).head(8).to_string(index=False))
print(s[s.bluegreen_coimprove_n>0][['display_name','bluegreen_gain_n','bluegreen_coimprove_n']].sort_values('bluegreen_coimprove_n',ascending=False).head(8).to_string(index=False))
