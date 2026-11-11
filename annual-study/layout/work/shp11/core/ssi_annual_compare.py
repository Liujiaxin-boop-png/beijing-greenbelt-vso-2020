from compute import *
def run():
 P={};G={s:cells(s) for s in S}
 for s in S:
  panel=pd.read_csv(W/('六项逐格逐年原值与得分'+('' if s==500 else f'_{s}m')+'.csv.gz'))
  g=G[s]; expected=pd.MultiIndex.from_product([Y,g.grid_id],names=['year','grid_id'])
  it=panel.set_index(['year','grid_id']).loc[expected,K]
  new=it.to_numpy().reshape(11,len(g),6).copy()
  for i,y in enumerate(Y):new[i,:,4]=field(A/f'landscape/{y}/fields_{s}_0.bin',g)[:,4]
  P[s]=new
 allx=np.concatenate([rr[np.isfinite(rr).all(axis=-1)] for rr in P.values()])
 lo=allx.min(0);hi=allx.max(0)
 def z(v):
  zz=(v-lo)/(hi-lo);return np.where(D>0,zz,1-zz)
 train=z(P[1000][:,np.isfinite(P[1000]).all(axis=(0,-1)),:]).reshape(-1,6);q=train/train.sum(0);info=1+xlogy(q,q).sum(0)/np.log(len(q));w=info/info.sum()
 has=np.isfinite(P[500]).all(axis=(0,-1));g=G[500].loc[has].copy();er=z(P[500][:,has,:])@w;g['delta_SSI']=er[-1]-er[0]
 v=pd.read_csv(W/'六项格网十年变化.csv')[['grid_id','delta']]
 g=g.merge(v,on='grid_id',validate='1:1');agree=np.sign(g.delta_SSI)==np.sign(g.delta)
 save(g[['grid_id','ix','iy','area_km2','delta','delta_SSI']],'两种六指标2015至2025净变化配对.csv')
 audit={'complete_model_SSI_grid_n':len(g),'n_missing_SSI':len(has)-int(has.sum()),'reference_1km_complete':len(train)//11,'reference_1km_records':len(train),'common_km2':g.area_km2.sum(),'excluded_km2':G[500].loc[~has,'area_km2'].sum(),'area_agree_pct':100*np.average(agree,weights=g.area_km2),'rho_delta':spearmanr(g.delta,g.delta_SSI).statistic,'SSI_weight':w.tolist(),'delta_SSI_areaweighted_mean':np.average(g.delta_SSI,weights=g.area_km2),'delta_ALLDIST_areaweighted_mean_on_paired':np.average(g.delta,weights=g.area_km2)}
 dump(audit,'SSI与全格距离全期同域方向复核.json');print(audit)
if __name__=='__main__':run()
