"""Insert evidence-linked process figures and replace styled figures in a new DOCX.

Preserves source manuscript, all tables/equations/references and existing marks.
The old figures remain in their original folder; no analysis is recomputed.
"""
from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
from lxml import etree
from PIL import Image
import json, hashlib, re, datetime, argparse

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/figure_revision_20261106'
FIGS=ROOT/'04_图件/统一图式与过程图_20261106'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'pic':'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
W='{'+NS['w']+'}'
REL='{http://schemas.openxmlformats.org/package/2006/relationships}'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
txt=lambda p:''.join(p.xpath('.//w:t/text()',namespaces=NS))
POLISHED_ABSTRACT_PARTS=json.loads((WORK/'abstract_polished_input.json').read_text(encoding='utf-8'))

def highlight(run):
    pr=run.find('w:rPr',NS)
    if pr is None:pr=etree.Element(W+'rPr');run.insert(0,pr)
    if pr.find('w:highlight',NS) is None:etree.SubElement(pr,W+'highlight').set(W+'val','yellow')

def paragraph(template,text,size=None,center=False):
    p=deepcopy(template)
    pr=p.find('w:pPr',NS)
    if pr is None:pr=etree.Element(W+'pPr');p.insert(0,pr)
    for k in ['keepNext','pageBreakBefore']:
        for el in list(pr.findall('w:'+k,NS)):pr.remove(el)
    if center:
        jc=pr.find('w:jc',NS)
        if jc is None:jc=etree.SubElement(pr,W+'jc')
        jc.set(W+'val','center')
    rpr=p.find('w:r/w:rPr',NS);rpr=deepcopy(rpr)if rpr is not None else etree.Element(W+'rPr')
    for ch in list(p):
        if ch.tag!=W+'pPr':p.remove(ch)
    if size:
        fonts=rpr.find('w:rFonts',NS)
        if fonts is None:fonts=etree.SubElement(rpr,W+'rFonts')
        for k in ['ascii','hAnsi','eastAsia','cs']:fonts.set(W+k,'SimHei')
        for k in ['sz','szCs']:
            el=rpr.find('w:'+k,NS)
            if el is None:el=etree.SubElement(rpr,W+k)
            el.set(W+'val',str(round(size*2)))
    run=etree.SubElement(p,W+'r');run.append(rpr);highlight(run);etree.SubElement(run,W+'t').text=text
    return p

