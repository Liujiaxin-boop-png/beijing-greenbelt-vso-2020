"""Approved six-indicator VSO evaluation with fail-closed data readiness.

All calculations are type-specific. Sensitivity schemes have paired valid
domains; no global complete-case intersection deletes the baseline domain.
The predeclared pool fixes scale endpoints once, before weights or scores.
"""
from pathlib import Path
import json,subprocess,sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/'03_结果文件/indicators'
OUT=ROOT/'03_结果文件/evaluation'
WORK=ROOT/'02_过程文件/evaluation'
METRICS=['HQ_H','NTL','CLUMPY','MCR','SSI','E_fraction']
DIRECTIONS=np.array([1,-1,1,-1,-1,1])
CRITERIA={'V':['HQ_H','NTL'],'S':['CLUMPY','MCR'],'O':['SSI','E_fraction']}
HABITATS=['forest_shrub','grassland','water_wetland']

def normalise(x,lo,hi):
    x=np.asarray(x,dtype=float);span=hi-lo
    z=np.divide(x-lo,span,out=np.zeros_like(x),where=span>0)
    z[:,DIRECTIONS<0]=1-z[:,DIRECTIONS<0]
    z[:,span==0]=0
    assert np.all(np.isfinite(z))
    assert np.min(z)>=-1e-10 and np.max(z)<=1+1e-10,'Endpoint pool omitted a scored observation'
    return np.clip(z,0,1)

def entropy(z):
    z=np.asarray(z,float);n=len(z)
    if n<2:raise ValueError('Entropy requires at least two valid observations')
    total=z.sum(axis=0)
    p=np.divide(z,total,out=np.zeros_like(z),where=total>0)
    plogp=np.zeros_like(p);positive=p>0;plogp[positive]=p[positive]*np.log(p[positive])
    e=-plogp.sum(axis=0)/np.log(n)
    divergence=np.maximum(0,1-e)
    divergence[np.ptp(z,axis=0)<=1e-14]=0
    if divergence.sum()<=1e-14:raise ValueError('All indicators constant: entropy weights unidentifiable')
    weights=divergence/divergence.sum()
    assert np.isclose(weights.sum(),1) and np.all(weights>=0)
    return weights,e,divergence

def score(frame,lo,hi,w):
    f=frame.copy();z=normalise(f[METRICS].to_numpy(),lo,hi)
    for j,name in enumerate(METRICS):f['z_'+name]=z[:,j];f['contribution_'+name]=z[:,j]*w[j]
    f['ER']=z@w
    for criterion,metrics in CRITERIA.items():
        idx=[METRICS.index(m) for m in metrics];den=w[idx].sum()
        f[criterion+'_score']=(z[:,idx]@w[idx])/den if den>0 else np.nan
    dimension=f[[c+'_score' for c in CRITERIA]].to_numpy()
    f['limiting_dimension']=[','.join(np.array(list(CRITERIA))[np.isclose(row,np.nanmin(row),atol=1e-12,rtol=0)]) for row in dimension]
    return f

def describe_pair(b,a,scenario,habitat):
    common=b.index.intersection(a.index)
    if not len(common):return {'scenario':scenario,'habitat':habitat,'n':0,'status':'NO_PAIRED_VALID_DOMAIN'}
    x=b.loc[common,'ER'];y=a.loc[common,'ER'];area=b.loc[common,'scope_area_m2']
    rho=float(spearmanr(x,y).statistic) if len(common)>1 and x.nunique()>1 and y.nunique()>1 else np.nan
    return {'scenario':scenario,'habitat':habitat,'n':len(common),'status':'VALID','baseline_valid_n':len(b),'baseline_valid_area_m2':float(b.scope_area_m2.sum()),'paired_area_m2':float(area.sum()),'spearman_rho':rho,'weighted_mean_difference':float(np.average(y-x,weights=area)),'weighted_MAE':float(np.average(np.abs(y-x),weights=area)),'interpretation':'descriptive paired cell comparison, not causal or independent spatial significance'}

