from pathlib import Path
import json,pandas as pd,numpy as np
w=Path(__file__).resolve().parent
town=pd.read_csv(w/'82镇街首末年分型与敏感性.csv')
ann=pd.read_csv(w.parent/'core/六项逐格逐年原值与得分.csv.gz')
m=pd.read_csv(w/'全区各格MCR源地与阻力面双方案分解.csv')
tmp=ann[ann.year.isin([2015,2025])].pivot(index='grid_id',columns='year',values='MCR')
check=m.set_index('grid_id').reindex(tmp.index)
errs={}
for y in [2015,2025]:
    errs[y]=float(max(abs(tmp[y]-check['mcr'+str(y)])))
    assert np.allclose(tmp[y],check['mcr'+str(y)],rtol=.000001,atol=.01)
assert np.max(abs(check.delta_MCR_raw-check.source-check.resistance))<1e-7
grid=ann[ann.year==2015][['grid_id','area_km2']].merge(m)
mcr_sample={}
for l,ww in [('region',grid)]:
    mcr_sample[l]={k:float(np.average(ww[k],weights=ww.area_km2)) for k in ['mcr2015','mcr2025','delta_MCR_raw','resistance','source']}
px=pd.read_csv(w/'patch_grid_contributions.csv').merge(m,on='grid_id',validate='m:1')
for code,sub in px.groupby('code'):
    mcr_sample[code]={k:float(np.average(sub[k],weights=sub.area_km2)) for k in ['mcr2015','mcr2025','delta_MCR_raw','resistance','source']}
pd.DataFrame.from_dict(mcr_sample,orient='index').rename_axis('code').to_csv(w/'全格和八个片区MCR两项模型输入格网贡献.csv',encoding='utf-8-sig')
cnt=lambda mask:int(mask.sum())
info=[]
for k,h in town.groupby('base_type'):
    a=h.km2.to_numpy()
    info.append(dict(k=k,n=len(h),area=sum(a),netmedian=h.delta.median(),pcmedian=h.down_share.median(),
                     netw=np.average(h.delta,weights=a),downp=np.average(h.down_share,weights=a),
                     hqdn=cnt(h.delta_HQI<0),lridn=cnt(h.delta_LRI<0),distup=cnt(h.delta_ALLDIST>0),
                     HQw=np.average(h.delta_HQI,weights=a),LRIw=np.average(h.delta_LRI,weights=a),distw=np.average(h.delta_ALLDIST,weights=a),
                     mcrup=cnt(h.delta_MCR>0),joint=cnt((h.delta_HQI>0)&(h.delta_MCR>0))))
pd.DataFrame(info).to_csv(w/'类型内全部镇街概况.csv',index=False,encoding='utf-8-sig')
case=town[town.nominated_1km2].sort_values('base_type')
l=pd.read_csv(w/'全镇街CLCD逐年地类面积_公顷.csv')
pr=pd.read_csv(w/'全镇街两套产品2017至2025建成林木水湿变化.csv')
tg=pd.read_csv(w/'四镇每格蓝绿面积净变与两项条件.csv')
trans=pd.read_csv(w/'patch_land_transitions.csv')
hg=pd.read_csv(w/'case_hotspots.csv')
roads=pd.read_csv(w/'patch_road_landmarks.csv')
tp=pd.read_csv(w/'八片区像元质量四因素与用地组分解.csv')
md=[]
def table(f,cols,d=4):
    return f[cols].round(d).to_string(index=False)
s={}
for r in case.itertuples():
    name=r.display_name;d=tg[tg.town==name];v=l[l.town_seq==r.town_seq].set_index('year');pw=pr[pr.town_seq==r.town_seq].iloc[0]
    vals=(v.loc[2025,['林灌草','蓝绿','水湿','不透水面']]-v.loc[2015,['林灌草','蓝绿','水湿','不透水面']]).to_dict()
    dual=d.same;vv=d.net_green;blue=(d.cut_bg_ha>1e-5)&(d.whole_bg_ha>1e-5)
    s[name]={'type':r.base_type,'net_area_ha':vals,'product_change_pp':{p:pw[p+'_built_delta_pp'] for p in ('CLCD','Esri')},'paired_grid_tests':{'n':len(d),'netveg':cnt(vv),'netbluegreen':cnt(blue),'joint_with_netveg':cnt(vv&dual),'joint_with_bluegreen':cnt(blue&dual),'both_improve_all_grids':cnt(dual)},'patches':{}}
    for rec in hg[hg.seq==r.town_seq].itertuples():
        code=rec.code
        p=trans[(trans.code==code)&(trans['from']!=trans.to)]
        s[name]['patches'][code]={'marker_quadrant':rec.point_quad,'size_ha':100*rec.area_km2,'same_fraction':rec.fraction_of_same_sign,'clcd_top_changes_ha':p.nlargest(4,'ha')[['from','to','ha']].to_dict('records'),'roads':roads[roads.code==code].head(3).road.tolist(),'grid_MCR_decomposition':mcr_sample[code]}
s['regionMCR']=mcr_sample['region'];s['MCR_max_abs_discrepancy_native_vs_panel']=errs
s['counts_ge1']=int((town.km2>=1).sum());s['counts_ge2']=int((town.km2>=2).sum())
s['threshold_flip_names']={q:town[town.base_type!=town[q]].display_name.tolist() for q in ['equal_type','sen_type']}
s['near_50']=town[town.down_share.between(45,55)][['display_name','base_type','down_share']].to_dict('records')
s['full_vs_common_changes']=town[town.common_type.isin(list('ABCD'))&(town.common_type!=town.base_type)][['display_name','base_type','common_type','common_km2']].to_dict('records')
s['new_edge_towns']=town[town.common_km2.isna()][['display_name','base_type','km2']].to_dict('records')
(w/'案例与全域核查总表.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),'utf8')
print(table(pd.DataFrame(info),['k','n','area','netw','downp','hqdn','lridn','distup','mcrup','joint']))
for name in case.display_name:
    res=s[name]
    print(name,res['net_area_ha'],res['paired_grid_tests'])
    for code,t in res['patches'].items():print(code,t['marker_quadrant'],'主要转换',[(a['from']+a['to'],round(a['ha'],2)) for a in t['clcd_top_changes_ha']],t['roads'])
print(s['regionMCR'],s['MCR_max_abs_discrepancy_native_vs_panel'])
print(s['full_vs_common_changes'],s['new_edge_towns'])
