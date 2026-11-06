from pathlib import Path
import json, hashlib, re

ROOT=Path.cwd();B=ROOT/'生态韧性正式研究_20261106';P=B/'02_过程文件/manuscript';LIB=B/'01_原始数据/参考文献'
refs=json.loads((P/'219_reference_inventory_verified.json').read_text(encoding='utf-8')); byid={r['id']:r for r in refs}
def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

intro=[
 {'paragraph':1,'role':'背景—现实管护需求','text':'气候变化与城镇扩张使城市生态系统面临持续扰动，生态韧性评价因而成为识别生态薄弱环节、安排保护修复的重要工具[2,7,16]。城乡交错地区的自然生境、农田与建设空间相互嵌合，生态空间的数量、质量及联系条件共同影响其维持生态过程的能力[2,5]。北京第二道绿化隔离地区承担连接浅山、平原与城市生态空间的任务，《北京市第二道绿化隔离地区减量提质规划（2021年—2035年）》进一步强调生态系统完整性与生态过程连续性[1]。落实这些要求，需要在区域评价的基础上定位乡镇内部的薄弱地段，区分生境维护、联系改善和灰绿配置等不同管护需求。','refs':['R01','R02','R05','R07','R16']},
 {'paragraph':2,'role':'研究进展—针对本文评价对象的不足','text':'现有生态韧性评价主要从城市综合条件、景观结构与扰动响应等方面展开。城市尺度研究采用综合指标或损益分析比较韧性水平与区域差异[15,20]；景观尺度研究将脆弱性、敏感性和自组织纳入评价，结合生境质量、斑块格局与源汇关系识别城市内部差异[2–4]；遥感时序研究则追踪扰动后植被功能、结构和组分的恢复[7,21]。针对绿隔管护，景观评价能够细化问题位置，但仍需处理两个影响应用判断的问题：部分景观指标同时包含生境数量和配置的信息，综合得分可能重复表达同一空间特征[5–6]；数据分类、指标权重与聚合规则的调整也可能改变低值区的识别[12]。因此，评价不仅需要给出高低排序，还应说明低值对应的具体短板，以及这些空间判断在不同方案下是否稳定。','refs':['R02','R03','R04','R05','R06','R07','R12','R15','R20','R21']},
 {'paragraph':3,'role':'研究问题—评价路径—面向管护的用途','text':'本文以2020年北京二道绿隔及周边35个乡镇的部分地区为对象，在边长1000 m的正方形格网上评价生态韧性潜力。评价从脆弱性、敏感性与自组织三个维度展开，分别选取生境质量与夜间灯光强度、聚集度与最小累积阻力、源汇平均距离与生态空间面积比例，刻画生境受损条件、斑块联系及灰绿配置。林灌、草地和水体湿地分别评价，在各类六项指标均有效的格网内进行熵权综合，结合单项和三维结果识别乡镇内部短板。进一步通过土地覆盖产品、参数与格网尺度对照，区分持续低值与方案敏感地段。研究将韧性评价落实为问题位置、主要短板和核查重点，为绿隔生境维护、连接改善及修复方案比选提供依据。','refs':['R02','R04','R05','R06','R09','R10','R11','R12','R17','R18','R19','R22'],'note':'本段为承接218的方法与研究目的陈述；没有预写任何空间结果或完成状态。'}]