def main():
    master=pd.read_csv(INPUT/'six_indicator_records.csv')
    receipt=json.loads((ROOT/'02_过程文件/aggregation/mcr_aggregation_receipt.json').read_text(encoding='utf8'))
    if receipt['status']!='COMPLETE':raise RuntimeError('MCR scenarios incomplete; final evaluation is not run')
    if master.NTL.notna().sum()==0:raise RuntimeError('EOG2020 NTL with original observation coverage is missing; no synthetic substitution')
    ntlqa=ROOT/'02_过程文件/aggregation/ntl_aggregation_receipt.json'
    if not ntlqa.exists() or json.loads(ntlqa.read_text(encoding='utf8'))['status']!='PASS':raise RuntimeError('Original NTL / cf_cvg alignment and valid coverage have not passed')
    OUT.mkdir(exist_ok=True);WORK.mkdir(exist_ok=True)
    mcr=pd.read_csv(INPUT/'mcr_by_grid.csv');allscored=[];normrecords=[];weightrecords=[];paired=[];coverage=[];reweight=[];correlations=[];descriptives=[]
    for habitat in HABITATS:
        valid=master.six_valid.astype(bool)
        b=master[(master.habitat==habitat)&(master['product']=='clcd')&(master.scale_m==1000)&valid].copy().set_index('grid_id',drop=False)
        if len(b)<2:raise RuntimeError('Insufficient complete baseline '+habitat)
        rho=b[METRICS].corr(method='spearman')
        for i,name in enumerate(METRICS):
            for other in METRICS[i+1:]:correlations.append({'habitat':habitat,'indicator_1':name,'indicator_2':other,'spearman_rho':rho.loc[name,other],'n':len(b),'domain':'baseline six-valid','meaning':'shared information diagnosis; not component-versus-total causal analysis'})
            v=b[name].to_numpy();ar=b.scope_area_m2.to_numpy();mean=float(np.average(v,weights=ar))
            descriptives.append({'habitat':habitat,'indicator':name,'n':len(b),'minimum':float(v.min()),'maximum':float(v.max()),'area_weighted_mean':mean,'area_weighted_sd':float(np.sqrt(np.average((v-mean)**2,weights=ar))),'unweighted_median':float(np.median(v))})
        candidates={}
        wc=master[(master.habitat==habitat)&(master['product']=='wc')&(master.scale_m==1000)&valid].copy().set_index('grid_id',drop=False)
        candidates['worldcover']=wc.loc[wc.index.intersection(b.index)].copy()
        for label in ['core35_land_road','core100_land_road','core10_land_only']:
            sel=mcr[(mcr.scenario=='clcd_'+habitat+'_'+label)&(mcr.scale_m==1000)].set_index('grid_id')
            f=b.copy()
            for col in [c for c in sel if c.startswith('MCR') or c in ['target_truncated_fraction','destination_truncated_fraction']]:f[col]=sel[col].reindex(f.index)
            f=f.dropna(subset=METRICS)
            candidates[label]=f
        crop=b.copy();crop['SSI']=crop.SSI_crop_included;crop['E_fraction']=crop.E_fraction_crop_included;candidates['crop_in_ecological_space']=crop.dropna(subset=METRICS)
        fine=master[(master.habitat==habitat)&(master['product']=='clcd')&(master.scale_m==500)&valid].copy().set_index('grid_id',drop=False)
        # Stable grid origin lets a 500m square map to one containing 1km square.
        # Explicit geometry correspondence is authoritative, not guessed row IDs.
        grid_info=json.loads((ROOT/'02_过程文件/spatial/grid_identity.json').read_text(encoding='utf8'))['grids']
        parents={}
        origins=np.array(json.loads((ROOT/'02_过程文件/spatial/native_config.json').read_text(encoding='utf8'))['origin_xy'])
        main_bounds={tuple(np.rint((np.array(g['bounds'][:2])-origins)/1000).astype(int)):g['grid_id'] for g in grid_info if g['scale_m']==1000}
        # Read real main-square coordinates; index by midpoint containment.
        for g in grid_info:
            if g['scale_m']!=500:continue
            x,y=g['bounds'][0],g['bounds'][1]
            key=tuple(np.floor((np.array([x,y])-origins+1e-7)/1000).astype(int))
            if key in main_bounds:parents[g['grid_id']]=main_bounds[key]
        fine['parent_grid_id']=fine.grid_id.map(parents)
        assert fine.parent_grid_id.notna().all(),'Every valid500m square must have one actual1km parent'
        fine=fine[fine.parent_grid_id.isin(b.index)].copy()
        # Pool only observations that will actually be scored in a declared
        # pairwise comparison, together with every baseline-valid observation.
        pool=pd.concat([b]+[v for v in candidates.values() if len(v)]+([fine] if len(fine) else []),ignore_index=True)
        lo=pool[METRICS].min().to_numpy();hi=pool[METRICS].max().to_numpy()
        z=normalise(b[METRICS].to_numpy(),lo,hi);w,e,d=entropy(z)
        for j,name in enumerate(METRICS):
            normrecords.append({'habitat':habitat,'indicator':name,'minimum':lo[j],'maximum':hi[j],'direction':int(DIRECTIONS[j]),'reference':'predeclared scored scenario union, not complete-case intersection'})
            weightrecords.append({'habitat':habitat,'indicator':name,'weight':w[j],'entropy':e[j],'divergence':d[j],'baseline_n':len(b)})
        bs=score(b,lo,hi,w);bs['scenario']='baseline';allscored.append(bs)
        coverage.append({'habitat':habitat,'scenario':'baseline','n':len(b),'area_m2':float(b.scope_area_m2.sum())})
        for scenario,f in candidates.items():
            if not len(f):
                paired.append(describe_pair(bs,f,scenario,habitat));coverage.append({'habitat':habitat,'scenario':scenario,'n':0,'area_m2':0.,'status':'NO_PAIRED_VALID_DOMAIN'});continue
            a=score(f,lo,hi,w);a['scenario']=scenario;allscored.append(a);paired.append(describe_pair(bs,a,scenario,habitat))
            coverage.append({'habitat':habitat,'scenario':scenario,'n':len(a),'area_m2':float(a.scope_area_m2.sum())})
            # Reweight both sides on this same domain to separate sample-domain
            # change from estimation of the weights themselves.
            try:
                wb,_,_=entropy(normalise(b.loc[f.index,METRICS].to_numpy(),lo,hi))
                wa,_,_=entropy(normalise(f[METRICS].to_numpy(),lo,hi))
            except ValueError as err:
                for j,name in enumerate(METRICS):reweight.append({'habitat':habitat,'scenario':scenario,'indicator':name,'baseline_full_weight':w[j],'baseline_paired_weight':np.nan,'scenario_paired_weight':np.nan,'paired_n':len(f),'status':'NOT_ESTIMABLE','reason':str(err)})
            else:
                for j,name in enumerate(METRICS):reweight.append({'habitat':habitat,'scenario':scenario,'indicator':name,'baseline_full_weight':w[j],'baseline_paired_weight':wb[j],'scenario_paired_weight':wa[j],'paired_n':len(f),'status':'VALID','reason':''})
                ar=score(f,lo,hi,wa);ar['scenario']=scenario+'_reweighted';allscored.append(ar)
                br=score(b.loc[f.index],lo,hi,wb);br['scenario']='baseline_paired_'+scenario+'_reweighted';allscored.append(br)
                paired.append(describe_pair(br,ar,scenario+'_paired_reestimated_weights',habitat))
        for j,name in enumerate(METRICS):
            wr=w.copy();wr[j]=0
            if wr.sum()<=1e-14:continue
            wr/=wr.sum();a=score(b,lo,hi,wr);a['scenario']='omit_'+name;allscored.append(a);paired.append(describe_pair(bs,a,'omit_'+name,habitat))
            coverage.append({'habitat':habitat,'scenario':'omit_'+name,'n':len(a),'area_m2':float(a.scope_area_m2.sum())})
        if len(fine):
            fs=score(fine,lo,hi,w);fs['scenario']='scale500_native';allscored.append(fs)
            rows=[]
            for gid,g in fs.groupby('parent_grid_id'):
                weights=g.scope_area_m2.to_numpy();r={'grid_id':gid,'habitat':habitat,'scenario':'scale500_to1000','scale_m':1000,'product':'clcd','scope_area_m2':float(weights.sum()),'fine_valid_fraction':float(weights.sum()/b.loc[gid,'scope_area_m2'])}
                for col in ['ER']+[c+'_score' for c in CRITERIA]:r[col]=float(np.average(g[col],weights=weights))
                rows.append(r)
            agg=pd.DataFrame(rows).set_index('grid_id',drop=False)
            full=np.isclose(agg.fine_valid_fraction,1,atol=1e-8,rtol=0)
            agg['scenario']=np.where(full,'scale500_to1000_full_coverage','scale500_to1000_partial_coverage')
            allscored.append(agg)
            for scen,g in agg.groupby('scenario'):coverage.append({'habitat':habitat,'scenario':scen,'n':len(g),'area_m2':float(g.scope_area_m2.sum()),'status':'FULL_BASELINE_SUPPORT' if scen.endswith('_full_coverage') else 'PARTIAL_FINE_SUPPORT_NOT_COMPARABLE'})
            paired.append(describe_pair(bs,agg.loc[full],'scale500_to1000_full_coverage',habitat))
            partial=agg.loc[~full]
            paired.append({'scenario':'scale500_to1000_partial_coverage','habitat':habitat,'n':len(partial),'status':'NOT_COMPARABLE_DIFFERENT_WITHIN_GRID_SUPPORT','fine_valid_area_m2':float(partial.scope_area_m2.sum()),'corresponding_baseline_area_m2':float(bs.loc[partial.index,'scope_area_m2'].sum()),'interpretation':'partial fine-cell support retained for coverage diagnosis; no equal-domain rank or score error claimed'})
    scores=pd.concat(allscored,ignore_index=True)
    scores.to_csv(OUT/'scores_all_scenarios.csv',index=False,encoding='utf-8-sig')
    for name,rows in [('normalization',normrecords),('entropy_weights',weightrecords),('paired_sensitivity',paired),('scenario_coverage',coverage),('reestimated_weights',reweight),('indicator_correlations',correlations),('indicator_descriptives',descriptives)]:pd.DataFrame(rows).to_csv(OUT/(name+'.csv'),index=False,encoding='utf-8-sig')
    report={'status':'SCORES_COMPUTED_CLASSIFICATION_AND_MAPS_PENDING','normalization':'one frozen favorable minmax per habitat, using predeclared comparison observation union','baseline_domain':'all baseline six-valid 1km cells; never removed for scenario missingness','entropy_domain':'baseline only, reestimation separate','classification':'native QGIS Jenks five baseline classes, then fixed bounds in comparisons; Shi2022 section2.3 and Fig2; not universal ecological thresholds','no_causal_driver_regression':True,'records':len(scores)}
    (WORK/'evaluation_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(report)

if __name__=='__main__':main()
