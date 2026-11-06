from pathlib import Path
import json,re,shutil,hashlib,concurrent.futures,requests
from pypdf import PdfReader

ROOT=Path.cwd(); BASE=ROOT/'生态韧性正式研究_20261106'
OUT=BASE/'01_原始数据/参考文献'; PROC=BASE/'02_过程文件/manuscript'; OUT.mkdir(parents=True,exist_ok=True); PROC.mkdir(parents=True,exist_ok=True)
SRC=BASE/'02_过程文件/参数文献核验/sources'
text=(ROOT/'2020年论文成果/02_过程数据/汇报清稿218_20261106/218_clean_fulltext.txt').read_text(encoding='utf-8')
refs=[]
for line in text.splitlines():
 m=re.match(r'^\[(\d+)\] (.*)',line)
 if m:
  n=int(m[1]); raw=m[2]; d=re.search(r'(10\.\d{4,9}/[^\s]+)',raw)
  refs.append({'id':f'R{n:02d}','approved218_no':n,'approved218_text':raw,'doi':d[1] if d else None,'files':[],'journal_rank':'NOT_VERIFIED_NOT_CLAIMED','citation_count':'NOT_VERIFIED_NOT_CLAIMED'})
refs[7]['doi']='10.5281/zenodo.8176941';refs[7]['correction']='Use actual archived2020 raster record8176941,v1.0.2,2023; approved218 citation5210928 is a different version.'
extra=[('R23','CHEN2016','10.13209/j.0479-8023.2016.057'),('R24','CHEN2024','10.1016/j.scitotenv.2023.167987'),('R25','JIN2024','10.1038/s41598-024-79433-9'),('R26','SOILLE2022','10.5194/isprs-archives-XLVIII-4-W1-2022-427-2022'),('R27','CALLAGHAN2018','10.1002/ecs2.2347'),('R28','MSPA_GUIDE',None),('R29','ARCMAP108_COSTDISTANCE',None),('R30','CHEN2024_CORRIGENDUM','10.1016/j.scitotenv.2024.170588')]
for id,key,doi in extra:refs.append({'id':id,'approved218_no':None,'key':key,'doi':doi,'files':[],'journal_rank':'NOT_VERIFIED_NOT_CLAIMED','citation_count':'NOT_VERIFIED_NOT_CLAIMED'})
byid={r['id']:r for r in refs}
pdfs={
'R01':'2020年论文成果/05_投稿文件/规划年会_评阅修订199/参考文献补充/[过程35_新稿4]_官方规划公开版_8组原图阅读图册.pdf',
'R02':str(SRC/'Feng2024_user_supplied.pdf'),
'R07':'2020年论文成果/01_原始数据/生态韧性专题文献203_20261102/候选全文/Runge2025.pdf',
'R15':'计算生态韧性参考文献2026.11.5/Study of regional variations and convergence in ecological resilience of Chinese cities.pdf',
'R16':'2020年论文成果/01_原始数据/生态韧性精准检索204_20261103/agent_ei/chambers.pdf',
'R17':'2020年论文成果/01_原始数据/开题报告214_新增文献/Chen2024_Ecological_Indicators.pdf',
'R18':'2020年论文成果/01_原始数据/开题报告214_新增文献/Shi2022_Land.pdf',
'R19':'2020年论文成果/01_原始数据/开题报告214_新增文献/Prokopova2026_Land.pdf',
'R21':'2020年论文成果/01_原始数据/生态韧性专题文献203_20261102/候选全文/Johnson2025_full.pdf',
'R24':str(SRC/'Chen2024_Beijing_STOTEN_accepted.pdf'),
'R25':str(SRC/'Jin2024_SciRep_79433.pdf'),
'R26':str(SRC/'SoilleVogt2022_MSPA.pdf'),
'R27':str(SRC/'Callaghan2018_Ecosphere_core_area_basis.pdf'),
'R28':str(SRC/'MSPA_Guide_official.pdf')}
misc={
'R01':['2020年论文成果/05_投稿文件/规划年会_评阅修订199/参考文献补充/[35]_北京市规自委_2023_二绿减量提质规划_官方原网页.html','2020年论文成果/05_投稿文件/规划年会_三轮修订198/参考文献阅读库/[06]_北京市政府_2023_二道绿隔减量提质规划发布会_官方原网页.html'],
'R08':[str(BASE/'01_原始数据/CLCD2020/zenodo_record_8176941.json'),str(BASE/'01_原始数据/CLCD2020/CLCD_v01_2020_albert.metadata.json')],
'R10':[str(SRC/'InVEST_HQ_official_current.html'),str(SRC/'InVEST3_20_2_habitat_quality.py')],
'R11':[str(SRC/'FRAGSTATS_CLUMPY_official.html'),str(SRC/'FRAGSTATS_CLUMPY_formula.jpg')],
'R12':['2020年论文成果/05_投稿文件/规划年会_方法优化202/本轮新增参考文献/OECD_EU_JRC_2008_复合指标构建指南.pdf'],
'R22':['学位论文：杨婷婷-超大城市边缘区居民点社会韧性研究——以北京二道绿隔及周边地区为例.docx'],
'R23':[str(SRC/'Chen2016_Beijing_HQ.html')],
'R24':[str(SRC/'Chen2024_1-s2.0-S0048969723066147-mmc1.docx')],
'R25':[str(SRC/'Jin2024_Crossmark.html')],
'R29':[str(SRC/'ArcMap10_8_CostDistance.html')],
'R30':[str(SRC/'Chen2024_corrigendum_api.xml')]}
def hash(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copyasset(id,path):
 src=Path(path);src=src if src.is_absolute() else ROOT/src
 if not src.is_file():byid[id].setdefault('missing_local_files',[]).append(str(src));return
 folder=OUT/id;folder.mkdir(exist_ok=True);dest=folder/src.name
 if not dest.exists():shutil.copy2(src,dest)
 a={'file':str(dest.relative_to(BASE)),'source':str(src),'sha256':hash(dest),'source_sha256':hash(src),'kind':'existing_local_copy','unmodified_original':hash(src)==hash(dest)}
 if dest.suffix.lower()=='.pdf':
  try:
   reader=PdfReader(dest);pages=[p.extract_text() or '' for p in reader.pages];a['pdf_page_count']=len(pages)
   rd=PROC/'reference_reads';rd.mkdir(exist_ok=True);(rd/f'{id}_fulltext_pages.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8');a['read_text']=str((rd/f'{id}_fulltext_pages.json').relative_to(BASE));a['text_available']=sum(map(len,pages))>100
  except Exception as e:a['pdf_read_error']=str(e)
 byid[id]['files'].append(a)
for id,path in pdfs.items():copyasset(id,path)
for id,paths in misc.items():
 for path in paths:copyasset(id,path)
urls={
'R01':'https://ghzrzyw.beijing.gov.cn/zhengwuxinxi/ghcg/zxgh/202312/t20231229_3520976.html',
'R02':'https://hub.hku.hk/handle/10722/353336',
'R03':'https://doi.org/10.1016/j.ecolind.2023.110981',
'R04':'https://doi.org/10.1016/j.ecolind.2024.112980',
'R05':'https://besjournals.onlinelibrary.wiley.com/doi/10.1111/2041-210x.12198',
'R06':'https://www.nature.com/articles/s41467-022-33962-x',
'R09':'https://www.mdpi.com/2072-4292/13/5/922',
'R12':'https://knowledge4policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en',
'R13':'https://zenodo.org/records/5571936',
'R14':'https://doi.org/10.5066/P9OGBGM6',
'R20':'https://doi.org/10.1016/j.scs.2024.105252',
'R28':'https://forest.jrc.ec.europa.eu/en/activities/lpa/mspa/' }
def fetch_ref(r):
 folder=OUT/r['id'];folder.mkdir(exist_ok=True);d=r.get('doi')
 if d:
  api='https://api.datacite.org/dois/'+d if d.startswith(('10.5281/','10.5066/')) else 'https://api.crossref.org/works/'+d
  try:
   rr=requests.get(api,timeout=30);r['metadata_http']=rr.status_code;r['metadata_url']=api
   if rr.status_code==200:
    raw=rr.json();(folder/'metadata_live_20261106.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8')
    if 'crossref' in api:
     m=raw['message'];r['verified_metadata']={k:m.get(k) for k in ['title','author','container-title','volume','issue','page','article-number','published','published-print','published-online','issued','URL','link','update-to','relation']}
    else:r['verified_metadata']=raw['data']['attributes']
  except Exception as e:r['metadata_error']=str(e)
 url=urls.get(r['id']) or ('https://doi.org/'+d if d else None);r['access_url']=url
 if url:
  (folder/'原文入口.url').write_text('[InternetShortcut]\nURL='+url+'\n',encoding='utf-8')
  try:
   h=requests.get(url,timeout=30);r['web_http']=h.status_code;r['web_final_url']=h.url
   if h.status_code==200:
    (folder/'official_or_institution_page_20261106.html').write_bytes(h.content)
   else:r['fulltext_access_note']='Official/institution page fetch failed; do not infer fulltext read from DOI metadata.'
  except Exception as e:r['web_error']=str(e)
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for r in ex.map(fetch_ref,refs):print(r['id'],r.get('metadata_http'),r.get('web_http'),flush=True)
(PROC/'agent_reference_inventory_working.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2),encoding='utf-8')
print('Initial archive and metadata completed',len(refs))
