# -*- coding: utf-8 -*-
"""同年、同年段：同期变化与韧性变化的空间关系；固定分组，面积和空间区块校验。"""
from pathlib import Path
import json,numpy as np,pandas as pd
from scipy.stats import spearmanr
D=Path(__file__).resolve().parent;B=D.parents[1];P=B/'高韧性空间因素_2020实证'/'02_过程';E=P/'生态空间';H=P/'人类活动'
T=[2015,2019,2021,2025];ts=list(zip(T[:-1],T[1:]));facs=['建设比例','植被绿度','夜光','人口密度'];tw=['2015–2019','2019–2021','2021–2025'];aw=['2019转折','2021转折']
a=pd.read_csv(B/'计算结果与核验'/'01_全区与格网'/'六项逐格逐年原值与得分.csv.gz',usecols=['year','grid_id','ix','iy','area_km2','ER6']);y=a.pivot(index='grid_id',columns='year',values='ER6')
g=a[a.year==2020].set_index('grid_id')[['area_km2','ix','iy']].loc[y.index]
ww=g.area_km2; assert len(ww)==4478 and g.index.is_unique
wc=pd.read_csv(E/'worldcover500.csv').set_index('grid_id')
dry=wc['water_full']+wc['wetland_full']<=.5
year_data={j:{} for j in facs};cover={}
for t in T:
 p=E/('ndvi_main_'+str(t)+'.csv');v=pd.read_csv(p).set_index('grid_id');cover[t]=v.coverage
 year_data['植被绿度'][t]=v.ndvi.where(dry & (v.coverage>=.8))
 p=E/('esri_built_'+str(t)+'.csv'); 
 if p.exists():
  v=pd.read_csv(p).set_index('grid_id');year_data['建设比例'][t]=100*v.built_pct_full.where(v.coverage>=.8)
 p=H/('pop_'+str(t)+'_grid500.csv');v=pd.read_csv(p).set_index('grid_id');year_data['人口密度'][t]=v.pop_density
nt=pd.read_csv(next((P/'跨年夜光').glob('OpenGeoHub_逐年500米夜光*.csv')))
for t,v in nt.groupby('year'):year_data['夜光'][t]=v.set_index('grid_id').ntl_oghub
stage=[]
for n,(t,u) in enumerate(ts):
 df=g.copy();df['Y']=((y[u]-y[t])/(u-t));df['时期']=tw[n]
 for j in facs:df[j]=(year_data[j][u]-year_data[j][t])/(u-t) if t in year_data[j] and u in year_data[j] else np.nan
 df['NDVI两端面积完整']=((cover[t]>=.999999)&(cover[u]>=.999999));stage.append(df)
turn=[]
for n in range(2):
 df=g.copy();df['时期']=aw[n]
 for j in ['Y']+facs:df[j]=stage[n+1][j]-stage[n][j]
 df['NDVI两端面积完整']=stage[n+1]['NDVI两端面积完整'] & stage[n]['NDVI两端面积完整'];turn.append(df)
def write(t,name):t.to_csv(D/(name+'.csv'),index=False,encoding='utf-8-sig',float_format='%.11g')
pd.concat(stage).reset_index().to_csv(D/'三个阶段的年均变化量_逐格.csv.gz',encoding='utf-8-sig',index=False)
pd.concat(turn).reset_index().to_csv(D/'两个转折的变化率差_逐格.csv.gz',encoding='utf-8-sig',index=False)
def wc(x,w,p):
 idx=np.argsort(x,kind='stable');s=np.cumsum(w[idx]);return x[idx][min(np.searchsorted(s,p*s[-1]),len(s)-1)]
r=[];gr=[];defs=[];sens=[];qc=[];inter=[]
def cgrp(x,c):return np.where(x< -c,0,np.where(x>c,2,1))
def design(j,frames,p):
 l=[];w=[]
 for f in frames:
  f=f.dropna(subset=[j]);v=f[j].to_numpy()
  if len(v): l.append(np.abs(v));k=f.area_km2.to_numpy();w.append(k/k.sum())
 return wc(np.concatenate(l),np.concatenate(w),p) if l else np.nan
def mean(y,w):return np.dot(y,w)/sum(w)
def stat(y,w,cl):
 u=mean(y,w);ss=np.bincount(cl,weights=w,minlength=3);sy=np.bincount(cl,weights=w*y,minlength=3)
 mu=np.divide(sy,ss,out=np.full_like(ss,np.nan),where=ss>0)
 return np.maximum(0,1-sum(w*(y-mu[cl])**2)/sum(w*(y-u)**2)),mu
