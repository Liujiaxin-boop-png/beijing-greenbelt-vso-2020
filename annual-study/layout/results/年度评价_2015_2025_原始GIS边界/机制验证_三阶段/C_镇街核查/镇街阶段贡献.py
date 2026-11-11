from pathlib import Path
import json
import pandas as pd,numpy as np
B=Path(__file__).resolve().parent;src=B.parent.parent/'计算结果与核验';gdir=src/'01_全区与格网';tdir=src/'02_镇街与案例'
catalog=pd.read_csv(tdir/'town_catalogue.csv',dtype={'town_id':str}).set_index('town_seq')
fr=pd.read_csv(tdir/'pieces_full.csv',usecols=['town_seq','grid_id','poly_area']);fr=fr.groupby(['town_seq','grid_id'],as_index=False).poly_area.sum();fr['w']=fr.poly_area/1e6
keys=['ER6','C_LDI','C_HQI','C_LBI','C_MCR','C_ALLDIST','C_LRI']
labels=['综合得分','地类多样性','生境质量','景观干扰','源地间通行成本','全格蓝绿距离','地类恢复潜力']
kw=dict(zip(keys,labels))
df=pd.read_csv(gdir/'六项逐格逐年原值与得分.csv.gz',usecols=['year','grid_id','area_km2']+keys);m=df[df.year==2020].set_index('grid_id');den=m.area_km2.sum()
assert m.index.is_unique and len(m)==4478 and len(catalog)==84 and set(fr.grid_id)==set(m.index)
err=(m.area_km2-fr.groupby('grid_id').w.sum()).abs().max();assert err<1e-6
fr=fr.loc[fr.w>0];names=catalog.display_name.to_dict()
years=[2015,2019,2021,2025];groups=np.array([2019,2021]);sy=[(2015,2019),(2019,2021),(2021,2025)]
wide={y:df.loc[df.year==y].set_index('grid_id')[keys] for y in years}
slopes=[(wide[b]-wide[a])/(b-a) for a,b in sy]
twstats=[(v.reindex(fr.grid_id).to_numpy()*fr.w.to_numpy()[:,None]) for v in slopes];tots=[pd.DataFrame(x,columns=keys,index=fr.town_seq).groupby(level=0).sum() for x in twstats]
sgs=[];tc=[];regional=[];close=[];dirs=[]
for i,t in enumerate(tots):
 wg=fr.groupby('town_seq').w.sum()
 for ix,row in t.iterrows():
  e=row/wg[ix];r=row/den;sgs.append({'镇街编码':catalog.town_id[ix],'镇街':names[ix],'地区':catalog.district[ix],'期初':sy[i][0],'期末':sy[i][1],'界内面积_km2':wg[ix],'镇内年均变化分':e.ER6,'对区域年均变化贡献':r.ER6,**{kw[k]+'加权分项_镇内年均变化分':e[k] for k in keys[1:]}})
 for k in keys:
  orig=(slopes[i][k]*m.area_km2).sum()/den;re=t[k].sum()/den;close.append(abs(re-orig))
  regional.append([f'{sy[i][0]}—{sy[i][1]}',kw[k],orig,orig*(sy[i][1]-sy[i][0])])
for i,year in enumerate(groups):
 D=tots[i+1]-tots[i];WG=fr.groupby('town_seq').w.sum();turn=D.sum()/den
 w=fr.copy();w['a']=slopes[i].ER6.reindex(w.grid_id).to_numpy();w['b']=slopes[i+1].ER6.reindex(w.grid_id).to_numpy()
 tol=1e-10
 def label(z,n):return np.select([z*n>tol,z*n< -tol],['升','降'],'持平')
 w['方向']=np.char.add(label(w.a,sy[i][1]-sy[i][0]).astype(str),label(w.b,sy[i+1][1]-sy[i+1][0]).astype(str))
 w['turn_num']=(w.b-w.a)*w.w/den
 for (ix,k),z in w.groupby(['town_seq','方向']):
  dirs.append([int(year),catalog.town_id[ix],names[ix],k,z.w.sum(),z.w.sum()/WG[ix]*100,z.turn_num.sum()])
 for ix,row in D.iterrows():
  area=WG[ix]; c=row/den;regional0=tots[i].loc[ix,'ER6']/area;regional1=tots[i+1].loc[ix,'ER6']/area
  tc.append({'转折年':int(year),'镇街编码':catalog.town_id[ix],'镇街':names[ix],'地区':catalog.district[ix],'界内面积_km2':area,'镇内前期年均变化':regional0,'镇内后期年均变化':regional1,'镇内年均变化的阶段差':c.ER6*den/area,'对全区转折的带符号贡献':c.ER6,'占全区净转折_pct':c.ER6/turn.ER6*100,**{kw[k]+'分项贡献':c[k] for k in keys[1:]}})
  assert abs(c[keys[1:]].sum()-c.ER6)<1e-11
z=pd.DataFrame(tc);z['按与区域转向一致的贡献排名_82个具名镇街']=float('nan')
for y,sign in [(2019,1),(2021,-1)]:
 idx=(z.转折年==y)&(z.地区!='未归属');z.loc[idx,'按与区域转向一致的贡献排名_82个具名镇街']=(z.loc[idx,'对全区转折的带符号贡献']*sign).rank(ascending=False,method='min')
z=z.sort_values(['转折年','按与区域转向一致的贡献排名_82个具名镇街']);z.to_csv(B/'镇街对区域两个转折的面积加权贡献.csv',index=False,encoding='utf-8-sig');pd.DataFrame(sgs).to_csv(B/'镇街三阶段年均变化及六分项.csv',index=False,encoding='utf-8-sig');dz=pd.DataFrame(dirs,columns=['转折年','镇街编码','镇街','镇内格网前后方向','片段面积_km2','占该镇界内面积_pct','对全区转折的带符号贡献']);dz.to_csv(B/'各镇街内实际升降方向与贡献.csv',index=False,encoding='utf-8-sig');pd.DataFrame(regional,columns=['阶段','分项','区域年均变化','阶段净变']).to_csv(B/'全区六分项与阶段净变化的镇界加总核对.csv',index=False,encoding='utf-8-sig')
ref=pd.read_csv(tdir/'镇街六项逐年指数与分项.csv');refs=[ref[ref.year==y].set_index('town_seq') for y in years]
ermax=0
for i,t in enumerate(tots):
 a0,a1=refs[i],refs[i+1];e=t.div(WG,axis=0)-(a1[keys]-a0[keys])/(years[i+1]-years[i]);ermax=max(ermax,np.nanmax(e.abs().values))
assert ermax<2e-7 and max(close)<1e-8
out={'格网':len(m),'具名镇街':sum(catalog.district!='未归属'),'多重归属与空隙面积_km2':float(WG.loc[[82,83]].sum()),'总面积':float(den),'格网拆分加总面积最大误差_km2':float(err),'镇街端点存档核验最大误差':float(ermax),'区域各阶段得分与分项由镇街汇总和原格网所得最大误差':float(max(close))};(B/'复核.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(out)
for y in groups:
 t=z[z.转折年==y].head(5);print(t.round(7).to_string(index=False));print(dz[(dz.转折年==y)&dz.镇街.isin(t.镇街[:2])].round(3).to_string(index=False))

