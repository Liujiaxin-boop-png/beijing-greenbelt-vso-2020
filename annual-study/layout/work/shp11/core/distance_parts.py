"""Decompose the regional mean distance into the non-blue-green area fraction and its conditional mean distance."""
from pathlib import Path
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent
candidate=pd.read_csv(here/'候选指标_500m.csv.gz',usecols=['year','ix','iy','grid_id','area_km2','PLAND','ALLDIST'])
assert candidate.ALLDIST.min()>=-1e-7
candidate.loc[candidate.ALLDIST.abs()<1e-7,'ALLDIST']=0.
ss=candidate.ALLDIST.clip(lower=0)
assert ss[candidate.PLAND>1-1e-8].abs().max()<1e-5
rows=[]
for year,g in candidate.groupby('year'):
    cover=np.average(g.PLAND,weights=g.area_km2)
    far=np.average(g.ALLDIST.clip(lower=0),weights=g.area_km2)
    rows.append(dict(year=year,mean_full_grid_blue_green_fraction=cover,
                     nonbluegreen_fraction=1-cover,mean_distance_m=far,
                     conditional_nonbluegreen_distance_m=far/(1-cover)))
d=pd.DataFrame(rows).set_index('year')
pairs=[(2015,2025),(2019,2021),*[(t,t+1) for t in range(2015,2025)]]
results=[]
for t0,t1 in pairs:
    a=d.loc[t0];b=d.loc[t1]
    quantity=(b.nonbluegreen_fraction-a.nonbluegreen_fraction)*(a.conditional_nonbluegreen_distance_m+b.conditional_nonbluegreen_distance_m)/2
    position=(a.nonbluegreen_fraction+b.nonbluegreen_fraction)/2*(b.conditional_nonbluegreen_distance_m-a.conditional_nonbluegreen_distance_m)
    change=b.mean_distance_m-a.mean_distance_m
    assert np.isclose(quantity+position,change,atol=1.e-12)
    results.append(dict(start=t0,end=t1,mean_start_m=a.mean_distance_m,mean_end_m=b.mean_distance_m,
                   change_m=change,nonbluegreen_fraction_component_m=quantity,nonbluegreen_conditional_distance_component_m=position))
d.to_csv(here/'蓝绿空间距离的数量与区位分项_逐年.csv',encoding='utf-8-sig',float_format='%.9g')
pd.DataFrame(results).to_csv(here/'蓝绿空间距离的数量与区位分项_归因.csv',index=False,encoding='utf-8-sig',float_format='%.9g')
print(d.loc[[2015,2025]].to_string());print(results[0])
