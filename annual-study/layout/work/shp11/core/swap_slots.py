"""Swap one component at a time; every model has six components. On like-for-like samples use satellite greenness as an external check."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
out=Path(__file__).resolve().parent
sys.path.insert(0,str(out.parent/'selection'))
from compare_six import fit,paired_boot
from inspect import signature

key=['ix','iy'];R=Path(r'D:/ER219_results/年度评价_2015_2025/格网与尺度')
raw=pd.read_csv(out/'基准及SSI.csv.gz').query('year==2020').copy()
old_vars=['NTL','HQ_H','CLUMPY','MCR','SSI','E_fraction']
old=pd.read_csv(out/'old_scores.csv',usecols=key+['habitat']+old_vars).rename(columns={a:'old_'+a for a in old_vars})
more=pd.read_csv(out/'候选指标_500m.csv.gz',usecols=key+['year','ALLDIST']).query('year==2020')
ndvi=pd.read_csv(out/'ndvi500.csv',usecols=key+['ndvi','valid_fraction'])
merged=raw.merge(more[key+['ALLDIST']],on=key,validate='one_to_one').merge(ndvi,on=key,validate='one_to_one')
core=['LDI','HQI','LBI','MCR','ALLDIST','LRI']
signs=[1,1,-1,-1,-1,1];old_signs=[-1,1,1,-1,-1,1]
allrows=[]
for habitat in ['forest_shrub','grassland']:
    group=merged.merge(old[old.habitat==habitat],on=key,validate='one_to_one').dropna(subset=core+['old_'+a for a in old_vars])
    observed=group[group.valid_fraction.ge(.8) & group.ndvi.notna()].copy()
    fields={'annual_six':(core,signs),'second_six':(['old_'+a for a in old_vars],old_signs)}
    for idx,(old_name,new_name) in enumerate(zip(old_vars,core)):
        v=core.copy();sg=signs.copy();v[idx]='old_'+old_name;sg[idx]=old_signs[idx]
        fields[f'{new_name}_to_{old_name}']=(v,sg)
    values={}
    for k,(v,sg) in fields.items():
        score,_=fit(group,v,sign=sg)
        values[k]=score(observed)
    for result in paired_boot(observed,values,0):
        result.update(habitat=habitat,training_n=len(group))
        allrows.append(result)
pd.DataFrame(allrows).to_csv(out/'2020六指标逐项替换_独立夏季绿度.csv',index=False,encoding='utf-8-sig')
print(pd.DataFrame(allrows).round(4).to_string(index=False))
