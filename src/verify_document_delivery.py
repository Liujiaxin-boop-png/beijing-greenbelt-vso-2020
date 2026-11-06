"""Reconcile actual native rendering, reviewed pages, OOXML and source facts."""
from pathlib import Path
import hashlib,json,re,zipfile,datetime
from lxml import etree

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/manuscript'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    content=read(WORK/'manuscript_content.json');docx=ROOT/'03_结果文件/论文'/content['filename']
    native=read(WORK/'final_render_v2/native_render.json')
    numeric=read(WORK/'final_numeric_text_QA.json')
    assert numeric['status']=='PASS' and numeric['content_sha256']==sha(WORK/'manuscript_content.json')
    assert sha(docx).lower()==native['sha256'].lower()
    assert native['words_before_references']<=8000 and native['pages']==17
    assert native['comments']==0 and native['native_equations']==6
    visual=[]
    for filename in ['visual_QA_pages1_9.json','visual_QA_pages10_17.json']:
        path=WORK/'final_render_v2'/filename;report=read(path)
        assert report['status']=='PASS',filename
        for row in report['pages']:
            n=int(row['page']);page=WORK/'final_render_v2/pages'/f'page-{n}.png'
            assert sha(page)==row['sha256'],(filename,n)
            visual.append(n)
    assert sorted(visual)==list(range(1,18))
    with zipfile.ZipFile(docx) as z:
        assert z.testzip() is None
        xml=etree.fromstring(z.read('word/document.xml'))
        core=etree.fromstring(z.read('docProps/core.xml'))
        assert not any((x.text or '').strip() for x in core.xpath('//*[local-name()="creator" or local-name()="lastModifiedBy"]'))
        margins=xml.find('.//w:pgMar',NS)
        assert [int(margins.get('{'+NS['w']+'}'+k)) for k in ['top','bottom','left','right']]==[1440,1440,1803,1803]
        assert len(xml.findall('.//m:oMath',NS))==6
        assert len(xml.findall('.//w:tbl',NS))==3
        assert not xml.findall('.//w:highlight',NS)
        assert not xml.findall('.//w:commentReference',NS)
        assert not xml.findall('.//w:ins',NS) and not xml.findall('.//w:del',NS)
        embedded={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
        figures=[]
        for b in content['blocks']:
            if b['type']=='figure':
                p=ROOT/b['path'];digest=sha(p);assert digest in embedded,b['path']
                figures.append({'path':b['path'],'sha256':digest})
        assert len(figures)==6 and len(embedded)==6
        paragraphs=[''.join(p.itertext()) for p in xml.findall('.//w:p',NS)]
        # Text is verified against the content source, not a manually retyped copy.
        doc_text=''.join(xml.xpath('.//w:t/text()',namespaces=NS))
        assert content['title'] in doc_text and content['abstract'] in doc_text
        for b in content['blocks']:
            if b['type'] in ('heading','paragraph'):assert b['text'] in doc_text,b.get('text','')[:30]
            elif b['type']=='table':
                for row in b['rows']:
                    for cell in row:assert str(cell).replace('\n','') in doc_text.replace('\n','')
        for i,ref in enumerate(content['references'],1):assert f'[{i}] '+ref in doc_text
    record={'status':'PASS','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'docx':str(docx.relative_to(ROOT)).replace('\\','/'),'docx_sha256':sha(docx),'content_sha256':sha(WORK/'manuscript_content.json'),
      'native_pages':native['pages'],'native_words_before_references':native['words_before_references'],
      'native_engine_path':native['engine_path'],'native_docx_unchanged':True,
      'all_17_pages_actually_visually_reviewed':True,'visual_review_files':['final_render_v2/visual_QA_pages1_9.json','final_render_v2/visual_QA_pages10_17.json'],
      'figures_exactly_match_final_native_exports':figures,'editable_OMML_equations':6,'tables':3,'references':len(content['references']),
      'highlights':0,'comments':0,'tracked_changes':0,'anonymous_metadata':True,'numeric_text_QA_sha256':sha(WORK/'final_numeric_text_QA.json'),
      'claim':'Artifact consistency and observed page quality; not a guarantee of publication or ecological external validity.'}
    (WORK/'final_delivery_QA.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:record[k]for k in ['status','native_pages','native_words_before_references','editable_OMML_equations','tables','references','docx_sha256']},ensure_ascii=False))

if __name__=='__main__':main()
