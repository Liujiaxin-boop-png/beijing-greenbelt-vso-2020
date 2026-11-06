from pathlib import Path
import json, csv, hashlib, shutil, re, requests
from concurrent.futures import ThreadPoolExecutor

ROOT=Path.cwd(); B=ROOT/'生态韧性正式研究_20261106'
P=B/'02_过程文件/manuscript'; LIB=B/'01_原始数据/参考文献'
refs=json.loads((P/'agent_reference_inventory_working.json').read_text(encoding='utf-8'))
byid={r['id']:r for r in refs}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

urls={
'JRC_step6_weighting':'https://knowledge-for-policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en/step-6-weighting_en',
'JRC_step7_aggregation':'https://knowledge-for-policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en/step-7-aggregating-indicators_en',
'JRC_step8_sensitivity':'https://knowledge-for-policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en/step-8-sensitivity-analysis_en'}
def fetch(kv):
 k,u=kv; p=LIB/'R12'/f'{k}_official_20261106.html'; rec={'id':'R12','url':u,'path':str(p.relative_to(B))}
 try:
  r=requests.get(u,timeout=30);rec.update(http=r.status_code,bytes=len(r.content))
  if r.status_code==200:p.write_bytes(r.content);rec['sha256']=sha(p)
 except Exception as e:rec['error']=str(e)
 return rec
with ThreadPoolExecutor(max_workers=3) as ex: receipts=list(ex.map(fetch,urls.items()))
save(P/'agent_jrc_download_receipts.json',receipts)

# Keep the earlier publisher-page capture explicitly separate from an article PDF.
old=ROOT/'2020年论文成果/02_过程数据/生态韧性精准检索204_20261103/agent_ei/Fan2025_methods_01.json'
if old.exists():
 dest=LIB/'R04'/'prior_publisher_web_capture_Fan2025_methods_01.json'
 if not dest.exists():shutil.copy2(old,dest)
 byid['R04']['files'].append({'file':str(dest.relative_to(B)),'source':str(old),'sha256':sha(dest),'source_sha256':sha(old),'kind':'prior_publisher_web_capture','unmodified_original':sha(dest)==sha(old)})

manual={
'R01':'北京市规划和自然资源委员会. 北京市第二道绿化隔离地区减量提质规划（2021年—2035年）[EB/OL]. (2023-12-29)[2026-11-06]. https://ghzrzyw.beijing.gov.cn/zhengwuxinxi/ghcg/zxgh/202312/t20231229_3520976.html.',
'R08':'YANG J, HUANG X. The 30 m annual land cover datasets and its dynamics in China from 1985 to 2022 (Version 1.0.2)[DB/OL]. Zenodo, 2023. doi:10.5281/zenodo.8176941.',
'R10':'Natural Capital Project. Habitat Quality—InVEST User Guide[EB/OL]. [2026-11-06]. https://storage.googleapis.com/releases.naturalcapitalproject.org/invest-userguide/latest/en/habitat_quality.html. 本轮运行版本3.20.2另在软件表记录。',
'R11':'FRAGSTATS. (C4) Clumpiness Index[EB/OL]. [2026-11-06]. https://www.fragstats.org/index.php/fragstats-metrics/patch-based-metrics/aggregation-metrics/c4-clumpiness-index.',
'R12':'European Commission, Joint Research Centre. Composite indicators: 10 Step Guide[EB/OL]. (2025-03-27)[2026-11-06]. https://knowledge-for-policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en. 权重、聚合及敏感性子页分别标注2020-12-01更新；附存OECD/EU/JRC 2008手册不冒充2025网页。',
'R13':'ZANAGA D, VAN DE KERCHOVE R, DE KEERSMAECKER W, et al. ESA WorldCover 10 m 2020 v100[DB/OL]. Zenodo, 2021. doi:10.5281/zenodo.5571936.',
'R14':'Earth Resources Observation and Science (EROS) Center. Landsat 8-9 Operational Land Imager / Thermal Infrared Sensor Level-2, Collection 2[DB/OL]. U.S. Geological Survey, 2020. doi:10.5066/P9OGBGM6.',
'R22':'杨婷婷. 超大城市边缘区居民点社会韧性研究——以北京二道绿隔及周边地区为例[D]. 北京: 北京林业大学, 2023.',
'R23':'陈妍, 乔飞, 江磊. 基于InVEST模型的土地利用格局变化对区域尺度生境质量的评估研究——以北京为例[J]. 北京大学学报(自然科学版), 2016, 52(3): 553-562. doi:10.13209/j.0479-8023.2016.057.',
'R28':'European Commission, Joint Research Centre. MSPA Guide[EB/OL]. October 2026[2026-11-06]. https://forest.jrc.ec.europa.eu/en/activities/lpa/mspa/.',
'R29':'Esri. Cost Distance (Spatial Analyst)—ArcMap 10.8[EB/OL]. [2026-11-06]. https://desktop.arcgis.com/en/arcmap/latest/tools/spatial-analyst-toolbox/cost-distance.htm.'}

