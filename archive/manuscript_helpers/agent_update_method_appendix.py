"""Versioned documentary update only; preserves all frozen numerical parameters."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,json,shutil

W=Path(r'D:\ER219_work'); M=W/'manuscript'; ROOT=W.resolve().parent
R=Path(r'D:\ER219_results'); RAW=Path(r'D:\ER219_raw')
STAMP=datetime.now().strftime('%Y%m%d_%H%M%S')
J=M/'219_方法参数细表_附录.json'; T=M/'219_方法参数细表_可读版.txt'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads(J.read_text(encoding='utf-8')); d=copy.deepcopy(old)
archive=M/'archive'/('219_附表更新前_'+STAMP);archive.mkdir(parents=True,exist_ok=False)
backup=[]
for p in [J,T,M/'219_方法参数细表_附录.txt']:
 if p.exists():
  dest=archive/p.name;shutil.copy2(p,dest);assert sha(dest)==sha(p)
  backup.append({'original':str(p),'archived':str(dest),'sha256':sha(dest)})
main=M/'manuscript_content.json';mh=sha(main)
receipt_path=W/'aggregation/ntl_aggregation_receipt.json'
qa_path=W/'aggregation/ntl_independent_QA.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
qa=json.loads(qa_path.read_text(encoding='utf-8'))
assert receipt['status']=='PASS' and qa['status']=='PASS'
ntl=d.pop('NTL_specification_not_acquisition_claim')
ntl['selected_product']=receipt['release']+' annual average_masked and cf_cvg'
ntl['valid_zero']='原始average_masked产品在两层掩膜有效、数值有限且cf_cvg>0时保留零值；零值包括产品背景处理所得的零，不解释为物理真实零亮度或无人类活动。'
ntl['receipt_current']={
 'status':receipt['status'],'created_utc':receipt['created_utc'],'release':receipt['release'],
 'result':receipt['result'],'result_sha256':receipt['result_sha256'],'rows':receipt['rows'],
 'inputs':receipt['inputs'],'analysis_support':receipt['analysis_support'],
 'quality_policy':qa['quality_semantics'],'zero_semantics':qa['zero_semantics'],
 'main_missing_policy':receipt['main_missing_policy'],'cf_cvg_mean':receipt['cf_cvg_mean'],
 'radiance_unit':receipt['radiance_unit'],'radiance_transform':receipt['radiance_transform'],
 'threshold_or_imputation':receipt['threshold_or_imputation'],
 'grids':[{'scale_m':r['scale_m'],'grid_rows':r['grid_rows'],
           'complete_support_grids':r['complete_support_grids'],
           'partial_support_grids':r['partial_support_grids'],
           'no_valid_support_grids':r['no_valid_support_grids']} for r in receipt['grids']],
 'source_receipt':str(receipt_path),'source_receipt_sha256':sha(receipt_path),
 'wording_note':'本附表按独立QA修正零值语义；未修改原始回执、像元数值或计算规则。'}
ntl['independent_QA']={k:qa[k] for k in ['status','created_utc','scope','sample_n','field_comparisons_n',
 'production_functions_imported','same_year_release_native_15_arcsecond_pair','zero_semantics','quality_semantics']}
ntl['independent_QA']['source_file']=str(qa_path);ntl['independent_QA']['sha256']=sha(qa_path)
d['NTL']=ntl
d['status']='PARAMETER_APPENDIX_WITH_ACTUAL_NTL_PASS_RECEIPTS_CLASSIFICATION_PENDING'
d['updated_utc']=datetime.now(timezone.utc).isoformat()
d['update_scope']='执行状态及产品零值语义更新；所有冻结数值参数、六指标、评价范围与统计方法不改。'
d['previous_version_archive']=backup
q_final=W/'evaluation/final_scientific_QA.json'
q=json.loads(q_final.read_text(encoding='utf-8'))
d['classification_implementation']={'method':'基线同类生境Jenks自然断点五级；对照沿用基线阈值',
 'current_numeric_QA':q.get('status'),'current_failure':q.get('failure'),
 'implementation_status':'精确五级实现由pipeline219核验后补充；此处不预填版本，不冻结未通过分级。',
 'source_receipt':str(q_final),'source_sha256':sha(q_final)}

sources=json.loads((M/'219_method_clarity_patch_20261106.json').read_text(encoding='utf-8'))['official_sources']
destdir=RAW/'参考文献'/'官方方法文档新增';destdir.mkdir(parents=True,exist_ok=True)
source_manifest=[]
for s in sources:
 src=M/s['html_file'];assert sha(src)==s['sha256']
 dst=destdir/src.name
 if dst.exists():assert sha(dst)==sha(src),f'Existing different archive: {dst}'
 else:shutil.copy2(src,dst)
 item={**s,'archive_file':str(dst.relative_to(RAW)),'archive_sha256':sha(dst),
       'archive_contains':'公开官方方法HTML；无认证信息、浏览器cookie或凭证。'}
 source_manifest.append(item)
manifest={'archived_utc':datetime.now(timezone.utc).isoformat(),'source_type':'official_public_documentation',
 'actual_runtime':'ArcGIS Pro 3.1.6','documentation_family':'ArcGIS Pro 3.1','sources':source_manifest}
mf=destdir/'219_Esri官方文档来源与哈希.json'
mf.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
d['official_software_documentation']=manifest

for s in d['supporting_files']:
 p=ROOT/s['file']
 s['current_exists']=p.exists()
 if p.exists():s['sha256']=sha(p)
for p in [qa_path,mf]:
 d['supporting_files'].append({'file':str(p.resolve().relative_to(ROOT)), 'sha256':sha(p),'current_exists':True})
for key in ['HQ','MCR_twofactor_table','CLUMPY','spatial_support','LST']:
 assert d[key]==old[key],key+' numerical or method change forbidden'

lines=['附表S1 生境质量参数（R23表2—3；InVEST 3.20.2）',
 '地类｜生境适宜性H｜建设胁迫敏感度｜道路胁迫敏感度']
zh={1:'耕地',2:'林地',3:'灌丛',4:'草地',5:'水体',7:'裸地',8:'建设不透水面',9:'湿地'}
for r in d['HQ']['sensitivity_table_actual']:
 lines.append(f"{zh[int(r['lucode'])]}｜{r['habitat']}｜{r['built']}｜{r['road']}")
lines.extend(['建设/主要道路最大影响距离分别10000/3000 m，相对权重1/1，线性衰减。',
 '主要道路包括motorway、trunk、primary及其link。无可达性矢量，使用模型默认可达性1。',
 'k由CLCD基准研究区有效像元最大退化值0.7985000014305115的一半取得：0.39925000071525574；各土地覆盖产品固定同一k。',
 '地类图例适配：不透水面对应城镇建设参数；耕地、草地、水体、湿地分别采用原表旱地、中覆盖草地、水库湖泊、滩地参数。','',
 '附表S2 两因子阻力参数（R25表1，第6页）','地类｜相对阻力'])
for r in d['MCR_twofactor_table']['land_cost']:lines.append(f"{r['label_zh']}｜{r['cost']}")
lines.extend(['道路距离｜相对阻力','0–<200 m｜9','200–<400 m｜7','400–<800 m｜5','800–<1000 m｜3','≥1000 m｜1',
 '阻力=(0.3445×地类分值+0.0281×道路分值)/0.3726；两个保留因子归一权重分别0.9245840042941492、0.07541599570585078。',
 '原文还使用RSEI、MSPA、DEM、坡度、铁路等因子；本研究按已确认方案仅保留地类与道路相对权重。道路分组边界采用左闭右开。',
 '去道路对照使用地类权重1，源地不变。该方案用于道路阻力设定敏感性检查。','',
 '附表S3 核心源地、同类联系与聚集度计算',
 'MSPA采用官方2.4，8邻接前景、有效边宽1像元，核心类别17与117。按8邻接核心连通块面积筛选，主方案≥10 ha，对照≥35 ha和>100 ha。',
 '母斑块按完整同类生境8邻接标识；查询最近最低成本核心时排除同一母斑块的全部核心。三个生境组分别评价，共用同一套两因子阻力。',
 'ArcGIS Pro 3.1.6 Spatial Analyst原生CostDistance/CostAllocation计算最小累积成本与目标标识；背景外边界接触记录另保留。',
 'CLUMPY由FRAGSTATS 4.2.1.612计算，斑块规则8邻接，类别邻接统计按4边相邻，landscape border关闭；按完整方格的像元中心范围统计。','',
 '附表S4 夜间灯光产品与聚合执行记录',
 '产品：'+receipt['release']+'；原生15角秒average_masked与cf_cvg同发布批次。',
 '亮度单位：nW cm⁻² sr⁻¹；保留原生网格，按像元投影轮廓与完整1 km/500 m方格相交面积加权。',
 '质量条件：两产品原始掩膜有效、数值有限且原始cf_cvg>0。cf_cvg只作质量门槛，不作亮度权重。',
 '有效产品零值保留，包括背景处理所得零值；不据此判定物理真实零亮度或不存在人类活动。',
 '主NTL要求完整方格有效覆盖，容差max(10⁻⁶ m²，格网面积×10⁻¹⁰)；部分覆盖均值另存，不替代主值。',
 '真实聚合与独立数值/空间支持QA均PASS；1 km为2478格，500 m为9001格，共11479格；独立抽核27格、270项字段比较。',
 '执行回执：02_过程文件/aggregation/ntl_aggregation_receipt.json；独立核验：ntl_independent_QA.json。','',
 '附表S5 空间统计口径与温度补充分析',
 '主方格1 km、对照500 m，固定起点(921000,4309000)；WGS84 Albers等积投影，中央经线105°、标准纬线25°/47°。',
 '景观指标用完整方格；区域统计用方格与研究区相交面积，乡镇统计用方格与研究区内乡镇部分相交面积。各生境有效覆盖范围可重叠，不相加为总量。',
 'Landsat8 C2 L2 ST_B10使用2020-08-03主景，06-16和08-10分别对照；温度=DN×0.00341802+149−273.15 ℃。',
 '使用原生产品像元轮廓相交统计，不跨日期拼接；QA_PIXEL低6位均0、QA_RADSAT=0，ST、ST_QA和ST_EMIS有效，水体标志不排除；不新增温度或ST_QA阈值。',
 '同一日期按1 km格网计算灰绿配置与热环境的Spearman相关；不将三类生境重复行计为独立样本。','',
 '分级执行备注：Jenks自然断点五级及基线阈值固定原则不变，数值实现正在独立核验；不在此版本冻结未通过分级的阈值。',
 '官方软件文档：01_原始数据/参考文献/官方方法文档新增/；来源URL、获取时间及SHA-256见同目录来源清单。'])
J.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
T.write_text('\n'.join(lines)+'\n',encoding='utf-8')
same=M/'219_方法参数细表_附录.txt';shutil.copy2(T,same)
supp=R/'论文补充材料';supp.mkdir(parents=True,exist_ok=True)
copies=[]
for p in [J,same]:
 dest=supp/p.name
 if dest.exists() and sha(dest)!=sha(p):shutil.copy2(dest,archive/('补充材料旧版_'+dest.name))
 shutil.copy2(p,dest);assert sha(p)==sha(dest)
 copies.append({'file':str(dest),'sha256':sha(dest)})
assert sha(main)==mh,'Main manuscript was changed by another process; this updater does not write it'
record={'status':'UPDATED_NTL_AND_DOCUMENTARY_RECORDS_NUMERIC_PARAMETERS_UNCHANGED',
 'created_utc':datetime.now(timezone.utc).isoformat(),'backup':backup,
 'updated':[str(J),str(T),str(same)],'supplement_copies':copies,
 'official_sources_manifest':str(mf),'official_sources_sha256':sha(mf),
 'unchanged_frozen_parameter_groups':['HQ','MCR_twofactor_table','CLUMPY','spatial_support','LST'],
 'main_content_sha256_before':mh,'main_content_sha256_after':sha(main),
 'main_content_not_written':True,'production_data_not_written':True}
(M/'219_附表执行回执更新记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':record['status'],'supplement':str(supp),'archive':str(archive),'official_sources':str(destdir)},ensure_ascii=False))
