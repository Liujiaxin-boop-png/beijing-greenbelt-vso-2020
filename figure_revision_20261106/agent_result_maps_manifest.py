"""Freeze final files after actual six-figure native/PNG visual inspections."""
from pathlib import Path
import json,hashlib,datetime,zipfile,xml.etree.ElementTree as ET
from PIL import Image
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/figure_revision_20261106/result_maps'
OUT=ROOT/'04_图件/统一图式与过程图_20261106'
CODE=ROOT/'05_代码/figure_revision_20261106'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
native=json.loads((WORK/'native_reopen_QA.json').read_text(encoding='utf8'))
snapshot=json.loads((WORK/'original_snapshot.json').read_text(encoding='utf8'))
assert native['status']=='NATIVE_REOPEN_PASS_VISUAL_PENDING'
assert native['all_14_layer_attribute_geometry_digests_match']
assert all(sha(ROOT/p)==s for p,s in snapshot['files'].items())
assert all(sha(p)==s for p,s in native['artifacts'].items())
artifacts=[]
for name,digest in native['artifacts'].items():
    p=Path(name);entry={'file':str(p),'sha256':digest,'bytes':p.stat().st_size,'structural_check':'PASS'}
    if p.suffix=='.png':
        with Image.open(p) as im:
            assert im.size==(4488,6236);entry['pixels']=list(im.size);entry['dpi']=list(im.info.get('dpi',[]));im.verify()
        entry['actual_visual_review']='PASS; final 600dpi PNG inspected with view_image'
    elif p.suffix=='.pdf':
        r=PdfReader(p);assert len(r.pages)==1
        page=r.pages[0];assert list(map(float,[page.mediabox.width,page.mediabox.height]))==[539.,748.]
        resources=page['/Resources'].get_object();font_resources=resources.get('/Font',{}).get_object()
        font_names=sorted({str(x.get_object().get('/BaseFont','')) for x in font_resources.values()})
        if font_names:
            assert all('SimHei' in n for n in font_names),font_names
            font_mode='embedded SimHei'
        else:
            # Native QGIS defaults to vector glyph outlines for PDF export.
            # Do not claim an embedded font when there are no PDF text objects.
            assert not resources.get('/XObject')
            assert not any(op==b'BT' for args,op in page.get_contents().operations)
            font_mode='vector outlines from QFontInfo-verified SimHei native layout'
        assert len(page.get_contents().get_data())>1000
        entry.update({'page_count':1,'pdf_font_names':font_names,'pdf_text_delivery':font_mode})
    elif p.suffix=='.svg':
        assert ET.parse(p).getroot().tag.endswith('svg')
    elif p.suffix=='.qgz':
        with zipfile.ZipFile(p) as z:assert z.testzip() is None
        entry['native_reopen']='PASS: 14 valid relative-path layers; 3 layouts; nonempty default view'
    artifacts.append(entry)
notes={
5:'标题、面板名、图例和注释层级清晰；三类生境分级界点和NA类别完整；面板细框、整图细框、箭头和外置关联比例尺均可见，未遮挡地图。',
6:'V/S/O短板颜色与共同配置一致；(a)(b)(c)面板、图例及NA注释完整；全部文字为黑体，未见截断或重叠。',
7:'完整对照域137/18/89及其中基线最低14/0/14格完整显示；对照不完整与分级变化分别呈现；五行解释、格网北及投影说明均未被图框或页边界裁切。'}
record={'status':'PASS','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'结果地图5—7统一图式重设计，原生重开、实际PNG目视与来源不变性验收；不重新计算或改变科学结果。','engine':'QGIS 3.28.2-Firenze','font':{'requested':'SimHei','QFontInfo_actual':'SimHei','pdf_text_delivery':'vector glyph outlines exported from native QFontInfo-verified SimHei; edit text in QGZ'},'canvas_mm':[190,264],'source_sizes_pt':{'title':16,'panel':13,'legend_title':11.5,'legend_label_and_north_and_scale':11,'notes':10},'word_display_width_mm':146.4,'font_sizes_after_word_scaling_pt':{str(n):n*146.4/190 for n in [16,13,11.5,11,10]},'map_frames_mm':0.22,'overall_neatline_mm':0.22,'actual_visual_reviews':{str(n):{'status':'PASS','observation':t} for n,t in notes.items()},'cartographic_elements':{'one_linked_scale_per_figure':True,'all_three_map_panels_share_extent_and_scale':True,'zero_map_rotation_and_grid_north_arrows':True,'projection':'WGS84 Albers Conic Equal Area','NA_distinct_from_low_value':True},'scientific_protection':{'original_qgz_and_original_figures_sha_unchanged':True,'scientific_input_and_scores_and_classification_sha_unchanged':True,'all_14_layer_attribute_and_geometry_digests_match_original':True,'data_or_value_recalculation_performed':False,'original_snapshot':str(WORK/'original_snapshot.json')},'artifacts':artifacts,'native_reopen_receipt':{'file':str(WORK/'native_reopen_QA.json'),'sha256':sha(WORK/'native_reopen_QA.json')},'style_file':{'file':str(CODE/'figure_style.json'),'sha256':sha(CODE/'figure_style.json')},'code_file':{'file':str(CODE/'agent_result_maps.py'),'sha256':sha(CODE/'agent_result_maps.py')},'warnings':['QGIS bundled GDAL warns about GeoPackage1.4 support; every layer, feature count, attribute and geometry was read back and checked.','PNG optional metadata update warning remains; final exported PNGs decode, have4488x6236 pixels and were visually inspected.'],'word_modified':False}
(WORK/'manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
(WORK/'visual_QA.json').write_text(json.dumps({'status':'PASS','created_utc':record['created_utc'],'actual_final_png_review':record['actual_visual_reviews'],'artifacts_sha256':native['artifacts'],'manifest':str(WORK/'manifest.json'),'manifest_sha256':sha(WORK/'manifest.json')},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':'PASS','files':len(artifacts),'manifest':str(WORK/'manifest.json')},ensure_ascii=False))
