from pathlib import Path
import numpy as np,pandas as pd
D=Path(__file__).resolve().parent;B=D.parents[1];P=B/'高韧性空间因素_2020实证'/'02_过程'/'生态空间'
z=pd.read_csv(D/'三个阶段的年均变化量_逐格.csv.gz');a=pd.read_csv(B/'计算结果与核验'/'01_全区与格网'/'六项逐格逐年原值与得分.csv.gz',usecols=['grid_id','year','ER6']);th=float(pd.read_csv(D/'03_不按Y优化的统一分组阈值.csv').query("检验=='阶段' and 因素=='植被绿度'")['主分界绝对值_50'].iloc[0]);out=[]
def tert(x,w):
 i=np.argsort(x,kind='stable');cs=np.cumsum(w[i]);return np.searchsorted(x[i][np.searchsorted(cs,cs[-1]*np.arange(1,3)/3)],x)
for period,hh in z.groupby('时期'):
 t=int(period[:4]);f=pd.read_csv(P/('ndvi_main_'+str(t)+'.csv')).rename(columns={'ndvi':'start_ndvi'})
 h=hh.merge(a[a.year==t],on='grid_id',validate='1:1').merge(f,on='grid_id',validate='1:1').dropna(subset=['植被绿度','start_ndvi']).copy()
 x=h['植被绿度'].to_numpy();y=h.Y.to_numpy();w=h.area_km2.to_numpy();n=len(y);ce=tert(h.ER6.to_numpy(),w);cn=tert(h.start_ndvi.to_numpy(),w)
 for mode,st in [('仅起始韧性三组',ce),('起始韧性与起始NDVI各三组',ce*3+cn)]:
  for sz in [8,16]:
   g=np.where(x< -th,0,np.where(x>th,2,1));bin=st*3+g
   _,b=np.unique(np.stack([h.ix//sz,h.iy//sz],axis=-1),axis=0,return_inverse=True);b=b.flatten();nb=b.max()+1;nst=st.max()+1
   full=nb*nst*3;ix=b*(3*nst)+bin
   bwt=np.bincount(ix,weights=w,minlength=full).reshape(nb,nst*3);by=np.bincount(ix,weights=w*y,minlength=full).reshape(nb,nst*3);count=np.bincount(ix,minlength=full).reshape(nb,nst,3)
   # Support: minimum 10 grid cells in both contrasting groups. Fixed before bootstrap, applied at each period.
   valid=(count.sum(axis=0)[:,[0,2]].min(axis=1)>=10)
   raw=count.sum(axis=0);rng=np.random.default_rng(38930);m=np.vstack([np.ones(nb),rng.multinomial(nb,np.ones(nb)/nb,size=999)])
   ww=(m@bwt).reshape(-1,nst,3)[:,valid,:];sy=(m@by).reshape(-1,nst,3)[:,valid,:];mu=np.divide(sy,ww,out=np.full_like(sy,np.nan),where=ww>0)
   delta=mu[:,:,2]-mu[:,:,0];sw=ww.sum(axis=2)
   # Support is allowed to vary within bootstrap only by discarding the whole replicate in case of absent extremes
   con=(delta*sw).sum(axis=1)/sw.sum(axis=1);ci=np.nanquantile(con[1:],[.025,.975]);out.append([period,mode,sz*.5,n,len(valid),valid.sum(),w[np.isin(st,np.flatnonzero(valid))].sum(),con[0],ci[0],ci[1],np.isfinite(con[1:]).sum()])
o=pd.DataFrame(out,columns=['时期','固定起始条件','区块边长_km','有效格网','层数','两端组各达十格的层数','覆盖面积_km2','调整后增加组减减少组的年均ER差','区块95%下限','区块95%上限','有效重抽次数']);o.to_csv(D/'06_起始条件相近的植被旁证.csv',index=False,encoding='utf-8-sig');print(o[o.区块边长_km==8].round(6).to_string(index=False))
