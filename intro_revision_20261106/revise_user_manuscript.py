"""Apply scoped changes to a read-only WPS Flat OPC snapshot; preserve user edits."""
from pathlib import Path,PurePosixPath
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
from PIL import Image
import json,hashlib,base64,io,posixpath,datetime

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/intro_revision_20261106'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','a':'http://schemas.openxmlformats.org/drawingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
W='{'+NS['w']+'}'
PK='http://schemas.microsoft.com/office/2006/xmlPackage'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
sha=lambda b:hashlib.sha256(b).hexdigest()
text=lambda p:''.join(p.xpath('.//w:t/text()',namespaces=NS))

def flat_parts(path):
    d=E.parse(str(path),E.XMLParser(resolve_entities=False,no_network=True,huge_tree=True,remove_blank_text=False))
    assert not d.docinfo.doctype and d.getroot().tag=='{'+PK+'}package'
    parts={};types=E.Element('{'+CT+'}Types',nsmap={None:CT})
    for p in d.getroot():
        assert p.tag=='{'+PK+'}part'
        name=p.get('{'+PK+'}name');mime=p.get('{'+PK+'}contentType');entry=name[1:]
        assert name.startswith('/') and mime and '\\' not in entry and '..' not in PurePosixPath(entry).parts
        assert entry not in parts and len(p)==1
        node=p[0]
        if node.tag=='{'+PK+'}xmlData':
            assert len(node)==1
            b=E.tostring(node[0],encoding='UTF-8',xml_declaration=True,with_tail=False)
        else:
            assert node.tag=='{'+PK+'}binaryData'
            b=base64.b64decode(''.join((node.text or '').split()),validate=True)
        parts[entry]=b;E.SubElement(types,'{'+CT+'}Override',PartName=name,ContentType=mime)
    parts['[Content_Types].xml']=E.tostring(types,encoding='UTF-8',xml_declaration=True)
    return parts

def save_new(parts,path):
    b=io.BytesIO()
    with ZipFile(b,'w',ZIP_DEFLATED)as z:
        for name,data in parts.items():z.writestr(name,data)
    with ZipFile(io.BytesIO(b.getvalue()))as z:assert z.testzip()is None
    with path.open('xb')as f:f.write(b.getvalue())

def highlight(t):
    r=t.getparent()
    assert r.tag==W+'r'
    pr=r.find('w:rPr',NS)
    if pr is None:pr=E.Element(W+'rPr');r.insert(0,pr)
    el=pr.find('w:highlight',NS)
    if el is None:el=E.SubElement(pr,W+'highlight')
    el.set(W+'val','yellow')

def replace_once(p,old,new):
    full=text(p);assert full.count(old)==1,(old,full)
    start=full.index(old);end=start+len(old);cursor=0;inserted=False
    for t in p.xpath('.//w:t',namespaces=NS):
        v=t.text or '';a=cursor;b=a+len(v);cursor=b
        if b<=start or a>=end:continue
        prefix=v[:max(0,start-a)];suffix=v[max(0,end-a):]if end<b else ''
        t.text=prefix+(new if not inserted else '')+suffix
        inserted=True;t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');highlight(t)
    assert text(p)==full[:start]+new+full[end:]

