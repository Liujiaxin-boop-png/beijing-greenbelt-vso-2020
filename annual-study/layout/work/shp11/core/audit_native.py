from pathlib import Path
import numpy as np,pandas as pd,rasterio as rio,json,hashlib
from scipy import ndimage
from scipy.special import xlogy
from scipy.stats import spearmanr
from compute import W,A,K,Y,D,save,dump,cells,surface,sen
from contextlib import ExitStack
def main():
 old=Path('D:/ER219_work/six_final11/annual/ALLDIST')
 oldp=pd.read_csv(old/'六项逐格逐年原值与得分.csv.gz')
 d=pd.read_csv(W/'六项逐格逐年原值与得分.csv.gz');par=json.loads((W/'parameters.json').read_text('utf8'))
 z=d.merge(oldp,on=['grid_id','year'],suffixes=('','_old'),validate='1:1')
 ids=set(d.grid_id)-set(oldp.grid_id)
 print('verifying all extra cells',len(ids),flush=True);assert len(ids)==166 and len(z)==4312*11
 er={k:float(abs(z[k]-z[k+'_old']).max()) for k in K}
 g=cells(500);new=g[g.grid_id.isin(ids)].copy();new['n_years']=11
 save(new[['grid_id','ix','iy','area_km2','n_years']],'新增166格_逐年齐全清单.csv')
 lo=np.array(par['LBI_component_lo']);hi=np.array(par['LBI_component_hi']);mxerr=np.zeros(6)
 group=np.array([0,1,2,2,3,4,0,5,6,4]);recovery=np.array([0,.5,1,.8,.7,1,0,.1,.4,.9])
 region=[];recalc=[]
 for y in Y:
  dr=d.loc[d.year.eq(y)].set_index('grid_id');  
  with ExitStack() as st:
   def ds(path):return st.enter_context(rio.open(path))
   land=ds(A/f'years/model/CLCD_{y}.tif');hq=ds(A/f'hq/results/HQI_{y}.tif');mcr=ds(A/f'mcr/{y}/MCR_{y}.tif')
   tr=land.transform; assert tr==hq.transform==mcr.transform and land.shape==hq.shape==mcr.shape
   dist=np.memmap(A/f'landscape/{y}/distance.raw',dtype='<f4',mode='r',shape=land.shape)
   for c in new.itertuples():
    s=500;x0=(c.ix*s-tr.c)/30;x1=((c.ix+1)*s-tr.c)/30;y0=(tr.f-(c.iy+1)*s)/30;y1=(tr.f-c.iy*s)/30
    left,right=int(np.floor(x0)),int(np.ceil(x1));top,bottom=int(np.floor(y0)),int(np.ceil(y1)); sl=(slice(top,bottom),slice(left,right)); win=rio.windows.Window(left,top,right-left,bottom-top)
    xs=np.arange(left,right);ys=np.arange(top,bottom);wx=np.minimum(xs+1,x1)-np.maximum(xs,x0);wy=np.minimum(ys+1,y1)-np.maximum(ys,y0);w=wx[None,:]*wy[:,None]*900
    assert abs(w.sum()-250000)<1e-5
    landv=land.read(1,window=win);v=group[landv]; cnt=np.bincount(v.ravel(),weights=w.ravel(),minlength=7);p=cnt[cnt>0]/w.sum()
    centers=((xs+.5>=x0)&(xs+.5<x1))[None,:]&((ys+.5>=y0)&(ys+.5<y1))[:,None];ns=[]
    for f in np.unique(v[centers]):
     lbl,n=ndimage.label((v==f)&centers,np.ones((3,3),dtype='u1'));ns.extend(np.bincount(lbl.ravel())[1:])
    pc=np.array(ns,dtype=float);assert pc.sum()==centers.sum();f=pc/pc.sum();sc=(f*f).sum(); b=np.array([len(f)/(.0009*centers.sum()),1/sc,1-sc]);lbi=(b-lo)/(hi-lo)@np.array([.5,.3,.2])
    val=np.array([-np.sum(p*np.log(p)),np.average(hq.read(1,window=win),weights=w),lbi,np.average(mcr.read(1,window=win),weights=w),np.average(dist[sl],weights=w),np.average(recovery[landv],weights=w)])
    ref=dr.loc[c.grid_id,K].to_numpy(dtype=float);mxerr=np.maximum(mxerr,abs(ref-val));recalc.append([c.grid_id,y,*val])
  print(y,mxerr,flush=True)
 assert np.all(mxerr < [1e-9,1e-8,1e-8,.0001,1e-5,1e-9]),mxerr
 save(pd.DataFrame(recalc,columns=['grid_id','year',*K]),'新增166格_原始像元独立复算.csv.gz')
 a=pd.read_csv(W/'区域六项逐年指数与分项.csv').set_index('year');c=pd.read_csv(W/'六项格网十年变化.csv')
 common=[]
 for yy in [2015,2025]:
  vv=surface(yy,500,g,'HQI_commonroad')
  common.append(np.average(vv,weights=g.area))
 hqdiff=float(common[1]-common[0]); v=(a.loc[2025]-a.loc[2015]);cc=v['ER6']+(hqdiff-v['HQI'])*par['weights']['HQI']/(par['max']['HQI']-par['min']['HQI'])
 slope=float(sen(a['ER6'].to_numpy()));pos=c.Sen.gt(1e-12);neg=c.Sen.lt(-1e-12)
 diag={'new_grids':166,'common_grids':4312,'old_only_grids':len(set(oldp.grid_id)-set(d.grid_id)),'edge_added_area_km2':float(new.area_km2.sum()),'observations_audited':len(recalc),'old_retained_grid_max_raw_diff_from_former_rounded_output':er,'fresh_native_pixel_max_raw_diff':dict(zip(K,mxerr)),'full_model_input_rect_crs':land.crs.to_wkt(),'support':{'model_raster_width':land.width,'model_raster_height':land.height,'source_rule':'native MSPA fixed full-rectangle from CLCD; core area > 1 km2, dPC>0.5%; dual-source MCR full native canvas; habitat threats fixed full raster; reporting boundary subsequent to input generation','ALLDIST':'full native 30m EDT predates both cutlines; nearest feature search crosses grid/reporting boundary. Distance field independently reproduced for all years.'},'sen_ER_areaweight_annual_mean_sequence':slope,'sen_declining_area_pct':100*c.loc[neg,'area_km2'].sum()/c.area_km2.sum(),'sen_increasing_area_pct':100*c.loc[pos,'area_km2'].sum()/c.area_km2.sum(),'common_road':{'deltaHQ_original':v.HQI,'deltaHQ_commonroad':hqdiff,'deltaER_original':v.ER6,'deltaER_commonroad':cc},'negative_contribution_fraction_HQI':-v.C_HQI/-sum(v['C_'+k] for k in K if v['C_'+k]<0),'HQI_LRI_rho2020':spearmanr(d.loc[d.year.eq(2020),'HQI'],d.loc[d.year.eq(2020),'LRI']).statistic}
 idx=d.pivot(index='grid_id',columns='year',values=['HQI','LRI']);diag['HQI_LRI_rho_change']=spearmanr(idx.HQI[2025]-idx.HQI[2015],idx.LRI[2025]-idx.LRI[2015]).statistic
 for eps in [0,1e-4,.0005,.001,.002,.005,.01]:diag[str(eps)]={'area_up_pct':100*c.loc[c.delta>eps,'area_km2'].sum()/c.area_km2.sum(),'area_down_pct':100*c.loc[c.delta< -eps,'area_km2'].sum()/c.area_km2.sum()}
 print(diag,flush=True);dump(diag,'独立核验_166全格与共同道路.json')
if __name__=='__main__':main()
