"""Restyle final empirical maps without changing any scientific attributes.

Native QGIS3.28.2 entrypoint. Default builds new figures5-7; --verify reopens
the saved new project and checks all layer values, geometry and map elements.
"""
import os,sys,json,hashlib,gc,shutil,zipfile,datetime
from pathlib import Path
import xml.etree.ElementTree as ET
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QColor,QFont,QFontDatabase,QFontInfo,QPolygonF
from qgis.PyQt.QtCore import QPointF,Qt

ROOT=Path(__file__).resolve().parents[2]
CODE=ROOT/'05_代码/figure_revision_20261106'
WORK=ROOT/'02_过程文件/figure_revision_20261106/result_maps'
ASCII_WORK=Path('D:/ER219_work/figure_revision_20261106/result_maps') if Path('D:/ER219_work').exists() else WORK
OUT=ROOT/'04_图件/统一图式与过程图_20261106'
OLD=ROOT/'04_图件/生态韧性结果_可编辑地图.qgz'
NEW=OUT/'图5至图7_统一图式_可编辑地图.qgz'
STYLE=json.loads((CODE/'figure_style.json').read_text(encoding='utf8'))
HAB={'forest_shrub':'林地—灌丛','grassland':'草地','water_wetland':'水体—湿地'}
STEMS={5:'图5_生态韧性空间分布',6:'图6_三维相对短板',7:'图7_空间分级稳定性'}
TITLES={5:'生态韧性潜力的空间分布',6:'综合评价对应的相对短板',7:'空间分级对预设方案的稳定性'}
FIELDS={5:'map_class',6:'shortfall_map',7:'stability_map'}
WORK.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
app=QgsApplication([],False);app.initQgis()
font_id=QFontDatabase.addApplicationFont('C:/Windows/Fonts/simhei.ttf');assert font_id>=0
assert 'SimHei' in QFontDatabase.applicationFontFamilies(font_id)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(ROOT))
def font(size,bold=False):
    q=QFont('SimHei');q.setPointSizeF(float(size));q.setBold(bold);return q
def fill(color,edge='transparent',width='0'):
    return QgsFillSymbol.createSimple({'color':color,'outline_color':edge,'outline_width':str(width)})
def layer_digest(layer):
    dig=hashlib.sha256();counts={}
    features=sorted(layer.getFeatures(),key=lambda f:f.id())
    for f in features:
        dig.update(json.dumps([f.id(),f.attributes()],ensure_ascii=False,default=str,separators=(',',':')).encode('utf8'))
        dig.update(bytes(f.geometry().asWkb()))
        for field in ['map_class','shortfall_map','stability_map']:
            if layer.fields().indexFromName(field)>=0:
                v=str(f[field]);counts.setdefault(field,{})[v]=counts.setdefault(field,{}).get(v,0)+1
    return {'name':layer.name(),'source':layer.source(),'features':len(features),'field_names':[f.name() for f in layer.fields()],'attribute_geometry_sha256':dig.hexdigest(),'category_counts':counts}
def tracked():
    paths=[OLD,ROOT/'05_代码/src/qgis_result_maps.py',ROOT/'03_结果文件/evaluation/evaluation_maps.gpkg',ROOT/'02_过程文件/spatial/scope.gpkg',ROOT/'03_结果文件/evaluation/classification.json',ROOT/'03_结果文件/evaluation/scores_all_scenarios.csv',ROOT/'03_结果文件/evaluation/scores_classified.csv']
    for stem in ['图3_生态韧性空间分布','图4_三维相对短板','图5_空间分级稳定性']:
        paths.extend(ROOT/'04_图件'/(stem+'.'+ext) for ext in ['png','pdf','svg'])
    return {rel(p):sha(p) for p in paths}

