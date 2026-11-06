"""Verify the delivered figure revision without changing scientific results."""
from pathlib import Path
import json,hashlib,datetime
from zipfile import ZipFile
from lxml import etree
from update_manuscript_figures import POLISHED_ABSTRACT_PARTS,NS

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/figure_revision_20261106'
FIGS=ROOT/'04_图件/统一图式与过程图_20261106'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    update=read(WORK/'word_figure_update.json');docx=Path(update['output'])
    assert sha(docx)==update['output_sha256']
    assert sha(Path(update['source']))==update['source_sha256']
    native=read(WORK/'word_render_final/native_render.json')
    assert native['sha256'].lower()==sha(docx)
    assert native['pages']==20 and native['native_equations']==6 and native['tables']==3
    with ZipFile(docx)as z:
        d=etree.fromstring(z.read('word/document.xml'))
        texts=[''.join(p.xpath('.//w:t/text()',namespaces=NS))for p in d.xpath('./w:body/w:p',namespaces=NS)]
        abstract=next(t for t in texts if t.startswith('摘要：'))
        assert abstract=='摘要：'+''.join(t for t,b in POLISHED_ABSTRACT_PARTS)
        for item in update['figures']:
            assert hashlib.sha256(z.read(item['media_part'])).hexdigest()==sha(ROOT/item['image'])==item['sha256']
        assert len(d.xpath('.//w:drawing',namespaces=NS))==8
        assert len([t for t in texts if t.startswith('[')])==32
    reviews=[]
    for name in ['word_visual_06_10.json','word_visual_11_15.json','word_visual_16_20.json']:
        report=read(WORK/name)
        assert report['status']=='PASS',(name,report['status'])
        reviews.append({'path':str((WORK/name).relative_to(ROOT)),'sha256':sha(WORK/name)})
    pages=[]
    for n in range(1,21):
        current=WORK/f'word_render_final/pages/page-{n}.png'
        old=WORK/f'word_render_v1/pages/page-{n}.png'
        unchanged=sha(current)==sha(old)
        if n>2:assert unchanged,n
        pages.append({'page':n,'sha256':sha(current),'same_as_reviewed_v1':unchanged,
                      'visual_status':'PASS','review':'root actually viewed final page' if n<=2 else ('root actually viewed v1; identical final PNG' if n<=5 else 'agent actually viewed v1; identical final PNG')})
    for name in ['context_figures_final_QA.json','process_figures_independent_reopen_QA.json']:
        assert read(WORK/name)['status']=='PASS'
    figure_files=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(FIGS.iterdir())if p.is_file()]
    report={'status':'PASS','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_unchanged':True,'source':update['source'],'source_sha256':update['source_sha256'],
            'output':str(docx),'output_sha256':sha(docx),'native_engine':native['engine_path'],
            'pages':20,'words_before_references':native['words_before_references'],
            'equations':6,'tables':3,'main_figures':8,'supplementary_figures':1,'references':32,
            'all_embedded_figures_match_final_exports':True,'abstract':'polished latest user draft; two correlation directions retained; significance/reliability overstatements removed',
            'page_reviews':pages,'agent_review_receipts':reviews,'figure_files':figure_files,
            'scope':'Visual standardization, two process figures, local result explanation and author-requested abstract polish; no new ecological model or significance test.',
            'layout_notes':'Pages before full-page figures may retain blank lower space to keep figures, captions and notes together.'}
    (WORK/'final_delivery_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (WORK/'final_abstract.txt').write_text(abstract,encoding='utf-8')
    print(json.dumps({'status':'PASS','pages':20,'figure_files':len(figure_files),'output_sha256':sha(docx)},ensure_ascii=False))

if __name__=='__main__':main()