def block_ci(g,y,w,cl,bs):
 a=np.array(list(zip(g.ix//bs,g.iy//bs)));u,b=np.unique(a,axis=0,return_inverse=True);n=len(u);b=b.flatten()
 bins=b*3+cl
 bw=np.bincount(bins,weights=w,minlength=3*n).reshape(n,3); by=np.bincount(bins,weights=w*y,minlength=3*n).reshape(n,3)
 rng=np.random.default_rng(20192021);rep=rng.multinomial(n,np.ones(n)/n,size=999);m=rep@bw;sy=rep@by;means=np.divide(sy,m,out=np.full_like(sy,np.nan),where=m>0);contr=means[:,2]-means[:,0]
 vals=contr[np.isfinite(contr)]
 return (len(vals),*np.quantile(vals,[.025,.975])) if len(vals)>=900 else (len(vals),np.nan,np.nan)
for kind,sets in [('阶段',stage),('转折',turn)]:
 eligible=[j for j in facs if any(f[j].notna().any() for f in sets)]
 th={j:design(j,sets,.50) for j in eligible}
 for j in eligible:
  defs.append([kind,j,th[j],design(j,sets,.33),design(j,sets,.67)])
 for j in eligible:
  available=[f for f in sets if f[j].notna().any()]
  common_series=set.intersection(*[set(f.dropna(subset=[j]).index) for f in available])
  for f in available:
   t=f.iloc[0]['时期'];jj=[k for k in facs if f[k].notna().any()]
   domains={'本阶段有效域':f.dropna(subset=[j]),'本因素跨阶段共同域':f.loc[f.index.isin(common_series)],'该阶段各可用因素共同域':f.dropna(subset=jj),'全阶段NDVI和人口都有值':f.loc[f.index.isin(set.intersection(*[set(k.dropna(subset=['植被绿度','人口密度']).index) for k in stage]))].dropna(subset=[j])}
   if j=='植被绿度':domains['NDVI原像元覆盖完整']=f[f['NDVI两端面积完整']].dropna(subset=[j])
   for dom,h in domains.items():
    w=h.area_km2.to_numpy();v=h.Y.to_numpy();x=h[j].to_numpy();n=len(h)
    if n<10:continue
    q,mu=stat(v,w,cgrp(x,th[j]));cl=cgrp(x,th[j]);q0,_=stat(v,np.ones(n),cl)
    co=np.corrcoef(pd.Series(x).rank(),pd.Series(v).rank())[0,1]
    for m in range(3):
     sub=cl==m;gname=['明显减少组','中间组','明显增加组'][m]
     gr.append([kind,t,j,dom,gname,int(sub.sum()),sum(w[sub]),mu[m],mean((v[sub]>0).astype(float),w[sub])*100 if sub.any() else np.nan])
    b4=block_ci(h,v,w,cl,8);b8=block_ci(h,v,w,cl,16)
    r.append([kind,t,j,dom,n,sum(w),q0,q,co,mu[0],mu[1],mu[2],mu[2]-mu[0],*b4,*b8])
    if dom=='本阶段有效域':
     for p in [.33,.50,.67]:
      cut=design(j,sets,p);val,m=stat(v,w,cgrp(x,cut));sens.append([kind,t,j,p,cut,val,m[2]-m[0]])
     if kind=='阶段':
      for k in jj:
       if facs.index(k)<=facs.index(j):continue
       s=f.dropna(subset=[j,k]);ww=s.area_km2.to_numpy();yy=s.Y.to_numpy();aa=cgrp(s[j].to_numpy(),th[j]);bb=cgrp(s[k].to_numpy(),th[k])
       joint,m=stat(yy,ww,aa*3+bb);qj,_=stat(yy,ww,aa);qk,_=stat(yy,ww,bb)
       inter.append([t,j,k,len(s),ww.sum(),qj,qk,joint,joint-max(qj,qk)])
write(pd.DataFrame(r,columns=['检验','时期','因素','样本口径','格数','面积_km2','常规q','面积加权q','Spearman_rho','减少组年均值','中间组年均值','增加组年均值','增加减减少差','4km重抽有效重复','4km差异CI下限','4km差异CI上限','8km重抽有效重复','8km差异CI下限','8km差异CI上限']),'01_分阶段外部关联检验')
write(pd.DataFrame(gr,columns=['检验','时期','因素','样本口径','X变化组','格数','面积_km2','Y均值','Y正值面积_pct']),'02_组间变化方向')
write(pd.DataFrame(defs,columns=['检验','因素','主分界绝对值_50','备选分界绝对值_33','备选分界绝对值_67']),'03_不按Y优化的统一分组阈值')
write(pd.DataFrame(sens,columns=['检验','时期','因素','设定分位','绝对阈值','加权q','增加减减少差']),'04_分组敏感性')
write(pd.DataFrame(inter,columns=['时期','因素1','因素2','格数','面积_km2','q1','q2','联合q','联合比最强单因素高出']),'05_两因素共同域探索')
z=pd.DataFrame(r);print(z[z[3]=='本阶段有效域'].iloc[:,[0,1,2,4,5,7,8,9,11,14,15,17,18]].round(6).to_string(index=False,header=False))

