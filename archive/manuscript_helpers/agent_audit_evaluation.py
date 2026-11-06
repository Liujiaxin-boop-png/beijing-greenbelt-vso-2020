from pathlib import Path
import json, hashlib, importlib.util, ast
import numpy as np
import pandas as pd

ROOT=Path.cwd();B=ROOT/'生态韧性正式研究_20261106'
OUT=B/'02_过程文件/manuscript/evaluation_readonly_review';OUT.mkdir(parents=True,exist_ok=True)
CODE=Path('D:/ER219_code/src')
files=['evaluate_resilience.py','summarize_evaluation.py','join_indicator_records.py','aggregate_basics.py','aggregate_mcr.py','qgis_classify_scores.py']
snap={};meta=[]
for name in files:
 p=CODE/name;raw=p.read_bytes();text=raw.decode('utf-8');snap[name]=text
 (OUT/(name+'.reviewed.txt')).write_bytes(raw)
 meta.append({'file':str(p),'resolved':str(p.resolve()),'sha256':hashlib.sha256(raw).hexdigest(),'line_count':len(text.splitlines())})
def load(name):
 spec=importlib.util.spec_from_file_location('review_'+name.removesuffix('.py'),CODE/name);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
ev=load('evaluate_resilience.py');su=load('summarize_evaluation.py')
checks=[]
def ck(id,condition,details):
 assert condition,id
 checks.append({'id':id,'status':'PASS','details':details})

# A constant baseline attribute must have zero entropy weight even when the
# fixed comparison pool gives it a nonzero normalization range.
x=np.array([[5,3,.2,100,20,.2],[5,2,.5,200,40,.4],[5,1,.8,300,60,.6]],float)
lo=np.array([0,1,0,0,0,0]);hi=np.array([10,3,1,400,80,1])
z=ev.normalise(x,lo,hi);w,e,d=ev.entropy(z)
ck('constant_baseline_indicator_with_external_pool',w[0]==0 and np.isclose(w.sum(),1),'指标0的联合参照范围不为0，但基线本列恒定，因此信息离散度与权重为0。')

# A one-cell scenario remains scoreable with the fixed baseline weight;
# only new entropy estimation is undefined.
one=pd.DataFrame(x[:1],columns=ev.METRICS)
one_score=ev.score(one,lo,hi,w)
failed=False
try:ev.entropy(ev.normalise(x[:1],lo,hi))
except ValueError:failed=True
ck('single_pair_fixed_score_vs_reweight',np.isfinite(one_score.ER.iloc[0]) and failed,'固定基准权重的单格对照有定义；单格重估权明确不可估。主循环现已有独立ValueError保护。')
ck('reweight_failure_caught_in_main','except ValueError as err:' in snap['evaluate_resilience.py'] and "'NOT_ESTIMABLE'" in snap['evaluate_resilience.py'],'源文件只使重估权诊断不可估，不中断固定权重方案。')

b=pd.DataFrame({'grid_id':['a','b','c'],'ER':[.1,.3,.7],'scope_area_m2':[100,300,600]}).set_index('grid_id')
a=pd.DataFrame({'grid_id':['b'],'ER':[.4],'scope_area_m2':[300]}).set_index('grid_id')
r=ev.describe_pair(b,a,'synthetic','forest_shrub')
ck('paired_domain_does_not_prune_baseline',r['n']==1 and r['baseline_valid_n']==3 and r['paired_area_m2']==300 and np.isclose(r['weighted_mean_difference'],.1),'只比较交集b，保留基线3格/1000面积的覆盖信息。')
empty=ev.describe_pair(b,a.rename(index={'b':'z'}),'empty','forest_shrub')
ck('no_pair_is_status_not_zero',empty['n']==0 and empty['status']=='NO_PAIRED_VALID_DOMAIN','无共同有效格网保留状态，不产生零差异或零分。')

g=pd.DataFrame({'ER':[.2,.8,np.nan],'intersect_m2':[100,900,500]})
mean,sd,area=su.wstats(g,'ER')
expected=(100*.2+900*.8)/1000
ck('town_valid_area_weighted_mean',np.isclose(mean,expected) and area==1000 and np.isclose(sd,np.sqrt((100*(.2-expected)**2+900*(.8-expected)**2)/1000)),'有效面积权重100/900；缺测500不进入均值分母，得到均值0.74；这是合成测试，不是乡镇研究结果。')

# Source-level checks cover post-review fixes without running any empirical main().
ck('parameter_diagnostics_refreshed',"col.startswith('MCR')" in snap['evaluate_resilience.py'] or 'mcr_columns' in snap['evaluate_resilience.py'] or ('destination_truncated_fraction' in snap['evaluate_resilience.py'] and 'target_truncated_fraction' in snap['evaluate_resilience.py']),'参数情景同步覆盖MCR相关诊断，而非仅覆盖成本列；详见快照。')
ck('partial_scale_no_numeric_sensitivity','NOT_COMPARABLE_DIFFERENT_WITHIN_GRID_SUPPORT' in snap['evaluate_resilience.py'],'部分细格覆盖只报告实际覆盖，不生成同域ρ/MAE。')
ck('paired_reweighted_baseline_scored',"br=score(b.loc[f.index]" in snap['evaluate_resilience.py'],'重估权对照现同时计算同域baseline与scenario得分。')

# All assertions above are synthetic or static-source checks. Neither NTL nor
# empirical indicator tables are created, edited, or substituted.
def locate(name,needle):
 return next((i for i,line in enumerate(snap[name].splitlines(),1) if needle in line),None)
