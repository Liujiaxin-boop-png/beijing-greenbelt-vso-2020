"""Academic three-column small-box workflow; native QGIS editable layout."""
import os,json,re,hashlib,gc,shutil
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QColor,QFont,QFontInfo,QFontDatabase,QRawFont,QPolygonF
from qgis.PyQt.QtCore import Qt,QPointF

C=Path('D:/ER219_code/intro_revision_20261106');C.mkdir(exist_ok=True)
W=Path('D:/ER219_work/intro_revision_20261106');W.mkdir(exist_ok=True)
T=W/'exports_route';T.mkdir(exist_ok=True)
O=Path('D:/ER219_figures/技术路线小框式_20261106');O.mkdir(exist_ok=True)
STYLE=json.loads(Path('D:/ER219_code/figure_revision_20261106/figure_style.json').read_text(encoding='utf8'))
SOURCE=Path('D:/ER219_figures/统一图式与过程图_20261106/图2_研究技术路线.qgz')
ORIGINAL=Path('D:/ER219_figures/技术路线_可编辑布局.qgz')
REFERENCE=Path('C:/Users/LJX/AppData/Local/Temp/codex-clipboard-e0ef1a27-aa61-4eae-867f-4675e15d0345.png')
FONT='SimHei';TEXT='#1F2528';LINE='#667971';COLORS=['#EDF4F1','#F0F4F5','#F5F3ED','#EFF4EF']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
frozen={str(p):sha(p) for p in [SOURCE,ORIGINAL,REFERENCE]}
app=QgsApplication([],False);app.initQgis();assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/simhei.ttf')>=0
project=QgsProject();assert project.read(str(SOURCE.resolve()));assert len(project.mapLayers())==0
for prior in list(project.layoutManager().layouts()):project.layoutManager().removeLayout(prior)
project.setFilePathStorage(Qgis.FilePathType.Relative)
layout=QgsPrintLayout(project);layout.initializeDefaults();layout.setName('图2 三列小框式技术路线')
layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(190,270))
refs=[];labels=[];nodes=[];arrows=[]

def label(txt,x,y,w,h,role='map_label',align=Qt.AlignHCenter,id=None):
 txt=txt.replace('−','-');font=QFont(FONT);font.setPointSizeF(STYLE['sizes_pt'][role]);font.setBold(False)
 item=QgsLayoutItemLabel(layout);item.setText(txt);item.setFont(font);item.setFontColor(QColor(TEXT));item.setMargin(0);item.setHAlign(align);item.setVAlign(Qt.AlignVCenter)
 layout.addLayoutItem(item);item.attemptMove(QgsLayoutPoint(x,y));item.attemptResize(QgsLayoutSize(w,h));item.setZValue(100)
 if id:item.setId(id)
 refs.append(item);labels.append({'text':txt,'role':role,'font_pt':font.pointSizeF(),'font':QFontInfo(font).family(),'bounds_mm':[x,y,w,h],'id':id})
 assert x>=0 and y>=0 and x+w<=190 and y+h<=270
 return item
def box(x,y,w,h,fill='#FFFFFF',border=LINE,dashed=False,id=None):
 item=QgsLayoutItemShape(layout);item.setShapeType(QgsLayoutItemShape.Rectangle)
 item.setSymbol(QgsFillSymbol.createSimple({'color':fill,'outline_color':border,'outline_width':'.18','outline_style':'dash' if dashed else 'solid','joinstyle':'miter'}))
 layout.addLayoutItem(item);item.attemptMove(QgsLayoutPoint(x,y));item.attemptResize(QgsLayoutSize(w,h));item.setZValue(2)
 if id:item.setId(id)
 refs.append(item);nodes.append({'id':id,'bounds_mm':[x,y,w,h],'dashed':dashed,'fill':fill});return item
def node(txt,x,y,w,h,fill,role='map_label',id=None):
 box(x,y,w,h,fill,id=id);label(txt,x+1,y+.2,w-2,h-.4,role,id=(id+'_text') if id else None)
def line(x1,y1,x2,y2,width=.18):
 item=QgsLayoutItemPolyline(QPolygonF([QPointF(x1,y1),QPointF(x2,y2)]),layout)
 item.setSymbol(QgsLineSymbol.createSimple({'line_color':LINE,'line_width':str(width),'line_width_unit':'MM'}));layout.addLayoutItem(item);item.setZValue(20);refs.append(item)