def size_image(p,path):
    with Image.open(path)as im:w,h=im.size
    cx=round(146.4*36000);cy=round(cx*h/w)
    for e in p.xpath('.//wp:extent|.//a:xfrm/a:ext',namespaces=NS):e.set('cx',str(cx));e.set('cy',str(cy))
    return {'width_mm':146.4,'height_mm':cy/36000,'pixel_size':[w,h]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-suffix',default='过程图与统一图式修订版_20261106');args=ap.parse_args()
    snap=json.loads((WORK/'source_snapshot.json').read_text(encoding='utf-8'))
    source=Path(snap['source']);assert sha(source)==snap['sha256']
    output=source.with_name('北京二道绿隔及周边生态韧性评价_'+args.output_suffix+'.docx');assert not output.exists()
    figures={}
    for n in range(1,9):
        match=list(FIGS.glob(f'图{n}_*.png'));assert len(match)==1,(n,match);figures[n]=match[0]
    manifest=[]
    with ZipFile(source)as z:
        document=etree.fromstring(z.read('word/document.xml'));body=document.find('w:body',NS);original=list(body)
        rels=etree.fromstring(z.read('word/_rels/document.xml.rels'))
        relmap={e.get('Id'):e for e in rels};pictures=[p for p in original if p.xpath('.//w:drawing',namespaces=NS)]
        assert len(pictures)==6
        replacements={};mapping={1:1,2:2,3:5,4:6,5:7,6:8}
        for old,p in enumerate(pictures,1):
            rid=p.xpath('.//a:blip/@r:embed',namespaces=NS)[0];part='word/'+relmap[rid].get('Target');new=mapping[old]
            replacements[part]=figures[new].read_bytes();dims=size_image(p,figures[new])
            manifest.append({'number':new,'image':str(figures[new].relative_to(ROOT)),'media_part':part,'sha256':sha(figures[new]),**dims})
        # Renumber old references in one pass to avoid cascading 3->5->7.
        for t in document.xpath('.//w:t',namespaces=NS):
            old=t.text or '';new=re.sub(r'图([3-6])(?!\d)',lambda m:'图'+str(mapping[int(m[1])]),old)
            if old!=new:t.text=new;highlight(t.getparent())
        # Latest user request authorizes polishing the revised abstract.
        # Preserve findings; do not infer significance or reliability from coverage.
        abstract_source=next(p for p in original if txt(p).startswith('摘要：'))
        abstract=paragraph(abstract_source,'')
        apr=abstract.find('w:r/w:rPr',NS)
        apr=deepcopy(apr)
        for tag in ['b','bCs']:
            for el in list(apr.findall('w:'+tag,NS)):apr.remove(el)
        for r in list(abstract.findall('w:r',NS)):abstract.remove(r)
        for text,bold in [('摘要：',True)]+POLISHED_ABSTRACT_PARTS:
            r=etree.SubElement(abstract,W+'r');rp=deepcopy(apr);r.append(rp)
            if bold:etree.SubElement(rp,W+'b')
            highlight(r)
            t=etree.SubElement(r,W+'t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=text
        body.replace(abstract_source,abstract)
        # Preserve prose and its previous revision highlights. Shorten only a
        # duplicated area explanation to make room for the process narrative.
        anchor=None
        for i,p in enumerate(original):
            text=txt(p)
            if text.startswith('4.1 有效评价范围'):
                replacement=paragraph(p,'4.1 有效评价范围与分项结果');body.replace(p,replacement)
            if text.startswith('表2所列面积是有效格网'):
                replacement=paragraph(p,'表2统计有效格网覆盖面积，而非生境实体面积；三类范围可能重叠，不能相加。')
                body.replace(p,replacement);anchor=replacement
        assert anchor is not None
        body_template=next(p for p in original if txt(p).startswith('乡镇均值会掩盖'))
        caption_template=next(p for p in original if txt(p).startswith('图5 各类生境'))
        note_template=next(p for p in original if txt(p).startswith('注：格网计算结果'))
        intro='同类生境内，分项条件并不同步。图3中，部分林灌格网的斑块聚集度较高，跨斑块联系阻力仍较高；图4中，部分敏感性维度得分较高的格网，自组织得分偏低。因此，综合分级（图5）需结合斑块内部集聚、跨斑块联系及灰绿配置分别解读。'
        inserts=[paragraph(body_template,intro)]
        ids=[int(x.get('id'))for x in document.xpath('.//wp:docPr',namespaces=NS)];next_id=max(ids)+1
        relnums=[int(x[3:])for x in relmap if re.fullmatch(r'rId\d+',x)];next_rel=max(relnums)+1
        for n in [3,4]:
            rid=f'rId{next_rel}';next_rel+=1;part=f'word/media/process_figure_{n}.png'
            etree.SubElement(rels,REL+'Relationship',Id=rid,Type=NS['r']+'/image',Target=part.removeprefix('word/'))
            replacements[part]=figures[n].read_bytes();p=deepcopy(pictures[0])
            p.xpath('.//a:blip',namespaces=NS)[0].set('{'+NS['r']+'}embed',rid)
            for e in p.xpath('.//wp:docPr|.//pic:cNvPr',namespaces=NS):e.set('id',str(next_id));e.set('name',f'Process figure {n}')
            next_id+=1;dims=size_image(p,figures[n]);inserts.append(p)
            if n==3:
                cap='图3 林灌有效格网的六项原始指标空间分布'
                note='注：840个格网范围一致。夜光、MCR用log10(1+x)色阶展示，刻度为原值；颜色深浅不表示综合韧性高低。'
            else:
                cap='图4 三类生境的脆弱性、敏感性与自组织得分'
                note='注：三维高值均有利；三类生境独立评价，不作跨生境排名。灰色未评价不等于低韧性。'
            inserts.extend([paragraph(caption_template,cap,9.5,True),paragraph(note_template,note,8.5)])
            manifest.append({'number':n,'image':str(figures[n].relative_to(ROOT)),'media_part':part,'sha256':sha(figures[n]),**dims})
        pos=body.index(anchor)+1
        for p in inserts:body.insert(pos,p);pos+=1
        # All figure captions use one Heiti hierarchy, including retained ones.
        for p in body:
            if re.match(r'^图[1-8] ',txt(p)):
                for r in p.findall('w:r',NS):
                    highlight(r)
                    rp=r.find('w:rPr',NS)
                    if rp is None:rp=etree.Element(W+'rPr');r.insert(0,rp)
                    rf=rp.find('w:rFonts',NS)
                    if rf is None:rf=etree.SubElement(rp,W+'rFonts')
                    for k in ['ascii','hAnsi','eastAsia','cs']:rf.set(W+k,'SimHei')
                    for k in ['sz','szCs']:
                        el=rp.find('w:'+k,NS)
                        if el is None:el=etree.SubElement(rp,W+k)
                        el.set(W+'val','19')
        replacements['word/document.xml']=etree.tostring(document,encoding='UTF-8',xml_declaration=True,standalone=True)
        replacements['word/_rels/document.xml.rels']=etree.tostring(rels,encoding='UTF-8',xml_declaration=True,standalone=True)
        with ZipFile(output,'w')as out:
            for info in z.infolist():out.writestr(deepcopy(info),replacements.pop(info.filename,z.read(info.filename)))
            for part,data in replacements.items():out.writestr(part,data)
        before=etree.fromstring(z.read('word/document.xml'))
        for path in ['.//m:oMath','.//w:tbl','.//w:sectPr']:
            assert [etree.tostring(x)for x in before.xpath(path,namespaces=NS)]==[etree.tostring(x)for x in document.xpath(path,namespaces=NS)],path
        oldrefs=[txt(p)for p in before.find('w:body',NS)if re.match(r'^\[\d+\]',txt(p))]
        assert oldrefs==[txt(p)for p in body if re.match(r'^\[\d+\]',txt(p))]
    assert sha(source)==snap['sha256']
    with ZipFile(output)as z:
        assert len(z.namelist())==len(set(z.namelist()))
        for item in manifest:assert hashlib.sha256(z.read(item['media_part'])).hexdigest()==item['sha256']
    assert txt(abstract)=='摘要：'+''.join(t for t,b in POLISHED_ABSTRACT_PARTS)
    receipt={'status':'DOCX_UPDATED_RENDER_PENDING','source':str(source),'source_sha256':sha(source),'output':str(output),'output_sha256':sha(output),'figures':sorted(manifest,key=lambda x:x['number']),'equations_tables_references_preserved':True,'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (WORK/'word_figure_update.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'status':receipt['status'],'output':str(output)},ensure_ascii=False))

if __name__=='__main__':main()
