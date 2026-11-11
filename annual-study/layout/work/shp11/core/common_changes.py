from pathlib import Path
import pandas as pd
from compare_six import OUT,PUB,BASE,CANDS,rho,save

a=pd.read_csv(OUT/'基准及SSI.csv.gz')
c=pd.read_csv(OUT/'候选指标_500m.csv.gz')
g=a.merge(c[['grid_id','year',*[x for x in CANDS if x!='SSI']]],on=['year','grid_id'],validate='one_to_one')
aligned=g[g.groupby('grid_id')[BASE+CANDS].transform('count').eq(11).all(axis=1)]
x=aligned[aligned.year==2015].set_index('grid_id').sort_index()
y=aligned[aligned.year==2025].set_index('grid_id').loc[x.index]
d=y[BASE+CANDS]-x[BASE+CANDS]
assert len(d)>4000
res=[]
for k in CANDS:
    res.append(dict(candidate=k,paired_grids=len(d),paired_km2=x.area_km2.sum(),**{'delta_rho_'+n:rho(d[k],d[n]) for n in BASE}))
save(pd.DataFrame(res),'同一批全期有效格_分项十年变化相关.csv')
