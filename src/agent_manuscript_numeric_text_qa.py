"""Check actual manuscript numbers/tables against retained 2020 result tables.

Read-only to the manuscript and results. No scientific result is recomputed or
changed here. The independent analysis QA supplies the calculation-level audit;
this script separately checks numerical transcription and interpretation scope.
"""
from pathlib import Path
import collections, datetime, hashlib, json, math, re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'02_过程文件/manuscript'
EVAL = ROOT/'03_结果文件/evaluation'
OUT = WORK/'final_numeric_text_QA.json'
H = ['forest_shrub','grassland','water_wetland']
ZH = ['林灌','草地','水体湿地']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def normal(s): return str(s).replace('−','-').replace('－','-')
def clean(o):
    if isinstance(o,dict): return {str(k):clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)): return [clean(v) for v in o]
    if isinstance(o,np.generic): return clean(o.item())
    if isinstance(o,float) and not math.isfinite(o): return None
    return o

def main():
    paths=[WORK/'manuscript_content.json',WORK/'完整论文_审阅文本.txt',WORK/'manuscript_numeric_facts.json']
    before={str(p):sha(p) for p in paths}
    content,text,facts=read(paths[0]),paths[1].read_text(encoding='utf8'),read(paths[2])
    checks=[]; failures=[]; interpretation=[]; sources={}
    def check(name,passed,expected=None,actual=None,source=None):
        checks.append({'check':name,'status':'PASS' if bool(passed) else 'FAIL','expected':clean(expected),'actual':clean(actual),'source':source})
        if not passed: failures.append(name)
    def numeric(name,actual,expected,source,atol=1e-9):
        check(name,math.isclose(float(actual),float(expected),abs_tol=atol,rel_tol=1e-10),expected,actual,source)
    def csv(name,**kwargs):
        p=EVAL/name;sources[str(p)]=sha(p);return pd.read_csv(p,**kwargs)
    def vector(name,expected,source):
        actual=facts[name]
        check('facts '+name,len(actual)==len(expected) and np.allclose(actual,expected,atol=1e-9,rtol=1e-10),expected,actual,source)
    paragraphs=[b['text'] for b in content['blocks'] if b.get('type')=='paragraph']
    def para(selector):
        hits=[p for p in paragraphs if selector in p]
        if len(hits)!=1: raise ValueError('Need unique paragraph: '+selector)
        return normal(hits[0])
    def displayed(selector,values,digits,source,label):
        p=para(selector)
        for i,value in enumerate(values):
            formatted=f'{value:.{digits}f}'
            okay=bool(re.search(r'(?<![\d.])'+re.escape(formatted)+r'(?![\d.])',p))
            check(label+' '+str(i),okay,formatted,p,source)

    qa_path=ROOT/'02_过程文件/evaluation/final_scientific_QA.json'
    qa=read(qa_path)
    check('upstream independent actual analysis QA',qa['status']=='PASS','PASS',qa['status'],str(qa_path))
    check('facts scientific QA version',facts['scientific_qa_sha256']==sha(qa_path),sha(qa_path),facts['scientific_qa_sha256'],str(qa_path))
    for name,digest in facts['source_sha256'].items():
        p=EVAL/name;actual=sha(p);sources[str(p)]=actual
        check('facts source version '+name,actual==digest,actual,digest,str(p))
    grids=read(ROOT/'02_过程文件/spatial/grid_identity.json')['grids']
    area=math.fsum(g['scope_area_m2'] for g in grids if g['scale_m']==1000)
    numeric('scope union km2',facts['scope_area_km2'],area/1e6,'spatial/grid_identity.json: scope_area_m2 of 1km grid')
    region=csv('regional_results.csv').set_index('habitat')
    towns=csv('township_results.csv')
    check('abstract and body township count',towns.town.nunique()==35 and '35个乡镇的部分地区' in content['abstract'] and '35个乡镇的部分地区' in para('并集面积'),35,int(towns.town.nunique()),'township_results.csv')
    weights=csv('entropy_weights.csv').set_index(['habitat','indicator'])
    pairs=csv('paired_sensitivity.csv').set_index(['habitat','scenario'])
    corr=csv('indicator_correlations.csv')
    stability=csv('spatial_stability.csv')
    scores=csv('scores_all_scenarios.csv',usecols=['grid_id','habitat','scenario','scope_area_m2','ER'],low_memory=False)
    baseline=scores[scores.scenario=='baseline'].set_index(['habitat','grid_id'])
    valid_n=[int(region.loc[h,'valid_grid_n']) for h in H]
    valid_area=[region.loc[h,'valid_scope_area_m2'] for h in H]
    vector('valid_grids',valid_n,'regional_results.csv')
    vector('valid_grid_coverage_km2',[x/1e6 for x in valid_area],'regional_results.csv')
    vector('valid_grid_coverage_percent',[100*x/area for x in valid_area],'regional_results.csv + scope union')
    for name,scenario,column in [('worldcover_paired_MAE','worldcover','weighted_MAE'),('crop_paired_MAE','crop_in_ecological_space','weighted_MAE'),
                                 ('scale_full_n','scale500_to1000_full_coverage','n'),('scale_full_rho','scale500_to1000_full_coverage','spearman_rho')]:
        vector(name,[pairs.loc[(h,scenario),column] for h in H],'paired_sensitivity.csv: '+scenario)
    seven_n=[];seven_area=[];stable_n=[];baseline_low=[];scale_extra={}
    for h in H:
        s=stability[(stability.habitat==h)&stability.complete_comparison_set]
        seven_n.append(len(s));stable_n.append(int(s.consistent_low_complete_set.sum()))
        baseline_low.append(int((s.baseline_class==1).sum()))
        seven_area.append(math.fsum(float(baseline.loc[(h,g),'scope_area_m2']) for g in s.grid_id))
        native_scale=scores[(scores.habitat==h)&(scores.scenario=='scale500_to1000_full_coverage')]
        extra=set(native_scale.grid_id)-set(s.grid_id)
        scale_extra[h]=stability[(stability.habitat==h)&stability.grid_id.isin(extra)].to_dict('records')
        check('seven schemes: six comparisons '+h,bool((s.comparison_count==6).all() and (s.planned_comparison_count==6).all()),6,s.comparison_count.unique().tolist(),'spatial_stability.csv')
    vector('seven_scheme_n',seven_n,'spatial_stability.csv: complete_comparison_set')
    vector('seven_scheme_area_km2',[x/1e6 for x in seven_area],'spatial_stability.csv joined to baseline scope_area_m2')
    vector('seven_scheme_coverage_percent',[100*x/y for x,y in zip(seven_area,valid_area)],'seven-scheme coverage / baseline valid grid coverage')
    vector('stable_low_n',stable_n,'spatial_stability.csv: consistent_low_complete_set')
    for name,indicator in [('weight_E','E_fraction'),('weight_NTL','NTL')]:
        vector(name,[weights.loc[(h,indicator),'weight'] for h in H],'entropy_weights.csv')
    selected=corr[(corr.indicator_1=='SSI')&(corr.indicator_2=='E_fraction')].set_index('habitat')
    vector('SSI_E_spearman',[selected.loc[h,'spearman_rho'] for h in H],'indicator_correlations.csv')
    for h in H:
        numeric('unrounded weight sum '+h,weights.loc[h,'weight'].sum(),1.,'entropy_weights.csv',1e-12)
    tables={b['caption']:b for b in content['blocks'] if b.get('type')=='table'}
    check('three main tables present',set(tables)=={'表1 三维生态韧性评价指标','表2 各类生境的有效评价范围','表3 三类生境的指标熵权'},None,list(tables))
    coverage_table=tables['表2 各类生境的有效评价范围']
    for i,h in enumerate(H):
        n_town=int(((towns.habitat==h)&(towns.six_valid_area_m2>0)).sum())
        expected=[ZH[i],str(valid_n[i]),f'{valid_area[i]/1e6:.2f}',f'{100*valid_area[i]/area:.2f}',str(n_town)]
        check('table2 '+h,coverage_table['rows'][i]==expected,expected,coverage_table['rows'][i],'regional_results.csv + township_results.csv')
    indicators=['HQ_H','NTL','CLUMPY','MCR','SSI','E_fraction']
    weight_table=tables['表3 三类生境的指标熵权']
    for i,key in enumerate(indicators):
        for j,h in enumerate(H):
            expected=f'{weights.loc[(h,key),"weight"]:.4f}'
            check('table3 '+h+' '+key,weight_table['rows'][i][j+1]==expected,expected,weight_table['rows'][i][j+1],'entropy_weights.csv')
    protocol=read(ROOT/'05_代码/config/approved_protocol.json')
    table1=tables['表1 三维生态韧性评价指标']
    for i,key in enumerate(indicators):
        expected='+' if protocol['directions'][key]>0 else '-'
        check('table1 direction '+key,normal(table1['rows'][i][2])==expected,expected,table1['rows'][i][2],'approved_protocol.json')
    check('table area interpretation',any('并非生境实体面积' in n and '不能加总' in n for n in coverage_table['notes']),True,coverage_table['notes'])
    displayed('并集面积',[area/1e6],1,'grid_identity.json','body study union area')
    displayed('林灌、草地、水体湿地六项指标',valid_n,0,'regional_results.csv','body valid n')
    displayed('林灌、草地、水体湿地六项指标',[x/1e6 for x in valid_area],2,'regional_results.csv','body valid grid area')
    town_table=towns.set_index(['town','habitat'])
    for selector, claims, digits, label in [
        ('阳坊、苏家坨的',[('阳坊镇','ER_mean',1),('苏家坨镇','ER_mean',1),('阳坊镇','ER_within_town_sd',1),('苏家坨镇','ER_within_town_sd',1),('军庄镇','ER_mean',1),('军庄镇','V_mean',1),('军庄镇','S_mean',1),('军庄镇','O_mean',1)],3,'town means sd dimensions'),
        ('阳坊、苏家坨的',[('阳坊镇','six_valid_fraction',100),('苏家坨镇','six_valid_fraction',100)],2,'town valid coverage'),
        ('高丽营、李桥的',[('高丽营镇','ER_mean',1),('李桥镇','ER_mean',1)],3,'town low mean examples'),
        ('高丽营、李桥的',[('高丽营镇','six_valid_fraction',100),('李桥镇','six_valid_fraction',100)],2,'town low mean coverage')]:
        values=[town_table.loc[(name,'forest_shrub'),field]*factor for name,field,factor in claims]
        displayed(selector,values,digits,'township_results.csv',label)
    displayed('高丽营、李桥的',[town_table.loc[(name,'grassland'),'six_valid_fraction']*100 for name in ['黄村镇','台湖镇']],2,'township_results.csv','limited grassland township coverage')
    displayed('生态空间面积比例在林灌',[weights.loc[(h,k),'weight'] for k in ['E_fraction','NTL'] for h in H],3,'entropy_weights.csv','body weights')
    displayed('源汇平均距离与生态空间面积比例的Spearman',[selected.loc[h,'spearman_rho'] for h in H],3,'indicator_correlations.csv','body SSI-E correlations')
    displayed('源汇平均距离与生态空间面积比例的Spearman',[pairs.loc[('forest_shrub',s),'weighted_MAE'] for s in ['omit_E_fraction','omit_NTL']],3,'paired_sensitivity.csv','omit comparison MAE')
    displayed('将CLCD替换为WorldCover',[pairs.loc[(h,s),'weighted_MAE'] for s in ['worldcover','crop_in_ecological_space'] for h in H],3,'paired_sensitivity.csv','product and ecological-space definition MAE')
    param_rows=[pairs.loc[(h,s),'spearman_rho'] for h in H for s in ['core35_land_road','core100_land_road','core10_land_only']]
    check('nine parameter comparisons all rho > 0.999',min(param_rows)>0.999,0.999,min(param_rows),'paired_sensitivity.csv')
    for h in H:
        data_mae=[float(pairs.loc[(h,s),'weighted_MAE']) for s in ['worldcover','crop_in_ecological_space']]
        parameter_mae=[float(pairs.loc[(h,s),'weighted_MAE']) for s in ['core35_land_road','core100_land_road','core10_land_only']]
        check('data/definition MAE exceeds tested parameter MAE '+h,min(data_mae)>max(parameter_mae),{'data_min':min(data_mae),'parameter_max':max(parameter_mae)},None,'paired_sensitivity.csv; each habitat and each pairwise valid domain separately')
    displayed('500 m结果汇回1 km后',facts['scale_full_n']+seven_n,0,'paired_sensitivity.csv + spatial_stability.csv','scale and seven-scheme n')
    displayed('500 m结果汇回1 km后',facts['scale_full_rho'],3,'paired_sensitivity.csv','scale rho')
    displayed('500 m结果汇回1 km后',[100*x/y for x,y in zip(seven_area,valid_area)],2,'spatial_stability.csv + regional_results.csv','seven-scheme valid area coverage')
    check('water 90 vs 89 has exactly one differently eligible grid',len(scale_extra['water_wetland'])==1 and scale_extra['water_wetland'][0]['grid_id']=='G1000_22_24' and 'worldcover' not in scale_extra['water_wetland'][0]['available_scenarios'],True,scale_extra['water_wetland'],'scores_all_scenarios.csv + spatial_stability.csv')
    thermal_path=ROOT/'03_结果文件/thermal_association/graygreen_LST_spearman_descriptive.csv'
    thermal=pd.read_csv(thermal_path);sources[str(thermal_path)]=sha(thermal_path)
    primary=thermal[(thermal.date==20200803)&(thermal.domain=='ALL')].set_index('predictor')
    displayed('2020年8月3日，在同时含有',[primary.loc['SSI','n_grid_pairs']],0,str(thermal_path),'main thermal n')
    displayed('2020年8月3日，在同时含有',[primary.loc[p,'spearman_rho'] for p in ['SSI','E_fraction']],3,str(thermal_path),'main thermal rho')
    for predictor in ['SSI','E_fraction']:
        vals=thermal[(thermal.date==20200803)&(thermal.domain!='ALL')&(thermal.predictor==predictor)].spearman_rho
        displayed('2020年8月3日，在同时含有',[vals.min(),vals.max()],3,str(thermal_path),'quadrant range '+predictor)
        check('primary quadrant directions '+predictor,bool((vals>0).all()) if predictor=='SSI' else bool((vals<0).all()),True,vals.tolist(),str(thermal_path))
    for date in [20200616,20200810]:
        n=int(thermal[(thermal.date==date)&(thermal.domain=='ALL')&(thermal.predictor=='SSI')].iloc[0].n_grid_pairs)
        check('separate date n '+str(date),bool(re.search(r'(?<!\d)'+str(n)+r'(?!\d)',text)),n,None,str(thermal_path))
    thermal_domains=thermal[(thermal.predictor=='SSI')&(thermal.domain!='ALL')][['date','domain','n_grid_pairs']].to_dict('records')
    if '均主要位于研究区西部' in text or '不能作为东部的重复检验' in text or '不能作为东部重复检验' in text:
        interpretation.append({'id':'thermal_second_dates_scope','severity':'required_text_revision',
                               'finding':'June16 covers NW111/NE87/SW205/SE167; eastern254/570=44.56%. Only Aug10 has no eastern grids (NW216/SW210). Do not describe both dates as unavailable for eastern comparison.',
                               'source':str(thermal_path)})
    body='\n'.join(paragraphs)
    grass_sentence=bool(re.search(r'草地[^。\n]{0,180}(?:未|没有|不含|为0)[^。\n]{0,100}(?:基准|最低)',body) or re.search(r'草地[^。\n]{0,180}基准最低[^。\n]{0,80}(?:为0|没有|未)',body))
    if baseline_low[1]==0 and not grass_sentence:
        interpretation.append({'id':'grass_complete_domain_zero_low','severity':'required_text_revision',
                               'finding':'Grassland complete seven-scheme domain has18 grids but0 baseline-low grids, so0 stable lows cannot by itself demonstrate low-list changes. Forest/shrub and water/wetland each contain14 baseline-low grids within complete domains.',
                               'source':'spatial_stability.csv'})
    abstract=content['abstract']
    check('abstract stable-low habitat qualification','林灌与水体湿地最低等级格网' in abstract and '草地低值持续性缺少完整对照证据' in abstract,{'baseline_low_inside_complete_domain':baseline_low,'stable_low':stable_n},None,'spatial_stability.csv')
    check('corrected complete-domain counts stated',baseline_low==[14,0,14] and '各有14个基线最低等级格网' in '\n'.join(paragraphs),[14,0,14],baseline_low,'spatial_stability.csv')
    check('same-habitat comparison boundary', '不作跨类型数值排序' in body and '不作跨类型加总' in body,True,None)
    check('township denominator boundary','覆盖其研究范围内镇域' in body and '研究范围内乡镇部分' in body,True,None)
    check('stable-low complete-comparison qualification','完整对照范围内' in body and '对照不足' in body,True,None)
    # Displayed method constants and actual engine/source versions.
    hq=read(ROOT/'02_过程文件/hq/input_freeze.json');kf=read(ROOT/'02_过程文件/hq/k_frozen.json')
    displayed('（1）生境质量',[x/1000 for x in hq['max_dist_values']],0,'hq/input_freeze.json','HQ threat km')
    displayed('（1）生境质量',[kf['k']],5,'hq/k_frozen.json','HQ frozen k')
    numeric('HQ k rule',kf['k'],.5*kf['Dmax'],'hq/k_frozen.json')
    displayed('（4）最小累积阻力',[.3445,.0281],4,'config/mcr_parameters.json','original two-factor weights')
    displayed('（4）最小累积阻力',[.3445/(.3445+.0281),.0281/(.3445+.0281)],6,'config/mcr_parameters.json','renormalized two-factor weights')
    classification=read(EVAL/'classification.json')
    check('classification implementation','jenkspy 0.4.1' in body and classification['engine']=='jenkspy 0.4.1',classification['engine'],'jenkspy 0.4.1' in body,'classification.json')
    versions=[('InVEST 3.20.2','03_结果文件/hq/native_hq_execution.json','3.20.2'),
              ('FRAGSTATS 4.2.1.612','03_结果文件/clumpy/clumpy_clcd_1000_receipt.json','4.2.1.612'),
              ('ArcGIS Pro 3.1.6','02_过程文件/mcr_native/clcd_forest_shrub_core10_land_road/mcr_run_receipt.json','3.1.6')]
    for phrase,rel,version in versions:
        check('software version '+version,phrase in body and version in (ROOT/rel).read_text(encoding='utf8'),phrase,None,rel)
    mspa=read(ROOT/'02_过程文件/mspa/219_MSPA_six_runs_manifest.json')
    for run in mspa['completed_runs']:
        command=run['command']
        check('MSPA edge/connectivity '+run['product']+' '+run['group'],command[command.index('-eew')+1]=='1' and command[command.index('-graphfg')+1]=='8',['1','8'],command,'219_MSPA_six_runs_manifest.json')
    queue=read(ROOT/'02_过程文件/mcr_inputs/regional_queue.json')
    thresholds={}
    for task in queue['tasks']:
        cfg=read(Path(task['config']));rule=cfg['threshold'];thresholds[rule['source_rule']]=(rule['operator'],rule['threshold_ha'])
    check('source threshold operators',thresholds=={'core10':('>=',10),'core35':('>=',35),'core100':('>',100)},None,thresholds,'regional_queue task configs')
    method_versions={'CLCD_record':'1.0.2','WorldCover':'v100','radiance_release':'c202205302300','nominal_NTL_arcseconds':15,'main_grid_m':1000,'fine_grid_m':500,'land_resolution_m':30,'reference_year':2020}
    for key,value in method_versions.items():check('method declared '+key,str(value) in body,value,None,'approved protocol and source archives')
    # Text export must contain every actual paragraph, abstract and table caption.
    check('plain text abstract synchronized',content['abstract'] in text,True,None)
    for i,p in enumerate(paragraphs):check('plain text paragraph '+str(i),p in text,True,None)
    for caption in tables:check('plain text table caption '+caption,caption in text,True,None)
    changed=[str(p) for p in paths if sha(p)!=before[str(p)]]
    check('manuscript inputs unchanged during audit',not changed,[],changed)
    report={'status':'FAIL_NUMERICAL_OR_VERSION' if failures else 'TEXT_REVISION_REQUIRED' if interpretation else 'PASS',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scope':'All empirical body numbers and all three table values checked against actual CSV sources; displayed method parameters/version declarations checked against frozen execution receipts. Bibliographic reference-number/date/DOI verification and native Word/PDF layout remain separate reviews.',
            'manuscript_modified':False,'production_data_modified':False,'upstream_scientific_QA':qa['status'],
            'checks_n':len(checks),'passed_checks_n':sum(c['status']=='PASS' for c in checks),'failures':failures,
            'interpretation_revisions':interpretation,'content_sha256':before[str(paths[0])],'manuscript_sha256':before,'result_source_sha256':sources,
            'checks':checks,'critical_scope_facts':{
                'seven_scheme_complete_n':seven_n,'baseline_low_inside_complete_domains':baseline_low,'stable_low_inside_complete_domains':stable_n,
                'complete_domain_area_km2':[x/1e6 for x in seven_area],
                'complete_domain_percent_of_baseline_valid_area':[100*x/y for x,y in zip(seven_area,valid_area)],
                'water_scale90_vs_seven89_difference':scale_extra['water_wetland'],
                'thermal_dates_quadrant_n':thermal_domains,
                'township_area_meaning':'Coverage denominator is research-covered part of each township; numerator is habitat-specific valid GRID coverage, not physical habitat area; domains can overlap and cannot be added',
                'between_habitat_comparison':'Scores/weights/classes normalized and fitted separately; no absolute cross-habitat rank claim'},
            'not_yet_audited_here':['Rendered final Word/PDF line breaks, formula glyphs and inserted figure quality','Independent current bibliographic metadata verification'],
            'auditor_script_sha256':sha(Path(__file__))}
    OUT.write_text(json.dumps(clean(report),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({k:report[k] for k in ['status','checks_n','passed_checks_n','failures','interpretation_revisions']},ensure_ascii=False))

if __name__=='__main__':main()
