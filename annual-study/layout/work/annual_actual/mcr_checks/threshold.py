"""Hold the landscape and resistance fixed while changing PC half-probability distance."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from scipy.sparse.csgraph import shortest_path
import numpy as np,pandas as pd,rasterio as rio,os,json,time,subprocess,shutil
D=Path(__file__).resolve().parent; A=D.parent; orig=Path(r'D:\ER219_work\feng_round2\source_mcr')
def score(ed,area,half):
 def pc(m,ar):
  ds=shortest_path(m,directed=False)
  return ar @ (np.exp(-np.log(2)*ds/half)) @ ar
 total=pc(ed,area)
 loss=[]
 for i in range(len(area)):
  keep=np.arange(len(area))!=i
  loss.append(100.*(total-pc(ed[np.ix_(keep,keep)],area[keep]))/total)
 return np.asarray(loss)
def link(src,dst):
 if not dst.exists():
  try:os.link(src,dst)
  except OSError:shutil.copy2(src,dst)
def run(y):
 ws=D/str(y);ws.mkdir(parents=True,exist_ok=True)
 base=A/'mcr'/str(y); sr=base if y!=2020 else orig
 ref=base/f'MCR_{y}.tif'
 ed=np.loadtxt(base/'edge_distances_m.csv',delimiter=',');tab=pd.read_csv(base/'source_dPC.csv')
 area=tab.area_m2.to_numpy();ids=tab.source_id.to_numpy()
 assert np.array_equal(ids,np.arange(1,len(ids)+1))
 cutoff=0.5
 computed=score(ed,area,1000);assert np.max(abs(computed-tab.dPC_percent))<1e-7
 baseids=tuple(ids[computed>cutoff].tolist());seen={baseids:ref};res=[]
 with rio.open(base/'sources_area.tif') as s:lab=s.read(1);prof=s.profile;nr,nc=s.shape
 link(sr/'cost.f32',ws/'cost.f32')
 edges=set(int(i) for i in np.unique(np.r_[lab[0],lab[-1],lab[:,0],lab[:,-1]]) if i>0)
 tabs=tab.copy()
 for half in [500,2000]:
  scorex=score(ed,area,half);pick=tuple(ids[scorex>cutoff].tolist());tabs['dPC_percent_half'+str(half)]=scorex
  assert len(pick)>=2
  dest=ws/f'MCR_half{half}.tif';scheme='half'+str(half)
  if pick in seen:link(seen[pick],dest)
  elif not dest.exists():
   source=ws/(scheme+'.i32');np.where(np.isin(lab,pick),lab,0).astype('int32').tofile(source)
   surf=ws/('surface_'+scheme+'.f32')
   subprocess.run([str(orig/'TwoSource.exe'),str(ws),scheme,str(nc),str(nr),'30'],check=True)
   arr=np.memmap(surf,dtype='float32',mode='r',shape=(nr,nc));assert np.isfinite(arr).all() and arr.min()>=0
   params=prof.copy();params.update(nodata=-9999,dtype='float32',tiled=True,blockxsize=256,blockysize=256,compress='deflate',predictor=3)
   tmp=dest.with_suffix('.partial.tif')
   with rio.open(tmp,'w',**params) as ds:ds.write(arr,1)
   tmp.replace(dest);del arr
  seen[pick]=dest
  comm=len(set(baseids)&set(pick));uni=len(set(baseids)|set(pick))
  res.append(dict(year=y,half_probability_m=half,n_candidates=len(ids),n_base=len(baseids),n_alt=len(pick),n_common=comm,n_union=uni,Jaccard=comm/uni,base_retained_fraction=comm/len(baseids),n_base_touched=len(edges&set(baseids)),n_alt_touched=len(edges&set(pick)),IDs_base=baseids,IDs_alt=pick,area_threshold_m2=1000000,dPC_threshold_pct=cutoff,output=str(dest)))
  print(y,half,len(baseids),len(pick),round(comm/uni,3),flush=True)
 tabs.to_csv(ws/'all_source_dPC_scenarios.csv',index=False,encoding='utf-8-sig')
 (ws/'threshold_receipt.json').write_text(json.dumps(res,indent=2),encoding='utf8')
 return res
if __name__=='__main__':
 with ThreadPoolExecutor(2) as e: groups=list(e.map(run,[2015,2025,2020,2016,2017,2018,2019,2021,2022,2023,2024]))
 df=pd.DataFrame([r for group in groups for r in group]).sort_values(['year','half_probability_m'])
 df.to_csv(D/'threshold_source_membership.csv',index=False,encoding='utf-8-sig')