mapping=[
 {'step':'研究对象与评价单元','approved218':'§2、§3.1','sources':['R01','R22','R18','R17','R19'],'evidence':'既有案例范围；Shi2022 PDFp3明确1km×1km评价单元；Chen2024 EI PDFp4为1km影响因素汇总；Prokopova2026 PDFpp10–11为500m方格。','implementation':'2020年、35乡镇部分地区；固定原点1km方格，500m尺度对照；乡镇统计按研究区相交面积；不把案例边界称官方二绿全域。','status':'APPROVED218'},
 {'step':'脆弱性—HQ','approved218':'§3.2–3.4、表2','sources':['R02','R10','R23'],'evidence':'Feng PDFp7 HQ；官方InVEST模型；陈妍等2016 §2.2/Table2/Table3北京参数。','implementation':'原生InVEST 3.20.2；道路与建设威胁；各类生境内部统计均值。参数原值、单位、地类适配另见参数核验JSON。','difference':'HQ为现有生境条件表征；生境内部均值属于218的适配统计，不能称作者原式均为此口径。','status':'OFFICIAL_ENGINE_RUN_COMPLETE_BY_ROOT'},
 {'step':'脆弱性—NTL','approved218':'§3.2–3.4、表2','sources':['R03','R09','R17'],'evidence':'Elvidge年度VIIRS方法；Chen2024 EI PDFp2以夜光表征人类活动；Zhang2023原指标表本轮未重新取得。','implementation':'2020 EOG年度产品，以原生像元交叠面积汇总；负向。','difference':'年度产品生成论文不是2020具体文件版本证明，需以实际文件元数据补足。','status':'2020_NATIVE_EOG_DATA_NOT_YET_AVAILABLE; R03_TABLE_NOT_REVERIFIED'},
 {'step':'敏感性—CLUMPY','approved218':'§3.2–3.4、表2','sources':['R05','R06','R11'],'evidence':'Wang2014 Table1指标筛选；Hagger2022 Methods生境破碎；FRAGSTATS官方C4定义。','implementation':'原生FRAGSTATS类级CLUMPY；林灌/草/水湿分别；固定邻接、背景与边界规则；正向。','difference':'对面积相对不敏感不等于绝对独立；仍保留指标相关和删项检查。','status':'NATIVE_SOFTWARE_PIPELINE_BY_PIPELINE219'},
 {'step':'敏感性—MCR','approved218':'§3.4','sources':['R02','R24','R25','R26','R27','R28','R29','R30'],'evidence':'Feng PDFpp7–8 MCR；Chen2024 STOTEN PDFp12核心10ha；Jin2024 PDFp6Table1完整地类/道路阻力；MSPA官方源码/Guide；Esri成本距离文档。','implementation':'官方MSPA eew=1、graphfg=8；核心17/117；主>=10ha、对照>=35ha与>100ha；保留母斑块ID并排除同母目的地；地类+道路两因子阻力按Jin原相对权重重新归一；道路影响对照移除道路项。','difference':'本研究不是Chen物种MaxEnt模型，也不是Jin原全因子模型；不引入HQ/NTL/RSEI形成指标输入互相嵌套。10/35/100ha为来源明确的筛选/尺度对照，非北京本地校准最优值。','parameter_spec':'02_过程文件/参数文献核验/219_MCR_Jin2024_twofactor_spec.json','status':'NATIVE_MSPA_COMPLETE; MCR_RUN_BY_ROOT'},
 {'step':'自组织—源汇平均距离','approved218':'§3.4、表2注','sources':['R02'],'evidence':'Feng PDFp8 Eq5源汇关系；建设空间为源、生态空间为汇。','implementation':'建设像元到最近生态空间Euclidean Distance；按建设面积加权；负向。','difference':'面积加权像元口径为218实施，不能写成Feng原文斑块个数平均的完全复制；没有建设空间不是距离0的最佳混合格网。','status':'APPROVED218'},
 {'step':'自组织—生态空间面积比例','approved218':'§3.4、表2注','sources':['R04'],'evidence':'Fan2025 §2.2.2 Eq1 ERS=S_EI/S_CL。','implementation':'E/(E+C)，E为林灌/草地/水体湿地，C为不透水面；耕地单列对照；正向。','difference':'r/(1+r)为生态—建设比的有界单调转换；地类E不同于Fan生态系统服务及保护区界定的EI，属于已批准适配。','status':'PUBLISHER_METHODS_WEB_VERIFIED'},
 {'step':'标准化与熵权','approved218':'§3.5–3.6','sources':['R02','R12'],'evidence':'Feng PDFp9 §4.2.2熵权线性加权；JRC Step6/7权重、重复表达与补偿关系。','implementation':'同类生境各自基线有效域；正负向统一；联合参照固定min/max；熵权在线性加权主方案；维度得分正向解释；主对照固定基准相对权重，重新估权单列。','difference':'权重反映样本信息分散程度，不直接等于生态过程重要性或政策投入比例。','status':'IMPLEMENTATION_RULES_WRITTEN; NOT_YET_COMPUTED_WITHOUT_NTL'},
 {'step':'分级显示','approved218':'§3.5保留连续值和分级图','sources':['R18'],'evidence':'Shi2022 PDFp5 §2.3自然断点；PDFp6 §3/Fig2五级。','implementation':'父任务已选定各生境基线Jenks五级一次拟合，对照固定；同时保留连续值、分级阈值和有效覆盖。','difference':'相对显示等级，不是通用生态阈值；不用Feng南昌0.5/0.6/0.7。','status':'APPROVED_BY_ROOT_20261106; THRESHOLDS_NOT_YET_FIT'},
 {'step':'稳健性与空间统计','approved218':'§3.5–3.6','sources':['R12'],'evidence':'JRC Step8列出数据、指标选取、标准化、权重与聚合不确定性。','implementation':'保留基线B；每一对照用B∩S_k成对共同有效域，不因一情景无源删掉所有基线；删项其余权重同比归一；500m汇总1km；有效范围、无生境/无建设/无其他同类源地/纯类CLUMPY未定义独立编码。','difference':'缺失和不适用不赋0，不写成低韧性；研究区域总面积与类型有效评价面积并报。','status':'RULES_REVIEWED_NO_NEW_RESULTS'},
 {'step':'热环境补充检查','approved218':'§3.6','sources':['R14'],'evidence':'USGS C2L2地表温度原生产品与QA。','implementation':'使用已获2020 Landsat8场景，质量筛查后考察灰绿配置与地表温度的空间关联并分片区重复比较。','difference':'对配置应用含义的补充解释，不对综合ER做过程或因果验证。','status':'DATA_AUDIT_BY_DATA219'}
]

