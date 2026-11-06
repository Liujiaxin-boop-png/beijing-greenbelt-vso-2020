"""Read-only result interpretation with input hashes; never edits production data."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import pandas as pd
import geopandas as gpd

WORK = Path(r'D:\ER219_work')
RESULT = Path(r'D:\ER219_results\evaluation')
OUT = WORK / 'manuscript'
NAMES = {'forest_shrub':'林灌生境', 'grassland':'草地生境', 'water_wetland':'水体湿地生境'}
FILES = ['regional_results.csv','entropy_weights.csv','paired_sensitivity.csv',
         'indicator_correlations.csv','township_results.csv','spatial_stability.csv',
         'class_agreement.csv','scenario_coverage.csv','scores_classified.csv']

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def clean(v):
    if isinstance(v, dict): return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v, (tuple,list)): return [clean(x) for x in v]
    if hasattr(v,'item'): return clean(v.item())
    if isinstance(v,float) and not math.isfinite(v): return None
    return v

inputs = {name:{'path':str(RESULT/name),'sha256':sha(RESULT/name)} for name in FILES}
tables = {name:pd.read_csv(RESULT/name,low_memory=False) for name in FILES}
qa_path=WORK/'evaluation/final_scientific_QA.json'
qa=json.loads(qa_path.read_text(encoding='utf-8-sig'))
qa_at_read={'path':str(qa_path),'sha256':sha(qa_path),'status':qa.get('status'),
            'created_utc':qa.get('created_utc'),'failure':qa.get('failure'),
            'scope':qa.get('scope')}
main=OUT/'manuscript_content.json'
main_hash_before=sha(main)
scope_path=WORK/'spatial/scope.gpkg'
scope_area=float(gpd.read_file(scope_path,layer='study_scope').geometry.union_all().area)
reg=tables['regional_results.csv'].set_index('habitat')
weights=tables['entropy_weights.csv']
paired=tables['paired_sensitivity.csv']
corr=tables['indicator_correlations.csv']
towns=tables['township_results.csv']
baseline=tables['scores_classified.csv'].query("scenario == 'baseline'").copy()
stability=tables['spatial_stability.csv'].merge(
    baseline[['grid_id','habitat','scope_area_m2']],on=['grid_id','habitat'],validate='one_to_one')
classification_ready=qa.get('status')=='PASS'
class_state='NUMERICAL_QA_PASS_NOT_ECOLOGICAL_VALIDATION' if classification_ready else 'CLASSIFICATION_QA_PENDING_DO_NOT_FREEZE'
raw_path=Path(r'D:\ER219_results\indicators\six_indicator_records.csv')
raw=pd.read_csv(raw_path,low_memory=False)
raw_baseline=raw.loc[(raw['product']=='clcd')&(raw.scale_m==1000)]
eligibility=[]
for h,g in raw_baseline.groupby('habitat'):
    eligibility.append({'habitat':h,'all_scope_intersected_square_n':len(g),
       'has_focal_habitat_n':int(g.has_habitat.sum()),
       'has_construction_n':int(g.has_construction.sum()),
       'six_valid_n':int(g.six_valid.sum()),
       'CLUMPY_status_counts':g.CLUMPY_status.value_counts(dropna=False).to_dict(),
       'interpretation':'无本类生境、单焦点像元、纯焦点类别或其他无法定义聚集度的情形，与无建设空间导致SSI不能定义的情形分别保留；未获分值不表示低韧性。'})

regional=[]
for h in NAMES:
    r=reg.loc[h]
    regional.append({'habitat':h,'label':NAMES[h], 'valid_grid_n':int(r.valid_grid_n),
        'valid_grid_coverage_km2':float(r.valid_scope_area_m2/1e6),
        'valid_grid_coverage_pct_scope':float(100*r.valid_scope_area_m2/scope_area),
        'within_type_ER_mean':float(r.ER_area_weighted_mean),
        'within_type_ER_sd':float(r.ER_area_weighted_sd),
        'towns_with_valid_grid':int((towns.loc[towns.habitat.eq(h),'grid_n']>0).sum()),
        'source':'regional_results.csv habitat row; township_results.csv grid_n>0; scope.gpkg union area',
        'interpretation':'有效面积是完整指标格网与研究区相交的覆盖面积，不是本类实际生境面积；三类覆盖域可重叠，均值不能跨生境排序。'})

selected_scenarios=['worldcover','core35_land_road','core100_land_road','core10_land_only',
                    'crop_in_ecological_space','scale500_to1000_full_coverage',
                    'omit_E_fraction','omit_HQ_H','omit_NTL']
sensitivity=paired[paired.scenario.isin(selected_scenarios)].to_dict('records')
correlations=corr.loc[((corr.indicator_1=='SSI')&(corr.indicator_2=='E_fraction'))|
                      ((corr.indicator_1=='E_fraction')&(corr.indicator_2=='SSI'))].to_dict('records')

cases=[]
case_specs=[
    ('阳坊镇','forest_shrub','乡镇均值不足以概括内部状况；先定位高低分交错格网，再核对建设边缘、林灌与其他生态空间的实际关系。'),
    ('苏家坨镇','forest_shrub','均值和镇内离散程度同时较高，保护连续生态空间的同时，应单列低值局部核查，不按全镇统一等级安排措施。'),
    ('军庄镇','forest_shrub','本类有效域内综合均值较高，但V有利度低于S和O，管护应同时核对生境质量与压力，不能把综合分值当作各维度均优。'),
    ('高丽营镇','forest_shrub','可将有效格网中的较低分值及V、O条件作为现状核查线索；不据此直接排出工程投资顺序。'),
    ('李桥镇','forest_shrub','结合林灌现状、周边胁迫和灰绿间隔逐格核查，以区分林灌数量、质量和配置问题。'),
    ('张家湾镇','water_wetland','核对本类有效格网中的水体湿地边界及周边生态用地配置，尤其检查底图分类变化是否改变综合判断。'),
    ('长阳镇','water_wetland','先核查水体湿地有效覆盖域，利用分项图定位生态用地构成与建设空间配置，不把综合低分等同河湖生态功能受损。'),
    ('青龙湖镇','water_wetland','有效覆盖不足研究区内镇域的一成，均值只描述这些局部，不能据其给全镇定级。'),
    ('黄村镇','grassland','仅3个有效格网、覆盖研究区内镇域约2.4%，适合列为局部草地核查样点，不适合发布全镇草地韧性等级。'),
    ('台湖镇','grassland','仅2个有效格网、覆盖研究区内镇域约1.7%，较低均值首先需要核对样本覆盖与草地类别，不外推全镇。'),
]
for town,h,action in case_specs:
    row=towns.loc[towns.town.eq(town)&towns.habitat.eq(h)]
    assert len(row)==1,(town,h)
    d=row.iloc[0].to_dict()
    d.pop('lowest_class_area_m2',None)
    d.update({'valid_grid_coverage_km2':d['six_valid_area_m2']/1e6,
              'valid_grid_coverage_pct_of_scope_intersected_town':100*d['six_valid_fraction'],
              'planning_use':action,
              'boundary':'镇域均指乡镇边界与研究区相交部分；ER只在六指标均有效格网上计算；建议为2020年基线支持的核查顺序，不是当前工程实施清单。',
              'source':{'file':'township_results.csv','row_key':{'town':town,'habitat':h}}})
    cases.append(d)

stable_rows=[]
for h,g in stability.groupby('habitat'):
    complete=g.complete_comparison_set.eq(True)
    stable=g.consistent_low_complete_set.eq(True)
    a=float(g.loc[complete,'scope_area_m2'].sum())
    stable_rows.append({'habitat':h,'complete_7_scheme_n':int(complete.sum()),
       'complete_7_scheme_grid_coverage_km2':a/1e6,
       'complete_7_scheme_coverage_pct_baseline':100*a/float(reg.loc[h,'valid_scope_area_m2']),
       'baseline_low_n_in_complete_domain':int((complete & g.baseline_class.eq(1)).sum()),
       'baseline_low_grid_coverage_km2_in_complete_domain':float(g.loc[complete & g.baseline_class.eq(1),'scope_area_m2'].sum()/1e6),
       'stable_low_n_current_snapshot':int(stable.sum()),
       'classification_status':class_state,
       'meaning':'缺失任一预定方案的格网不判断稳定性；不能把不完整比较记为不稳定。完整比较域内的结论也不外推到全域。'})

weight_rows=[]
for h in NAMES:
    w=weights[weights.habitat.eq(h)]
    weight_rows.append({'habitat':h,'weights':dict(zip(w.indicator,w.weight)),
       'meaning':'熵权量化本类基线有效样本中各标准化指标的离散信息，不是生态因果贡献、政策重要程度或预算分配比例。'})

texts=[
{'id':'R1','role':'result','heading':'有效评价范围与类型内差异','source_files':['regional_results.csv','township_results.csv','scope.gpkg'],
 'text':'六项指标同时有效的林灌、草地、水体湿地格网分别为840、153和532个，其研究区内覆盖面积分别为687.58、130.41和401.82 km²，占研究区面积的34.59%、6.56%和20.21%。上述面积描述可评价格网的覆盖范围，三类范围存在重叠。林灌、草地和水体湿地分别形成独立的标准化与赋权体系，因此评价用于比较同类生境内部差异，不据三类综合指数均值判定生境优劣。35个乡镇中，分别有35、20和34个乡镇存在相应生境的有效格网。'},
{'id':'R2','role':'result','heading':'乡镇内部差异','source_files':['township_results.csv'],
 'text':'林灌生境的乡镇均值不能完整反映镇内状况。阳坊镇、苏家坨镇的综合指数均值分别为0.374和0.427，镇内标准差分别达0.307和0.277，对应有效格网覆盖研究区内镇域的52.04%和49.03%。军庄镇的林灌综合均值为0.583，但脆弱性维度的有利度均值为0.234，低于其敏感性与自组织维度的有利度（0.943和0.749）。综合得分较高仍可能伴随局部或分项不足，需要由乡镇统计返回格网与分项指标进行研判。'},
{'id':'R3','role':'result','heading':'基线口径与参数变动的不同影响','source_files':['paired_sensitivity.csv'],
 'text':'不同扰动方案对综合评价的影响存在明显差别。在共同有效格网上，将土地覆盖底图替换为WorldCover后，林灌、草地和水体湿地综合指数的面积加权平均绝对差分别为0.227、0.097和0.339；将耕地纳入生态空间统计口径后，相应差值为0.219、0.064和0.319。相比之下，源地核心面积阈值由10 ha调整为35 ha或大于100 ha，以及移除道路阻力成分，三类综合排序与基线的Spearman相关系数均超过0.999。上述变化描述同一研究期在不同数据与设定下的评分差异，不表示生态条件随方案发生改善。'},
{'id':'R4','role':'result','heading':'尺度比较的适用范围','source_files':['paired_sensitivity.csv','spatial_stability.csv','scores_classified.csv'],
 'text':'500 m结果回并至1 km后，仅完整覆盖对应基线有效范围的格网参与尺度比较，林灌、草地和水体湿地分别为137、18和90个，排序相关系数分别为0.936、0.851和0.766。三类生境同时具备基线及全部六项主对照结果的格网分别为137、18和89个，仅覆盖本类基线有效面积的13.94%、9.92%和7.53%。完整七方案比较的覆盖范围较小，稳定性判断应随比较覆盖图一并报告。'},
{'id':'D1','role':'discussion','heading':'综合指数的含义与共享信息','source_files':['entropy_weights.csv','indicator_correlations.csv','paired_sensitivity.csv'],
 'text':'生态空间比例在林灌、草地和水体湿地评价中的熵权分别为0.556、0.312和0.792；夜间灯光权重分别仅为0.008、0.025和0.031。权重反映本类有效样本的指标离散程度，不能解释为生态作用强弱。灰绿空间间隔与生态空间比例的Spearman相关系数在林灌、草地和水体湿地中分别为−0.814、−0.870和−0.681，说明数量与空间配置指标仍共享部分信息。因此，规划研判需同步查看综合分值、分维度评价和原始指标，避免由总分替代问题诊断。'},
{'id':'P1','role':'planning_implication','heading':'从乡镇均值转向格网核查','source_files':['township_results.csv'],
 'text':'乡镇管护可将评价作为2020年基线筛查工具，先识别具有充分有效覆盖的镇域差异，再落到格网核查。对阳坊、苏家坨等林灌评价内部离散程度较大的乡镇，应分别核查连续林灌空间与较低得分局部，不以镇域均值安排一致的管护措施。高丽营、李桥的林灌有效格网均值分别为0.157和0.183，有效覆盖分别为研究区内镇域的65.66%和55.73%，可据分项指标组织生境质量、周边压力及灰绿配置核查。黄村、台湖的草地有效覆盖仅约2.39%和1.70%，应定位到具体样点，不能给全镇作同等级判断。'},
{'id':'P2','role':'planning_implication','heading':'先核对底图与用地口径，再讨论整治措施','source_files':['paired_sensitivity.csv','entropy_weights.csv','township_results.csv'],
 'text':'对水体湿地等受生态空间比例权重影响较大的评价，应在形成管护项目清单前核对土地覆盖分类与生态空间边界。张家湾、长阳的水体湿地有效格网综合均值分别为0.220和0.184，覆盖研究区内镇域的35.39%和29.00%，可作为核对水体湿地边界、周边生态用地构成和建设空间配置的线索。对底图或生态用地口径改变即出现较大评分差异的区域，优先更新现状信息；确需采取修复措施时，再结合现场生境调查与现行规划确定对象和方式。'},
{'id':'L1','role':'limitation','heading':'评价解释边界','source_files':['regional_results.csv','paired_sensitivity.csv','indicator_correlations.csv'],
 'text':'本研究评价2020年静态景观与压力条件，未直接测量扰动后的恢复过程。综合评价覆盖同时存在目标生境与建设空间、聚集度等六项指标均可定义的混合景观；无本类生境、纯类景观或指标无法定义的格网单列状态，未获分值不等于低韧性。类型间独立归一化也限制了跨生境数值比较。土地覆盖、生态空间定义及共享信息会影响综合得分，而熵权不能消除指标相关性。因此，结果适合作为同类生境的历史基线和现状复核线索，不能单独替代当前生态修复选址或投资论证。'},
]

contributions=[
 {'claim':'把生态韧性评价结果与乡镇管护范围连接，并同步报告内部差异和有效覆盖。','basis':['R1','R2','P1'],
  'not_claim':'不称新理论或新算法；不称全镇或全域均已获得完整评价。'},
 {'claim':'在相同评价框架内区分土地覆盖分类、生态空间口径与本轮阻力/源阈值扰动对评分判断的影响。','basis':['R3','P2'],
  'not_claim':'不把数值敏感性解释为生态过程的主导因子，不声称某底图是真值。'},
 {'claim':'把评分、比较覆盖和分项诊断同时用于前期筛查，使现状核查对象及不能外推的范围可追踪。','basis':['R4','D1','L1'],
  'not_claim':'不声称已识别经实地验证的工程优先区，未完整比较的格网不称不稳定。'},
]
if classification_ready:
    texts.insert(4,{'id':'R5','role':'result','heading':'持续最低等级及其可比范围',
        'source_files':['spatial_stability.csv','scores_classified.csv','class_agreement.csv'],
        'text':'完整七方案比较域内，林灌和水体湿地各有14个格网在基线中处于最低等级，均未在全部方案下维持最低等级。草地完整比较域不含基线最低等级格网，因而尚不能检验这部分低值的持续性。WorldCover对照与基线的等级面积一致率在林灌、草地和水体湿地中分别为18.89%、42.71%和5.66%。这些结果支持在现状核查中关注数据口径对分级的影响，但不支持把对照不完整的格网判为不稳定。'})

blocked_claims=[
 '不得跨生境排列ER均值，或将三类有效格网覆盖面积相加当作全域评价面积。',
 '不得把熵权或加权分量称为生态因果贡献；夜光权重小不表示人为干扰不重要。',
 '不得把本轮去道路成分对总分扰动小写成道路没有生态影响。',
 '不得把没有有效结果的格网、乡镇或未完整比较的格网填为低分或不稳定。',
 '不得在分级数值QA完成前冻结最低等级面积、等级一致率和稳定低值清单。',
 '不得将乡镇边界与研究区相交部分误写为完整行政镇域；面积覆盖不是生境实际面积。',
 '不得依据少量有效格网给黄村、台湖等整个乡镇作草地韧性判断。',
 '不得预设普遍西北高东南低、真实生态恢复速度、政策净效应或工程投入回报。',
]

report={
 'created_utc':datetime.now(timezone.utc).isoformat(),
 'status':'INDEPENDENT_INTERPRETATION_SUGGESTIONS_NOT_MAIN_MANUSCRIPT',
 'scientific_release_gate':qa_at_read,
 'classification_numbers_release_status':class_state,
 'production_data_or_main_manuscript_changed':False,
 'scope_area_m2_verified_from_union':scope_area,
 'scope_area_source':str(scope_path),
 'source_snapshot':inputs,
 'continuous_results':regional,
 'eligibility_support':{'file':str(raw_path),'sha256':sha(raw_path),'by_habitat':eligibility},
 'entropy_weights':weight_rows,
 'shared_information_correlations':correlations,
 'selected_paired_sensitivity':sensitivity,
 'township_cases':cases,
 'seven_scheme_support':stable_rows,
 'conditional_classification_snapshot':{
   'status':class_state,
   'regional_lowest_class_rows':tables['regional_results.csv'][['habitat','lowest_class_area_m2']].to_dict('records'),
   'selected_class_agreement':tables['class_agreement.csv'].loc[
      tables['class_agreement.csv'].scenario.isin(['worldcover','crop_in_ecological_space','scale500_to1000_full_coverage'])].to_dict('records'),
   'note':'仅保存此时可追溯快照；QA未通过时不得纳入定稿。需在分类实现修正并全局复核后整体刷新。'},
 'proposed_manuscript_paragraphs':texts,
 'defensible_contributions':contributions,
 'prohibited_overclaims':blocked_claims,
 'validation_notes':[
   '本文件为结果解释建议，不代替pipeline219独立数值QA，也不是生态外部验证。',
   '所有连续值、权重和比较值均来自真实CSV；无插值或生成实验数据。',
   '文中数值按读者理解需要取2位百分比和3位指数；JSON保留原始精度。',
   '主稿、评价CSV、参数及代码均不改写。',
 ],
}
unchanged={name:sha(RESULT/name)==r['sha256'] for name,r in inputs.items()}
report['snapshot_unchanged_at_end']=unchanged
report['main_content_sha256_before']=main_hash_before
report['main_content_sha256_after']=sha(main)
report['main_content_unchanged_by_agent']=report['main_content_sha256_before']==report['main_content_sha256_after']
if not all(unchanged.values()):
    report['status']='SOURCE_CHANGED_DURING_REVIEW_RERUN_REQUIRED'
out_json=OUT/'219_真实结果规划解释建议.json'
out_txt=OUT/'219_真实结果规划解释建议.txt'
out_json.write_text(json.dumps(clean(report),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
lines=['真实结果的独立规划解释建议','用途：供主稿作者在独立QA通过后选用；本文件不改主稿。',
       f"读取时数值QA：{qa_at_read['status']}；分级释放状态：{class_state}",
       f"当前QA说明：{qa_at_read.get('failure')}",
       ('以下正文建议据已通过独立数值QA的数据刷新；数值核验不替代生态外部验证。' if classification_ready else '以下正文段落仅使用连续分值、覆盖范围、权重与相关性；不冻结尚待复核的等级统计。'),'']
for t in texts:
    lines.extend([t['id']+' '+t['heading'],t['text'],'依据：'+', '.join(t['source_files']),''])
lines.extend(['可支持的贡献'])
for c in contributions:lines.extend([c['claim'],'边界：'+c['not_claim']])
lines.extend(['',('已核验的分级统计及覆盖边界' if classification_ready else '暂缓纳入定稿的分级统计')])
for x in stable_rows:
    lines.append(f"{NAMES[x['habitat']]}：完整七方案{x['complete_7_scheme_n']}格，覆盖{x['complete_7_scheme_grid_coverage_km2']:.3f} km²，占本类基线有效面积{x['complete_7_scheme_coverage_pct_baseline']:.2f}%；其中基线最低{x['baseline_low_n_in_complete_domain']}格，持续最低{x['stable_low_n_current_snapshot']}格。只在本完整域解释，不外推全域。")
lines.extend(['','必须避免的表述']+blocked_claims)
out_txt.write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'json':str(out_json),'txt':str(out_txt),'qa_status_at_read':qa.get('status'),
                  'source_snapshot_stable':all(unchanged.values()),'main_content_unchanged':report['main_content_unchanged_by_agent'],
                  'paragraphs':len(texts),'town_cases':len(cases)},ensure_ascii=False))