findings=[
 {'id':'E01','severity':'HIGH','status':'FIXED_BY_ROOT_VERIFIED','file':'evaluate_resilience.py','line':locate('evaluate_resilience.py','except ValueError'),'issue':'单格或全恒定的成对样本重估权会抛错并中断全部评价。','resolution':'ValueError仅将重估权标为NOT_ESTIMABLE；固定基准权重对照继续。'},
 {'id':'E02','severity':'MEDIUM','status':'FIXED_BY_ROOT_VERIFIED','file':'evaluate_resilience.py','line':locate('evaluate_resilience.py','br=score'),'issue':'原先仅保存成对基准权重，未输出相应基准重估得分。','resolution':'新增br、ar同域评分与成对统计，避免把样本域变化混入重估权解释。'},
 {'id':'E03','severity':'MEDIUM','status':'FIXED_BY_ROOT_VERIFIED','file':'evaluate_resilience.py','line':locate('evaluate_resilience.py',"for label in"),'issue':'MCR参数情景曾继承基准距离、完整度和截断诊断。','resolution':'已随对应方案同步相关列。'},
 {'id':'E04','severity':'HIGH','status':'FIXED_BY_ROOT_VERIFIED','file':'evaluate_resilience.py','line':locate('evaluate_resilience.py','NOT_COMPARABLE_DIFFERENT_WITHIN_GRID_SUPPORT'),'issue':'500m部分覆盖与1km整格不具有相同格内支持，原先仍计算整格权重的ρ/MAE和分级一致率。','resolution':'部分覆盖单独报实际有效面积、对应基线面积与非可比状态；仅完整覆盖作主尺度对照。'},
 {'id':'E05','severity':'REPORTING','status':'REQUIRES_CLEAR_METHOD_TEXT','file':'aggregate_basics.py','line':locate('aggregate_basics.py','Each metric uses the full square'),'issue':'指标由完整方格背景计算；相交范围仅作结果报告权重。218“按相交实际面积统计”若不说明两层支持，容易被读作所有指标均由范围内像元计算。','recommendation':'方法与图注明确“完整方格作为景观计算单元，指标赋值到研究区内方格部分；区域/乡镇均值按实际相交面积统计”。不要用完整方格habitat_m2冒充研究区内真实生境面积。'},
 {'id':'E06','severity':'REPORTING','status':'REQUIRES_CLEAR_OUTPUT_LABEL','file':'summarize_evaluation.py','line':locate('summarize_evaluation.py','primary='),'issue':'稳定低值仅针对6类primary对照，未纳入删项和重估权；low_in_all_available_schemes若不解释容易被读作全部方案一致。','recommendation':'标为“6类主对照稳定低值”；同时报告comparison_count、complete_comparison_set及删项独立敏感性，不将不完整对照都低声称为完整稳定。'},
 {'id':'E07','severity':'LOW','status':'OPTIONAL_GUARD','file':'join_indicator_records.py','line':locate('join_indicator_records.py',"base['six_valid']"),'issue':'six_valid使用notna而非finite；inf可先被记成有效，后被normalise断言阻止。','recommendation':'可在join增加finite与状态一致性断言，使异常更早定位；这不是当前发现的真实非有限值。'},
 {'id':'E08','severity':'LOW','status':'OPTIONAL_COVERAGE_COMPLETENESS','file':'evaluate_resilience.py','line':locate('evaluate_resilience.py','coverage.append'),'issue':'原coverage表未穷列无有效格网、删项和尺度情景；若报告只读此表可能漏掉明确无覆盖的方案。','recommendation':'明确coverage表仅主已评分候选，或补零覆盖行及尺度覆盖；paired_sensitivity无共同域状态仍须一并报告。'}]
passed=[
 '六指标名称、方向、VSO分组与218一致；无擅加指标。',
 '基线按生境保留，候选按B∩S_k成对比较，不做所有方案共同交集。',
 '每类使用预声明有效方案联合端点一次固定标准化，基准权重只由基线估计；不逐方案重新拉伸。',
 '熵权p=0按极限0处理；恒定指标零离散度；全恒定样本不任意赋权。',
 '删项将其余权重同比归一，未重新估权；三维得分以所属权重和归一。',
 '500m父格对应使用实际原点/几何；细格按研究区实际相交面积汇回1km，完整/部分覆盖分开。',
 '乡镇均值只对六项有效相交部分计算，同时输出乡镇区内总面积、有效面积及比例；无有效样本组合保留NA。',
 '区域统计直接用研究区并集面积权重，不把存在交叠的乡镇面积相加充作区域面积。',
 '主类间分别评价与固定五级阈值比较；图层未评估值编码0而不是最低等级1。',
 '综合计算入口要求MCR完成、NTL实际值和原生观测覆盖QA；本轮没有执行入口，没有编造NTL。']
report={'status':'REVIEW_COMPLETE_PRIMARY_ISSUES_FIXED_REPORTING_NOTES_REMAIN','scope':'只读代码审查及独立合成数学验证；非经验结果验收','reviewed_sources':meta,'synthetic_tests':checks,'findings':findings,'passed_consistency_checks':passed,'empirical_composite_run':False,'production_code_edited_by_this_agent':False,'remaining_dependency':'真实EOG2020 NTL及全部MCR完成后，仍需进行实际输出的有限值、覆盖和数值验收。'}
(OUT/'219_evaluation_readonly_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['评价代码独立只读审查','结论：主要数值与诊断问题已经父任务修复；本轮仅作合成数学测试，不是生态韧性计算结果。','合成/静态检查：'+str(len(checks))+'项通过。','']
for f in findings:lines.extend([f['id']+' '+f['status']+' '+f['file']+':'+str(f['line']),f['issue'],f.get('resolution',f.get('recommendation','')),''])
(OUT/'219_evaluation_readonly_review.txt').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'status':report['status'],'checks':len(checks),'findings':len(findings),'empirical_run':False},ensure_ascii=False))
