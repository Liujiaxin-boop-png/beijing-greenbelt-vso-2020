# -*- coding: utf-8 -*-
"""在新的运行目录重建机制统计及案例。输入起点与输出范围逐项登记。"""
from pathlib import Path
from datetime import datetime
import argparse, hashlib, os, subprocess, sys, shutil, json, importlib.util
import pandas as pd
import numpy as np
W=Path('D:/ER219_work/shp11'); A=Path('D:/ER219_work/annual_actual')

def main():
    opt=argparse.ArgumentParser(description=__doc__)
    opt.add_argument('--out',type=Path,default=Path.home()/'Documents'/'二道绿隔机制复核',help='选择个人目录；每次自动新建带时间的目录，不修改历史输出')
    opt.add_argument('--panel',type=Path,default=W/'core',help='可改为从原始数据重跑得到的 panel，栅格模型输入仍取本机归档。')
    o=opt.parse_args()
    root=o.out.resolve()
    for pr in ['D:/ER219_raw','D:/ER219_work','D:/ER219_results','D:/ER219_figures','D:/ER219_code']:
        pp=Path(pr).resolve()
        if root==pp or pp in root.parents: raise ValueError('请选择原始、过程、结果和代码存档外的个人目录。')
    run=root/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    c=run/'core'; t=run/'towns';c.mkdir(parents=True);t.mkdir()
    manifest=[];summary=[]
    def h(p):
        with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
    def copy(src,dest):
        manifest.append({'输入副本':str(src.resolve()),'指纹':h(src)})
        shutil.copyfile(src,dest)
    # Only copies; no links to data that an upstream script could overwrite.
    for n in ['六项格网十年变化.csv','六项逐格逐年原值与得分.csv.gz','parameters.json','annual_grid_500.gpkg','domain.json']:
        copy(o.panel/n,c/n)
    copy(W/'core/候选指标_500m.csv.gz',c/'候选指标_500m.csv.gz')
    for n in ['planning_towns.gpkg','四类入选镇街指标与增减地段强度.csv','pieces_full.csv','town_catalogue.csv','全镇街两套产品2017至2025建成林木水湿变化.csv']:
        copy(W/'towns'/n,t/n)
    def job(source,group):
        dest=run/group/source;copy(W/group/source,dest)
        print('复算',source,'…',flush=True)
        with (run/(source+'.log')).open('wb') as log:
            res=subprocess.run([sys.executable,'-B',str(dest)],cwd=dest.parent,stdout=log,stderr=log,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'})
        if res.returncode!=0:raise RuntimeError(str(run/(source+'.log'))+' 报错，请打开日志。')
    def check(src,ref,keys,columns,tol):
        a=pd.read_csv(src);b=pd.read_csv(ref)
        if keys:
            a=a.set_index(keys).sort_index();b=b.set_index(keys).sort_index()
            if not a.index.equals(b.index):raise AssertionError(str(src)+' 样本键不一致')
        assert len(a)==len(b)>0
        err=float(np.nanmax(np.abs(a[columns].to_numpy(float)-b[columns].to_numpy(float))))
        if not (err<=tol and np.array_equal(a[columns].isna(),b[columns].isna())):raise AssertionError((src,err,tol))
        return err
    def note(name,source,action,out,err):
        summary.append(dict(实验=name,本次起点=source,本次确实重算=action,结果=out,与归档对照最大差=float(err)))
        pd.DataFrame(summary).to_csv(run/'结果与输入层级.csv',index=False,encoding='utf-8-sig')
    job('hq_attribution.py','core')
    n='HQI_input_attribution.csv';col=['delta_HQI','delta_HQI_land_class','delta_HQI_built_field','delta_HQI_crop_field','delta_HQI_road_field']
    err=check(c/n,W/'core'/n,['id'],col,1e-9);d=pd.read_csv(c/n).iloc[0]
    note('模型生境质量四因素分解','首末CLCD、归档已卷积三威胁场、固定参数，未重跑威胁卷积','按30 m重新计算全部16种生境质量，并按24种可能顺序的等价权重分解；再叠合4478整格作界内面积加权',f'HQI总差{d.delta_HQI:.8f}，地类{d.delta_HQI_land_class/d.delta_HQI:.2%}、道路{d.delta_HQI_road_field/d.delta_HQI:.2%}',err)
    job('distance_parts.py','core')
    n='蓝绿空间距离的数量与区位分项_归因.csv';col=['change_m','nonbluegreen_fraction_component_m','nonbluegreen_conditional_distance_component_m']
    err=check(c/n,W/'core'/n,['start','end'],col,1e-6);d=pd.read_csv(c/n).iloc[0]
    note('蓝绿距离数量和位置','归档各格年度蓝绿面积比例、平均距离、界内面积（未重新求距离场）','重新逐年计算区域面积加权距离、非蓝绿面积比例与条件均距，对两端做两项分解',f'全期 {d.change_m:.5f} m；两项为 {d.iloc[-2]:.5f}、{d.iloc[-1]:.5f} m',err)
    job('mcr_decomposition.py','towns')
    n='全区各格MCR源地与阻力面双方案分解.csv';col=['mcr2015','mcr2025','delta_MCR_raw','source','resistance']
    err=check(t/n,W/'towns'/n,['grid_id'],col,1e-5)
    g=pd.read_csv(c/'六项格网十年变化.csv');v=pd.read_csv(t/n).merge(g[['grid_id','area_km2']],validate='1:1')
    total=np.average(v[col[2:]],axis=0,weights=v.area_km2)
    assert np.max(abs(v.delta_MCR_raw-v.source-v.resistance))<1e-7
    note('源地与阻力面','首末两情景和两个交叉情景的30 m累计成本场，来自已保存的寻路结果','从四幅场重新提取每个完整格的像元面积加权均值，计算替换两种顺序的平均边际差，检查4478格闭合',f'原值全区净差{total[0]:.5f}；源地{total[1]:.5f}，阻力面{total[2]:.5f}',err)
    job('case_patch_evidence.py','towns')
    n='case_hotspots.csv';cols=['area_km2','fraction_of_same_sign','delta','delta_HQI','delta_MCR','n_grids']
    err=check(t/n,W/'towns'/n,['code'],cols,1e-8)
    assert check(t/'patch_land_transitions.csv',W/'towns/patch_land_transitions.csv',['code','from','to'],['ha','pct'],1e-7)<1e-7
    note('四镇最大连续片与地类转换','归档镇界叠置、上一步使用的首末单格得分、归档选例名单；非凭位置挑选','对实际镇内碎面按升降与共边重新连片，各取面积最大的上/下降片和标记；在两期CLCD逐像元累计各片转换公顷数','8个最大连续变化片；另见towns/case_hotspots.csv、patch_land_transitions.csv',err)
    patch=pd.read_csv(t/'patch_grid_contributions.csv').merge(v[['grid_id',*col]],on='grid_id',validate='m:1')
    pat=[{'code':'region',**dict(zip(col,np.average(v[col],axis=0,weights=v.area_km2)))}]
    for code,blk in patch.groupby('code'):pat.append({'code':code,**dict(zip(col,np.average(blk[col],axis=0,weights=blk.area_km2)))})
    n='全格和八个片区MCR两项模型输入格网贡献.csv';pd.DataFrame(pat).to_csv(t/n,index=False,encoding='utf-8-sig')
    err=check(t/n,W/'towns'/n,['code'],col,1e-5)
    note('八片区的斑块联系变化','本轮新生成的片区与格网相交面积、四输入格网统计','同一片内按片格交面积求平均，两种贡献相加核对MCR原值差','全区和8片区，见towns/'+n,err)
    job('pixel_habitat.py','towns')
    n='八片区像元质量四因素与用地组分解.csv';cols=['ha','local_classes','built','crop','road','hq_change','mcr_change']
    err=check(t/n,W/'towns'/n,['code','group'],cols,1e-7)
    note('片区内部生境质量四因素','新划出的八个变化片；首末CLCD、质量、已卷积威胁场和通行成本场','按像元实际落在片区的比例重建16种质量，分别在整片和转入、保留、转出林灌草等组内求平均','见towns/'+n+'；面积为实际片内公顷，并非整格代理',err)
    job('pixel_mcr.py','towns')
    n='八片区MCR两项模型输入变化分解.csv';cols=['mcr2015','mcr2025','cost15sources25','cost25sources15','delta_MCR_raw','resistance','source']
    err=check(t/n,W/'towns'/n,['code'],cols,1e-7)
    note('片区内部源地和阻力面','新划片区与四组既有累计成本场','按像元落在各片区的实际比例重新计算两个模型输入的贡献','见towns/'+n+'；与先算完整格再加权为不同空间口径',err)
    job('grid_product.py','towns')
    n='全区两产品共有效建设变化.csv';cols=['valid_ha','CLCD_delta_pp','Esri_delta_pp','CLCD_delta_ha','Esri_delta_ha'];err=check(t/n,W/'towns'/n,[],cols,1e-6)
    z=pd.read_csv(t/n).iloc[0]
    note('两产品建设地变化','2017与2025的CLCD、Esri对齐30 m栅格及固定镇街；未重新下载/投影产品','四幅图逐像元取共同有效交集，计入真实相交比例，分产品统计新增、退出和净差','CLCD %+0.5f、Esri %+0.5f 个百分点'%(z.CLCD_delta_pp,z.Esri_delta_pp),err)
    bld=pd.read_csv(t/'全区4478格两产品共有效建设变化.csv.gz').merge(g,on='grid_id',validate='1:1')
    bld['a']=bld.valid_ha/100;bld['x']=bld.Esri_delta_ha/bld.valid_ha;bld['y']=bld.ER2025-bld.ER2017
    def rho(x,y):return float(x.rank().corr(y.rank()))
    rr=[[.5,len(bld),rho(bld.x,bld.y)]]
    for km in [3,5,10]:
        ag=bld.assign(xs=bld.x*bld.a,ys=bld.y*bld.a).groupby([bld.ix//(km*2),bld.iy//(km*2)])[['a','xs','ys']].sum()
        rr.append([km,len(ag),rho(ag['xs']/ag.a,ag['ys']/ag.a)])
    pd.DataFrame(rr,columns=['边长km','单元数','与同区间ER变化的Spearman']).to_csv(run/'Esri建设地变化关联.csv',index=False,encoding='utf-8-sig')
    ref=json.loads((W/'checks/figures_cross.json').read_text(encoding='utf8'))['Esri_2017_2025_v_exact_scope_km2']
    targets=[ref['rho']]+[ref['block'][str(k)]['rho'] for k in [3,5,10]]
    err=max(abs(v[-1]-u) for v,u in zip(rr,targets));assert err<1e-7
    note('建成地变化与指数的同期关联','本轮Esri共同有效范围的净变化；2017和2025同一格ER','逐格排名计算Spearman，仅以共同有效面积将两个变量汇总至3/5/10 km再分别排名','500米、3、5、10公里依次'+', '.join('%.3f'%v[-1] for v in rr),err)
    # All raw transfers are freshly generated above.
    copy(W/'towns/82镇街首末年分型与敏感性.csv',t/'82镇街首末年分型与敏感性.csv')
    job('paired_every_town.py','towns')
    n='镇街内增绿与质量联系同步格网对照.csv';cols=['veg_gain_n','veg_coimprove_n','bluegreen_gain_n','bluegreen_coimprove_n'];err=check(t/n,W/'towns'/n,['town_seq'],cols,1e-12)
    z=pd.read_csv(t/n);idx=z.nominated_1km2.eq(True)
    note('四镇增绿与同步改善','本轮格镇地类转移、首末CLCD、HQI与通行成本的格网贡献','检查完整格与镇内面积均净增的格网，再检验两项贡献是否同时为正；分开林灌草与含水湿地的蓝绿','四镇林灌草增量且两项同时改善为%d格。'%z.loc[idx,'veg_coimprove_n'].sum(),err)
    # Turn accounting from original per-grid components, independent of formatted stage/slope tables.
    ann=pd.read_csv(c/'六项逐格逐年原值与得分.csv.gz');fs=['ER6','C_LDI','C_HQI','C_LBI','C_MCR','C_ALLDIST','C_LRI']
    av={int(y):np.average(s[fs],axis=0,weights=s.area_km2) for y,s in ann.groupby('year')}
    slopes=np.array([(av[b]-av[a])/(b-a) for a,b in [(2015,2019),(2019,2021),(2021,2025)]])
    stages=np.vstack([slopes,np.diff(slopes,axis=0)])
    assert np.max(abs(stages[:,0]-stages[:,1:].sum(axis=1)))<1e-12
    ref=pd.read_csv(W/'method_clarify/三个阶段与两次转折_六项固定权重分解.csv').iloc[:,2:].to_numpy()
    err=float(np.max(abs(stages-ref)));assert err<1e-11
    z=pd.DataFrame(stages,columns=fs);z.insert(0,'阶段或转向',['2015—2019','2019—2021','2021—2025','2019转向','2021转向']);z.to_csv(run/'三个阶段与两次转向.csv',encoding='utf-8-sig',index=False)
    note('阶段与转向','逐年逐格已加权分项与界内面积（没有重新估权）','从各格出发汇总年度，再以4/2/4年求阶段速度和两次速度差；核对六项贡献可加回总差',f'{stages[-2,0]:+.10f}、{stages[-1,0]:+.10f}分/年，不是统计断点检验',err)
    # Recompute the area's weighted control distribution separately by district.
    pilot={'长辛店镇','宋庄镇','台湖镇','青云店镇','金盏地区','高丽营镇'}
    cat=pd.read_csv(t/'town_catalogue.csv');pieces=pd.read_csv(t/'pieces_full.csv')
    z=pieces.merge(cat[['town_seq','town_id','display_name','district']],on='town_seq',validate='m:1').merge(g[['grid_id','ER2015','delta']],on='grid_id',validate='m:1')
    z=z[~z.town_id.str.startswith('UN_')].copy();z['pilot']=z.display_name.isin(pilot);z['a']=z.poly_area/1e6
    z=z[z.district.isin(z.loc[z.pilot,'district'])].copy()
    outrows=[]
    for n in (1,3,5,10):
        data=[]
        for dd,sl in z.groupby('district'):
            base=sl[~sl.pilot].sort_values('ER2015');cumu=base.a.cumsum().to_numpy()
            q=base.ER2015.to_numpy()[np.searchsorted(cumu,cumu[-1]*np.arange(1,n)/n)]
            for _,h0 in sl.groupby(np.searchsorted(q,sl.ER2015,side='right')):
                aa=h0[h0.pilot];bb=h0[~h0.pilot]
                if not len(aa) or not len(bb):continue
                data.append((aa.a.sum(),np.average(aa.delta,weights=aa.a),np.average(bb.delta,weights=bb.a)))
        ar=np.asarray(data);u1,u2=np.average(ar[:,1:],weights=ar[:,0],axis=0);outrows.append((n,ar[:,0].sum(),u1,u2,u1-u2))
    pp=run/'试点组分层对照.csv';cols=['matched_km2','pilot_delta','control_delta','difference'];pd.DataFrame(outrows,columns=['bins',*cols]).to_csv(pp,index=False,encoding='utf-8-sig')
    err=check(pp,W/'towns'/pp.name,['bins'],cols,1e-6)
    note('试点比较','首末每格得分、镇界叠置面积、既定首批六镇名单','在同区非试点按基期得分与面积分位定层；两组在层内求面积加权净差，以试点层面积合并','1层与10层的组间差依次%+.6f、%+.6f；不能据此判断政策因果'%(outrows[0][-1],outrows[-1][-1]),err)
    pd.DataFrame(manifest).to_csv(run/'工作副本来源.csv',index=False,encoding='utf-8-sig')
    print('通过',len(summary),'项。结果：',run,flush=True)
if __name__=='__main__': main()