def build():
    before=tracked()
    p=QgsProject.instance();assert p.read(str(OLD))
    original_layers={lid:layer_digest(lyr) for lid,lyr in p.mapLayers().items()}
    (WORK/'original_snapshot.json').write_text(json.dumps({'files':before,'layers':original_layers},ensure_ascii=False,indent=2),encoding='utf8')
    p.setFilePathStorage(Qgis.FilePathType.Relative)
    for old in list(p.layoutManager().layouts()):p.layoutManager().removeLayout(old)
    scope=p.mapLayersByName('研究范围')[0];towns=p.mapLayersByName('乡镇覆盖部分')[0]
    breaks=json.loads((ROOT/'03_结果文件/evaluation/classification.json').read_text(encoding='utf8'))['habitats']
    pal=STYLE['palette'];dims=STYLE['dimension_colors'];sizes=STYLE['sizes_pt']
    er=[(0,'不可评价（NA）',pal['missing'])]+[(i+1,n,c) for i,(n,c) in enumerate(zip(['低','较低','中','较高','高'],pal['sequential']))]
    short=[(0,'不可评价（NA）',pal['missing']),(1,'生态基础与活动压力（V）',dims['V']),(2,'斑块联系（S）',dims['S']),(3,'灰绿配置（O）',dims['O']),(4,'两个及以上维度并列','#A7A5B4')]
    stable=[(0,'基准不可评价（NA）',pal['missing']),(1,'稳定低值（本次未检出）',pal['negative_difference']),(2,'完整对照：分级一致',dims['V']),(3,'完整对照：分级变化','#D8CBA3'),(4,'主对照不完整','#BBC6C4')]
    cats_by_fig={5:er,6:short,7:stable};coverage={};audit=[];live=[]
    for h,name in HAB.items():
        lyr=p.mapLayersByName(name)[0]
        fs=list(lyr.getFeatures())
        coverage[h]={'baseline':sum(int(f['map_class'])>0 for f in fs),'complete':sum(int(f['map_class'])>0 and int(f['complete_comparison_set'])==1 for f in fs),'baseline_low_in_complete':sum(int(f['map_class'])==1 and int(f['complete_comparison_set'])==1 for f in fs),'stable_low':sum(int(f['map_class'])>0 and int(f['consistent_low_complete_set'])==1 for f in fs)}
    assert [coverage[h]['baseline_low_in_complete'] for h in HAB]==[14,0,14]
    for fig in [5,6,7]:
        title=TITLES[fig];cats=cats_by_fig[fig];field=FIELDS[fig]
        layout=QgsPrintLayout(p);layout.initializeDefaults();layout.setName(f'图{fig} {title}')
        layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(190,264));layout.renderContext().setDpi(600)
        def label(text,x,y,w,h,size,bold=False,role='label'):
            o=QgsLayoutItemLabel(layout);o.setText(text);o.setFont(font(size,bold));o.setFontColor(QColor(STYLE['text_color']));o.setId(f'{role}_{len(live)}')
            layout.addLayoutItem(o);o.attemptMove(QgsLayoutPoint(x,y));o.attemptResize(QgsLayoutSize(w,h));o.setZValue(100);live.append(o);return o
        outer=QgsLayoutItemShape(layout);outer.setShapeType(QgsLayoutItemShape.Rectangle);outer.setSymbol(fill('transparent',STYLE['frame']['color'],STYLE['frame']['width_mm']));layout.addLayoutItem(outer);outer.attemptMove(QgsLayoutPoint(2,2));outer.attemptResize(QgsLayoutSize(186,260));outer.setZValue(5);outer.setId('overall_neatline');live.append(outer)
        label(title,7,6,176,9,sizes['figure_title'],False,'figure_title')
        label('2020年  |  1 km方格  |  三类生境分别评价',7,18,176,7,sizes['note'],False,'subtitle')
        for i,(hab,name) in enumerate(HAB.items()):
            lyr=p.mapLayersByName(name+' — '+title)[0]
            lyr.setRenderer(QgsCategorizedSymbolRenderer(field,[QgsRendererCategory(c,fill(co),n) for c,n,co in cats]))
            x=7+(i%2)*93;y=27+(i//2)*101
            label('('+'abc'[i]+')  '+name,x,y,83,8,sizes['panel_title'],False,'panel_title')
            mp=QgsLayoutItemMap(layout);layout.addLayoutItem(mp);mp.setId(f'{hab}_map');mp.attemptMove(QgsLayoutPoint(x,y+10));mp.attemptResize(QgsLayoutSize(83,70));mp.setCrs(scope.crs());mp.setLayers([scope,towns,lyr]);mp.setKeepLayerSet(True);mp.setKeepLayerStyles(True);mp.setMapRotation(0)
            ex=QgsRectangle(scope.extent());ex.scale(1.06);cx=ex.center().x();dx=ex.height()*83/70/2;ex.setXMinimum(cx-dx);ex.setXMaximum(cx+dx);mp.setExtent(ex)
            mp.setFrameEnabled(True);mp.setFrameStrokeColor(QColor(STYLE['frame']['color']));mp.setFrameStrokeWidth(QgsLayoutMeasurement(STYLE['frame']['width_mm']));live.append(mp)
            # An upward arrow represents GRID north because every map rotation is 0.
            north=label('N',x+74,y+10,8,5,sizes['map_label'],False,'north_label');north.setHAlign(Qt.AlignHCenter)
            arrow=QgsLayoutItemPolygon(QPolygonF([QPointF(2,0),QPointF(4,7),QPointF(2,5.5),QPointF(0,7)]),layout);arrow.setSymbol(fill(STYLE['text_color']));layout.addLayoutItem(arrow);arrow.attemptMove(QgsLayoutPoint(x+76,y+16));arrow.setId('grid_north_arrow');live.append(arrow)
            if i==0:
                scale=QgsLayoutItemScaleBar(layout);scale.setId('linked_shared_scale');scale.setStyle('Single Box');scale.setLinkedMap(mp);scale.setUnits(QgsUnitTypes.DistanceKilometers);scale.setUnitsPerSegment(10);scale.setNumberOfSegments(2);scale.setNumberOfSegmentsLeft(0);scale.setUnitLabel('km');scale.setFont(font(sizes['map_label']));scale.setHeight(1);layout.addLayoutItem(scale);scale.attemptMove(QgsLayoutPoint(102,210));live.append(scale)
            if fig==5:
                vals=[f'{c["upper"]:.3f}' for c in breaks[hab]['classes'][:-1]]
                label('分级界点：'+' / '.join(vals),x,y+81,84,12,sizes['note'],False,'class_breaks')
            if fig==7:
                c=coverage[hab]
                label(f'完整对照 {c["complete"]} / 基准 {c["baseline"]} 格\n其中基线最低 {c["baseline_low_in_complete"]} 格',x,y+81,84,12,sizes['note'],False,'coverage')
        label('图例',102,130,78,8,sizes['legend_title'],False,'legend_title')
        ypos=142
        for code,name,color in cats:
            sw=QgsLayoutItemShape(layout);sw.setShapeType(QgsLayoutItemShape.Rectangle);sw.setSymbol(fill(color,STYLE['frame']['color'],'0.08'));layout.addLayoutItem(sw);sw.attemptMove(QgsLayoutPoint(102,ypos+1));sw.attemptResize(QgsLayoutSize(5,4));live.append(sw)
            label(name,109,ypos,74,9,sizes['legend_label'],False,'legend_label');ypos+=11
        if fig==5:
            note='六项指标共同有效的方格进入评价；三类生境分别标准化、赋权和分级。\n颜色表示同类生境内部的相对等级，不用于跨生境比较。\n采用既定Fisher–Jenks五级断点；NA不表示低韧性。'
        elif fig==6:
            note='三维得分已转为高值有利；最低得分维度标记相对短板。\n短板应结合原始指标与现状核查解释，再研判生境维护、\n斑块联系改善和灰绿配置措施；NA表示未进入综合评价。'
        else:
            note='七方案仅在全部有效的格网内比较；对照不完整不等于不稳定。\n完整域基线最低格网：林灌14格、草地0格、水湿14格。\n林灌和水湿的上述低值均未持续为最低级；\n草地最低格网无完整对照，不能判断其低值持续性。\n完整域结论不能外推至对照不完整区域。'
        label(note,7,225,176,24,sizes['note'],False,'interpretation_note')
        label('WGS 84 Albers等积投影；指北针表示格网北。\n指标取完整方格，制图裁至研究区；三幅地图使用同一比例尺。',7,250,176,10,sizes['note'],False,'map_metadata')
        p.layoutManager().addLayout(layout);layout.refresh();app.processEvents()
        exporter=QgsLayoutExporter(layout);temp=ASCII_WORK/'exports';temp.mkdir(exist_ok=True)
        for ext,settings,fun in [('png',QgsLayoutExporter.ImageExportSettings(),exporter.exportToImage),('pdf',QgsLayoutExporter.PdfExportSettings(),exporter.exportToPdf),('svg',QgsLayoutExporter.SvgExportSettings(),exporter.exportToSvg)]:
            settings.dpi=STYLE['export_dpi']
            if ext=='svg':settings.exportAsLayers=True
            target=temp/f'fig{fig}.{ext}';assert fun(str(target),settings)==QgsLayoutExporter.Success
            shutil.copy2(target,OUT/(STEMS[fig]+'.'+ext))
    default=p.mapLayersByName(HAB['forest_shrub']+' — '+TITLES[5])[0]
    tree=p.layerTreeRoot();visible={scope.id(),towns.id(),default.id()}
    for node in tree.findLayers():node.setItemVisibilityChecked(node.layerId() in visible);node.setExpanded(False)
    tree.setHasCustomLayerOrder(True);tree.setCustomLayerOrder([scope,towns,default]+[v for v in p.mapLayers().values() if v.id() not in visible])
    ex=QgsRectangle(scope.extent());ex.scale(1.08);p.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(ex,scope.crs()))
    assert p.write(str(NEW));assert tracked()==before
    assert {lid:layer_digest(lyr) for lid,lyr in p.mapLayers().items()}==original_layers
    (WORK/'build_receipt.json').write_text(json.dumps({'status':'NATIVE_EXPORT_COMPLETE_REOPEN_AND_VISUAL_PENDING','engine':Qgis.QGIS_VERSION,'font_family':'SimHei','style_sha256':sha(CODE/'figure_style.json'),'coverage':coverage,'original_file_sha256':before,'original_layers':original_layers,'originals_and_scientific_values_unchanged':True,'outputs':[str(OUT/(s+'.'+e)) for s in STEMS.values() for e in ['png','pdf','svg']]+[str(NEW)]},ensure_ascii=False,indent=2),encoding='utf8')
    p.clear();gc.collect()

