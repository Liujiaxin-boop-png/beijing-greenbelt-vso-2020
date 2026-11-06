from pathlib import Path
import json,csv,re,hashlib

ROOT=Path.cwd();B=ROOT/'生态韧性正式研究_20261106';P=B/'02_过程文件';OUT=P/'manuscript'
def read(rel):return json.loads((P/rel).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

sections=[
 {'heading':'2 研究区域与数据','paragraphs':[
 '研究沿用既有二道绿隔案例范围[22]，涉及北京35个乡镇的部分地区，并集面积1987.9 km²。范围大致衔接一道绿隔外缘与二道绿隔及相邻乡镇边界，剔除既有研究确定的集中建设地区。乡镇作为管护统计单元，区域总量按研究范围并集计算。评价以2020年为时点，分别考察林地—灌丛、草地、水体—湿地三类生境的生态韧性潜力。',
 '土地覆盖主数据为CLCD 2020年30 m产品，使用Zenodo记录8176941的1.0.2版本[8]；分类对照采用ESA WorldCover 2020 v100产品[13]，镶嵌后以众数法统一至30 m。道路取OpenStreetMap 2020年1月1日快照，保留motorway、trunk、primary及对应link等级。夜间活动指标选用EOG VIIRS 2020年度平均辐亮度及有效观测次数，原生分辨率为15角秒[9]；Landsat 8 Collection 2 Level-2地表温度用于热环境补充分析[14]。各数据统一到WGS84 Albers等积坐标系；土地覆盖固定原点、像元大小与范围，夜光和温度按原生像元与方格的交叠面积汇总。']},
 {'heading':'3 研究方法','paragraphs':[
 '评价从脆弱性、敏感性和自组织三个维度展开[2]。脆弱性对应生境受扰时容易受损的条件，以生境质量和夜间灯光强度表征生态基础与活动压力；敏感性对应景观联系对扰动的响应条件，以聚集度和最小累积阻力分别刻画局部邻接与跨斑块联系；自组织对应生态空间维持内部调节的条件，以源汇平均距离和生态空间面积比例刻画灰绿空间的位置与数量关系。六项指标先独立计算，再同向化并综合。']},
 {'heading':'3.1 空间单元与计算范围','paragraphs':[
 '采用边长1000 m的正方形格网，并以同原点500 m格网检查尺度影响[18–19]。完整方格为景观计算单元，边缘方格保留区外背景；生境质量和阻力分析在扩展背景中计算，以计入跨界威胁与联系。结果制图裁至研究区，乡镇均值按格网与乡镇覆盖部分的实际相交面积加权。因而，边缘格网呈现的是完整方格的景观条件，报告面积仅计研究区内部分。无目标生境、无建设空间或指标未定义的格网分别记录状态；综合评价仅在同类生境六项均有效的范围内开展，并同步报告有效面积。']},
 {'heading':'3.2 六项指标计算','paragraphs':[
 '（1）生境质量。采用InVEST 3.20.2 Habitat Quality模块，综合地类适宜度、威胁距离衰减和生境敏感度[10]。参照北京研究[23]，建设与主要道路的最大影响距离分别取10 km和3 km，相对权重均为1，采用线性衰减；地类适宜度及敏感度列于附表。模型按Q=H[1−D²·⁵/(D²·⁵+k²·⁵)]计算，H为适宜度，D为退化程度。先由CLCD基准运行获得研究区有效像元的最大D，再依用户指南令k=0.5Dmax，冻结为0.39925，所有产品采用同一k。格网HQ取目标生境内部均值，数值越高表明现有生境条件越好。',
 '（2）夜间灯光。以年度平均辐亮度反映夜间人类活动压力[9,17]，按原生像元面积加权汇总。有有效观测的零亮度保留为真实观测；观测次数仅用于识别无观测像元，不作为辐亮度权重。完整有效覆盖的格网进入综合评价，数值越高按越不利计分。',
 '（3）聚集度。使用FRAGSTATS 4.2.1.612计算类级CLUMPY[5–6,11]。各类生境分别按方格内像元中心取样，以四侧邻接统计同类接触，斑块划分采用八邻域，统一边界处理。该指标以随机配置为参照识别连片或离散，正向计分。',
 '（4）最小累积阻力。采用JRC MSPA 2.4识别各类生境核心区，前景连通性设为8，边宽参数设为1像元[26,28]；核心连通块面积≥10 ha作为主源地[24]。每个核心保留原完整生境斑块编号，计算时排除同一母斑块的全部源单元，避免将斑块内部移动计为外部联系。阻力面仅由地类与主要道路距离组成，采用已发表的同一分级表[25]：地类与道路的原权重0.3445、0.0281重新归一为0.924584、0.075416。利用ArcGIS Pro 3.1.6的Cost Distance与Cost Allocation，求完整生境斑块到其他同类核心的最低累积成本，再按斑块与格网相交的生境面积加权。成本越高，跨斑块联系条件越不利。',
 '（5）源汇平均距离。以建设空间为源、生态空间为汇[2]，利用ArcGIS Pro 3.1.6 Euclidean Distance计算建设像元至最近生态像元的距离，再按建设面积求均值，反映建设空间周边生态空间的邻近程度，负向计分。',
 '（6）生态空间面积比例。将生态—建设面积比转换为E/(E+C)[4]，E为林灌、草地、水体和湿地面积，C为不透水面面积。该指标反映生态空间相对建设空间的规模，正向计分；与源汇距离共同描述数量和位置配置。耕地纳入E的情景另作对照。']},
 {'heading':'3.3 综合评价与乡镇统计','paragraphs':[
 '在各类生境内，用基线及预设对照实际参与评分的观测值共同确定极差端点，统一固定参照。正向指标取z=(x−xmin)/(xmax−xmin)，负向取1−z。基准有效格网的标准化值用于熵权估计，令pij=zij/Σizij、ej=−Σipijlnpij/lnn，wj=(1−ej)/Σj(1−ej)，综合指数ER=Σjwjzij[2]；恒定指标的信息离散度取0。三维得分分别用维度内权重归一后计算，均以高值为有利。保留连续值，并参照自然断点五级显示方法[18]，使用QGIS 3.28.2对每类基线拟合一次阈值，所有对照沿用。乡镇统计同时报告有效覆盖比例、面积加权均值、内部标准差及最低等级面积，将综合水平与具体短板位置对应。']},
 {'heading':'3.4 评价检验与热环境补充','paragraphs':[
 '检验包括指标相关、逐项删除、产品、源地、阻力和尺度对照[12]。删项后其余权重同比归一；其他对照保持基准相对权重，重估权单列比较。源地阈值另取≥35 ha与>100 ha[2,24,27]，道路影响通过移除道路项、地类权重归一为1检查。每一方案分别与基线在共同有效格网内比较排序、得分差和等级一致率。500 m得分按区内相交面积汇回1 km，仅完整覆盖组进入同域比较；部分覆盖单列。六类主对照均有效且均属最低等级的格网记为稳定低值，不完整对照同时报告可比次数。',
 '热环境分析采用2020年8月3日Landsat地表温度，以6月16日和8月10日影像分别对照。剔除填充值、云及其扩展区、卷云、阴影、积雪、饱和和无有效发射率像元，按官方比例系数转为摄氏温度[14]。每日期每方格仅保留一条记录，比较源汇距离、生态空间比例与温度的Spearman相关，并分空间片区重复计算。该分析用于解释灰绿配置的热环境意义，各日期分别报告覆盖范围，不合成为年度温度。']}
]

sections[3]['paragraphs'][0]+='为匹配土地覆盖图例，耕地对应原表旱地，草地取中覆盖草地，水体取水库湖泊，湿地取滩地参数。各产品保持相同映射，使产品对照主要反映分类差异。'
sections[3]['paragraphs'][2]+='聚集度较低表示同类像元相互分散；与仅统计生态面积相比，它进一步描述相同面积在空间上如何排列。'
sections[4]['paragraphs'][0]+='式中，i表示格网，j表示指标，n为该生境基准有效格网数；权重取决于样本差异。维度得分较低的项目用于定位相对短板，并与对应单项图共同解释。'
sections[5]['paragraphs'][1]=sections[5]['paragraphs'][1].replace('并分空间片区重复计算','并以研究区外包矩形中心为界，按方格质心划分东北、西北、东南、西南四片区重复计算')
for s in sections:s['paragraphs']=[t.replace('²·⁵','^2.5') for t in s['paragraphs']]
body='\n\n'.join(s['heading']+'\n'+'\n\n'.join(s['paragraphs']) for s in sections)+'\n'
(OUT/'219_研究区域数据与方法正文_草稿.txt').write_text(body,encoding='utf-8')

freeze=read('hq/input_freeze.json');k=read('hq/k_frozen.json');mcr=read('参数文献核验/219_MCR_Jin2024_twofactor_spec.json')
ntlr=read('aggregation/ntl_aggregation_receipt.json');mcrr=read('aggregation/mcr_aggregation_receipt.json');therm=read('thermal/thermal_preparation_receipt.json');assoc=read('thermal_association/association_receipt.json')
sens=list(csv.DictReader((P/'hq/sensitivity.csv').open(encoding='utf-8-sig')))
sources=['hq/input_freeze.json','hq/k_frozen.json','hq/clcd_final.json','hq/wc_final.json','hq/sensitivity.csv','hq/clcd_threats.csv','spatial/native_config.json','spatial/native_fishnet_receipt.json','spatial/spatial_preparation_receipt.json','mspa/219_software_versions.json','mspa/219_MSPA_full_pixel_QA.json','计算审计/FRAGSTATS4.2/software_provenance.json','计算审计/FRAGSTATS4.2/independent_validation/run_receipt.json','参数文献核验/219_MCR_Jin2024_twofactor_spec.json','mcr_native/clcd_forest_shrub_core10_land_road/mcr_run_receipt.json','aggregation/mcr_aggregation_receipt.json','aggregation/ntl_aggregation_receipt.json','thermal/thermal_preparation_receipt.json','thermal_association/association_receipt.json','map_inputs/context_project_native_QA.json']
appendix={
 'status':'PARAMETER_APPENDIX_FROM_ACTUAL_CONFIGURATION_NOT_EMPIRICAL_RESULT','references_numbering':'R01–R30 as219_reference_inventory_verified.json',
 'HQ':{'software':freeze['model_version'],'source':['R10','R23'],'formula':'Q=H*(1-D^2.5/(D^2.5+k^2.5))','threats':[{'name':'construction','max_distance_m':10000,'weight':1,'decay':'linear'},{'name':'main_road','max_distance_m':3000,'weight':1,'decay':'linear'}],'sensitivity_table_actual':sens,'landcover_mapping_note':'全部不透水面映射城镇建设参数；耕地用旱地、草地用中覆盖草地、水体用水库湖泊、湿地用滩地参数。均为原表向本研究图例的明确适配。','road_classes':freeze['roads_whitelist'],'k_freeze':k,'pilot_k':freeze['pilot_k'],'pilot_role':'仅用于取得D；试运行Q不作为最终HQ','accessibility':'no_access_vector; model default accessibility=1'},
 'MCR_twofactor_table':{'land_cost':mcr['land_cost']['rows'],'road_cost':mcr['road_cost']['bins_executable'],'source':'R25 Table1, PDFp6','resistance_formula':mcr['weights']['resistance_formula'],'weights':mcr['weights'],'road_filter_same_as_HQ':True,'source_selection':{'software':'officialJRCMSPA2.4','foreground_connectivity':8,'effective_edge_width':1,'core_codes':[17,117],'baseline_area_ha':10,'baseline_operator':'>=','comparison_area_rules':['>=35ha','>100ha'],'component_rule':'8-connected core-component area; not summed parent habitat area','parent_rule':'all cores from the same complete 8-connected habitat ParentPatchID excluded together','source_references':['R24','R26','R27','R28','R02']},'cost_engine':'ArcGIS Pro3.1.6 Spatial Analyst CostDistance/CostAllocation','cost_units':'relative-resistance metre','background_boundary':'retained; original and destination parent touching outer modeled frame are flagged','direct_distance_diagnostic':'shortest Euclidean distance from chosen minimum-cost origin to selected destination-core cells; not necessarily the cost-path endpoint','original_model_adaptation':'Jin2024 retains land and road relative weights only; omitted original RSEI/MSPA/DEM/slope/rail factors. Same generic surface for three separate source types; not aquatic flow or species-specific migration model.'},
 'CLUMPY':{'software':'FRAGSTATS4.2.1.612','focal_codes':{'forest_shrub':[2,3],'grassland':[4],'water_wetland':[5,9]},'adjacency':'4-sided class adjacency','patch_neighbor_rule':8,'landscape_border':False,'sample_window':'pixel centres within full square; 30m grid may yield33/34 cells per1000m side and16/17 per500m side','raw_metric_support_area':'reported separately from exact geometric square area','source':['R05','R06','R11']},
 'NTL_specification_not_acquisition_claim':{'selected_product':'EOG VNL_v21_npp_2020_global_vcmslcfg annual average_masked and cf_cvg with identical release prefix','native_resolution_arcsec':15,'aggregation':'native-pixel projected intersection-area weighted','counts_use':'cf_cvg>0 quality gate, not brightness weight','valid_zero':'retain if observed and native mask valid','composite_support':'complete effective pixel coverage within numerical geometry tolerance','receipt_current':ntlr},
 'spatial_support':{'scope_area_km2':read('spatial/spatial_preparation_receipt.json')['scope_area_km2'],'towns':35,'projection':'WGS84 Albers equal-area; CM105, SP25/47, latOrigin0, falseE/N0','main_grid_m':1000,'comparison_grid_m':500,'origin':read('spatial/native_config.json')['origin_xy'],'metric_support':'full square landscape context; threats/sources include expanded background','report_support':'square∩study/selected-town geometry; no replacing selected-town parts with whole township','town_overlap':'regional area from scope union; township areas not summed to regional totals'},
 'LST':{'product':'Landsat8 Collection2 Level2 ST_B10','source':'R14 + archived USGS LSDS1619v4','formula_C':therm['temperature_formula_C'],'primary_scene':therm['primary_scene'],'separate_date_comparisons':assoc['comparison_scenes'],'QA_policy':therm['QA_policy'],'temperature_cutoff':None,'STQA_uncertainty_cutoff':None,'native_acquisition_m':100,'distributed_product_m':30,'spatial_support':'projected native footprint intersections; no raster resampling or cross-date composite','association_unit':assoc['observation_unit'],'correlation':assoc['correlation'],'regional_repeats':{k:v for k,v in read('thermal_association/quadrant_definition.json').items() if k!='grid_ids'},'interpretation':'gray-green configuration thermal association; not whole-ER process or causal validation'},
 'software_versions':{'InVEST':'3.20.2','FRAGSTATS':'4.2.1.612','MSPA':'2.4 October2026','ArcGIS_Pro':'3.1.6','QGIS':'3.28.2-Firenze','Python':'3.12.9','numpy':'2.5.1','scipy':'1.18.0','rasterio':'1.5.0'},
 'supporting_files':[{'file':str((P/s).relative_to(B)),'sha256':sha(P/s)} for s in sources]}
save('219_方法参数细表_附录.json',appendix)

cn=len(re.findall(r'[\u4e00-\u9fff]',body));allchars=len(body)
doc={'status':'MANUSCRIPT_METHODS_DRAFT_NOT_COMPLETION_REPORT','created':'2026-11-06','approved_framework':'218 VSO six indicators unchanged','word_count':{'Chinese_characters':cn,'all_characters_including_titles_formulas_latin_and_punctuation':allchars},'sections':sections,'appendix':'02_过程文件/manuscript/219_方法参数细表_附录.json','workflow_metadata_not_for_manuscript':{'NTL':ntlr,'MCR':{'status':mcrr['status'],'completed_scenarios':mcrr['completed'],'pending_scenarios':mcrr['pending']},'composite_status':'Not performed while originalNTL missing; no numericalER results in thismethods draft','reader_text_convention':'方法用规范论文式现在时说明选定流程，不作“数据已全部获取/实验已全部完成”的声称','HQ_parameter_sensitivity':'文献候选表中其他草地/水体适配参数未自动进入218主对照；正文不声称这些候选均已计算','NTL_table_pending':'R03原指标表本轮未核；NTL活动压力正文引用已读R17及产品R09','supplementary_status_timing':'收据是写作时快照；最终正文提交前应重读最新数据与计算完成度'},'source_receipts':appendix['supporting_files'],'scientific_claim_scope':'2020 landscape ecological-resilience potential; no future result, causal mechanism, verified biological threshold or whole-area complete score claim'}
save('agent_methods_draft.json',doc)

table=['附表 MCR两因子分级及权重（来源[25]，本文仅保留地类与道路两项）','地类：'+ '；'.join(x['label_zh']+' '+str(x['cost']) for x in mcr['land_cost']['rows']), '道路距离：0–<200m 9；200–<400m 7；400–<800m 5；800–<1000m 3；≥1000m 1。','阻力＝(0.3445×地类分值＋0.0281×道路分值)/0.3726。两个保留因子归一权重分别0.9245840042941492、0.07541599570585078。','原表边界重合处采用左闭右开实现，≥1000m归最后组；此为计算边界规则。','移除道路对照直接采用地类分值（权重1），源地保持不变。','', '附表 HQ参数（来源[23]表2–3；实际软件3.20.2）','地类｜H｜建设敏感度｜道路敏感度']
table+=['｜'.join([x['name'],x['habitat'],x['built'],x['road']]) for x in sens]
table+=['建设/主要道路最大影响距离10000/3000m；相对权重1/1；线性衰减。','k由CLCD基准研究区有效像元最大退化值0.7985000014305115的一半取得：0.39925000071525574；跨产品冻结。']
(OUT/'219_方法参数细表_可读版.txt').write_text('\n'.join(table)+'\n',encoding='utf-8')
print(json.dumps({'status':'DRAFT_WRITTEN','Chinese_characters':cn,'all_characters':allchars,'sections':len(sections),'NTL_receipt_status':ntlr['status'],'MCR_receipt_status':mcrr['status']},ensure_ascii=False))