classification={
 'created':'2026-11-06','Feng2024':{'doi':'10.1016/j.scs.2024.105933','bibliographic_year':2024,'publisher_volume':'116 (2024),105933','online_date_pdf':'22 October2024','crossref_publication_month':'December2024','HKU_issue_date':'1-Dec-2024','repository_accessioned':'17-Jan-2025','decision':'2024在线且2024卷年；2025为机构入库时间，不能改成2025文献。','classification_method_reported':'four case-defined levels; no Jenks/quantile statement found in checked text','locator':'PDFp10 §5.2，PDFp8 Fig6','levels':['low','medium-low','medium-high','high'],'thresholds':[0.5,0.6,0.7],'threshold_basis':'本文原文将阈值与南昌生态韧性状况相联系；不是通用阈值。','legend_printed':['<0.50','0.50–0.59','0.60–0.69','>0.70'],'boundary_caveat':'印刷图例为保留两位的显示；0.70闭开边界不得由本研究擅自补写为作者原规则。','screenshots':['reference_reads/R02_pdf_page01.png','reference_reads/R02_pdf_page08.png','reference_reads/R02_pdf_page10.png']},
 'Shi2022':{'doi':'10.3390/land11060921','method':'natural break method','classes':5,'locators':['PDFp5 §2.3','PDFp6 §3 and Fig2'],'screenshots':['reference_reads/R18_pdf_page05.png','reference_reads/R18_pdf_page06.png'],'use':'分级形式的参考先例；不转移其数值阈值或不同生态模型。'},
 'this_study_decision':{'source':'root2026-11-06message','rule':'每类生境基线Jenks五级拟合一次；所有对照使用该基线阈值；保留连续值','actual_numeric_breaks':'NOT_FIT_PENDING_COMPLETE_SIX_INDICATORS','classification_scope':'各生境六项有效格网；不适用/缺测另类','does_not_change_218_indicators':True}}
save(P/'219_Feng分级与年份核验.json',classification)

doc={'status':'DRAFT_EVIDENCE_PACKAGE_ONLY_NOT_MAIN_MANUSCRIPT','created':'2026-11-06','approved_source':'2020年论文成果/02_过程数据/汇报清稿218_20261106/218_clean_fulltext.txt','title':'北京二道绿隔及周边地区生态韧性评价与规划管护研究','intro_draft':intro,'method_evidence_mapping':mapping,
 'bibliographic_corrections':[{'ref':'R02','action':'保留2024，已核PDF卷年/Crossref/HKU出版日期；不误用2025入库年。'},{'ref':'R08','action':'引用实际CLCD记录8176941版本1.0.2（2023），替代新稿中的旧记录5210928；旧批准文件不改。'},{'ref':'R17','action':'不再将组成项-总分相关警告归给Chen；该文可支持夜光压力及1km影响因素统计。'},{'ref':'R23','action':'按官方期刊中文全题名登记，不缩写成相似题名。'}],
 'critical_pending':[{'id':'NTL2020','status':'本轮原生EOG2020未获取；六指标综合评价不能写已完成。'},{'id':'R03_indicator_table','status':'本轮仅核出版商摘要及元数据；NTL原表待取得，已有Chen2024原文可作活动压力补充依据，不伪称原表核验通过。'},{'id':'R04_fullpdf','status':'方法公式已有出版商网页支持，未获完整PDF；归档为网页证据。'},{'id':'R30_fullpdf','status':'勘误元数据及公开片段已核，全文PDF未获。'}],
 'data_source_notes':{'CLCD':'record8176941 v1.0.2;2020fileMD5已由data219核对','WorldCover':'2020v100；不作为实测真值','OSM':'china-200101-free.shp.zip，2020-01-01快照，不称年末','NASADEM':'主要原始观测2000；不称2020观测，未擅自进入MCR主阻力','EOG':'未获原生文件，方法文献≠数据获取证明'},
 'coverage_language':{'required':'综合指数按林灌、草地、水体湿地分别在六指标均有效格网内报告，乡镇统计注明有效覆盖面积。','independent_states':['没有目标生境','没有建设空间','纯类CLUMPY未定义','没有其他同类源地','数据覆盖不足'],'prohibited':'把缺测/不适用写成低分或把有效混合格网结论外推研究全域。'},
 'no_claims':['不声称一区/高被引已核验','不预写本轮空间结果','不声称首次构建或因果机制','不把公开版本参数称北京实测校准','不改变六项VSO指标'],
 'reference_inventory':'01_原始数据/参考文献/参考文献清单_核验信息.json','classification_evidence':'02_过程文件/manuscript/219_Feng分级与年份核验.json'}
