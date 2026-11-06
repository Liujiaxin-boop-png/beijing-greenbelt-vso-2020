"""Native editable QGIS layouts for actual six-indicator results only.

Run after summarize_evaluation.py. No sample or simulated map can pass this
entrypoint. Layouts share the study extent, scale, palette and data footprint.
"""
import os,json,gc,shutil
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QColor,QFont,QFontDatabase
from qgis.PyQt.QtCore import QVariant

ROOT=Path(__file__).resolve().parents[2]
RESULT=ROOT/'03_结果文件/evaluation';OUT=ROOT/'04_图件'
WORK=ROOT/'02_过程文件/map_results'
HAB={'forest_shrub':'林地—灌丛','grassland':'草地','water_wetland':'水体—湿地'}
app=QgsApplication([],False);app.initQgis()
assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')>=0

def fill(color,edge='transparent',width='0'):
    return QgsFillSymbol.createSimple({'color':color,'outline_color':edge,'outline_width':width})

def mapfont(size,bold=False):
    font=QFont('Microsoft YaHei');font.setPointSizeF(float(size));font.setBold(bold);return font

def categories(field,values):
    return QgsCategorizedSymbolRenderer(field,[QgsRendererCategory(code,fill(color),name) for code,name,color in values])

def build():
    receipt=json.loads((ROOT/'02_过程文件/evaluation/reporting_receipt.json').read_text(encoding='utf8'))
    assert receipt['status']=='TABLES_AND_MAP_LAYERS_COMPLETE'
    ntl=json.loads((ROOT/'02_过程文件/aggregation/ntl_aggregation_receipt.json').read_text(encoding='utf8'))
    assert ntl['status']=='PASS','Actual night lights are required for result maps.'
    WORK.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
    palette=json.loads((ROOT/'05_代码/config/palette.json').read_text(encoding='utf8'))
    breaks=json.loads((RESULT/'classification.json').read_text(encoding='utf8'))['habitats']
    project=QgsProject.instance();project.setFilePathStorage(Qgis.FilePathType.Relative)
    scope=QgsVectorLayer(str(ROOT/'02_过程文件/spatial/scope.gpkg')+'|layername=study_scope','研究范围','ogr')
    towns=QgsVectorLayer(str(ROOT/'02_过程文件/spatial/scope.gpkg')+'|layername=towns','乡镇覆盖部分','ogr')
    assert scope.isValid() and towns.isValid()
    scope.renderer().setSymbol(fill('transparent','#505A55','0.18'))
    towns.renderer().setSymbol(fill('transparent','#919A95','0.08'))
    project.addMapLayer(scope);project.addMapLayer(towns);project.setCrs(scope.crs())
    live=[];layers={};audit=[];coverage={};default_layer=None
    for habitat,name in HAB.items():
        layer=QgsVectorLayer(str(RESULT/'evaluation_maps.gpkg')+'|layername='+habitat,name,'ogr')
        assert layer.isValid() and layer.featureCount()==2478
        # Virtual fields preserve the source GeoPackage and remain editable in QGIS.
        layer.addExpressionField("CASE WHEN coalesce(\"map_class\",0)=0 THEN 0 WHEN \"limiting_dimension\"='V' THEN 1 WHEN \"limiting_dimension\"='S' THEN 2 WHEN \"limiting_dimension\"='O' THEN 3 ELSE 4 END",QgsField('shortfall_map',QVariant.Int))
        layer.addExpressionField("CASE WHEN coalesce(\"map_class\",0)=0 THEN 0 WHEN NOT coalesce(\"complete_comparison_set\",false) THEN 4 WHEN coalesce(\"consistent_low_complete_set\",false) THEN 1 WHEN \"class_span\"=0 THEN 2 ELSE 3 END",QgsField('stability_map',QVariant.Int))
        layers[habitat]=layer;project.addMapLayer(layer)
        coverage[habitat]={'baseline':sum(int(f['map_class'])>0 for f in layer.getFeatures()),
                          'complete':sum(int(f['map_class'])>0 and int(f['complete_comparison_set'])==1 for f in layer.getFeatures()),
                          'complete_baseline_low':sum(int(f['map_class'])==1 and int(f['complete_comparison_set'])==1 for f in layer.getFeatures()),
                          'stable_low':sum(int(f['map_class'])>0 and int(f['consistent_low_complete_set'])==1 for f in layer.getFeatures())}
        for fld in ['map_class','shortfall_map','stability_map']:
            counts={}
            for f in layer.getFeatures():counts[str(f[fld])]=counts.get(str(f[fld]),0)+1
            audit.append({'habitat':habitat,'field':fld,'feature_counts':counts})
    er=[(0,'不可评价',palette['missing'])]+[(i+1,n,c) for i,(n,c) in enumerate(zip(['低','较低','中','较高','高'],palette['sequential']))]
    short=[(0,'不可评价',palette['missing']),(1,'生态基础与活动压力（V）','#527F71'),(2,'斑块联系（S）','#649DB4'),(3,'灰绿配置（O）','#B89765'),(4,'两个及以上维度并列','#A7A5B4')]
    stable_label='稳定低值（本次未检出）' if sum(v['stable_low'] for v in coverage.values())==0 else '稳定低值（七方案均低）'
    stability=[(0,'基准不可评价',palette['missing']),(1,stable_label,'#B97846'),(2,'完整对照：分级一致','#527F71'),(3,'完整对照：分级变化','#D8CBA3'),(4,'主对照不完整','#BBC6C4')]
    specs=[
      (3,'生态韧性潜力的空间分布','map_class',er,'图3_生态韧性空间分布','六项均有效的1 km方格；三类生境分别标准化、赋权与分级，颜色不能用于跨生境比较。'),
      (4,'综合评价对应的相对短板','shortfall_map',short,'图4_三维相对短板','三维得分均已转为高值有利；最低维度标记相对短板，需结合单项指标研判具体管护措施。'),
      (5,'空间分级对预设方案的稳定性','stability_map',stability,'图5_空间分级稳定性','基准及六类主对照共七方案；缺少任一主对照的格网单列，不作为已证实的稳定区域。')]
    for fig,title,field,cats,stem,note in specs:
        layout=QgsPrintLayout(project);layout.initializeDefaults();layout.setName('图'+str(fig)+' '+title)
        layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(190,264))
        def label(text,x,y,w,h,size=11,bold=False):
            obj=QgsLayoutItemLabel(layout);obj.setText(text);obj.setFont(mapfont(size,bold));obj.setFontColor(QColor('#303A36'))
            layout.addLayoutItem(obj);obj.attemptMove(QgsLayoutPoint(x,y));obj.attemptResize(QgsLayoutSize(w,h));obj.setZValue(100);live.append(obj);return obj
        label(title,6,3,178,10,14,True)
        label('2020年  |  研究范围内的格网结果  |  三类生境分别评价',6,14,178,8,10.5)
        for ix,(habitat,name) in enumerate(HAB.items()):
            lyr=layers[habitat].clone();lyr.setName(name+' — '+title);lyr.setRenderer(categories(field,cats));project.addMapLayer(lyr)
            if fig==3 and ix==0:default_layer=lyr
            x=6+(ix%2)*92; y=26+(ix//2)*100
            label('abc'[ix]+'  '+name,x,y,86,8,11.5,True)
            mp=QgsLayoutItemMap(layout);layout.addLayoutItem(mp);mp.attemptMove(QgsLayoutPoint(x,y+10));mp.attemptResize(QgsLayoutSize(84,70));mp.setCrs(scope.crs());mp.setLayers([scope,towns,lyr]);mp.setKeepLayerSet(True);mp.setKeepLayerStyles(True)
            ex=QgsRectangle(scope.extent());ex.scale(1.04);cx=ex.center().x();dx=ex.height()*84/70/2;ex.setXMinimum(cx-dx);ex.setXMaximum(cx+dx);mp.setExtent(ex);live.append(mp)
            if ix==0:
                # One shared scale: all three locked map panels have the same
                # physical size and extent. Keep it outside mapped data in the
                # whitespace below the lower-right legend.
                scale=QgsLayoutItemScaleBar(layout);scale.setStyle('Single Box');scale.setLinkedMap(mp);scale.setUnits(QgsUnitTypes.DistanceKilometers);scale.setUnitsPerSegment(10);scale.setNumberOfSegments(2);scale.setNumberOfSegmentsLeft(0);scale.setUnitLabel('km');scale.setFont(mapfont(10.5));scale.setHeight(1);layout.addLayoutItem(scale);scale.attemptMove(QgsLayoutPoint(102,210));live.append(scale)
                label('N ↑',x+72,y+10,14,8,11)
            if field=='map_class':
                vals=[f'{c["upper"]:.3f}' for c in breaks[habitat]['classes'][:-1]]
                label('分级界点：'+' / '.join(vals),x,y+81,88,12,10.5)
            elif field=='stability_map':
                ct=coverage[habitat]
                label(f'完整对照 {ct["complete"]} / 基准 {ct["baseline"]} 格\n其中基线最低 {ct["complete_baseline_low"]} 格',x,y+81,88,15,10.5)
        xpos=101;ypos=140
        label('图例',xpos,ypos-11,80,8,11.5,True)
        for code,name,color in cats:
            sw=QgsLayoutItemShape(layout);sw.setShapeType(QgsLayoutItemShape.Rectangle);sw.setSymbol(fill(color));layout.addLayoutItem(sw);sw.attemptMove(QgsLayoutPoint(xpos,ypos+1));sw.attemptResize(QgsLayoutSize(5,4));live.append(sw)
            label(name,xpos+7,ypos,76,10,11);ypos+=12
        if field=='map_class':
            note='六项均有效的1 km方格；三类生境分别标准化、赋权与分级。\n颜色表示各生境内部的相对等级，不用于跨生境比较。\nFisher–Jenks五级分级；不存在通用的生态韧性分级阈值。'
        elif field=='shortfall_map':
            note='三维得分均已转为高值有利；最低维度标记相对短板。\n短板位置应结合单项指标解释，再研判生境维护、\n斑块联系改善和灰绿配置措施。'
        else:
            nl=[coverage[h]['complete_baseline_low'] for h in HAB]
            note=('七方案仅在全部有效的格网内比较；缺失不等于不稳定。\n'
                  f'完整域基线最低格网：林灌{nl[0]}格、草地{nl[1]}格、水湿{nl[2]}格。\n'
                  '林灌和水湿的上述低值均未持续为最低级；\n'
                  '草地最低格网无完整对照，不能判断其低值持续性。\n'
                  '完整域结论不能外推至对照不完整区域。')
        label(note,6,224,180,26,10.5)
        label('WGS 84 Albers等积投影；N为格网北。\n指标取完整方格，制图裁至研究区。',6,251,180,11,10.5)
        project.layoutManager().addLayout(layout);layout.refresh();app.processEvents()
        export=QgsLayoutExporter(layout);ascii_dir=Path('D:/ER219_work/map_exports');ascii_dir.mkdir(exist_ok=True)
        for ext,setting,fun in [('png',QgsLayoutExporter.ImageExportSettings(),export.exportToImage),('pdf',QgsLayoutExporter.PdfExportSettings(),export.exportToPdf),('svg',QgsLayoutExporter.SvgExportSettings(),export.exportToSvg)]:
            setting.dpi=300
            if ext=='svg':setting.exportAsLayers=True
            path=ascii_dir/('fig'+str(fig)+'.'+ext);assert fun(str(path),setting)==QgsLayoutExporter.Success
            shutil.copy2(path,OUT/(stem+'.'+ext))
    # Preserve a meaningful initial desktop canvas as well as locked layouts.
    # Only the first result panel is initially visible; all layouts keep their
    # own three locked habitat layers and remain fully editable.
    tree=project.layerTreeRoot()
    visible={scope.id(),towns.id(),default_layer.id()}
    for node in tree.findLayers():
        node.setItemVisibilityChecked(node.layerId() in visible);node.setExpanded(False)
    order=[scope,towns,default_layer]+[x for x in project.mapLayers().values() if x.id() not in visible]
    tree.setHasCustomLayerOrder(True);tree.setCustomLayerOrder(order)
    initial=QgsRectangle(scope.extent());initial.scale(1.08)
    project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(initial,scope.crs()))
    assert project.write(str(OUT/'生态韧性结果_可编辑地图.qgz'))
    (WORK/'native_export_receipt.json').write_text(json.dumps({'status':'EXPORTED_NATIVE_REOPEN_AND_VISUAL_REVIEW_PENDING','engine':Qgis.QGIS_VERSION,'feature_counts':audit,'comparison_coverage':coverage,'source':'Actual final six-indicator evaluation_maps.gpkg','classification':'exact Fisher-Jenks, jenkspy0.4.1; QGIS native layouts','minimum_source_label_pt':10.5,'intended_Word_width_mm':146.4,'figures':[s[4] for s in specs]},ensure_ascii=False,indent=2),encoding='utf8')
    print('ACTUAL_RESULT_LAYOUTS_EXPORTED')

build()
QgsProject.instance().clear();gc.collect();app.exitQgis()
