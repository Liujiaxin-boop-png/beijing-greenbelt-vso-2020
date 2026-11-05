"""Native QGIS editable layout for the approved six-indicator workflow."""
import os,json,gc,shutil
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QFont,QColor,QFontDatabase,QPolygonF
from qgis.PyQt.QtCore import QPointF
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'04_图件'
app=QgsApplication([],False);app.initQgis();assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')>=0

def build():
    project=QgsProject.instance();layout=QgsPrintLayout(project);layout.initializeDefaults();layout.setName('图2 技术路线')
    layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(190,150))
    def label(txt,x,y,w,h,size=8,bold=False):
        o=QgsLayoutItemLabel(layout);o.setText(txt);f=QFont('Microsoft YaHei',size);f.setBold(bold);o.setFont(f);o.setFontColor(QColor('#303A36'));layout.addLayoutItem(o);o.attemptMove(QgsLayoutPoint(x,y));o.attemptResize(QgsLayoutSize(w,h));return o
    def box(x,y,w,h,fill='#EFF6F4',border='#9BB5AD'):
        o=QgsLayoutItemShape(layout);o.setShapeType(QgsLayoutItemShape.Rectangle);o.setSymbol(QgsFillSymbol.createSimple({'color':fill,'outline_color':border,'outline_width':'.2'}));layout.addLayoutItem(o);o.attemptMove(QgsLayoutPoint(x,y));o.attemptResize(QgsLayoutSize(w,h))
    def arrow(x,y):label('↓',x,y,7,8,12,True)
    label('从景观条件评价生态韧性并定位管护问题',7,3,180,9,11,True)
    columns=[('脆弱性相关条件','生境质量 HQ  ＋','土地覆盖与道路 → InVEST','夜间灯光 NTL  －','VIIRS年度辐亮度及有效覆盖'),('敏感性相关条件','聚集度 CLUMPY  ＋','FRAGSTATS计算同类生境邻接','最小累积阻力 MCR  －','ArcGIS计算至其他同类源地成本'),('自组织相关条件','源汇平均距离 SSI  －','建设空间至最近生态空间距离','生态空间比例 E/(E+C)  ＋','生态与建设空间的相对规模')]
    for i,(title,m1,s1,m2,s2) in enumerate(columns):
        x=7+i*60;box(x,16,56,40);label(title,x+2,18,52,7,9,True);label(m1,x+2,27,52,6,8.3,True);label(s1,x+2,33,52,6,7);label(m2,x+2,41,52,6,8.3,True);label(s2,x+2,47,52,6,7)
    arrow(91,56)
    box(7,65,176,13);label('1 km正方形格网   林灌、草地、水体湿地分别评价',11,67,168,8,9,True)
    arrow(91,78)
    box(7,87,176,13);label('六项均有效 → 固定标准化参照 → 熵权加权 → 三维得分与综合指数',10,89,170,8,8.6,True)
    arrow(48,100);arrow(137,100)
    box(7,109,85,17,fill='#F5F7F6');box(98,109,85,17,fill='#F5F7F6')
    label('空间诊断',10,110,78,6,8.5,True);label('格网短板、乡镇内部差异与有效覆盖',10,117,78,6,7.5)
    label('评价稳定性检查',101,110,78,6,8.5,True);label('地类、源地、阻力、尺度、删项与权重',101,117,78,6,7.5)
    label('规划用途：持续低值区域核查、底图与参数核验、分类管护',7,131,176,7,9,True)
    label('＋/－表示有利方向；同期地表温度用于灰绿配置的补充对照。',7,141,176,6,7)
    project.layoutManager().addLayout(layout);layout.refresh();app.processEvents()
    assert project.write(str(OUT/'技术路线_可编辑布局.qgz'))
    export=QgsLayoutExporter(layout);temp=Path('D:/ER219_work/map_exports');temp.mkdir(exist_ok=True)
    configs=[('png',QgsLayoutExporter.ImageExportSettings(),export.exportToImage),('pdf',QgsLayoutExporter.PdfExportSettings(),export.exportToPdf),('svg',QgsLayoutExporter.SvgExportSettings(),export.exportToSvg)]
    for ext,cfg,fn in configs:
        cfg.dpi=300
        if ext=='svg':cfg.exportAsLayers=True
        assert fn(str(temp/('fig2.'+ext)),cfg)==QgsLayoutExporter.Success
        shutil.copy2(temp/('fig2.'+ext),OUT/('图2_研究技术路线.'+ext))
    (ROOT/'02_过程文件/map_inputs/method_diagram_receipt.json').write_text(json.dumps({'engine':'QGIS '+Qgis.QGIS_VERSION,'all_elements_editable':True,'method_source':'approved218','figure_is_method_not_results':True},ensure_ascii=False,indent=2),encoding='utf8')
    print('METHOD_DIAGRAM_EXPORTED')

build();QgsProject.instance().clear();gc.collect();app.exitQgis()
