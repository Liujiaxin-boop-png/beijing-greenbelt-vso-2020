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
    live=[];layers={};audit=[]
    for habitat,name in HAB.items():
        layer=QgsVectorLayer(str(RESULT/'evaluation_maps.gpkg')+'|layername='+habitat,name,'ogr')
        assert layer.isValid() and layer.featureCount()==2478
        # Virtual fields preserve the source GeoPackage and remain editable in QGIS.
        layer.addExpressionField("CASE WHEN coalesce(\"map_class\",0)=0 THEN 0 WHEN \"limiting_dimension\"='V' THEN 1 WHEN \"limiting_dimension\"='S' THEN 2 WHEN \"limiting_dimension\"='O' THEN 3 ELSE 4 END",QgsField('shortfall_map',QVariant.Int))
        layer.addExpressionField("CASE WHEN coalesce(\"map_class\",0)=0 THEN 0 WHEN NOT coalesce(\"complete_comparison_set\",false) THEN 4 WHEN coalesce(\"consistent_low_complete_set\",false) THEN 1 WHEN \"class_span\"=0 THEN 2 ELSE 3 END",QgsField('stability_map',QVariant.Int))
        layers[habitat]=layer;project.addMapLayer(layer)
        for fld in ['map_class','shortfall_map','stability_map']:
            counts={}
            for f in layer.getFeatures():counts[str(f[fld])]=counts.get(str(f[fld]),0)+1
            audit.append({'habitat':habitat,'field':fld,'feature_counts':counts})
    er=[(0,'不可评价',palette['missing'])]+[(i+1,n,c) for i,(n,c) in enumerate(zip(['低','较低','中','较高','高'],palette['sequential']))]
    short=[(0,'不可评价',palette['missing']),(1,'生态基础与活动压力（V）','#527F71'),(2,'斑块联系（S）','#649DB4'),(3,'灰绿配置（O）','#B89765'),(4,'两个及以上维度并列','#A7A5B4')]
    stability=[(0,'不可评价',palette['missing']),(1,'稳定低值（七方案均低）','#B97846'),(2,'分级一致（非最低级）','#527F71'),(3,'不同方案分级变化','#D8CBA3'),(4,'对照有效范围不完整','#BBC6C4')]
    specs=[
      (3,'生态韧性潜力的空间分布','map_class',er,'图3_生态韧性空间分布','六项均有效的1 km方格；三类生境分别标准化、赋权与分级，颜色不能用于跨生境比较。'),
      (4,'综合评价对应的相对短板','shortfall_map',short,'图4_三维相对短板','三维得分均已转为高值有利；最低维度标记相对短板，需结合单项指标研判具体管护措施。'),
      (5,'空间分级对预设方案的稳定性','stability_map',stability,'图5_空间分级稳定性','基准及六类主对照共七方案；缺少任一主对照的格网单列，不作为已证实的稳定区域。')]
    for fig,title,field,cats,stem,note in specs:
        layout=QgsPrintLayout(project);layout.initializeDefaults();layout.setName('图'+str(fig)+' '+title)
        layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(190,225))
        def label(text,x,y,w,h,size=8,bold=False):
            obj=QgsLayoutItemLabel(layout);obj.setText(text);f=QFont('Microsoft YaHei',size);f.setBold(bold);obj.setFont(f);obj.setFontColor(QColor('#303A36'))
            layout.addLayoutItem(obj);obj.attemptMove(QgsLayoutPoint(x,y));obj.attemptResize(QgsLayoutSize(w,h));obj.setZValue(100);live.append(obj);return obj
        label(title,6,3,178,10,12,True)
        label('2020年  |  研究范围内的格网结果  |  三类生境分别评价',6,14,178,7,8)
        for ix,(habitat,name) in enumerate(HAB.items()):
            lyr=layers[habitat].clone();lyr.setName(name+' — '+title);lyr.setRenderer(categories(field,cats));project.addMapLayer(lyr)
            x=6+(ix%2)*92; y=26+(ix//2)*88
            label('abc'[ix]+'  '+name,x,y,86,7,10,True)
            mp=QgsLayoutItemMap(layout);layout.addLayoutItem(mp);mp.attemptMove(QgsLayoutPoint(x,y+10));mp.attemptResize(QgsLayoutSize(84,70));mp.setCrs(scope.crs());mp.setLayers([scope,towns,lyr]);mp.setKeepLayerSet(True);mp.setKeepLayerStyles(True)
            ex=QgsRectangle(scope.extent());ex.scale(1.04);cx=ex.center().x();dx=ex.height()*84/70/2;ex.setXMinimum(cx-dx);ex.setXMaximum(cx+dx);mp.setExtent(ex);live.append(mp)
            if ix==0:
                scale=QgsLayoutItemScaleBar(layout);scale.setStyle('Single Box');scale.setLinkedMap(mp);scale.setUnits(QgsUnitTypes.DistanceKilometers);scale.setUnitsPerSegment(10);scale.setNumberOfSegments(2);scale.setNumberOfSegmentsLeft(0);scale.setUnitLabel('km');scale.setFont(QFont('Microsoft YaHei',6));scale.setHeight(1);layout.addLayoutItem(scale);scale.attemptMove(QgsLayoutPoint(x+2,y+69));live.append(scale)
                label('N ↑',x+72,y+10,14,8,8)
            if field=='map_class':
                vals=[f'{c["upper"]:.3f}' for c in breaks[habitat]['classes'][:-1]]
                label('分级界点：'+' / '.join(vals),x,y+81,88,6,7)
        xpos=101;ypos=128
        label('图例',xpos,ypos-10,80,7,9,True)
        for code,name,color in cats:
            sw=QgsLayoutItemShape(layout);sw.setShapeType(QgsLayoutItemShape.Rectangle);sw.setSymbol(fill(color));layout.addLayoutItem(sw);sw.attemptMove(QgsLayoutPoint(xpos,ypos+1));sw.attemptResize(QgsLayoutSize(5,4));live.append(sw)
            label(name,xpos+7,ypos,76,7,8);ypos+=9
        if field=='map_class':
            note='六项均有效的1 km方格；三类生境分别标准化、赋权与分级。\n颜色表示各生境内部的相对等级，不用于跨生境比较，无通用分级阈值。'
        elif field=='shortfall_map':
            note='三维得分均已转为高值有利；最低维度标记相对短板。\n短板位置应结合单项指标解释，再研判生境维护、联系改善和灰绿配置措施。'
        else:
            note='基准及六类主对照共七方案；缺少任一主对照的格网单列。\n对照不完整的格网不作为已证实的稳定区域。'
        label(note,6,204,180,11,7.3)
        label('WGS 84 Albers等积投影；N为格网北。指标取完整方格，制图裁至研究区。',6,217,180,5,6.8)
        project.layoutManager().addLayout(layout);layout.refresh();app.processEvents()
        export=QgsLayoutExporter(layout);ascii_dir=Path('D:/ER219_work/map_exports');ascii_dir.mkdir(exist_ok=True)
        for ext,setting,fun in [('png',QgsLayoutExporter.ImageExportSettings(),export.exportToImage),('pdf',QgsLayoutExporter.PdfExportSettings(),export.exportToPdf),('svg',QgsLayoutExporter.SvgExportSettings(),export.exportToSvg)]:
            setting.dpi=300
            if ext=='svg':setting.exportAsLayers=True
            path=ascii_dir/('fig'+str(fig)+'.'+ext);assert fun(str(path),setting)==QgsLayoutExporter.Success
            shutil.copy2(path,OUT/(stem+'.'+ext))
    assert project.write(str(OUT/'生态韧性结果_可编辑地图.qgz'))
    (WORK/'native_export_receipt.json').write_text(json.dumps({'status':'EXPORTED_NATIVE_REOPEN_AND_VISUAL_REVIEW_PENDING','engine':Qgis.QGIS_VERSION,'feature_counts':audit,'source':'Actual final six-indicator evaluation_maps.gpkg','figures':[s[4] for s in specs]},ensure_ascii=False,indent=2),encoding='utf8')
    print('ACTUAL_RESULT_LAYOUTS_EXPORTED')

build()
QgsProject.instance().clear();gc.collect();app.exitQgis()