def arrow(x1,y1,x2,y2):
 line(x1,y1,x2,y2)
 if x1==x2:
  sign=1 if y2>y1 else -1;line(x2-1,y2-sign*1.4,x2,y2);line(x2+1,y2-sign*1.4,x2,y2)
 elif y1==y2:
  sign=1 if x2>x1 else -1;line(x2-sign*1.4,y2-1,x2,y2);line(x2-sign*1.4,y2+1,x2,y2)
 else:raise ValueError('Only orthogonal arrows are used')
 arrows.append([x1,y1,x2,y2])

box(2,2,186,266,'#FFFFFF','#3A4043',id='outer_neatline')
label('生态韧性评价技术路线',6,4,178,10,'figure_title')
for x,w,txt in [(6,33,'研究目标'),(43,100,'研究过程'),(147,37,'研究方法')]:node(txt,x,17,w,8,'#E8EFEB','panel_title')

# I. Indicator construction; the reference supplies structure only, not contents.
box(43,31,100,82,'#FFFFFF','#8A9D95',True,'module_indicators')
node('建立生态韧性\n评价指标体系',6,62,33,20,COLORS[0],'map_label','goal_indicators')
node('土地覆盖 / 道路 / 夜间灯光',47,35,92,9,COLORS[0],'map_label','input_data')
arrow(93,44.5,93,49)
node('V—S—O 三维六指标',47,49,92,8,'#E1EDE7','legend_title','six_indices')
rows=[('V 脆弱性','生境质量\nHQ (+)','夜间灯光\nNTL (-)'),('S 敏感性','聚集度\nCLUMPY (+)','最小累积阻力\nMCR (-)'),('O 自组织','源汇平均距离\nSSI (-)','生态空间比例\nE/(E+C) (+)')]
for i,(dimension,a,b) in enumerate(rows):
 y=61+i*15;node(dimension,47,y,22,12,COLORS[0],'map_label','criterion_'+str(i));node(a,73,y,31,12,'#FAFCFB','note','indicator_'+str(i)+'a');node(b,108,y,31,12,'#FAFCFB','note','indicator_'+str(i)+'b')
 line(69,y+6,73,y+6);line(104,y+6,108,y+6)
for i,text in enumerate(['多源数据匹配','InVEST生境质量','FRAGSTATS聚集度','MSPA与成本距离','夜光及GIS统计']):node(text,147,36+i*14,37,10,COLORS[0],'note','method1_'+str(i))
arrow(39.4,72,42.4,72);arrow(143.4,72,146.4,72);arrow(93,113.5,93,118.5)

# II. Index calculation and independent habitat domains.
box(43,119,100,44,'#FFFFFF','#8A9D95',True,'module_evaluation')
node('识别生态韧性\n空间差异',6,131,33,20,COLORS[1],'map_label','goal_patterns')
node('1 km正方形格网\n林灌 / 草地 / 水体湿地分别评价',47,123,92,12,COLORS[1],'map_label','independent_habitats')
line(93,135,93,138);line(60,138,93,138);arrow(60,138,60,141.5)
node('六项均有效',47,142,26,13,'#FAFCFC','note','complete_six')
node('固定标准化',80,142,25,13,'#FAFCFC','note','normalization')
node('熵权加权\n三维与综合指数',112,142,27,13,'#FAFCFC','note','entropy_ER')
arrow(73,148.5,79.5,148.5);arrow(105,148.5,111.5,148.5)
for i,text in enumerate(['格网空间统计','分生境标准化','熵权法','五级自然断点']):node(text,147,121+i*10,37,8,COLORS[1],'note','method2_'+str(i))
arrow(39.4,141,42.4,141);arrow(143.4,141,146.4,141);arrow(93,163.5,93,168.5)

# III. Sensitivity comparison uses fixed classifications and paired valid support.
box(43,169,100,44,'#FFFFFF','#8A9D95',True,'module_robustness')
node('检验评价稳定性\n明确有效范围',6,181,33,20,COLORS[2],'map_label','goal_robustness')
for x,txt,id in [(47,'土地覆盖\n与地类口径','data'),(79,'源地阈值\n与道路阻力','parameters'),(111,'500 m尺度\n与权重 / 删项','scale')]:
 node(txt,x,173,28,12,COLORS[2],'note','contrast_'+id);arrow(x+14,185.5,x+14,190.5)
