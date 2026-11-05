"""Draw and export an editable study map in locally installed QGIS 3.28.
No image-generation service or synthetic spatial data is used.
"""
import os,json,gc,shutil
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QColor,QFont,QFontDatabase
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'04_图件';OUT.mkdir(exist_ok=True)
app=QgsApplication([],False);app.initQgis()
assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')>=0

def build():
    project=QgsProject.instance()
    palette=json.loads((ROOT/'02_过程文件/map_inputs/palette.json').read_text(encoding='utf8'))
    scope=QgsVectorLayer(str(ROOT/'02_过程文件/spatial/scope.gpkg')+'|layername=study_scope','研究范围','ogr')
    towns=QgsVectorLayer(str(ROOT/'02_过程文件/spatial/scope.gpkg')+'|layername=towns','乡镇覆盖部分','ogr')
    land=QgsRasterLayer(str(ROOT/'02_过程文件/map_inputs/clcd2020_scope_display.tif'),'2020年土地覆盖 CLCD','gdal')
    assert all(x.isValid() for x in [scope,towns,land])
    classes=[QgsPalettedRasterRenderer.Class(int(k),QColor(v[1]),v[0]) for k,v in palette['landcover'].items()]
    land.setRenderer(QgsPalettedRasterRenderer(land.dataProvider(),1,classes))
    scope.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'transparent','outline_color':'#343E3B','outline_width':'0.35'}))
    towns.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'transparent','outline_color':'#6B716E','outline_width':'0.13'}))
    for lyr in [land,towns,scope]:project.addMapLayer(lyr)
    project.setCrs(scope.crs());project.setFilePathStorage(Qgis.FilePathType.Relative)
    layout=QgsPrintLayout(project);layout.initializeDefaults();layout.setName('图1 研究范围与土地覆盖')
    layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(190,220))
    def label(text,x,y,w,h,size=9,bold=False):
        item=QgsLayoutItemLabel(layout);item.setText(text);font=QFont('Microsoft YaHei');font.setPointSizeF(size);font.setBold(bold);item.setFont(font);item.setFontColor(QColor('#303A36'))
        layout.addLayoutItem(item);item.attemptMove(QgsLayoutPoint(x,y));item.attemptResize(QgsLayoutSize(w,h));return item
    label('研究区范围与2020年土地覆盖',8,4,176,9,12,True)
    label('35个乡镇覆盖部分  |  研究区面积 1987.900 km²',8,13,170,7,8)
    mp=QgsLayoutItemMap(layout);layout.addLayoutItem(mp);mp.attemptMove(QgsLayoutPoint(12,24));mp.attemptResize(QgsLayoutSize(164,143));mp.setCrs(scope.crs());mp.setLayers([scope,towns,land]);mp.setKeepLayerSet(True)
    ex=QgsRectangle(scope.extent());ex.scale(1.045)
    cx=ex.center().x();halfwidth=ex.height()*164/143/2
    ex.setXMinimum(cx-halfwidth);ex.setXMaximum(cx+halfwidth);mp.setExtent(ex)
    print('MAP_SIZE',mp.sizeWithUnits().width(),mp.sizeWithUnits().height(),'MAP_EXTENT',mp.extent().toString(),flush=True)
    mp.setFrameEnabled(False)
    label('N',167,24,10,7,10,True)
    # Use a simple north glyph; map is not rotated, and caption states grid north.
    label('↑',168,30,7,10,15)
    scale=QgsLayoutItemScaleBar(layout);scale.setStyle('Single Box');scale.setLinkedMap(mp);scale.setUnits(QgsUnitTypes.DistanceKilometers);scale.setUnitsPerSegment(10);scale.setNumberOfSegments(2);scale.setNumberOfSegmentsLeft(0);scale.setUnitLabel('km');scale.setFont(QFont('Microsoft YaHei',11));scale.setHeight(1.5);layout.addLayoutItem(scale);scale.attemptMove(QgsLayoutPoint(14,167))
    for i,(key,(name,color)) in enumerate(palette['landcover'].items()):
        col=i%4;row=i//4;x=12+col*42;y=182+row*9
        sw=QgsLayoutItemShape(layout);sw.setShapeType(QgsLayoutItemShape.Rectangle);sw.setSymbol(QgsFillSymbol.createSimple({'color':color,'outline_style':'no'}));layout.addLayoutItem(sw);sw.attemptMove(QgsLayoutPoint(x,y+1));sw.attemptResize(QgsLayoutSize(5,3.5));label(name,x+7,y,34,6,10.5)
    label('WGS 84 Albers等积投影；N为格网北。\n乡镇界仅显示研究范围内部分。',8,203,176,12,9.5)
    project.layoutManager().addLayout(layout)
    layout.refresh();app.processEvents()
    qgz=OUT/'生态韧性2020_可编辑地图.qgz';assert project.write(str(qgz))
    exporter=QgsLayoutExporter(layout)
    exportdir=Path('D:/ER219_work/map_exports');exportdir.mkdir(exist_ok=True)
    image=QgsLayoutExporter.ImageExportSettings();image.dpi=300
    assert exporter.exportToImage(str(exportdir/'fig1.png'),image)==QgsLayoutExporter.Success
    pdf=QgsLayoutExporter.PdfExportSettings();pdf.dpi=300
    assert exporter.exportToPdf(str(exportdir/'fig1.pdf'),pdf)==QgsLayoutExporter.Success
    svg=QgsLayoutExporter.SvgExportSettings();svg.dpi=300;svg.exportAsLayers=True
    assert exporter.exportToSvg(str(exportdir/'fig1.svg'),svg)==QgsLayoutExporter.Success
    for ext in ['png','pdf','svg']:shutil.copy2(exportdir/('fig1.'+ext),OUT/('图1_研究范围与土地覆盖.'+ext))
    receipt={'engine':'QGIS '+Qgis.QGIS_VERSION,'project':str(qgz),'exports':['PNG 300dpi','PDF','SVG'],'source':'CLCD2020 source mask display; original study/town coverage','metric_scope':'no resilience scores in this context map','map_extent':mp.extent().toString(),'project_relative_paths':True}
    (ROOT/'02_过程文件/map_inputs/study_map_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print('STUDY_MAP_EXPORTED')

build()
QgsProject.instance().clear();gc.collect();app.exitQgis()
