from pathlib import Path
import numpy as np,pandas as pd
from collections import defaultdict
B=Path(__file__).resolve().parents[1];d=B/'D_阶段分解';src=B.parent/'计算结果与核验'/'01_全区与格网'
fields=['ER6','C_LDI','C_HQI','C_LBI','C_MCR','C_ALLDIST','C_LRI']
x=pd.read_csv(src/'六项逐格逐年原值与得分.csv.gz')
assert len(x)==49258 and not x.duplicated(['grid_id','year']).any()
x=x.set_index(['grid_id','year']).sort_index();w=x['area_km2'].xs(2020,level='year')
g=pd.DataFrame(index=w.index);g['km2']=w;st=[(2015,2019),(2019,2021),(2021,2025)];ss=[];cs=[];sep=[]
for i,(u,v) in enumerate(st):
 a=x[fields].xs(u,level='year');b=x[fields].xs(v,level='year');delta=b-a
 assert np.max(abs(delta.iloc[:,0]-delta.iloc[:,1:].sum(axis=1)))<1e-8
 ss.append(delta/(v-u));g[f'r{i}']=ss[-1]['ER6'];g[f's{i}']=np.select([delta.ER6>1e-10,delta.ER6< -1e-10],['升','降'],default='平')
 for k in fields:cs.append([u,v,k,np.average(delta[k],weights=w),np.average(ss[-1][k],weights=w)])
for i,t in enumerate([2019,2021]):
 delta=ss[i+1]-ss[i];f=f't{t}';g[f]=g[f's{i}']+g[f's{i+1}']
 g[f'D{t}']=delta.ER6;g[f'cont{t}']=delta.ER6*w/w.sum()
 for name,group in g.groupby(f):
  ix=group.index
  row=[t,name,len(ix),sum(w[ix]),sum(w[ix])/sum(w)*100]+[np.average(delta.loc[ix,k],weights=w[ix])*sum(w[ix])/sum(w) for k in fields]
  sep.append(row)
g.index.name='grid_id';g.to_csv(d/'格网阶段与两次转折.csv.gz',encoding='utf-8-sig')
pd.DataFrame(cs,columns=['起年','止年','分项','对全区指数净贡献','折合每年']).to_csv(d/'三个阶段六分项核对.csv',index=False,encoding='utf-8-sig')
z=pd.DataFrame(sep,columns=['年份','格网前后方向','格数','界内面积_km2','面积占比_pct']+fields);z.to_csv(d/'各类地段对全区转折的带符号贡献.csv',encoding='utf-8-sig',index=False)
turn=[] 
for i,t in enumerate([2019,2021]):
 h=ss[i+1]-ss[i];rv={k:np.average(h[k],weights=w) for k in fields};assert abs(rv['ER6']-sum(rv[k] for k in fields[1:]))<1e-11
 turn.append([t,*rv.values()]);print(t,{k:round(v,8) for k,v in rv.items()})
zt=pd.DataFrame(turn,columns=['转折年份']+fields);zt.to_csv(d/'区域两次转折的分解.csv',encoding='utf-8-sig',index=False)
print(z.iloc[:,:6].round(6).to_string(index=False))

