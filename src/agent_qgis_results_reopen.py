"""Read-only native QGIS reopening and export QA for empirical result maps."""
import os,json,hashlib,gc,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import QgsApplication,QgsProject,Qgis,QgsLayoutItemMap,QgsLayoutExporter,QgsLayoutItemLabel,QgsLayoutItemScaleBar
from qgis.PyQt.QtGui import QFontDatabase
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/map_results';OUT=ROOT/'04_图件'
project_file=OUT/'生态韧性结果_可编辑地图.qgz'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
app=QgsApplication([],False);app.initQgis()
assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')>=0
assert json.loads((ROOT/'02_过程文件/evaluation/final_scientific_QA.json').read_text(encoding='utf8'))['status']=='PASS'
tracked=[project_file,ROOT/'03_结果文件/evaluation/evaluation_maps.gpkg',ROOT/'02_过程文件/spatial/scope.gpkg']
before={str(p.relative_to(ROOT)):sha(p) for p in tracked}
p=QgsProject();assert p.read(str(project_file)), 'Native QGIS cannot reopen saved project'
assert p.crs().isValid()
layers=list(p.mapLayers().values());assert len(layers)==14
assert not p.viewSettings().defaultViewExtent().isEmpty()
visible=[n.layer().name() for n in p.layerTreeRoot().findLayers() if n.itemVisibilityChecked()]
assert len(visible)==3 and '研究范围' in visible and '乡镇覆盖部分' in visible
with zipfile.ZipFile(project_file) as z:
    xml=ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.qgs'))))
sources=[e.text or '' for e in xml.findall('.//projectlayers/maplayer/datasource')]
assert len(sources)==14 and all(s.startswith('../') or s.startswith('./') for s in sources),'Saved data sources must be relative'
layer_reports=[]
for layer in layers:
    assert layer.isValid() and layer.crs().isValid() and not layer.extent().isEmpty()
    r={'name':layer.name(),'provider':layer.providerType(),'source':layer.source(),'valid':True,'feature_count':layer.featureCount(),'crs_wkt':layer.crs().toWkt()}
    if 'evaluation_maps.gpkg' in layer.source():
        assert layer.featureCount()==2478
        assert all(layer.fields().indexFromName(n)>=0 for n in ('grid_id','map_class','shortfall_map','stability_map'))
        r['category_counts']={}
        for fld in ('map_class','shortfall_map','stability_map'):
            counts={}
            for feature in layer.getFeatures():
                v=int(feature[fld]);counts[str(v)]=counts.get(str(v),0)+1
                mc=int(feature['map_class'])
                if mc==0:assert int(feature['shortfall_map'])==0 and int(feature['stability_map'])==0
                else:
                    dim=str(feature['limiting_dimension']);short={'V':1,'S':2,'O':3}.get(dim,4)
                    assert int(feature['shortfall_map'])==short
                    expected=4 if not int(feature['complete_comparison_set']) else (1 if int(feature['consistent_low_complete_set']) else (2 if int(feature['class_span'])==0 else 3))
                    assert int(feature['stability_map'])==expected
            r['category_counts'][fld]=counts
    layer_reports.append(r)
layouts=list(p.layoutManager().layouts());assert len(layouts)==3
exports=WORK/'native_reopened';exports.mkdir(parents=True,exist_ok=True)
layout_reports=[];extents=[]
for i,layout in enumerate(sorted(layouts,key=lambda x:x.name()),3):
    assert layout.pageCollection().pageCount()==1
    page=layout.pageCollection().pages()[0].pageSize()
    assert abs(page.width()-190)<1e-8 and abs(page.height()-264)<1e-8
    maps=[x for x in layout.items() if isinstance(x,QgsLayoutItemMap)]
    assert len(maps)==3
    fonts=[x.font().pointSizeF() for x in layout.items() if isinstance(x,QgsLayoutItemLabel)]
    assert min(fonts)>=10.5
    scalebars=[x for x in layout.items() if isinstance(x,QgsLayoutItemScaleBar)]
    assert len(scalebars)==1 and scalebars[0].linkedMap() in maps
    sb=scalebars[0]
    assert sb.font().pointSizeF()>=10.5
    assert all(not sb.sceneBoundingRect().intersects(m.sceneBoundingRect()) for m in maps),'Scale bar must not overlap mapped data'
    assert sb.sceneBoundingRect().bottom()<224,('Scale bar must end before footer',sb.sceneBoundingRect().getRect())
    for m in maps:
        assert m.keepLayerSet() and m.keepLayerStyles()
        assert len(m.layers())==3 and all(x.isValid() for x in m.layers())
        extents.append([m.extent().xMinimum(),m.extent().yMinimum(),m.extent().xMaximum(),m.extent().yMaximum()])
    layout.refresh();app.processEvents()
    setting=QgsLayoutExporter.ImageExportSettings();setting.dpi=150
    target=exports/('figure'+str(i)+'_native_reopened.png')
    assert QgsLayoutExporter(layout).exportToImage(str(target),setting)==QgsLayoutExporter.Success
    layout_reports.append({'name':layout.name(),'page_mm':[page.width(),page.height()],'map_panels':len(maps),'minimum_label_source_pt':min(fonts),'minimum_label_pt_at_Word_146_4mm':min(fonts)*146.4/190,'shared_scalebar_outside_maps':True,'scalebar_rectangle_mm':[sb.sceneBoundingRect().x(),sb.sceneBoundingRect().y(),sb.sceneBoundingRect().width(),sb.sceneBoundingRect().height()],'native_reopened_image':str(target.relative_to(ROOT)),'image_sha256':sha(target)})
assert all(all(abs(x-y)<1e-6 for x,y in zip(extents[0],e)) for e in extents)
after={str(x.relative_to(ROOT)):sha(x) for x in tracked};assert before==after
record={'status':'NATIVE_REOPEN_PASS_VISUAL_QA_PENDING','engine':'QGIS '+Qgis.QGIS_VERSION,
 'scientific_QA_required':'PASS','project_sha256':sha(project_file),'layers':layer_reports,'layouts':layout_reports,
 'all_nine_map_extents_equal':True,'map_virtual_fields_match_saved_data':True,'source_and_project_hashes_unchanged':before==after,
 'default_canvas_has_study_extent':True,'default_visible_layers':visible,
 'relative_saved_data_sources':sources,
 'tracked_sha256':after,'visual_review':'Not yet performed; native export alone is not visual approval.'}
(WORK/'native_reopen_QA.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':record['status'],'layers':len(layers),'layouts':len(layouts)},ensure_ascii=False))
p.clear();del maps;del layouts;del layers;del p;gc.collect();app.exitQgis()