def verify():
    snapshot=json.loads((WORK/'original_snapshot.json').read_text(encoding='utf8'))
    p=QgsProject();assert p.read(str(NEW));assert len(p.mapLayers())==14
    actual={lid:layer_digest(lyr) for lid,lyr in p.mapLayers().items()}
    assert actual==snapshot['layers'],'Scientific layer attributes or geometries changed'
    assert tracked()==snapshot['files'],'An original artifact or input changed'
    assert not p.viewSettings().defaultViewExtent().isEmpty()
    visible=[x.layer().name() for x in p.layerTreeRoot().findLayers() if x.itemVisibilityChecked()];assert len(visible)==3
    with zipfile.ZipFile(NEW) as z:
        xml=ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.qgs'))))
    sources=[e.text for e in xml.findall('.//projectlayers/maplayer/datasource')];assert len(sources)==14 and all(s.startswith('../') for s in sources)
    reports=[];extents=[]
    for fig,layout in zip([5,6,7],sorted(p.layoutManager().layouts(),key=lambda l:l.name())):
        assert layout.name().startswith(f'图{fig}')
        maps=[i for i in layout.items() if isinstance(i,QgsLayoutItemMap)];assert len(maps)==3
        labels=[i for i in layout.items() if isinstance(i,QgsLayoutItemLabel)]
        for label in labels:
            assert label.font().family()=='SimHei'
            assert QFontInfo(label.font()).family()=='SimHei','Requested SimHei must resolve to actual SimHei'
        for label in labels:
            if label.id().startswith('figure_title_'):assert label.font().pointSizeF()==16
            if label.id().startswith('panel_title_'):assert label.font().pointSizeF()==13
            if label.id().startswith('legend_label_'):assert label.font().pointSizeF()==11
        for m in maps:
            assert m.frameEnabled() and abs(m.frameStrokeWidth().length()-0.22)<1e-9
            assert m.keepLayerSet() and m.keepLayerStyles() and m.mapRotation()==0
            extents.append([m.extent().xMinimum(),m.extent().yMinimum(),m.extent().xMaximum(),m.extent().yMaximum()])
        scales=[i for i in layout.items() if isinstance(i,QgsLayoutItemScaleBar)];assert len(scales)==1
        scale=scales[0];assert scale.linkedMap() in maps and scale.font().family()=='SimHei'
        assert QFontInfo(scale.font()).family()=='SimHei'
        assert all(not scale.sceneBoundingRect().intersects(m.sceneBoundingRect()) for m in maps)
        assert scale.sceneBoundingRect().bottom()<225
        assert layout.itemById('overall_neatline') is not None and layout.itemById('overall_neatline').zValue()>0
        # Independent new-process rendering for visual review after native reopen.
        preview=ASCII_WORK/f'fig{fig}_native_reopened.png';settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=150
        assert QgsLayoutExporter(layout).exportToImage(str(preview),settings)==QgsLayoutExporter.Success
        reports.append({'figure':fig,'layout':layout.name(),'source_font_sizes':sorted(set(x.font().pointSizeF() for x in labels)),'all_fonts_simhei':True,'qfontinfo_actual_family':'SimHei','map_frames_mm':0.22,'shared_scale_linked_and_outside_data':True,'preview':str(preview),'preview_sha256':sha(preview)})
    assert all(all(abs(a-b)<1e-6 for a,b in zip(extents[0],e)) for e in extents)
    assert tracked()==snapshot['files']
    files=[OUT/(s+'.'+e) for s in STEMS.values() for e in ['png','pdf','svg']]+[NEW]
    record={'status':'NATIVE_REOPEN_PASS_VISUAL_PENDING','engine':Qgis.QGIS_VERSION,'original_files_unchanged':True,'all_14_layer_attribute_geometry_digests_match':True,'all_map_extents_equal':True,'relative_sources':sources,'default_visible_layers':visible,'layouts':reports,'artifacts':{str(f):sha(f) for f in files},'layer_checks':actual}
    (WORK/'native_reopen_QA.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    p.clear();del p;gc.collect();print('NATIVE_REOPEN_PASS_VISUAL_PENDING')

if '--verify' in sys.argv:verify()
else:build();print('EXPORTED_NEW_FIGURES_5_6_7')
QgsProject.instance().clear();gc.collect();app.exitQgis()
