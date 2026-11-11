from pathlib import Path
import pandas as pd,numpy as np
B=Path(__file__).resolve().parent;d=B.parent.parent;tdir=d/'计算结果与核验'/'02_镇街与案例';gdir=d/'计算结果与核验'/'01_全区与格网';src=d/'高韧性空间因素_2020实证'/'02_过程'
z=pd.read_csv(tdir/'pieces_full.csv',usecols=['grid_id','town_seq','poly_area']).merge(pd.read_csv(tdir/'town_catalogue.csv',usecols=['town_seq','display_name']),on='town_seq');z=z[z.display_name.isin(['宛平城地区','黄村地区','宋庄镇'])].copy();z['w']=z.poly_area/1e6
er=pd.read_csv(gdir/'六项逐格逐年原值与得分.csv.gz',usecols=['grid_id','year','ER6']).pivot(index='grid_id',columns='year',values='ER6')
c=pd.read_csv(src/'年度建设比例_30米等积网格.csv.gz');c=c[(c['product']=='CLCD')&(c.coverage>=.8)].pivot(index='grid_id',columns='year',values='built')
es={}
for y in [2019,2021,2025]:
 yv=pd.read_csv(src/'生态空间'/f'esri_built_{y}.csv').set_index('grid_id');es[y]=yv['built_pct_full'].where(yv.coverage>=.8)
out=[]
for a,b in [(2019,2021),(2021,2025)]:
 p=pd.concat([(er[b]-er[a]).rename('dER'),(c[b]-c[a]).rename('c'),(es[b]-es[a]).rename('e')],axis=1)
 g=z.merge(p,on='grid_id',validate='m:1').dropna();g['mean']=g.w*g.dER
 for eps in (0.005,.01,.02):
  h=g.copy();h['同向']=np.select([(h.c>eps)&(h.e>eps),(h.c< -eps)&(h.e< -eps),(abs(h.c)<=eps)&(abs(h.e)<=eps)],['两产品均增','两产品均减','两产品均小幅变化'],default='其余或不同意')
  for (name,cat),v in h.groupby(['display_name','同向']):
   out.append([name,a,b,100*eps,cat,v.w.sum(),v.w[v.dER< -1e-10].sum()*100/v.w.sum(),sum(v['mean'])/v.w.sum()])
df=pd.DataFrame(out,columns=['镇街','期初','期末','排除微小变化_百分点','建设变化一致性','界内面积_km2','韧性下降面积占组面积_pct','组内加权平均阶段变化']);df.to_csv(B/'三镇街_两套建设用地同时变化与得分对照.csv',encoding='utf-8-sig',index=False);print(df[(df.镇街=='宋庄镇')&(df.期初==2021)&(df.排除微小变化_百分点==1)].round(4).to_string(index=False))

