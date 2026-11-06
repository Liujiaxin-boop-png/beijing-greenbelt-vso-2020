"""Prepare isolated wording patches; never write the main manuscript or run data."""
from pathlib import Path
import concurrent.futures, datetime, hashlib, json, requests

BASE=Path(__file__).resolve().parent
MAIN=BASE/'manuscript_content.json'
SOURCES=BASE/'method_clarity_patch_sources'
SOURCES.mkdir(exist_ok=True)
before=MAIN.read_bytes();doc=json.loads(before.decode('utf8'))
sha=lambda b:hashlib.sha256(b).hexdigest()
urls={
 'cost_distance':'https://pro.arcgis.com/en/pro-app/3.1/tool-reference/spatial-analyst/cost-distance.htm',
 'cost_allocation':'https://pro.arcgis.com/en/pro-app/3.1/tool-reference/spatial-analyst/cost-allocation.htm',
 'euclidean_distance':'https://pro.arcgis.com/en/pro-app/3.1/tool-reference/spatial-analyst/euclidean-distance.htm'}
claims={
 'cost_distance':{'official_title':'Cost Distance (Spatial Analyst)—ArcGIS Pro','locator':'Summary; Usage; Parameters/Input cost raster','supported_claim_zh':'在成本表面计算像元到最低成本源的最小累积成本；输入成本须为正值，源栅格有效值参与分析、NoData不参与。','usage_note':'本研究同母斑块排除与分区批次由已冻结代码实现，不将其归为Esri提出的生态方法。'},
 'cost_allocation':{'official_title':'Cost Allocation (Spatial Analyst)—ArcGIS Pro','locator':'Summary; Usage/source field; Parameters/Input value raster','supported_claim_zh':'按最小累积成本为像元分配源地标识；整数源值可保留目的源地编号。','usage_note':'用于保留与核验目的源地标识，不改变冻结的成本数值或候选源。'},
 'euclidean_distance':{'official_title':'Euclidean Distance (Spatial Analyst)—ArcGIS Pro','locator':'Summary; Usage/source cells; Parameters/Distance Method','supported_claim_zh':'计算像元至最近源位置的欧氏距离，支持投影平面的PLANAR距离计算。','usage_note':'软件输入源为生态空间；论文源汇术语中的建设空间是距离提取与面积汇总对象，二者术语层级不同。'}}
def fetch(item):
 key,url=item;r=requests.get(url,timeout=(10,30));r.raise_for_status()
 assert r.url==url,(key,r.url)
 assert 'text/html' in r.headers.get('Content-Type','')
 p=SOURCES/(key+'_ArcGISPro3_1_official.html');p.write_bytes(r.content)
 return {'key':key,'url':url,'final_url':r.url,'http_status':r.status_code,
         'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'html_file':str(p.relative_to(BASE)),'sha256':sha(r.content),'bytes':len(r.content),
         'documentation_release':'3.1 family','actual_native_runtime':'ArcGIS Pro 3.1.6',**claims[key]}
with concurrent.futures.ThreadPoolExecutor(3) as pool:refs=list(pool.map(fetch,urls.items()))
ops=[]
def paragraph(id,old,new,reason,evidence):
 matches=[i for i,b in enumerate(doc['blocks']) if b.get('type')=='paragraph' and old in b.get('text','')]
 assert len(matches)==1,(id,matches)
 text=doc['blocks'][matches[0]]['text'];assert text.count(old)==1
 ops.append({'id':id,'operation':'replace_exact_substring','json_path':f"blocks[{matches[0]}].text",'old':old,'new':new,'expected_occurrences':1,'reason':reason,'evidence':evidence})

paragraph('C01_native_grid',
 '各数据统一到WGS84 Albers等积坐标系；土地覆盖固定原点、像元大小与范围，夜光和温度按原生像元与方格的交叠面积汇总。',
 '采用WGS84 Albers等积坐标系进行空间分析，土地覆盖固定原点、像元大小与范围。夜光和地表温度保留原生栅格，按原生像元投影后与评价格网的交叠面积加权汇总。',
 '将分析坐标系统一与栅格重采样区分，准确描述已冻结原生像元面积汇总方法。',
 ['approved218 §2、§3.1','219_方法参数细表_附录.json: NTL_specification_not_acquisition_claim.aggregation; LST.spatial_support'])

paragraph('C02_stable_low_seven',
 '六类主对照均有效且均属最低等级的格网记为稳定低值，不完整对照同时报告可比次数。',
 '基线与六项主对照共七个方案均有效且均属最低等级的格网记为稳定低值。六项主对照为WorldCover分类、≥35 ha源地、>100 ha源地、移除道路项、耕地纳入生态空间，以及500 m完整覆盖汇回1 km；未集齐全部方案的格网另报可比次数。',
 '明确代码已采用的基线加六项对照集合，不把缺失对照误判为不稳定。',
 ['approved218 §3.6','05_代码/src/summarize_evaluation.py: primary列表及classes中含baseline_class；consistent_low_complete_set'])