# This table records scientific use, not claims about journal quartile or citation rank.
checks={
'R01':('LOCAL_OFFICIAL_HTML_AND_PUBLIC_PLAN','公开规划及发布会“生态系统完整性、生态过程连续性”段落；规划区镇衔接目标','政策提出蓝绿联系、生态完整性及规划衔接需求，为管护问题设定背景。','研究区含35乡镇的部分地区，不等同于官方规划全域。'),
'R02':('USER_PDF_AND_LIVE_PUBLISHER_METADATA','PDF pp.2–4概念；pp.7–9指标与熵权；p.10 §5.2分级；p.8 Fig.6','VSO景观评价框架、HQ、MCR、源汇距离、熵权线性聚合及城市内部差异。','原文为南昌六边形与六项原始指标；本研究方格、六项适配指标和参数需逐项说明，不称完整复现。2024卷年已核。'),
'R03':('PUBLISHER_ABSTRACT_METADATA_ONLY_TABLE_PENDING','出版商摘要、Crossref元数据；本轮未取得原指标表全文','多维数据开展沿海复合生态韧性评价的研究进展。','218以该文支持NTL；本轮尚未重新核验原表，不能声称已读取其夜光指标原表。'),
'R04':('PUBLISHER_METHODS_WEB_CAPTURE_NO_PDF','出版商正文 §2.2.2、Eq.(1)；既有原站网页抓取副本','原式ERS=S_EI/S_CL，以生态基础设施相对建设用地规模表征相关条件。','本文E/(E+C)为比值的有界转换；生态空间按地类界定，不等于原文80%生态系统服务累积范围与法定保护区定义。'),
'R05':('LIVE_PUBLISHER_FULLTEXT_HTML_READ','Summary；Table 1 CLUMPY；Introduction habitat amount/configuration','景观指标存在数量与配置混合效应；其比较支持选用对数量相对不敏感的CLUMPY。','不是对任何格网、分类或生境都绝对独立；原文结论不替代本研究相关与删项检验。'),
'R06':('PUBLISHER_PDF_AND_HTML','Methods—Biophysical variables—Habitat fragmentation','红树林研究采用clumpiness描述相对独立于面积的生境聚集/破碎配置。','支持指标使用先例，不将全球红树林生态结论转移到北京。PDF已用PDFium读取，pypdf流解析失败不是PDF缺失。'),
'R07':('LOCAL_FULL_PDF','PDF pp.2–4及13；PDF前置机构封面1页','地球观测的韧性指标具有不同生态含义，功能恢复与结构/组分恢复不可混同。','用于概念与观测边界；不要求本研究新增NPP，也不把静态潜力写成实测恢复速度。'),
'R08':('OFFICIAL_ZENODO_JSON_AND_FILE_HASH','Zenodo record8176941 version1.0.2 publication2023-08-01；CLCD2020文件metadata','2020主土地覆盖实际下载版本及来源。','不用旧记录5210928代替实际数据版本；文件名v01不等于记录v1.0.1；不将该数据记录的关联期刊字段写成新论文。'),
'R09':('PUBLISHER_FULL_PDF','PDF pp.1–6年度产品生成、背景及覆盖处理','VIIRS年度夜间灯光产品的生成及辐亮度解释。','文章覆盖2012–2019，2020具体版本必须另据EOG文件元数据；原始2020数据目前未取得。'),
'R10':('OFFICIAL_GUIDE_AND_SOURCE_CODE','Habitat Quality公式、威胁距离、适宜度/敏感度表；3.20.2源码','InVEST计算公式、输入字段、威胁衰减与半饱和参数语义。','软件公式与地方参数分开；北京表值依据另列R23。'),
'R11':('OFFICIAL_METRIC_DOCUMENT','C4 Clumpiness Index定义、公式与特殊取值','CLUMPY类级邻接及面积校正公式。','本轮原生FRAGSTATS执行；纯类/无焦点生境按定义状态记录，不强填最优或低分。'),
'R12':('OFFICIAL_GUIDE_LIVE_AND_ARCHIVED','Step6 weighting、Step7 aggregation、Step8 sensitivity','指标重复表达、权重/聚合假设及综合结果敏感性应联合核查。','该指南支持检查原则；删项权重归一、共同有效域、固定基准为218和本研究实施细则，不假称指南给出本地区阈值。'),
'R13':('OFFICIAL_DATACITE_ZENODO_METADATA','Zenodo5571936；2020v100文件元数据','2020 ESA WorldCover10m产品用于分类对照。','先统一图例、等积投影与30m网格；对照不是独立真值。'),
'R14':('OFFICIAL_USGS_DATACITE','USGS数据记录、场景MTL/STAC/QA','Landsat8/9 Collection2 Level2地表温度产品。','本轮仅用已获取2020 Landsat8场景；热环境关联是灰绿配置补充检查，不充当整体生态韧性实测验证。'),
'R15':('USER_FULL_PDF','PDF p.1摘要、p.2 Table1及方法','城市统计型生态韧性、熵权及区域差异研究。','城市统计指标不能直接移植到1km格网；引言仅用作研究类型对照。'),
'R16':('LOCAL_FULL_PDF','PDF pp.1–2及12','针对特定干旱生态系统的恢复力、入侵抵抗及管理规划应用。','不转移美国干旱区系数或生态阈值到北京。'),
'R17':('LOCAL_FULL_PDF','PDF p.2夜光说明；p.4 VIF、影响因素1000m×1000m汇总','城市活动压力的夜光代理、空间汇总尺度及共线检查先例。','1km在该段是影响因素统计单元；未发现其专门提出组成项-总分循环解释警告，不把该观点归给作者。'),
'R18':('LOCAL_FULL_PDF_AND_RENDERED_MAP','PDF p.3 §2.1；p.5 §2.3；p.6 §3及Fig.2','1km方格生态韧性评价和五级自然断点显示先例。','其NPP等模型不同；本文采用其分级形式，基线每类一次拟合后固定用于对照为本研究可比性实施，不移植原数值。'),
'R19':('LOCAL_FULL_PDF','PDF pp.7、10–11；500×500m/25ha方格','城郊生态系统功能评价使用500m方格的尺度先例。','不声称该尺度对本区已最优；仅为218尺度对照提供先例。'),
'R20':('AUTHOR_REPOSITORY_FULL_PDF_CC_BY','Figshare article25750938/file46096089；PDF p.1及方法','损益综合与城市内部生态韧性制图的研究类型。','作者机构公开全文已下载；不把其25变量体系写成本研究六指标。'),
'R21':('LOCAL_FULL_PDF','PDF pp.1–3','事件后功能、结构、组分的恢复评价揭示单一表征局限。','火灾时序评价与本研究2020景观潜力评价对象不同。'),
'R22':('USER_THESIS_DOCX','研究区域章节与2023-06-19作者签署页','既有研究区与35乡镇部分地区基础。','区域依据来自既有案例资料；不自动等同官方二绿边界。'),
'R23':('OFFICIAL_JOURNAL_FULLTEXT_HTML','§2.2；Table2威胁参数、Table3适宜度/敏感度','北京HQ地类适宜度、建设和道路威胁与敏感度参数的地方研究先例。','参数转录表及软件单位转换见参数核验JSON；不能称已用2020实测数据重新校准。'),
'R24':('ACCEPTED_FULL_PDF_AND_SUPPLEMENT','作者接受稿PDF p.12/印刷p.11；supplement；勘误R30','北京同类生境MSPA核心源地>=10ha及相关阈值区间的先例。','原文鸟类模型与阻力构成不同；本研究仅采用已注明的源地筛选先例，地类+道路阻力依据另列R25。'),
'R25':('PUBLISHER_FULL_PDF_AND_CROSSMARK','PDF p.6 Table1；2026-11-06 Crossmark Document is current','通用地类和道路分级阻力表。','只保留218规定地类与道路两因子，将原文两权重重新归一；不是原文全因子模型或北京本地AHP。'),
'R26':('OPEN_PUBLISHER_FULL_PDF','PDF pp.2–3/印刷428–429','MSPA开源形态分类及核心区处理。','本轮使用原生程序并按官方类别映射提取，不把自写欧氏内缩称完整MSPA。'),
'R27':('LOCAL_FULL_PDF','PDF p.10有关10–35ha绿地面积先例及其引文','城市鸟类多样性与绿地面积/景观条件的相关研究。','只能支持源地阈值对照的跨研究范围；非北京局部10ha生物学阈值校准。'),
'R28':('OFFICIAL_GUIDE_AND_NATIVE_RUN_QA','October2026 Guide p.2参数、p.6分类编码；本轮全像元QA','官方MSPA eew=1、graphfg=8及Core17/117、NoData129。','原生核心计算已完成；缺失地理参考的原输出保留，附回地理参考另存并有像元一致性核查。'),
'R29':('OFFICIAL_SOFTWARE_GUIDE','Cost Distance Usage与输入source/cost要求','正且有限的阻力、源单元与NoData处理以及最小累积成本。','同母斑块源排除与格网汇总属于218的本研究操作，不归为Esri生态参数。'),
'R30':('PUBLISHER_CORRIGENDUM_METADATA_AND_TEXT_EXCERPT','Corrigendum 917:170588；勘误原站片段','核查R24相关更正涉及鸟类/调查资料归属。','未取得完整勘误PDF；不得写全文已读，当前可核片段不提示10ha核心参数更改。')}

