from pathlib import Path
import json
import sys,numpy as np,pandas as pd,rasterio as rio
from scipy.stats import spearmanr
import importlib.util
W=Path(__file__).resolve().parent
D=W.parent/'人类活动'
s=importlib.util.spec_from_file_location('support',D/'grid_population_light.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
files=sorted((W/'发布者COG的北京范围').glob('OpenGeoHub_average_*_北京.tif'))
frames=[]
for f in files:
 yr=int(f.stem.split('_')[-2])
 with rio.open(f) as ds:
  win,i,row,col,pa,a=h.cross(ds);v=ds.read(1,window=win,masked=True)[row,col].astype(float).filled(np.nan)
  meta=json.loads((f.parent/f'{yr}_源与窗口.json').read_text(encoding='utf8')); factor=float(meta['source_scale'][0]);
  ok=np.isfinite(v)&(v>=0);M=len(h.FRAME);w=np.bincount(i[ok],weights=a[ok],minlength=M);cover=np.bincount(i,weights=a,minlength=M);r=np.bincount(i[ok],weights=(v[ok]*factor/10)*a[ok],minlength=M)/np.where(w>0,w,np.nan)
  data=h.BASE.copy();data['year']=yr; data['native_tiff_scale']=factor; data['ntl_oghub']=np.where(w>=249999,r,np.nan);data['valid_fraction']=w/250000;data['source_pixel_extent_fraction']=cover/250000
  frames.append(data)
df=pd.concat(frames,ignore_index=True)
df.to_csv(W/'OpenGeoHub_逐年500米夜光_禁止拼接EOG.csv',encoding='utf-8-sig',index=False)
orig=pd.read_csv(D/'ntl_2020_grid500.csv')[['grid_id','ntl_radiance']]
q=df[df.year==2020].merge(orig,on='grid_id',validate='one_to_one').dropna(subset=['ntl_radiance','ntl_oghub']);diff=q.ntl_oghub-q.ntl_radiance
E=W.parents[1].parent/'计算结果与核验/01_全区与格网/六项逐格逐年原值与得分.csv.gz'
sc=pd.read_csv(E,usecols=['grid_id','year','ER6'])
pnl=df.merge(sc,on=['year','grid_id'],validate='one_to_one')
res=[]
for year,g in pnl.groupby('year'):
 g=g[g.ntl_oghub.notna()].copy()
 def weightedmean(x,w):return np.average(x,weights=w)
 res.append({'year':year,'n_grids':len(g),'study_support_km2':g.intersection_m2.sum()/1e6,'average_nightlights':weightedmean(g.ntl_oghub,g.intersection_m2),'spearman_NTL_ER_all':spearmanr(g.ntl_oghub,g.ER6).statistic,'ER_comparison':'未作空间置换；只描述秩关联'})
pd.DataFrame(res).to_csv(W/'夜光年度与韧性秩关联_不作因果.csv',encoding='utf-8-sig',index=False)
import json
v={'years_ready':sorted(df.year.unique().tolist()),'n_2020_comparable':len(q),'rho_2020_vs_original_EOG':spearmanr(q.ntl_oghub,q.ntl_radiance).statistic,'MAE_vs_EOG_weighted':weightedmean(np.abs(diff),q.intersection_m2),'mean_signed_diff_vs_EOG_weighted':weightedmean(diff,q.intersection_m2),'support_mean_EOG':weightedmean(q.ntl_radiance,q.intersection_m2),'support_mean_opengeohub':weightedmean(q.ntl_oghub,q.intersection_m2),'valid_range':df.valid_fraction.agg(['min','max']).tolist()}
(W/'跨年产品2020同格与官方EOG检验.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8');print(v)
