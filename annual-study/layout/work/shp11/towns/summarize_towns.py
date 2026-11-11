from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
w=Path(__file__).resolve().parent
src=w.parent/'core'
sys.path.insert(0,'D:/ER219_work/six_final11/annual')
from six_years import PILOT,policy_layers
keys=['LDI','HQI','LBI','MCR','ALLDIST','LRI']
terms=['ER6','ER_equal',*['C_'+k for k in keys],*keys]
def save(df,name):
    df.to_csv(w/name,index=False,encoding='utf-8-sig',float_format='%.15g')
grid=pd.read_csv(src/'六项格网十年变化.csv')
ann=pd.read_csv(src/'六项逐格逐年原值与得分.csv.gz')
cat=pd.read_csv(w/'town_catalogue.csv',dtype={'town_id':str})[['town_seq','district','town_id','display_name']]
p=pd.read_csv(w/'pieces_full.csv').merge(cat,validate='m:1')
p['km2']=p.poly_area/1e6
cut=p.merge(grid.drop(columns=['iy','ix']),on='grid_id',validate='m:1')
assert abs(cut.km2.sum()-grid.area_km2.sum())<1e-6
dd=p.merge(ann[['grid_id','year',*terms]],on='grid_id',validate='m:m')
def aggregate(df,groups,terms=terms):
    population=df.groupby(groups,sort=True).km2.sum()
    weighted=df[groups].copy()
    weighted[terms]=df[terms].mul(df.km2,axis=0)
    result=weighted.groupby(groups)[terms].sum().div(population,axis=0)
    result.insert(0,'km2',population)
    return result.reset_index()
town=aggregate(dd,['town_seq','year']).merge(cat,validate='m:1')
save(town,'镇街六项逐年指数与分项.csv')
a=town[town.year==2015].set_index('town_seq')
b=town[town.year==2025].set_index('town_seq')
su=a[['display_name','town_id','district','km2']].copy()
su['ER2015']=a.ER6;su['ER2025']=b.ER6;su['delta']=b.ER6-a.ER6
for k in keys:
    su['delta_'+k]=b['C_'+k]-a['C_'+k]
su['decline_pct']=100*cut[cut.delta<0].groupby('town_seq').km2.sum().reindex(su.index).fillna(0)/su.km2
save(su.reset_index(),'镇街六项十年变化.csv')
named=town[~town.town_id.str.startswith('UN_')].copy()
named['group']=np.where(named.display_name.isin(PILOT),'首批六镇','其余具名镇街')
g=aggregate(named,['group','year'])
g=g.merge(named.groupby(['group','year']).town_id.nunique().rename('n_towns'),left_on=['group','year'],right_index=True,validate='1:1')
save(g,'首批六镇与其余镇街逐年指数.csv')
save(aggregate(named,['district','year']),'各区逐年指数与分项.csv')
policy=policy_layers(w,cut)
rows=[]
for k,grp in g.groupby('group'):
    first=grp[grp.year==2015].iloc[0];last=grp[grp.year==2025].iloc[0]
    rec={'group':k,'n_towns':int(first.n_towns),'km2':first.km2,'start':first.ER6,'end':last.ER6,'delta':last.ER6-first.ER6}
    rec.update({'delta_'+key:last['C_'+key]-first['C_'+key] for key in keys})
    rows.append(rec)
(w/'政策组摘要.json').write_text(json.dumps({'groups':rows,'poststrata':policy},ensure_ascii=False,indent=2),'utf8')
np.testing.assert_allclose(su.delta,su[['delta_'+k for k in keys]].sum(axis=1),atol=2e-9)
print('Town aggregates closed:',len(su),su.km2.sum(),rows)
