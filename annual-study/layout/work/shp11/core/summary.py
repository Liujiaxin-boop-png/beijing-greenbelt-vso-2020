from compute import *
from scipy.stats import spearmanr
def summary():
 df=pd.read_csv(W/'六项逐格逐年原值与得分.csv.gz');g=cells(500).set_index('grid_id');w=g.area_km2
 p=df.pivot(index='grid_id',columns='year',values='ER6').reindex(g.index);annual=p.apply(lambda v:np.average(v,weights=w));sl=sen(p.T.values);t=p[2025]-p[2015];t19=p[2021]-p[2019]
 mask=lambda k:float(w[k].sum());pct=lambda k:100*mask(k)/w.sum()
 tr=[{'year':int(y),'ER':annual[y],'change':float(annual[y]-annual[y-1]),'down_pct':pct((p[y]-p[y-1])<0),'up_pct':pct((p[y]-p[y-1])>0)} for y in Y[1:]]
 a=pd.read_csv(W/'区域六项逐年指数与分项.csv').set_index('year')
 stage={str(y)+':'+str(z):{'delta':a.loc[z].sub(a.loc[y])[['ER6','ER_equal',*['C_'+k for k in K],*K]].to_dict(),'down_pct':pct((p[z]-p[y])<0)} for y,z in [(2015,2025),(2015,2019),(2019,2021),(2021,2025)]}
 figA={z:{} for z in Y if z in (2015,2020,2025)}
 for y in figA:
  v=df[df.year==y].set_index('grid_id').loc[g.index];figA[y]={'HQI_le_006_km2':mask(v.HQI<=.06),'ALLDIST_le_200_km2':mask(v.ALLDIST<=200)}
 same=np.digitize(p[2015],[.15,.2,.3,.4])==np.digitize(p[2025],[.15,.2,.3,.4])
 h=pd.read_csv(W/'HQI_input_attribution.csv').iloc[0]
 cphi={k.removeprefix('delta_HQI_'):100*h[k]/h.delta_HQI for k in h.index if k.startswith('delta_HQI_')}
 oldp=Path('D:/ER219_work/six_final11/annual/ALLDIST');eids=set(pd.read_csv(W/'新增166格_逐年齐全清单.csv').grid_id)
 edgecheck={'n_added':len(eids),'added_km2':mask(g.index.isin(eids))}
 ob=pd.read_csv(W/'ndvi500.csv').merge(g.reset_index()[['grid_id','ix','iy']],on=['ix','iy'],validate='1:1');ov=pd.read_csv(W/'old_scores.csv')
 for hab in ['forest_shrub','grassland']:
  f=ov[ov.habitat==hab].dropna(subset=['NTL','HQ_H','CLUMPY','MCR','SSI','E_fraction']);u=f.merge(ob[['grid_id','valid_fraction','ndvi']],on='grid_id',validate='1:1').query('valid_fraction>=0.8').dropna(subset=['ndvi'])
  edgecheck[hab]={'training':len(f),'new_training':int(f.grid_id.isin(eids).sum()),'valid_NDVI':len(u),'new_observed':int(u.grid_id.isin(eids).sum())}
 edgecheck['ndvi_valid_all_new']=int((ob.grid_id.isin(eids)&ob.valid_fraction.ge(.8)).sum())
 layout=pd.read_csv(W/'2020固定地类面积和建设位置的灰绿配置置换.csv')
 edgecheck['layout_eligible_added']=int(layout.grid_id.isin(eids).sum())
 s={'annual':tr,'stages':stage,'regional_rebound_fraction':100*(annual[2021]-annual[2019])/(annual[2015]-annual[2019]),'sen_decline_pct':pct(sl<0),'sen_decline_area':mask(sl<0),'sen_plus':pct(sl>0),'sen_zero':pct(sl==0),'overlap_sen_lt_zero_and_2019_2021_down_km2':mask((sl<0)&(t19<0)),'overlap_sen_lt_zero_and_2019_2021_down_percent':pct((sl<0)&(t19<0)),'A5_same_5bin_pct':pct(same),'figureA':figA,'HQI_shapley_pct':cphi,'added_grids_sample_coverage':edgecheck}
 dump(s,'文稿核数_附录与全区.json');save(pd.DataFrame(tr),'逐年同步变化与下降面积占比.csv');print(json.dumps({k:v for k,v in s.items() if k!='stages'},ensure_ascii=False,indent=1))
if __name__=='__main__':summary()
