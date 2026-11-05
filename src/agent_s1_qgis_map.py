"""Eight native QGIS maps of four completed raw indicators, not ER scores."""
import os,json,gc,shutil,hashlib,csv
from pathlib import Path
os.environ["QT_QPA_PLATFORM"]="offscreen"
from qgis.core import *
from qgis.PyQt.QtGui import QColor,QFont
from qgis.PyQt.QtGui import QFontDatabase
from qgis.PyQt.QtCore import Qt
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/"02_过程文件/map_inputs_s1"
OUT=ROOT/"04_图件"
app=QgsApplication([],False);app.initQgis()
assert QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")>=0

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build():
    project=QgsProject.instance()
    palette=json.loads((ROOT/"02_过程文件/map_inputs/palette.json").read_text(encoding="utf8"))
    colors=[QColor(x) for x in palette["sequential"]]
    stats=json.loads((WORK/"S1_data_receipt.json").read_text(encoding="utf8"))
    bounds={p["field"]:(p["legend_min"],p["legend_max"]) for p in stats["panels"]}
    scope=QgsVectorLayer(str(ROOT/"02_过程文件/spatial/scope.gpkg")+"|layername=study_scope","研究范围边界","ogr")
    assert scope.isValid()
    scope.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"style":"no","outline_style":"solid","outline_color":"#51615A","outline_width":"0.15"})))
    project.addMapLayer(scope);project.setCrs(scope.crs());project.setFilePathStorage(Qgis.FilePathType.Relative)
    layout=QgsPrintLayout(project);layout.initializeDefaults();layout.setName("图S1 四项原始指标")
    layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(300,220))
    refs=[];maps=[];layers=[];panels=[]
    def label(text,x,y,w,h,size=8,bold=False,align=Qt.AlignLeft):
        item=QgsLayoutItemLabel(layout);item.setText(text)
        font=QFont("Microsoft YaHei");font.setPointSizeF(size);font.setBold(bold)
        item.setFont(font);item.setFontColor(QColor("#303A36"));item.setMargin(0)
        item.setHAlign(align);item.setVAlign(Qt.AlignVCenter)
        layout.addLayoutItem(item);item.attemptMove(QgsLayoutPoint(x,y));item.attemptResize(QgsLayoutSize(w,h));refs.append(item)
        return item
    def rectangle(x,y,w,h,color):
        item=QgsLayoutItemShape(layout);item.setShapeType(QgsLayoutItemShape.Rectangle)
        item.setSymbol(QgsFillSymbol.createSimple({"color":color,"outline_style":"no"}))
        layout.addLayoutItem(item);item.attemptMove(QgsLayoutPoint(x,y));item.attemptResize(QgsLayoutSize(w,h));refs.append(item)
        return item
    def ramp_at(t):
        z=max(0,min(4,t*4));i=min(3,int(z));u=z-i
        return QColor(*[round(getattr(colors[i],c)()*(1-u)+getattr(colors[i+1],c)()*u) for c in ["red","green","blue"]]).name()
    def fill_expression(field,lo,hi):
        t='(("'+field+'"-('+format(lo,".17g")+'))/'+format(hi-lo,".17g")+')'
        channels=[]
        for component in ["red","green","blue"]:
            parts=[]
            for j in range(4):
                a=getattr(colors[j],component)();b=getattr(colors[j+1],component)()
                val=str(a)+'+('+str(b-a)+')*('+t+'*4-'+str(j)+')'
                parts.append(('WHEN '+t+'<='+str((j+1)/4)+' THEN '+val) if j<3 else ('ELSE '+val))
            channels.append('round(CASE '+' '.join(parts)+' END)')
        return 'CASE WHEN "'+field+'" IS NULL THEN \''+palette['missing']+'\' ELSE color_rgb('+','.join(channels)+') END'
    def colorbar(x,y,w,lo,hi,title,title_x=None,title_w=None):
        label(title,title_x if title_x is not None else x,y-1,title_w or w,5,8.1)
        for j in range(40):rectangle(x+j*w/40,y+5,w/40+.015,3,ramp_at((j+.5)/40))
        def fmt(v):
            if abs(v)>=10:return format(v,",.0f")
            return format(v,".1f").rstrip('0').rstrip('.')
        for fraction,value in [(0,lo),(.5,(lo+hi)/2),(1,hi)]:
            label(fmt(value),x+fraction*w-7,y+8,14,5,7.2,align=Qt.AlignHCenter)
    label("S1  四项原始指标的空间分布",8,3,280,9,13,True)
    label("2020年  ·  CLCD  ·  1 km正方形格网  ·  全部面板范围与比例尺一致",8,13,210,7,8.1)
    fields=[("HQ_FS","a  生境质量：林灌"),("HQ_G","b  生境质量：草地"),("HQ_W","c  生境质量：水体湿地"),("SSI","d  源汇平均距离"),
            ("CLUMPY_FS","e  聚集度：林灌"),("CLUMPY_G","f  聚集度：草地"),("CLUMPY_W","g  聚集度：水体湿地"),("E_fraction","h  生态空间面积比例")]
    xs=[8,82,156,230];mw=66;mh=60
    extent=QgsRectangle(scope.extent());extent.scale(1.045)
    cx,cy=extent.center().x(),extent.center().y()
    width=max(extent.width(),extent.height()*mw/mh);height=width*mh/mw
    extent=QgsRectangle(cx-width/2,cy-height/2,cx+width/2,cy+height/2)
    for k,(field,title) in enumerate(fields):
        row,col=divmod(k,4);x=xs[col];y=33+92*row
        label(title,x,y-9,70,7,9.1,True)
        layer=QgsVectorLayer(str(WORK/"S1_raw_indicator_cells.gpkg")+"|layername=cells",title,"ogr")
        assert layer.isValid() and layer.featureCount()==2478
        expr=fill_expression(field,*bounds[field]);test=QgsExpression(expr);assert not test.hasParserError(),test.parserErrorString()
        symbol=QgsFillSymbol.createSimple({"color":palette["sequential"][0],"outline_style":"no"})
        symbol.symbolLayer(0).setDataDefinedProperty(QgsSymbolLayer.PropertyFillColor,QgsProperty.fromExpression(expr))
        layer.setRenderer(QgsSingleSymbolRenderer(symbol));project.addMapLayer(layer);layers.append(layer)
        mp=QgsLayoutItemMap(layout);layout.addLayoutItem(mp);refs.append(mp);maps.append(mp)
        mp.attemptMove(QgsLayoutPoint(x,y));mp.attemptResize(QgsLayoutSize(mw,mh));mp.setCrs(scope.crs())
        mp.setLayers([scope,layer]);mp.setKeepLayerSet(True);mp.setKeepLayerStyles(True);mp.setExtent(extent);mp.setFrameEnabled(False)
        mp.setId("map_"+field)
        panels.append({"field":field,"title":title,"source_layer_id":layer.id(),"map_item_id":mp.id(),"continuous_min_max":list(bounds[field]),"fill_expression":expr})
    scale=QgsLayoutItemScaleBar(layout);scale.setStyle("Single Box");scale.setLinkedMap(maps[0]);scale.setUnits(QgsUnitTypes.DistanceKilometers)
    scale.setUnitsPerSegment(10);scale.setNumberOfSegments(2);scale.setNumberOfSegmentsLeft(0);scale.setUnitLabel("km")
    scale.setFont(QFont("Microsoft YaHei",7));scale.setHeight(1.2)
    layout.addLayoutItem(scale);scale.attemptMove(QgsLayoutPoint(233,13));refs.append(scale)
    label("N  ↑",283,12,14,9,10,True)
    colorbar(76,96,103,0,1,"生境质量 HQ",8,63)
    colorbar(233,96,60,*bounds["SSI"],"SSI（m）")
    colorbar(76,188,103,-1,1,"聚集度 CLUMPY",8,65)
    colorbar(233,188,60,0,1,"E/(E+C)")
    rectangle(8,206,5,3,palette["missing"])
    label("NA：无焦点生境或未满足计算条件。完整方格计算，按研究范围裁剪显示；E为生态空间，C为建设空间。",16,204,280,6,7.2)
    label("原始指标不等同综合生态韧性；深色仅表示数值较高。WGS 84 Albers等积投影，N为格网北。",8,211,288,6,7.2)
    project.layoutManager().addLayout(layout)
    layout.pageCollection().pages()[0].setZValue(-1000)
    for item in refs:
        if isinstance(item,QgsLayoutItemLabel):item.setZValue(100)
        elif isinstance(item,QgsLayoutItemMap):item.setZValue(10)
        else:item.setZValue(20)
    layout.refresh();app.processEvents()
    qgz=OUT/"补充图S1_原始指标地图.qgz";assert project.write(str(qgz))
    exp=QgsLayoutExporter(layout);temp=Path("D:/ER219_work/s1_exports");temp.mkdir(exist_ok=True)
    im=QgsLayoutExporter.ImageExportSettings();im.dpi=300;assert exp.exportToImage(str(temp/"S1.png"),im)==QgsLayoutExporter.Success
    pdf=QgsLayoutExporter.PdfExportSettings();pdf.dpi=300;pdf.forceVectorOutput=True;assert exp.exportToPdf(str(temp/"S1.pdf"),pdf)==QgsLayoutExporter.Success
    svg=QgsLayoutExporter.SvgExportSettings();svg.dpi=300;svg.exportAsLayers=True;assert exp.exportToSvg(str(temp/"S1.svg"),svg)==QgsLayoutExporter.Success
    exported=[]
    for suffix in ["png","pdf","svg"]:
        dst=OUT/("图S1_四项原始指标空间分布."+suffix);shutil.copy2(temp/("S1."+suffix),dst)
        exported.append({"path":str(dst.relative_to(ROOT)),"bytes":dst.stat().st_size,"sha256":digest(dst)})
    record={"status":"NATIVE_QGIS_EXPORTED_PENDING_REOPEN_AND_VISUAL_QA","engine":"QGIS "+Qgis.QGIS_VERSION,
            "project":str(qgz.relative_to(ROOT)),"layout_mm":[300,220],"maps":panels,"source_GPKG_sha256":digest(WORK/"S1_raw_indicator_cells.gpkg"),
            "palette":palette["sequential"],"NA":palette["missing"],"map_extent":extent.toString(),"source_values_unchanged":True,
            "color_policy":"continuous piecewise linear interpolation through the same five teal anchors; fixed shared HQ 0-1 and CLUMPY -1 to 1 across habitats, E/(E+C) 0-1; SSI observed full raw range in metres",
            "exported":exported,"relative_project_sources":True}
    (WORK/"S1_native_receipt.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf8")
    print("S1_NATIVE_MAPS_EXPORTED",flush=True)

build()
QgsProject.instance().clear();gc.collect();app.exitQgis()
