from compute import *
from compare_six import alt
def run():
 pr=json.loads((W/'parameters.json').read_text('utf8')); g=cells(500);t=pd.read_csv(W/'六项逐格逐年原值与得分.csv.gz').set_index(['year','grid_id'])
 wt=np.array([pr['weights'][k] for k in K]);lo=np.array([pr['min'][k] for k in K]);hi=np.array([pr['max'][k] for k in K]);z=alt().set_index('grid_id').loc[g.grid_id];raw=z[K].values; norm=(raw-lo)/(hi-lo);q=(np.where(D>0,norm,1.-norm)@wt);z['ER6']=q
 b=t.loc[2020].loc[g.grid_id];result=[]
 for key in K+['ER6']:
  v=z[key];u=b[key];check=(np.isfinite(v)&np.isfinite(u)).to_numpy();a=g.loc[check,'area_km2'];v=v[check].to_numpy();u=u[check].to_numpy();result.append(dict(name=key,n=len(v),km2=a.sum(),CLCD=np.average(u,weights=a),WorldCover=np.average(v,weights=a),Spearman=spearmanr(v,u).statistic,W_MAD=np.average(abs(v-u),weights=a)))
 save(pd.DataFrame(result),'完整范围两套地类500米六项与得分.csv')
 z=z[K+['ER6']].reset_index().rename(columns={k:'WC_'+k for k in K+['ER6']}).merge(b[K+['ER6']].reset_index().rename(columns={k:'CLCD_'+k for k in K+['ER6']}),on='grid_id',validate='1:1')
 save(z,'两套地类2020年六项与分数逐格.csv.gz')
 edge=set(pd.read_csv(W/'新增166格_逐年齐全清单.csv').grid_id);rr=[]
 for year in Y:
  a=t.loc[year].loc[g.grid_id]
  for name in (['MCR_half500','MCR_half2000','MCR_expand10200'] if year in (2015,2025) else ['MCR_half500','MCR_half2000']):
   er=a.ER6.to_numpy();mcr=a.MCR.to_numpy();new=surface(year,500,g,name);chg=-(new-mcr)*wt[3]/(hi[3]-lo[3]);er2=er+chg
   for sub,mask in [('全区',np.ones(len(g),bool)),('新增166格',g.grid_id.isin(edge))]:
    area=g.area_km2.to_numpy()[mask];rr.append(dict(year=year,subgroup=sub,scenario=name,n=sum(mask),km2=area.sum(),MCR_rank=spearmanr(mcr[mask],new[mask]).statistic,ER_rank=spearmanr(er[mask],er2[mask]).statistic,raw_WMAD=np.average(abs(mcr-new)[mask],weights=area),ER_WMAD=np.average(abs(chg)[mask],weights=area),regional_mean_ER_diff=np.average(chg[mask],weights=area)))
 save(pd.DataFrame(rr),'MCR背景扩展与连接概率半距实算.csv')
if __name__=='__main__':run()
