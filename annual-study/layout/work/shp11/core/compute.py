from pathlib import Path
import sys,json,itertools
import numpy as np,pandas as pd,rasterio
from scipy.special import xlogy
from scipy.stats import spearmanr
W=Path(__file__).resolve().parent; A=Path('D:/ER219_work/annual_actual')
sys.dont_write_bytecode=True
sys.path.insert(0,str(A/'analysis'))
from surfaces import grids_mean,source
K=['LDI','HQI','LBI','MCR','ALLDIST','LRI']; D=np.array([1,1,-1,-1,-1,1]);Y=list(range(2015,2026));S=[500,1000,200]
def save(df,name):
 dest=W/name;f=dest.with_name('part_'+dest.name);df.to_csv(f,index=False,encoding='utf-8-sig',float_format='%.14g');f.replace(dest)
def dump(o,name):
 (W/name).write_text(json.dumps(o,ensure_ascii=False,indent=2),'utf8')
def cells(s):
 c=pd.read_csv(W/f'cells_{s}_0.csv');c['grid_id']=[f'{s}_{x}_{y}' for x,y in zip(c.ix,c.iy)];c['area_km2']=c.area/1e6
 return c
def direct_grids(g,idx):
 x,y=g.ix.values,g.iy.values;a,b,A1,B=idx
 assert x.min()>=a and x.max()<A1 and y.min()>=b and y.max()<B
 return y-b,x-a
def field(p,g):
 with p.open('rb') as f:
  a,b,c,d=np.fromfile(f,'<i4',4)
 raw=np.memmap(p,dtype='<f8',offset=16,shape=(d-b,c-a,10),mode='r')
 return raw[direct_grids(g,(a,b,c,d))]
def surface(y,s,g,key,alt=False):
 p=(A/'alternative_model'/'surfaces'/f'{key}.npz') if alt else A/'surfaces'/str(y)/f'{key}_{s}_0.npz'
 with np.load(p) as f:
  return f['arr'][direct_grids(g,f['limits'])]
def dist_grid(pref,tr,g,s):
 x0,y0,x1,y1=int(g.ix.min()),int(g.iy.min()),int(g.ix.max()+1),int(g.iy.max()+1)
 val=grids_mean(pref,tr,(x0,y0,x1,y1),s,0)[g.iy-y0,g.ix-x0]
 assert np.isfinite(val).all() and val.min()>-1e-7
 return np.where(abs(val)<1e-7,0,val)
def distance_pref(y,alt=False):
 ras=A/('alternative_model/years/model/CLCD_2020.tif' if alt else f'years/model/CLCD_{y}.tif')
 dist=A/('alternative_model/distance.raw' if alt else f'landscape/{y}/distance.raw')
 with rasterio.open(ras) as ds:
  rect=ds.window(910000,4300000,1000000,4395000)
  w=rasterio.windows.Window(np.floor(rect.col_off),np.floor(rect.row_off),np.ceil(rect.width)+2,np.ceil(rect.height)+2)
  tr=ds.window_transform(w);r,c=int(w.row_off),int(w.col_off)
  arr=np.memmap(dist,dtype='<f4',mode='r',shape=ds.shape)[r:r+int(w.height),c:c+int(w.width)]
  pre=np.zeros((arr.shape[0]+1,arr.shape[1]+1),np.float64)
  np.cumsum(arr,axis=0,out=pre[1:,1:],dtype=np.float64);np.cumsum(pre[1:,1:],axis=1,out=pre[1:,1:])
 return pre,tr
def sen(series):
 return np.median(np.stack([(series[j]-series[i])/(j-i) for i,j in itertools.combinations(range(11),2)]),axis=0)
