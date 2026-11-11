from pathlib import Path
import geopandas as gp,shapely as sh,pandas as pd,numpy as np,json
w=Path(__file__).resolve().parent
part=gp.read_file(w/'二道绿隔边界精确叠置.gpkg',layer='parts').set_index('zone')
I,A,B=(part.loc[k,'geometry'] for k in ['common','user_only','recon_only'])
user=sh.union(I,A);R=sh.union(I,B)
data=pd.read_csv('D:/ER219_work/six_final11/annual/ALLDIST/六项格网十年变化.csv')
m=pd.read_csv('D:/ER219_work/six_final11/annual/ALLDIST/六项逐格逐年原值与得分.csv.gz',usecols=['grid_id','year','ER6']).pivot(index='grid_id',columns='year',values='ER6')
cols=[c for c in data.columns if c not in ['ix','iy']]
ixmin,iymin,ixmax,iymax=np.floor(np.array(user.union(R).bounds)/500).astype(int);ix,iy=np.meshgrid(np.arange(ixmin,ixmax+1),np.arange(iymin,iymax+1));ix=ix.ravel();iy=iy.ravel()
g=sh.box(ix*500,iy*500,(ix+1)*500,(iy+1)*500)
out=pd.DataFrame({'grid_id':['500_%d_%d'%(x,y) for x,y in zip(ix,iy)],'ix':ix,'iy':iy})
for k,poly in [('common',I),('user_only',A),('recon_only',B)]:
    ar=np.zeros(len(g));valid=sh.intersects(g,poly);ar[valid]=sh.area(sh.intersection(g[valid],poly))
    out[k+'_m2']=ar
out['user_m2']=out.common_m2+out.user_only_m2
out['recon_m2']=out.common_m2+out.recon_only_m2
out=out[(out.user_m2+out.recon_m2)>1e-6].set_index('grid_id')
assert np.isclose(out.user_m2.sum(),user.area) and np.isclose(out.recon_m2.sum(),R.area)
out=out.join(m,how='left')
for k in [2015,2025]:assert out.loc[out.recon_m2>1e-6,k].notna().all()
recs=[]
for label,area in [('重建',out.recon_m2),('自有',out.user_m2),('交集',out.common_m2),('仅自有',out.user_only_m2),('仅重建',out.recon_only_m2)]:
    mask=area>1e-6;valid=mask&out[2015].notna()
    r={'范围':label,'格数':int(mask.sum()),'面积km2':area[mask].sum()/1e6,'有现成六指标格数':int(valid.sum()),'有现成六指标面积km2':area[valid].sum()/1e6,'缺少得分格数':int((mask&~valid).sum()),'缺少得分面积km2':area[mask&~valid].sum()/1e6,'既有得分面积覆盖率%':100*area[valid].sum()/area[mask].sum()}
    for year in m.columns:r['既有支持区'+str(year)]=np.average(out.loc[valid,year],weights=area[valid])
    r['既有支持区首末差']=r['既有支持区2025']-r['既有支持区2015']
    r['既有支持区下降面积比例%']=100*area[(out[2025]<out[2015])&valid].sum()/area[valid].sum()
    recs.append(r)
pd.DataFrame(recs).to_csv(w/'边界对照格网支持域.csv',encoding='utf-8-sig',index=False)
out.to_csv(w/'边界对照逐格面积与已有年度得分.csv',encoding='utf-8-sig')
print(pd.DataFrame(recs).iloc[:,np.r_[0:8,-2:0 or None]].round(6).to_string(index=False))