save(P/'agent_intro_and_evidence.json',doc)
(P/'219_引言三段草稿.txt').write_text('\n\n'.join(x['text'] for x in intro)+'\n',encoding='utf-8')
(P/'219_精简方法证据映射.txt').write_text('\n\n'.join(x['step']+'｜'+x['approved218']+'\n依据：'+x['evidence']+'\n本文做法：'+x['implementation']+'\n适配说明：'+x.get('difference','见研究对象口径。')+'\n参考：'+','.join(x['sources'])+'\n状态：'+x['status'] for x in mapping)+'\n',encoding='utf-8')

# Final QA: intact copied sources, manifests, real source IDs and file presence.
errors=[]; copied=0
for r in refs:
 for a in r['files']:
  f=B/a['file']
  if not f.exists(): errors.append('Missing '+str(f));continue
  got=hashlib.sha256(f.read_bytes()).hexdigest()
  if got!=a['sha256']: errors.append('Hash changed '+a['file'])
  if a.get('source_sha256'):
   copied+=1
   if got!=a['source_sha256']:errors.append('Copy mismatch '+a['file'])
for para in intro:
 for ref in para['refs']:
  if ref not in byid:errors.append('Bad citation '+ref)
for step in mapping:
 for ref in step['sources']:
  if ref not in byid:errors.append('Bad mapping '+ref)
readable_pdf=sum(a['file'].lower().endswith('.pdf') and a.get('text_available',False) for r in refs for a in r['files'])
qa={'status':'PASS' if not errors else 'FAIL','errors':errors,'references':len(refs),'approved218_references':22,'added_parameter_references':8,'pdf_assets':sum(a['file'].lower().endswith('.pdf') for r in refs for a in r['files']),'pdf_assets_with_text':readable_pdf,'copied_assets_hash_equal':copied,'originals_untouched':True,'intro_paragraphs':3,'intro_characters':sum(len(x['text']) for x in intro),'all_citation_ids_valid':not errors,'fulltext_completeness':'PARTIAL_AS_DOCUMENTED','journal_rank_or_citation_count_verified':False}
save(P/'219_intro_reference_QA.json',qa)
(LIB/'00_阅读与核验说明.txt').write_text('本目录收录批准开题报告218的22条来源，以及本轮HQ/MSPA/MCR参数追加的8条来源。每条文献独立R编号目录，参考文献表_推荐引用.txt可直接查阅；CSV可筛选，JSON记录文件哈希和核验边界。\n\n共30条、18个PDF资产（含1份政策阅读图册与1份指南附册），不是30篇均已获得完整PDF。未获PDF的条目保留原文入口、合法元数据和可用原站网页；短跳转网页与元数据XML均不冒充全文。原始已有文件只复制，副本哈希与来源匹配。\n\n关键更正：Feng为2024卷年；CLCD使用实际记录8176941版本1.0.2（2023）。Zhang2023原指标表本轮未重新核验；EOG2020原始数据仍未获取，不能据方法文献声称数据已就绪。各条适用范围见本条README。\n\n未核验中科院分区或实时被引数，不作一区/高被引标签。来源的可靠使用依赖原文支持的具体命题，不能用期刊标签代替参数适用性核查。\n',encoding='utf-8')
print(json.dumps(qa,ensure_ascii=False))