for r in refs:
 id=r['id']; folder=LIB/id; prior={f['file']:f for f in r.get('files',[])}
 assets=[]
 for f in sorted(folder.iterdir()):
  if not f.is_file() or f.name=='README_本条核验.txt':continue
  rel=str(f.relative_to(B));a=prior.get(rel,{'file':rel,'kind':'archived_reference_asset'})
  a['sha256']=sha(f);a['bytes']=f.stat().st_size
  if f.suffix.lower()=='.html':
   html=f.read_text(encoding='utf-8',errors='ignore');a['html_is_redirect_stub']=('Redirecting' in html and len(html)<10000)
  if f.suffix.lower()=='.pdf':
   read=P/'reference_reads'/f'{id}_fulltext_pages.json'
   if read.exists():
    pages=json.loads(read.read_text(encoding='utf-8'));a.update(pdf_page_count=len(pages),text_available=sum(len(str(x)) for x in pages)>100,read_text=str(read.relative_to(B)))
  assets.append(a)
 r['files']=assets
 r['verification']={'status':checks[id][0],'locator':checks[id][1],'supported_claim':checks[id][2],'scope_and_pending':checks[id][3]}
 if id in manual:r['recommended_citation']=manual[id]
 else:
  m=r.get('verified_metadata',{});authors=m.get('author',[])
  names=[' '.join([x.get('family','').upper(),x.get('given','')]).strip() for x in authors[:3]]
  au=', '.join(names)+(', et al' if len(authors)>3 else '')
  title=(m.get('title') or [''])[0];journal=(m.get('container-title') or [''])[0]
  date=(m.get('published') or {}).get('date-parts',[[None]])[0][0]
  vol=m.get('volume','');issue=m.get('issue');page=m.get('article-number') or m.get('page','')
  r['recommended_citation']=f"{au}. {title}[J]. {journal}, {date}, {vol}{'('+issue+')' if issue else ''}: {page}. doi:{r['doi']}."
 r['journal_rank']='NOT_VERIFIED_NOT_CLAIMED';r['citation_count']='NOT_VERIFIED_NOT_CLAIMED'
 if id=='R02':r['year_audit']={'pdf_volume_year':2024,'crossref_volume116_publication':'2024-12','hku_issue_date':'2024-12-01','hku_repository_accession':'2025-01-17','online':'2024-10-22','decision':'Cite2024; repository accession2025 is not publication year.'}
 if id=='R08':r['actual_data_version']={'record':8176941,'version':'1.0.2','record_publication':'2023-08-01','file':'CLCD_v01_2020_albert.tif','publisher_md5':'1274285bb18f9b1d443a3cc906b1310c'}
 (folder/'README_本条核验.txt').write_text(r['recommended_citation']+'\n\n核验状态：'+checks[id][0]+'\n定位：'+checks[id][1]+'\n用于：'+checks[id][2]+'\n适用范围及缺口：'+checks[id][3]+'\n\n本目录仅归档合法已有副本或公开来源。元数据、网页跳转壳不等于全文。期刊分区与被引数未核验，不作相关声称。\n',encoding='utf-8')

save(P/'219_reference_inventory_verified.json',refs)
save(LIB/'参考文献清单_核验信息.json',refs)
fields=['id','approved218_no','recommended_citation','verification_status','locator','supported_claim','scope_and_pending','pdf_count','doi','journal_rank','citation_count']
rows=[]
for r in refs:
 v=r['verification']; rows.append({k:r.get(k) for k in fields}|{'verification_status':v['status'],'locator':v['locator'],'supported_claim':v['supported_claim'],'scope_and_pending':v['scope_and_pending'],'pdf_count':sum(f['file'].lower().endswith('.pdf') for f in r['files'])})
with (LIB/'参考文献清单_可筛选.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
(LIB/'参考文献表_推荐引用.txt').write_text('\n\n'.join('['+str(int(r['id'][1:]))+'] '+r['recommended_citation'] for r in refs)+'\n',encoding='utf-8')
print('Compiled',len(refs),'references',sum(f['file'].lower().endswith('.pdf') for r in refs for f in r['files']),'PDF assets')
