"""Lay out a reviewed, evidence-complete Chinese manuscript in editable Word.

This writer does not author missing results. It fails closed until the content
and scientific QA explicitly declare readiness. Invoke the Documents artifact
operation marker before the first actual document creation in a delivery turn.
"""
from pathlib import Path
import json,re,hashlib
from docx import Document
from docx.shared import Mm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/manuscript'

def font(run,name='宋体',size=10.5,bold=False):
    run.font.name='Times New Roman';run.font.size=Pt(size);run.bold=bold;run.font.color.rgb=RGBColor(0,0,0)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),name)

def ptext(doc,text,style=None,fontname='宋体',size=10.5,indent=True):
    p=doc.add_paragraph(style=style)
    p.paragraph_format.line_spacing=1.5
    p.paragraph_format.space_after=Pt(0)
    if indent:p.paragraph_format.first_line_indent=Pt(21)
    font(p.add_run(text),fontname,size)
    return p

def caption(doc,text):
    p=ptext(doc,text,size=9,indent=False)
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next=True
    return p

def repeat_header(row):
    pr=row._tr.get_or_add_trPr();el=OxmlElement('w:tblHeader');pr.append(el)

def table(doc,obj):
    caption(doc,obj['caption'])
    t=doc.add_table(rows=1,cols=len(obj['headers']));t.autofit=False
    borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        edge=OxmlElement('w:'+side);edge.set(qn('w:val'),'single');edge.set(qn('w:sz'),'4');edge.set(qn('w:color'),'D9D9D9');borders.append(edge)
    t._tbl.tblPr.append(borders)
    for cell,text in zip(t.rows[0].cells,obj['headers']):
        font(cell.paragraphs[0].add_run(str(text)),size=9,bold=True)
        shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'F0F1F2');cell._tc.get_or_add_tcPr().append(shade)
    repeat_header(t.rows[0])
    for vals in obj['rows']:
        row=t.add_row()
        for cell,text in zip(row.cells,vals):font(cell.paragraphs[0].add_run(str(text)),size=9)
    if 'widths_mm' in obj:
        for col,w in zip(t.columns,obj['widths_mm']):col.width=Mm(w)
        for row in t.rows:
            for c,w in zip(row.cells,obj['widths_mm']):c.width=Mm(w)
    for row in t.rows:
        cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
        for col,cell in enumerate(row.cells):
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            margins=OxmlElement('w:tcMar')
            for edge,width in [('top','60'),('bottom','60'),('left','80'),('right','80')]:
                item=OxmlElement('w:'+edge);item.set(qn('w:w'),width);item.set(qn('w:type'),'dxa');margins.append(item)
            cell._tc.get_or_add_tcPr().append(margins)
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing=1.15;p.paragraph_format.space_after=Pt(3)
                if col in obj.get('center_columns',[0,2]):p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for note in obj.get('notes',[]):ptext(doc,note,size=9,indent=False)