paragraph('C03_area_support',
 '乡镇统计同时报告有效覆盖比例、面积加权均值、内部标准差及最低等级格网覆盖面积，将综合水平与具体短板位置对应。',
 '乡镇统计同时报告有效覆盖比例、面积加权均值、内部标准差及最低等级格网覆盖面积。覆盖面积按格网与研究范围内乡镇部分的相交面积统计，区别于格网内生境本身的面积；三类生境的有效格网可重叠，面积分别报告，不作跨类型加总。',
 '说明正式报告面积的空间支持，保持乡镇内部研判口径，避免把有效格网覆盖面积解释为生境实体面积。',
 ['approved218 §2、§3.1、§3.5','219_方法参数细表_附录.json:spatial_support','05_代码/src/summarize_evaluation.py:intersect_m2汇总、six_valid_area_m2'])

paragraph('C04a_cost_tool_citation',
 '利用ArcGIS Pro 3.1.6的Cost Distance与Cost Allocation，',
 '利用ArcGIS Pro 3.1.6的Cost Distance与Cost Allocation工具[29]，',
 '引用实际使用的Pro工具文档；不改变算法或软件版本。',
 [urls['cost_distance'],urls['cost_allocation']])
paragraph('C04b_euclidean_tool_citation',
 '利用ArcGIS Pro 3.1.6 Euclidean Distance计算建设像元至最近生态像元的距离，',
 '利用ArcGIS Pro 3.1.6的Euclidean Distance工具[29]计算建设像元至最近生态像元的距离，',
 '补齐实际使用的Pro距离工具官方依据。',
 [urls['euclidean_distance']])

oldref=doc['references'][28]
assert 'ArcMap 10.8' in oldref and 'Cost Distance' in oldref
newref=('Esri. Cost Distance, Cost Allocation and Euclidean Distance (Spatial Analyst)—ArcGIS Pro 3.1[EB/OL]. '
        '[2026-11-06]. '+urls['cost_distance']+'; '+urls['cost_allocation']+'; '+urls['euclidean_distance']+'.')
ops.append({'id':'C04c_reference29','operation':'replace_exact_value','json_path':'references[28]',
            'reference_number':29,'old':oldref,'new':newref,'expected_occurrences':1,
            'reason':'保留编号29，替换原ArcMap指南为相同工具的Pro3.1官方文档集合；3.1.6是实际安装补丁版本，官方帮助按3.1系列组织。',
            'evidence':list(urls.values()),'individual_official_titles':[r['official_title'] for r in refs]})

report={'status':'PREPARED_NOT_APPLIED','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'target':'02_过程文件/manuscript/manuscript_content.json','target_sha256_at_preparation':sha(before),
        'scope':'Four wording/source clarity adaptations only; no main manuscript write or recomputation.',
        'groups':['native raster preservation','baseline plus six comparisons','habitat-specific grid coverage area','actual Pro official tools'],
        'operations':ops,'official_sources':refs,
        'application_rule':'Apply each exact old fragment/value only if it occurs once; if the main content has changed, recheck anchors. Preserve all unrelated blocks and all formula/parameter objects.',
        'unchanged':['six indicators and VSO dimensions','2020','1km square baseline/500m comparison','three habitat groups','HQ k and all coefficients','MCR source thresholds/cost weights','entropy and normalisation','published fixed source data','approved proposal218'],
        'no_new_empirical_claims':True,'main_file_modified':False}
assert MAIN.read_bytes()==before,'Main file changed while preparing patch; review snapshot.'
out=BASE/'219_method_clarity_patch_20261106.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
readback=json.loads(out.read_text(encoding='utf8'));assert len(readback['operations'])==6
text=['方法表述适配补丁（尚未应用）','',f'主稿原始SHA256：{sha(before)}','']
for op in ops:text += [op['id']+'  '+op['json_path'],'原文：'+op['old'],'建议：'+op['new'],'依据：'+'；'.join(op['evidence']),'']
text += ['仅保存独立补丁及官方来源；未修改主content、公式、参数、结果或开题原件。']
(BASE/'219_method_clarity_patch_20261106.txt').write_text('\n'.join(text),encoding='utf8')
print(json.dumps({'status':report['status'],'patch':str(out),'operations':len(ops),'official_documents_verified':len(refs),'main_sha256_unchanged':True},ensure_ascii=False))
