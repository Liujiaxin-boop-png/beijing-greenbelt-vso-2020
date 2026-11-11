# -*- coding: utf-8 -*-
"""Area-weighted township comparison for all named townships within the author-supplied planning boundary."""
from pathlib import Path
import json, hashlib
import pandas as pd
import numpy as np
w=Path(__file__).resolve().parent
src=w.parent/'core'
geo=w
town=pd.read_csv(w/'镇街六项十年变化.csv',dtype={'town_id':str})
grid=pd.read_csv(src/'六项格网十年变化.csv')
ann=pd.read_csv(src/'六项逐格逐年原值与得分.csv.gz')
tann=pd.read_csv(w/'镇街六项逐年指数与分项.csv',dtype={'town_id':str})
# Restrict on the same fixed named administrative units with non-zero assignable intersections as the source analysis.
bad=town[town.town_id.str.startswith('UN_')]; town=town[~town.town_id.str.startswith('UN_')].copy()
assert len(town)==town.town_id.nunique()==82
yr=range(2015,2026)
eq=ann.pivot(index='grid_id',columns='year',values='ER_equal')
grid=grid.merge((eq[2025]-eq[2015]).rename('delta_equal'),left_on='grid_id',right_index=True,validate='1:1')
a=tann[tann.town_id.isin(town.town_id)].pivot(index='town_id',columns='year',values='ER6')
newtrend=pd.Series(np.median(np.stack([(a[j]-a[i])/(j-i) for i in yr for j in yr if j>i]),axis=0),index=a.index,name='town_sen')
town=town.merge(newtrend,left_on='town_id',right_index=True,validate='1:1')
def classify(change,share):
 if pd.isna(change) or pd.isna(share):return '无有效面积'
 if np.isclose(change,0,rtol=0,atol=1e-14) or np.isclose(share,50,rtol=0,atol=1e-9):return '界值'
 return ('A' if share>50 else 'D') if change<0 else ('C' if share>50 else 'B')
pieces={}
for domain in ['full','interior','common']:
 pieces[domain]=pd.read_csv(geo/f'pieces_{domain}.csv').groupby(['town_seq','ix','iy'],as_index=False).poly_area.sum().merge(grid,on=['ix','iy'],validate='m:1')
 pieces[domain]['km2_piece']=pieces[domain].poly_area/1e6
def summary(df):
 v=df.delta; ar=df.km2_piece; tot=ar.sum()
 neg=v<0; pos=v>0; z=v==0
 down=ar[neg].sum(); up=ar[pos].sum()
 rows={'effective_km2':tot,'count_clipped_cells':len(df),'area_effective_n':tot**2/(ar**2).sum(),
 'down_km2':down,'up_km2':up,'unchanged_km2':ar[z].sum(),'down_share':100*down/tot,
 'down_mean':(ar[neg]*v[neg]).sum()/down if down else np.nan,'up_mean':(ar[pos]*v[pos]).sum()/up if up else np.nan,
 'delta_rebuilt':np.average(v,weights=ar),'sen_down_pct':100*ar[df.Sen<0].sum()/tot,
 'eq_down_pct':100*ar[df.delta_equal<0].sum()/tot,'eq_delta':np.average(df.delta_equal,weights=ar)}
 for i in ['LDI','HQI','LBI','MCR','ALLDIST','LRI']:
  for name,mask in [('up',pos),('down',neg)]:
   rows[f'{name}_C_{i}']=np.average(df.loc[mask,'delta_'+i],weights=ar[mask]) if mask.any() else np.nan
 return rows
def allsummary(domain):
 return pd.DataFrame([{'town_seq':seq,**summary(g)} for seq,g in pieces[domain].groupby('town_seq')])
town=town.merge(allsummary('full'),on='town_seq',validate='1:1')
small=allsummary('interior')[['town_seq','effective_km2','delta_rebuilt','down_share']].rename(columns={'effective_km2':'inner_km2','delta_rebuilt':'inner_delta','down_share':'inner_down_pct'})
town=town.merge(small,on='town_seq',how='left',validate='1:1');town.inner_km2=town.inner_km2.fillna(0)
for ref,new in [('km2','effective_km2'),('delta','delta_rebuilt'),('decline_pct','down_share')]:
 np.testing.assert_allclose(town[new],town[ref],rtol=1e-8,atol=2e-8)
assert town.unchanged_km2.sum() < 1e-8 # exact zeros checked before application of complementary shares
town['base_type']=[classify(a,b) for a,b in zip(town.delta,town.down_share)]
for p,c,s in [('inner','inner_delta','inner_down_pct'),('equal','eq_delta','eq_down_pct'),('sen','town_sen','sen_down_pct')]:
 town[p+'_type']=[classify(a,b) for a,b in zip(town[c],town[s])]