node('成对有效格网对照，分级阈值固定\n七方案均有效格网：检查低值持续性',47,191,92,14,'#FCFBF8','map_label','robustness_support')
for i,text in enumerate(['成对共同有效域','参数 / 尺度对照','权重 / 删项检验']):node(text,147,173+i*13,37,11,COLORS[2],'note','method3_'+str(i))
arrow(39.4,191,42.4,191);arrow(143.4,191,146.4,191);arrow(93,213.5,93,218.5)

# IV. Planning interpretation and separate temperature association.
box(43,219,100,38,'#FFFFFF','#8A9D95',True,'module_planning')
node('转化为乡镇\n管护筛查线索',6,228,33,20,COLORS[3],'map_label','goal_planning')
node('格网薄弱条件 → 乡镇内部差异',47,223,92,10,COLORS[3],'map_label','grid_to_town')
line(93,233,93,235.5);line(69,235.5,117,235.5);arrow(69,235.5,69,238);arrow(117,235.5,117,238)
node('低值与短板核查\n底图 / 参数核验',47,238,44,13,'#FAFCFA','note','field_check')
node('生态管护建议\n对接实地核查',95,238,44,13,'#FAFCFA','note','planning_application')
for i,text in enumerate(['乡镇加权统计','原始指标解释','同期地表温度','仅作辅助对照']):node(text,147,221+i*9,37,7.5,COLORS[3],'note','method4_'+str(i))
arrow(39.4,238,42.4,238);arrow(143.4,238,146.4,238)
label('注：(+)/(-)为有利/不利方向；温度仅作辅助，不进入综合指数。',6,260,178,6,'note',Qt.AlignLeft,'figure_note')

project.layoutManager().addLayout(layout);layout.pageCollection().pages()[0].setZValue(-1000)
raw=QRawFont.fromFont(QFont(FONT,10));missing=sorted({ch for x in labels for ch in x['text'] if not ch.isspace() and not raw.supportsCharacter(ord(ch))});assert not missing,missing
assert all(x['font']==FONT for x in labels)
layout.refresh();app.processEvents();qgz=O/'图2_技术路线_三列小框式.qgz';assert project.write(str(qgz.resolve()))
export=QgsLayoutExporter(layout);exports=[]
for ext,setting,fn in [('png',QgsLayoutExporter.ImageExportSettings(),export.exportToImage),('pdf',QgsLayoutExporter.PdfExportSettings(),export.exportToPdf),('svg',QgsLayoutExporter.SvgExportSettings(),export.exportToSvg)]:
 setting.dpi=600
 if ext=='pdf':setting.forceVectorOutput=True
 if ext=='svg':setting.exportAsLayers=True
 temp=T/('route_smallbox.'+ext);assert fn(str(temp),setting)==QgsLayoutExporter.Success and temp.stat().st_size>1000
 dest=O/('图2_技术路线_三列小框式.'+ext);shutil.copy2(temp,dest);assert sha(dest)==sha(temp)
 exports.append({'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size})
settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=180;preview=T/'route_smallbox_preview.png';assert export.exportToImage(str(preview),settings)==QgsLayoutExporter.Success
record={'status':'NATIVE_EXPORT_PENDING_REOPEN_VISUAL','engine':Qgis.QGIS_VERSION,'project':str(qgz),'project_sha256':sha(qgz),'layout_mm':[190,270],'font':'SimHei','font_sizes_pt':STYLE['sizes_pt'],'minimum_at_Word_146_4_mm_pt':10*146.4/190,'unsupported_glyphs':missing,'labels':labels,'nodes':nodes,'arrows':arrows,'exports':exports,'preview':str(preview),'frozen_source_hashes':frozen,'scientific_content':'six approved VSO indicators, independent three habitats, 1km square grid, entropy weighting, paired valid-domain/data/parameter/500m/weight/deletion checks, township interpretation; LST auxiliary only','reference_image_used_for':'Three-column structure and small orthogonal nodes only; no social-resilience/visit/Citespace content copied','no_other_files_changed':all(sha(p)==h for p,h in frozen.items())}
(W/'route_smallbox_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print('SMALLBOX_ROUTE_EXPORTED',flush=True)
project.clear();gc.collect();app.exitQgis()