def main():
    plan=json.loads((WORK/'edit_plan.json').read_text(encoding='utf-8'))
    source=Path(plan['original_file']);source_bytes=source.read_bytes()
    flat=WORK/plan['snapshot'];parts=flat_parts(flat);before_parts=dict(parts)
    snapshot=WORK/plan.get('snapshot_docx_name','source_live_snapshot.docx')
    if snapshot.exists():
        with ZipFile(snapshot)as z:assert {n:z.read(n)for n in z.namelist()}==parts,'Frozen snapshot differs'
    else:save_new(parts,snapshot)
    doc=E.fromstring(parts['word/document.xml']);before=deepcopy(doc);body=doc.find('w:body',NS);old_body=list(before.find('w:body',NS));children=list(body)
    changed=set();changes=[]
    for i,p in enumerate(children):
        value=text(p)
        if value.startswith('绿化隔离地区减量提质，需要识别生态短板'):
            replace_once(p,value,plan['first_paragraph']);changed.add(i);changes.append('first_introduction_paragraph_user_verbatim')
        elif plan['second_old']in value:
            replace_once(p,plan['second_old'],plan['second_new']);changed.add(i);changes.append('second_paragraph_transition_only')
        elif plan['comment_old']in value:
            replace_once(p,plan['comment_old'],plan['comment_new']);replace_once(p,'提供依据，','提供依据。');changed.add(i);changes.append('comment_0_positive_sentence')
        for old,new in plan['terminology_replacements']:
            while old in text(p):
                # This review has one occurrence per paragraph; fail if unexpected.
                replace_once(p,old,new);changed.add(i);changes.append('terminology_or_duplicate_word')
    assert len(changes)==4,changes
    pictures=[p for p in children if p.xpath('.//w:drawing',namespaces=NS)];assert len(pictures)==8
    pic=pictures[1];changed.add(children.index(pic))
    rid=pic.xpath('.//a:blip/@r:embed',namespaces=NS)[0]
    rels=E.fromstring(parts['word/_rels/document.xml.rels'])
    target=next(x.get('Target')for x in rels if x.get('Id')==rid)
    media=target.lstrip('/')if target.startswith('/')else posixpath.normpath('word/'+target)
    image=Path(plan['figure']);parts[media]=image.read_bytes()
    with Image.open(image)as im:iw,ih=im.size
    cx=int(pic.xpath('.//wp:extent',namespaces=NS)[0].get('cx'));cy=round(cx*ih/iw)
    for el in pic.xpath('.//wp:extent|.//a:xfrm/a:ext',namespaces=NS):el.set('cx',str(cx));el.set('cy',str(cy))
    parts['word/document.xml']=E.tostring(doc,encoding='UTF-8',xml_declaration=True,standalone=True)
    for i,(old,new)in enumerate(zip(old_body,list(body))):
        if i not in changed:assert E.tostring(old)==E.tostring(new),i
    for xp in ['.//m:oMath','.//w:tbl','.//w:sectPr']:
        assert [E.tostring(x)for x in before.xpath(xp,namespaces=NS)]==[E.tostring(x)for x in doc.xpath(xp,namespaces=NS)],xp
    assert [text(x)for x in old_body if text(x).startswith('[')]==[text(x)for x in body if text(x).startswith('[')]
    assert all(parts[n]==v for n,v in before_parts.items()if n not in ['word/document.xml',media])
    assert all(text(children[i])==text(old_body[i])for i in [13,14,15,25])
    assert plan['first_paragraph']in [text(x)for x in body]
    assert source.read_bytes()==source_bytes,'User source changed during build; recapture before delivery'
    output=ROOT/'03_结果文件/论文'/plan['output_name'];save_new(parts,output)
    report={'status':'STRUCTURAL_PASS_RENDER_PENDING','source':str(source.resolve()),'disk_source_sha256':sha(source_bytes),'flat_snapshot_sha256':sha(flat.read_bytes()),'snapshot_docx':str(snapshot),'output':str(output),'output_sha256':sha(output.read_bytes()),'changed_body_indices':sorted(changed),'changes':changes,'preserved_user_scope_paragraphs':[13,14,15],'blank_comment_1':'No change, explicitly requested by user','comments_preserved':True,'media_updated':media,'new_image_sha256':sha(image.read_bytes()),'other_parts_preserved':True,'equations':len(doc.xpath('.//m:oMath',namespaces=NS)),'tables':len(doc.xpath('.//w:tbl',namespaces=NS)),'main_figures':8,'image_display_width_mm':cx/36000,'image_display_height_mm':cy/36000,'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (WORK/'revision_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'output':str(output),'changed_body_indices':sorted(changed)},ensure_ascii=False))

if __name__=='__main__':main()