def main():
 G={s:cells(s) for s in S};data={s:np.zeros((11,len(G[s]),6)) for s in S};comp={s:np.zeros((11,len(G[s]),3)) for s in S}
 for i,y in enumerate(Y):
  pf,tr=distance_pref(y)
  for s,g in G.items():
   v=data[s][i];raw=field(A/f'landscape/{y}/fields_{s}_0.bin',g)
   v[:,0]=raw[:,0];v[:,5]=raw[:,5];comp[s][i]=raw[:,1:4]
   v[:,1]=np.clip(surface(y,s,g,'HQI'),0,1);v[:,3]=surface(y,s,g,'MCR')
   v[:,4]=dist_grid(pf,tr,g,s)
  del pf
  print('Read complete',y,flush=True)
 lo=np.min([b.min(axis=(0,1)) for b in comp.values()],axis=0);hi=np.max([b.max(axis=(0,1)) for b in comp.values()],axis=0)
 for s in S:data[s][:,:,2]=((comp[s]-lo)/(hi-lo))@np.array([.5,.3,.2])
 mi=np.min([d.min(axis=(0,1)) for d in data.values()],axis=0);mx=np.max([d.max(axis=(0,1)) for d in data.values()],axis=0)
 def norm(d):
  z=(d-mi)/(mx-mi);return np.where(D>0,z,1-z)
 train=norm(data[1000]).reshape(-1,6);assert len(train)==1297*11 and np.isfinite(train).all()
 frac=train/train.sum(0);info=1+xlogy(frac,frac).sum(0)/np.log(len(frac));w=info/info.sum()
 dump({'fields':K,'n':len(train),'entropy_balanced_1km_cells':len(G[1000]),'weights':dict(zip(K,w.tolist())),'min':dict(zip(K,mi.tolist())),'max':dict(zip(K,mx.tolist())),'LBI_component_lo':lo.tolist(),'LBI_component_hi':hi.tolist(),'information_utility':dict(zip(K,info.tolist())),'k':json.loads((W/'domain.json').read_text('utf8'))['new_hq_k'],'data_source_root':str(A)},'parameters.json')
 results={}; periods=[]
 for s in S:
  g=G[s];v=data[s]; z=norm(v);con=z*w; er=con.sum(-1);eq=z.mean(-1);assert np.isfinite(er).all()
  results[s]=er
  df=pd.concat([g[['grid_id','ix','iy','area_km2']].assign(year=y) for y in Y],ignore_index=True)
  for j,k in enumerate(K):df[k]=v[:,:,j].ravel();df['C_'+k]=con[:,:,j].ravel()
  df['ER6']=er.ravel();df['ER_equal']=eq.ravel();df=df[['grid_id','ix','iy','year','area_km2',*K,*['C_'+k for k in K],'ER6','ER_equal']]
  if s==500:
   save(df,'六项逐格逐年原值与得分.csv.gz')
   t=g[['grid_id','ix','iy','area_km2']].copy();t['ER2015']=er[0];t['ER2017']=er[2];t['ER2025']=er[-1];t['delta']=er[-1]-er[0];t['Sen']=sen(er)
   for j,k in enumerate(K):t['delta_'+k]=con[-1,:,j]-con[0,:,j]
   assert np.max(abs(t.delta-t[['delta_'+k for k in K]].sum(axis=1)))<2e-14
   save(t,'六项格网十年变化.csv')
   val=['ER6','ER_equal',*['C_'+k for k in K],*K]
   reg=pd.DataFrame([dict(year=yr,n=len(b),km2=b.area_km2.sum(),**dict(zip(val,np.average(b[val],axis=0,weights=b.area_km2)))) for yr,b in df.groupby('year',sort=True)])
   save(reg,'区域六项逐年指数与分项.csv')
   for a,b in [(0,10),(0,4),(4,6),(6,10),(0,2),(2,10)]:
    wgt=g.area_km2.to_numpy();dn=er[b]-er[a];periods.append(dict(start=Y[a],end=Y[b],change=np.average(dn,weights=wgt),up_km2=wgt[dn>1e-10].sum(),down_km2=wgt[dn< -1e-10].sum(),nearzero_km2=wgt[abs(dn)<=1e-10].sum(),down_pct=100*wgt[dn< -1e-10].sum()/wgt.sum()))
   save(pd.DataFrame(periods),'全区变化面积与阶段.csv')
   print('500m complete',reg[['year','ER6']].to_dict('records'),w,flush=True)
  else:save(df,f'六项逐格逐年原值与得分_{s}m.csv.gz')
 pair=[]
 gp=G[1000];full=gp.area.ge(1e6-1).values;pp=gp.loc[full]
 for s in [200,500]:
  g=G[s];idx=pd.MultiIndex.from_frame(g[['ix','iy']]);f=1000//s
  children=np.vstack([idx.get_indexer(pd.MultiIndex.from_arrays([pp.ix*f+dx,pp.iy*f+dy])) for dy,dx in itertools.product(range(f),repeat=2)]).T
  assert children.min()>=0
  for i,y in enumerate(Y):
   kids=results[s][i,children];pred=kids.mean(axis=1);ref=results[1000][i,full]
   pair.append(dict(year=y,child_m=s,full_parents=len(pp),rho=spearmanr(pred,ref).statistic,mean_abs_gap=np.mean(abs(pred-ref)),median_child_range=np.median(kids.max(axis=1)-kids.min(axis=1))))
 save(pd.DataFrame(pair),'年度六项综合分_嵌套尺度对照.csv')
 print('Complete',flush=True)
if __name__=='__main__': main()