def layout_document(content):
    doc=Document();s=doc.sections[0]
    s.page_width=Mm(210);s.page_height=Mm(297)
    s.top_margin=s.bottom_margin=Mm(25.4);s.left_margin=s.right_margin=Mm(31.8)
    for sty in ['Normal','Body Text']:
        st=doc.styles[sty];st.font.name='Times New Roman';st.font.size=Pt(10.5);st.font.color.rgb=RGBColor(0,0,0)
        st._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
        st.paragraph_format.line_spacing=1.5;st.paragraph_format.space_after=Pt(0)
    for level,name,size,bold in [(1,'黑体',14,False),(2,'宋体',12,True),(3,'楷体',12,False)]:
        st=doc.styles['Heading '+str(level)];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.bold=bold;st.font.color.rgb=RGBColor(0,0,0)
        st._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),name)
        st.paragraph_format.keep_with_next=True;st.paragraph_format.space_before=Pt(10);st.paragraph_format.space_after=Pt(5)
    title_style=doc.styles['Title'];title_style.font.color.rgb=RGBColor(0,0,0);title_style.paragraph_format.space_after=Pt(0)
    p=doc.add_paragraph(style='Title');p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    font(p.add_run(content['title']),size=16,bold=True)
    if content.get('subtitle'):
        p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;font(p.add_run(content['subtitle']),size=11)
    doc.add_paragraph();doc.add_paragraph()
    if content.get('preview_note'):ptext(doc,content['preview_note'],fontname='楷体',size=9,indent=False)
    if content.get('abstract'):ptext(doc,'摘要：'+content['abstract'],fontname='楷体',size=9)
    ptext(doc,'关键词：'+'；'.join(content['keywords']),fontname='楷体',size=9)
    doc.add_paragraph();doc.add_paragraph()
    for block in content['blocks']:
        kind=block['type']
        if kind=='heading':doc.add_heading(block['text'],level=block.get('level',1))
        elif kind=='paragraph':ptext(doc,block['text'])
        elif kind=='table':table(doc,block)
        elif kind=='figure':
            figure=ROOT/block['path'];assert figure.is_file(),str(figure)
            p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing=1.0;p.paragraph_format.space_after=Pt(3)
            p.paragraph_format.keep_with_next=True
            p.add_run().add_picture(str(figure),width=Mm(min(146.4,block.get('width_mm',146.4))))
            c=caption(doc,block['caption']);c.paragraph_format.keep_with_next=False
            for note in block.get('notes',[]):ptext(doc,note,size=9,indent=False)
        elif kind=='equation':
            p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if block.get('formula_id'):
                from manuscript_math import equation
                p._p.append(equation(block['formula_id'],block.get('number')))
            else:
                om=OxmlElement('m:oMath');mr=OxmlElement('m:r');mt=OxmlElement('m:t');mt.text=block['text'];mr.append(mt);om.append(mr);p._p.append(om)
        else:raise ValueError(kind)
    p=ptext(doc,'参考文献',fontname='楷体',size=9,indent=False);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for i,ref in enumerate(content['references'],1):ptext(doc,f'[{i}] '+ref,fontname='楷体',size=9)
    # Anonymous-review copy: no author, institution or private source paths.
    props=doc.core_properties;props.author='';props.last_modified_by='';props.comments='';props.title=content['title'];props.subject='2020年生态韧性评价'
    # Automatic page number is editable and will update in the native application.
    fp=s.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');fp._p.append(fld)
    # The bundled default Title style contains a blue bottom border. Remove
    # paragraph-border residue from this newly authored document, not tables.
    for parent in [doc.styles.element,doc.element]:
        for border in list(parent.iter(qn('w:pBdr'))):border.getparent().remove(border)
    return doc


def main():
    source=WORK/'manuscript_content.json'
    content=json.loads(source.read_text(encoding='utf8'))
    assert content['status']=='READY_FOR_LAYOUT','Manuscript text/results not ready; no placeholder paper created.'
    qa=ROOT/content['scientific_qa_receipt']
    verified=json.loads(qa.read_text(encoding='utf8'))
    assert verified['status']=='PASS', 'Full actual-data QA is required.'
    assert len(content['title'])<=20
    assert 300<=len(content['abstract'])<=500
    assert 3<=len(content['keywords'])<=7
    assert content['results_are_actual_2020_six_indicator_run'] is True
    doc=layout_document(content)
    out=ROOT/'03_结果文件/论文'/content.get('filename','北京二道绿隔生态韧性评价_论文_20261106.docx')
    out.parent.mkdir(parents=True,exist_ok=True)
    assert not out.exists(),'Use a new reviewed filename; do not overwrite a previously delivered Word file.'
    doc.save(out)
    receipt={'status':'DOCX_CREATED_NATIVE_RENDER_AND_VISUAL_QA_PENDING','file':str(out.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scientific_qa_sha256':hashlib.sha256(qa.read_bytes()).hexdigest(),'docx_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'abstract_characters':len(content['abstract']),'title_characters':len(content['title'])}
    (WORK/'docx_creation_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
