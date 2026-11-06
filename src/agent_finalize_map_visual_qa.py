"""Freeze map artifacts AFTER actual native reopening and human-visible review.

This records the assistant's observed review, not an automated aesthetic score.
It is deliberately separate from numerical ecological-model verification.
"""
from pathlib import Path
import datetime,hashlib,json,zipfile,xml.etree.ElementTree as ET
from PIL import Image
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/map_results'
OUT=ROOT/'04_图件'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return str(p.relative_to(ROOT))

science_path=ROOT/'02_过程文件/evaluation/final_scientific_QA.json'
science=json.loads(science_path.read_text(encoding='utf8'))
native_path=WORK/'native_reopen_QA.json'
native=json.loads(native_path.read_text(encoding='utf8'))
exports=json.loads((WORK/'native_export_receipt.json').read_text(encoding='utf8'))
before=json.loads((WORK/'before_scalebar_outside_final/before_sha256.json').read_text(encoding='utf8'))
assert science['status']=='PASS'
assert native['status']=='NATIVE_REOPEN_PASS_VISUAL_QA_PENDING'
assert len(native['layers'])==14 and len(native['layouts'])==3
assert all(x['valid'] for x in native['layers'])
assert native['default_canvas_has_study_extent']
assert all(x['shared_scalebar_outside_maps'] for x in native['layouts'])
assert all(sha(ROOT/p)==value for p,value in science['checked_file_sha256'].items()),'Scientific inputs/results changed after independent QA'
assert all(sha(ROOT/p)==value for p,value in native['tracked_sha256'].items()),'GUI review must not modify the project or data sources'
coverage=exports['comparison_coverage']
assert [coverage[h]['complete'] for h in ['forest_shrub','grassland','water_wetland']]==[137,18,89]
assert [coverage[h]['complete_baseline_low'] for h in ['forest_shrub','grassland','water_wetland']]==[14,0,14]
assert sum(x['stable_low'] for x in coverage.values())==0

artifacts=[];png_changed={}
notes={
3:'Three within-habitat five-class maps, four class boundaries each, missing cells distinct; no cross-habitat or universal-threshold claim. All labels, note and shared external scale readable without clipping.',
4:'Three maps distinguish V/S/O relative shortfall and non-evaluable grids. Labels explain the dimensions in plain Chinese. Legend and external scale do not cover map data.',
5:'Three maps separately show non-evaluable, incomplete comparison, complete comparison consistent/changed classes. Complete-domain counts 137/18/89 and baseline-low counts 14/0/14 shown. No persistent-low cells in complete domain; grass low-class persistence explicitly cannot be judged. No full-region extrapolation.'}
stems={3:'图3_生态韧性空间分布',4:'图4_三维相对短板',5:'图5_空间分级稳定性'}
for fig,stem in stems.items():
    for ext in ['png','pdf','svg']:
        p=OUT/(stem+'.'+ext);assert p.is_file() and p.stat().st_size>1000
        info={'file':rel(p),'sha256':sha(p),'bytes':p.stat().st_size,'structural_validation':'PASS'}
        if ext=='png':
            with Image.open(p) as im:
                assert im.size==(2244,3118);info['pixel_dimensions']=list(im.size);im.verify()
            png_changed[stem+'.png']=sha(p)!=before[rel(p)]
        elif ext=='pdf':
            doc=PdfReader(p);assert len(doc.pages)==1
            page=doc.pages[0]
            # Qt's PDF writer stores this page's MediaBox in integer points.
            # Verify the nearest integer point to the 190 x 264 mm layout.
            assert float(page.mediabox.width)==round(190*72/25.4)
            assert float(page.mediabox.height)==round(264*72/25.4)
            content=page.get_contents().get_data();assert len(content)>1000
            info['pages']=1;info['parsed_content_bytes']=len(content)
            info['pdf_mediabox_pt']=[float(page.mediabox.width),float(page.mediabox.height)]
        else:
            xml=ET.parse(p);assert xml.getroot().tag.endswith('svg')
        artifacts.append(info)
    reviewed=ROOT/native['layouts'][fig-3]['native_reopened_image']
    assert sha(reviewed)==native['layouts'][fig-3]['image_sha256']
project=OUT/'生态韧性结果_可编辑地图.qgz'
with zipfile.ZipFile(project) as z:assert z.testzip() is None
artifacts.append({'file':rel(project),'sha256':sha(project),'bytes':project.stat().st_size,'structural_validation':'PASS','native_reopen':'14 valid layers / 3 editable layouts / 14 relative data sources'})

record={
 'status':'PASS','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'Final native GIS artifact and actual visual QA; not an additional ecological validation or model recalculation.',
 'engine':'QGIS 3.28.2-Firenze; editable native layouts',
 'classification_engine':'Fisher-Jenks, jenkspy 0.4.1; scientific classification unchanged by this cartographic revision',
 'artifacts':artifacts,'sha256':{x['file']:x['sha256'] for x in artifacts},
 'final_png_changed_from_previous_export':png_changed,
 'word_sync_required':all(png_changed.values()),
 'reviewed_images':[{'file':x['native_reopened_image'],'sha256':x['image_sha256'],'actual_visual_review':'PASS'} for x in native['layouts']],
 'per_figure_visual_review':{str(k):{'status':'PASS','notes':v} for k,v in notes.items()},
 'native_gui_review':{
   'status':'PASS','project_window_id':395252,'layout5_window_id':15927240,
   'observations':['Reopened final saved project using QGIS desktop Open dialog.','Default map canvas immediately showed forest_shrub result, township boundaries and study outline at approximately 1:468619.','Layout manager listed all three result layouts.','Opened final figure5 layout editor; three map panels, complete-domain captions, legend, external scale and five-line interpretation note visibly rendered. Individual text/map items were exposed in the native item tree.','No GUI save, data edit, project parameter edit or scientific recalculation performed.']},
 'layout_checks':{'all_nine_map_extents_equal':native['all_nine_map_extents_equal'],'source_font_min_pt':10.5,'intended_word_width_mm':146.4,'minimum_pt_at_intended_word_width':10.5*146.4/190,'shared_scalebar_outside_mapped_data':True,'scalebar_not_overlapping_footer':True,'palette_and_missing_categories_preserved':True,'observed_text_clipping_or_overlap':False},
 'comparison_coverage':coverage,
 'data_and_scientific_code_hashes_still_match_independent_QA':True,
 'source_and_project_hashes_unchanged_during_native_GUI_review':True,
 'evidence':{'scientific_qa':{'file':rel(science_path),'sha256':sha(science_path)},'native_reopen_qa':{'file':rel(native_path),'sha256':sha(native_path)},'native_export_receipt':{'file':rel(WORK/'native_export_receipt.json'),'sha256':sha(WORK/'native_export_receipt.json')}},
 'nonblocking_observed_warnings':['Older bundled GDAL reports GeoPackage1.4 partial support; all14 layers read valid with exact feature/category checks.','PNG metadata update/Chinese-path auxiliary-open warnings remain in exporter logs; actual PNGs decode, correct dimensions and native re-render visually verified.','Desktop startup shows Open Sans install warning; maps use Microsoft YaHei, and Chinese labels render correctly.'],
 'boundary':'This receipt verifies standalone figures and native project. Word page integration and final paper review are performed separately by the parent agent.'
}
(WORK/'visual_QA.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
(WORK/'final_artifact_sha256.json').write_text(json.dumps(record['sha256'],ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':'PASS','artifacts':len(artifacts),'png_changed':png_changed,'receipt':str(WORK/'visual_QA.json')},ensure_ascii=False))
