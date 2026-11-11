from pathlib import Path
import json,numpy as np,pandas as pd,hashlib
from compute import W,A,K,Y,save,dump
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 panels={s:pd.read_csv(W/('六项逐格逐年原值与得分'+('' if s==500 else f'_{s}m')+'.csv.gz')) for s in [200,500,1000]}
 allx=pd.concat([p[K] for p in panels.values()],ignore_index=True);lo=allx.min();hi=allx.max()
 def scale(x):
  z=x[K].sub(lo).div(hi-lo);z[['LBI','MCR','ALLDIST']]=1-z[['LBI','MCR','ALLDIST']];return z
 x=panels[1000];assert len(x)==14267 and x.groupby('grid_id').year.nunique().eq(11).all()
 a=scale(x);p=a.div(a.sum());withlog=p.where(p.gt(0));eff=1+(p*np.log(withlog)).sum()/np.log(len(p));w=eff/eff.sum()
 par=json.loads((W/'parameters.json').read_text('utf8'));ref=pd.Series(par['weights']);weight_error=(w-ref).abs().max()
 d=panels[500];v=scale(d);total=v.dot(w);ts=d.assign(score=total,weighted=total*d.area_km2).groupby('year')[['weighted','area_km2']].sum()
 reg=pd.read_csv(W/'区域六项逐年指数与分项.csv').set_index('year')
 _,lower,upper=[None,pd.Series(par['min']),pd.Series(par['max'])]
 score_err=(d.ER6-total).abs().max();component_err=(v*w-d[['C_'+i for i in K]].set_axis(K,axis=1)).abs().max().max()
 regerr=(ts.weighted/ts.area_km2-reg.ER6).abs().max()
 assert weight_error<1e-12 and component_err<1e-12 and score_err<1e-12 and regerr<1e-12
 for r,ng in [(200,25058),(500,4478),(1000,1297)]:
  p=panels[r];assert len(p)==ng*11 and not p[['grid_id','year']].duplicated().any() and p[K+['ER6']].notna().all().all()
  assert abs(p.groupby('year').area_km2.sum().to_numpy()-922.18601113392).max()<2e-8
 dump({'balanced_1km_cells':1297,'records_1km':14267,'fresh_entropy_weights':w.to_dict(),'max_abs_weight_diff':weight_error,'max_abs_grid_ER_diff':score_err,'max_abs_regional_annual_ER_diff':regerr,'max_abs_grid_component_diff':component_err,'max_difference_in_normalisation_min':float((lo-lower).abs().max()),'max_difference_in_normalisation_max':float((hi-upper).abs().max()),'checks':['unique cell-year on all scales','each reporting year 922.18601113392 km²','no missing on any scale','equal-weight total separately provided']},'熵权与区域汇总独立校核.json')
 files=[W/'domain.json',A/'analysis/Landscape.cs',A/'analysis/surfaces.py',A/'analysis/annual_landscape.py',A/'analysis/annual_mcr.py',A/'hq/annual_hq.py',A/'hq/sensitivity_3threat.csv',A/'hq/full_scope_frozen_k.json']
 for y in Y:
  files.extend([A/f'years/model/CLCD_{y}.tif',A/f'hq/degradation/D_{y}.tif',A/f'hq/results/HQI_{y}.tif',A/f'mcr/{y}/MCR_{y}.tif',A/f'mcr/{y}/verified.json',A/f'mcr/{y}/source_dPC.csv',A/f'landscape/{y}/distance.raw'])
  files.extend([A/f'landscape/{y}/fields_{s}_0.bin' for s in [200,500,1000]])
  files.extend([A/f'surfaces/{y}/{k}_{s}_0.npz' for s in [200,500,1000] for k in ['HQI','MCR']])
 out=[]
 for f in files:out.append(dict(file=str(f),bytes=f.stat().st_size,sha256=sha(f)))
 save(pd.DataFrame(out),'原始与模型输入文件指纹.csv')
 print('Verified',score_err,regerr,weight_error,len(files))
if __name__=='__main__':main()
