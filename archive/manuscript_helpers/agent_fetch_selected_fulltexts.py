from pathlib import Path
import requests,concurrent.futures,json,re,hashlib
from pypdf import PdfReader
BASE=Path.cwd()/'生态韧性正式研究_20261106';OUT=BASE/'01_原始数据/参考文献';PROC=BASE/'02_过程文件/manuscript'
targets=[
 ('R03','Elsevier_primary_xml','https://api.elsevier.com/content/article/pii/S1470160X23011238?httpAccept=text/xml'),
 ('R04','Elsevier_primary_xml','https://api.elsevier.com/content/article/pii/S1470160X24014377?httpAccept=text/xml'),
 ('R20','Elsevier_primary_xml','https://api.elsevier.com/content/article/doi/10.1016/j.scs.2024.105252?httpAccept=text/xml'),
 ('R06','publisher_fulltext_pdf','https://www.nature.com/articles/s41467-022-33962-x.pdf'),
 ('R09','publisher_fulltext_pdf','https://mdpi-res.com/d_attachment/remotesensing/remotesensing-13-00922/article_deploy/remotesensing-13-00922.pdf'),
 ('R05','author_institution_html','https://researchportal.helsinki.fi/en/publications/measuring-habitat-fragmentation-an-evaluation-of-landscape-patter/'),
 ('R01','policy_press_conference_html','https://www.beijing.gov.cn/shipin/Interviewlive/990.html')]
def fetch(t):
 id,label,url=t;rec={'id':id,'label':label,'url':url}
 try:
  r=requests.get(url,timeout=40);rec.update({'http':r.status_code,'content_type':r.headers.get('Content-Type'),'bytes':len(r.content)})
  if r.status_code==200:
   ext='.pdf' if r.content[:4]==b'%PDF' else '.xml' if 'xml' in label else '.html'
   dest=OUT/id/(label+ext);dest.write_bytes(r.content);rec.update({'path':str(dest.relative_to(BASE)),'sha256':hashlib.sha256(r.content).hexdigest()})
   if ext=='.pdf':
    pages=[p.extract_text() or '' for p in PdfReader(dest).pages];rec['pages']=len(pages);(PROC/'reference_reads'/f'{id}_fulltext_pages.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
 except Exception as e:rec['error']=str(e)
 return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 records=list(ex.map(fetch,targets))
(PROC/'agent_selected_fulltext_downloads.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
for r in records:print(json.dumps(r,ensure_ascii=False),flush=True)