commons=allsummary('common')[['town_seq','effective_km2','delta_rebuilt','down_share']].rename(columns={'effective_km2':'common_km2','delta_rebuilt':'common_delta','down_share':'common_down_pct'})
town=town.merge(commons,on='town_seq',how='left',validate='1:1')
town['common_type']=[classify(u,v) for u,v in zip(town.common_delta,town.common_down_pct)]
town['rank_distance']=np.nan
for k,g in town.groupby('base_type'):
 n=len(g);r1=(g.delta.rank(method='average')-.5)/n;r2=(g.down_share.rank(method='average')-.5)/n
 town.loc[g.index,'rank_distance']=np.sqrt((r1-.5)**2+(r2-.5)**2)
town['rank_distance_12d']=town.rank_distance.round(12)
town['rank_in_type']=town.sort_values(['rank_distance_12d','km2'],ascending=[True,False]).groupby('base_type').cumcount()+1
town['nominated_1km2']=False
summ={};picked={}
for k,g in town.groupby('base_type'):
 g=g.sort_values(['rank_distance_12d','km2'],ascending=[True,False]);nom=g[g.km2>=1].iloc[0]
 town.loc[nom.name,'nominated_1km2']=True
 record=dict(n=len(g),km2=g.km2.sum(),area_pct_named=100*g.km2.sum()/town.km2.sum(),n_ge1=(g.km2>=1).sum(),n_ge2=(g.km2>=2).sum(),
 candidates_ge1=[dict(name=r.display_name,km2=r.km2,distance=r.rank_distance) for r in g[g.km2>=1].head(3).itertuples()],
 selected={str(c):g[g.km2>=c].iloc[0].display_name for c in [0,1,2]},list=g.display_name.tolist())
 summ[k]=record;picked[k]=nom.display_name
def write(f,x):x.to_csv(w/f,index=False,encoding='utf-8-sig',float_format='%.12g')
write('82镇街首末年分型与敏感性.csv',town.sort_values(['base_type','rank_in_type']))
sels=town[town.nominated_1km2].sort_values('base_type');write('四类入选镇街指标与增减地段强度.csv',sels)
write('四类入选镇街十一期指数与贡献.csv',tann[tann.town_id.isin(sels.town_id)].sort_values(['town_id','year']))
def tov(obj):
 if isinstance(obj,np.integer):return int(obj)
 if isinstance(obj,np.floating):return float(obj)
 if isinstance(obj,np.bool_):return bool(obj)
 raise TypeError(type(obj))
x={'definition':{'A':'镇均下降、下降面积过半','B':'镇均上升、上升面积过半','C':'镇均上升、下降面积过半','D':'镇均下降、上升面积过半'},'groups':summ,
'named_area':town.km2.sum(),'unassigned_area':bad.km2.sum(),'unstable_band_45_55':town[town.down_share.between(45,55)][['display_name','down_share']].to_dict('records'),
'common_n_valid':int((town.common_km2>0).sum()),'common_match':int((town.common_type==town.base_type).sum()),'inner_n_valid':int((town.inner_km2>0).sum()),'inner_match':int((town.inner_type==town.base_type).sum()),'equal_match':int((town.equal_type==town.base_type).sum()),'sen_match':int((town.sen_type==town.base_type).sum()),
'source_path_hash':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [src/'六项格网十年变化.csv',src/'六项逐格逐年原值与得分.csv.gz',w/'镇街六项十年变化.csv',w/'镇街六项逐年指数与分项.csv',geo/'pieces_full.csv',geo/'pieces_interior.csv']}}
(w/'全域分型摘要.json').write_text(json.dumps(x,default=tov,ensure_ascii=False,indent=2),'utf8')
print('group',[(k,s['n'],float(s['km2'])) for k,s in summ.items()]);print('stable',[(k,v) for k,v in x.items() if k.endswith(('match','valid'))])
print(sels[['display_name','down_km2','up_km2','down_mean','up_mean','inner_km2','inner_delta','inner_down_pct','inner_type','eq_delta','eq_down_pct','equal_type','town_sen','sen_down_pct','sen_type','count_clipped_cells','area_effective_n']].round(6).to_string(index=False))
print(sels[['display_name','delta_LDI','delta_HQI','delta_LBI','delta_MCR','delta_ALLDIST','delta_LRI']].round(6).to_string(index=False))
print(((a.loc[sels.town_id]).round(5)).to_string())

