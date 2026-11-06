"""Add the existing area-weighted comparison definition as editable Word math."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import json,hashlib,re,datetime,sys

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/wamad_revision_20261106'
sys.path.insert(0,str(ROOT/'05_代码/intro_revision_20261106'))
from revise_user_manuscript import replace_once
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+NS['w']+'}';M='{'+NS['m']+'}'
sha=lambda b:hashlib.sha256(b).hexdigest()
txt=lambda p:''.join(p.xpath('.//w:t/text()',namespaces=NS))

def mr(value,upright=False):
    r=E.Element(M+'r');pr=E.SubElement(r,M+'rPr')
    if upright:E.SubElement(pr,M+'sty').set(M+'val','p')
    wp=E.SubElement(r,W+'rPr');f=E.SubElement(wp,W+'rFonts')
    for k in ['ascii','hAnsi']:f.set(W+k,'Cambria Math')
    E.SubElement(wp,W+'highlight').set(W+'val','yellow')
    E.SubElement(wp,W+'sz').set(W+'val','24')
    t=E.SubElement(r,M+'t');t.text=value;t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    return r

def slot(name,nodes):
    x=E.Element(M+name)
    for n in nodes:x.append(n)
    return x

def sub(base,index,upright=False):
    return slot('sSub',[slot('e',[mr(base,upright)]),slot('sub',[mr(index)])])

def er(s):
    return slot('sSubSup',[slot('e',[mr('ER')]),slot('sub',[mr('i')]),slot('sup',[mr('('+s+')')])])

def sigma():
    return slot('sSub',[slot('e',[mr('∑')]),slot('sub',[mr('i∈'),sub('I','s')])])

def equation7():
    absolute=slot('d',[slot('dPr',[]),slot('e',[er('s'),mr('−'),er('0')])])
    for k in ['begChr','endChr']:E.SubElement(absolute[0],M+k).set(M+'val','|')
    frac=slot('f',[slot('num',[sigma(),sub('a','i'),absolute]),slot('den',[sigma(),sub('a','i')])])
    return slot('oMath',[sub('WMAD','s',True),mr(' = '),frac,mr('，  '),sub('a','i'),mr(' = '),mr('Area',True),mr('('),sub('G','i'),mr('∩Ω)'),mr('     （7）',True)])

def ppr(p):
    x=p.find('w:pPr',NS)
    if x is None:x=E.Element(W+'pPr');p.insert(0,x)
    return x

def plain(p,value):
    r=E.SubElement(p,W+'r');rp=E.SubElement(r,W+'rPr')
    E.SubElement(rp,W+'highlight').set(W+'val','yellow')
    t=E.SubElement(r,W+'t');t.text=value;t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')

def para(template,value,keep=False):
    p=deepcopy(template)
    for x in list(p):
        if x.tag!=W+'pPr':p.remove(x)
    pr=ppr(p)
    for tag in ['keepNext','pageBreakBefore']:
        for x in list(pr.findall('w:'+tag,NS)):pr.remove(x)
    if keep:E.SubElement(pr,W+'keepNext')
    for piece in re.split(r'(\{\{[^}]+\}\})',value):
        if not piece:continue
        if piece.startswith('{{'):
            key=piece[2:-2]
            node={'I_s':lambda:sub('I','s'),'ER_0':lambda:er('0'),'ER_s':lambda:er('s'),'G_i':lambda:sub('G','i'),'a_i':lambda:sub('a','i')}[key]()
            p.append(slot('oMath',[node]))
        else:plain(p,piece)
    return p

def main():
    plan=json.loads((WORK/'edit_plan.json').read_text(encoding='utf-8'))
    source=Path(plan['source']);source_bytes=source.read_bytes();assert sha(source_bytes)==plan['expected_source_sha256']
    output=ROOT/'03_结果文件/论文'/plan['output_name'];assert not output.exists()
    with ZipFile(source)as z:
        original_parts={n:z.read(n)for n in z.namelist()};parts=dict(original_parts)
    doc=E.fromstring(parts['word/document.xml']);before=deepcopy(doc);body=doc.find('w:body',NS);original=list(body);oldbody=list(before.find('w:body',NS))
    method=next(p for p in original if txt(p).startswith('多方案对照用于定位'))
    scale=next(p for p in original if plan['scale_old']in txt(p))
    result=next(p for p in original if plan['result_old']in txt(p))
    old_result=txt(result)
    replace_once(scale,plan['scale_old'],plan['scale_new'])
    replace_once(result,plan['result_old'],plan['result_new'])
    assert re.findall(r'\d+\.\d+',old_result)==re.findall(r'\d+\.\d+',txt(result))
    eq_template=next(p for p in original if p.xpath('.//m:oMathPara',namespaces=NS) and any('（6）'in s for s in p.xpath('.//m:t/text()',namespaces=NS)))
    eqp=deepcopy(eq_template)
    for child in list(eqp):
        if child.tag!=W+'pPr':eqp.remove(child)
    pr=ppr(eqp)
    if pr.find('w:keepNext',NS)is None:E.SubElement(pr,W+'keepNext')
    omp=E.SubElement(eqp,M+'oMathPara');omppr=E.SubElement(omp,M+'oMathParaPr');E.SubElement(omppr,M+'jc').set(M+'val','center');omp.append(equation7())
    additions=[para(method,plan['method_intro'],True),eqp,para(method,plan['method_explanation'])]
    pos=body.index(method)+1
    for p in additions:body.insert(pos,p);pos+=1
    changed={original.index(scale),original.index(result)}
    for i,(old,current)in enumerate(zip(oldbody,original)):
        if i not in changed:assert E.tostring(old)==E.tostring(current),i
    for xp in ['.//w:tbl','.//w:drawing','.//w:sectPr']:
        assert [E.tostring(x)for x in before.xpath(xp,namespaces=NS)]==[E.tostring(x)for x in doc.xpath(xp,namespaces=NS)],xp
    assert [E.tostring(x)for x in before.xpath('.//m:oMath',namespaces=NS)]==[E.tostring(x)for x in doc.xpath('.//m:oMath',namespaces=NS)][:6]
    assert len(doc.xpath('.//m:oMathPara',namespaces=NS))==7
    assert len(doc.xpath('.//m:oMath',namespaces=NS))==12
    parts['word/document.xml']=E.tostring(doc,encoding='UTF-8',xml_declaration=True,standalone=True)
    assert all(parts[n]==v for n,v in original_parts.items()if n!='word/document.xml')
    with ZipFile(output,'x',ZIP_DEFLATED)as out:
        for name,data in parts.items():out.writestr(name,data)
    assert source.read_bytes()==source_bytes
    report={'status':'STRUCTURAL_PASS_RENDER_PENDING','source':str(source.resolve()),'source_sha256':sha(source_bytes),'output':str(output),'output_sha256':sha(output.read_bytes()),'changed_original_body_indices':sorted(changed),'added_method_paragraphs':3,'display_equations':7,'inline_symbol_equations_added':5,'native_math_objects':12,'source_parts_unchanged_except_document_xml':True,'all_figures_tables_existing_equations_comments_references_preserved':True,'result_values_unchanged':True,'weight_area_unit':'m2','weight_definition':'Area(full grid intersection study scope union)','scope':'Separate habitat and pairwise common valid scores; full support group for 500m comparison','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (WORK/'revision_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'output':str(output),'sha256':report['output_sha256']},ensure_ascii=False))

if __name__=='__main__':main()
