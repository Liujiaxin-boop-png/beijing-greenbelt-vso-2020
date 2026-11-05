"""Native QGIS 3.28 print-layout figure from frozen real grid observations.
All points/axes/labels are editable QGIS layout items; no matplotlib or AI image.
Run using locally installed python-qgis.bat.
"""
import os,csv,json,hashlib,gc,shutil,math
from pathlib import Path
os.environ["QT_QPA_PLATFORM"]="offscreen"
from qgis.core import *
from qgis.PyQt.QtGui import QColor,QFont,QFontDatabase,QPolygonF
from qgis.PyQt.QtCore import Qt,QPointF
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"04_图件"
QA=ROOT/"02_过程文件/figure6_QGIS"
QA.mkdir(parents=True,exist_ok=True);OUT.mkdir(exist_ok=True)
DATA=ROOT/"03_结果文件/thermal_association"
SCENE="LC08_L2SP_123032_20200803_02_T1"
SCATTER=DATA/(SCENE+"_scatter_real_grid_values.csv")
STATS=DATA/"graygreen_LST_spearman_descriptive.csv"
PALETTE={"point":"#527F71","emphasis":"#2C6E62","auxiliary":"#649DB4","text":"#303A36","axis":"#63716A","grid":"#DDE4E0",
"positive_row":"#EEF4F1","negative_row":"#EEF4F7","positive_text":"#2C6E62","negative_text":"#365E70"}
app=QgsApplication([],False);app.initQgis()
assert QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")>=0
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_csv(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def build():
 points=read_csv(SCATTER); stats=[r for r in read_csv(STATS) if r["date"]=="20200803"]
 assert len(points)==1268 and len({r["Grid_ID"] for r in points})==1268
 lookup={(r["domain"],r["predictor"]):r for r in stats}
 assert all(int(r["n_grid_pairs"])==1268 for r in stats if r["domain"]=="ALL")
 project=QgsProject.instance()
 project.setFilePathStorage(Qgis.FilePathType.Relative)
 # Non-spatial source tables are intentionally not assigned geographical coordinates.
 for path,title in [(SCATTER,"主景真实方格散点数值"),(STATS,"逐日期分片区Spearman系数")]:
  layer=QgsVectorLayer(str(path),title,"ogr")
  assert layer.isValid()
  project.addMapLayer(layer)
 layout=QgsPrintLayout(project);layout.initializeDefaults();layout.setName("图6 灰绿配置与热环境")
 layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(210,228))
 item_bounds=[];point_audit=[];native_item_refs=[]
 def label(text,x,y,w,h,size=11.5,bold=False,color=None,align=Qt.AlignLeft,item_id=None):
  it=QgsLayoutItemLabel(layout);it.setText(text)
  font=QFont("Microsoft YaHei");font.setPointSizeF(size);font.setBold(bold);it.setFont(font)
  it.setFontColor(QColor(color or PALETTE["text"]));it.setMargin(0)
  it.setHAlign(align);it.setVAlign(Qt.AlignVCenter)
  layout.addLayoutItem(it);it.attemptMove(QgsLayoutPoint(x,y));it.attemptResize(QgsLayoutSize(w,h))
  if item_id:it.setId(item_id)
  item_bounds.append({"type":"label","text":text,"x":x,"y":y,"width":w,"height":h,"font_pt":size})
  native_item_refs.append(it)
  return it
 def line(x1,y1,x2,y2,color=None,width=.18,item_id=None):
  it=QgsLayoutItemPolyline(QPolygonF([QPointF(x1,y1),QPointF(x2,y2)]),layout)
  it.setSymbol(QgsLineSymbol.createSimple({"line_color":color or PALETTE["axis"],"line_width":str(width),"line_width_unit":"MM"}))
  layout.addLayoutItem(it)
  if item_id:it.setId(item_id)
  native_item_refs.append(it)
  return it
 def shape(x,y,w,h,fill,ellipse=False,item_id=None):
  it=QgsLayoutItemShape(layout);it.setShapeType(QgsLayoutItemShape.Ellipse if ellipse else QgsLayoutItemShape.Rectangle)
  it.setSymbol(QgsFillSymbol.createSimple({"color":fill,"outline_style":"no","joinstyle":"miter"}))
  layout.addLayoutItem(it);it.attemptMove(QgsLayoutPoint(x,y));it.attemptResize(QgsLayoutSize(w,h))
  if item_id:it.setId(item_id)
  native_item_refs.append(it)
  return it
 label("灰绿配置与同期地表温度",10,4,190,10,16,True,item_id="figure_title")
 label("2020年8月3日  ·  完整1 km方格  ·  每幅 n = 1,268",10,14,190,8,11.5,item_id="figure_subtitle")
 panel_configs=[{"key":"SSI","x":24,"xmin":0,"xmax":1000,"ticks":[0,200,400,600,800,1000],
 "heading":"a  源汇平均距离","xlabel":"源汇平均距离 SSI（m）"},
 {"key":"E_fraction","x":124,"xmin":0,"xmax":1,"ticks":[0,.2,.4,.6,.8,1],
 "heading":"b  生态空间相对比例","xlabel":"生态空间面积比例 E/(E+C)"}]
 plot_y=40;pw=76;ph=62;ymin=30;ymax=50
 for config in panel_configs:
  key=config["key"];px=config["x"]
  label(config["heading"],px,24,pw,7,12.5,True,item_id="panel_"+key+"_heading")
  label("地表温度 LST（℃）",px,32,40,7,11.5,item_id="panel_"+key+"_y_title")
  rho=float(lookup[("ALL",key)]["spearman_rho"])
  rho_text=("−" if rho<0 else "")+format(abs(rho),".3f")
  label("ρ = "+rho_text,px+40,32,36,7,11.5,True,PALETTE["emphasis"],Qt.AlignRight,item_id="panel_"+key+"_rho")
  for yv in [30,35,40,45,50]:
   yy=plot_y+ph-(yv-ymin)/(ymax-ymin)*ph
   line(px,yy,px+pw,yy,PALETTE["grid"],.12)
   line(px-1,yy,px,yy,width=.18)
   label(str(yv),px-11,yy-3.5,8,7,11.5,align=Qt.AlignRight)
  for xv in config["ticks"]:
   xx=px+(xv-config["xmin"])/(config["xmax"]-config["xmin"])*pw
   line(xx,plot_y+ph,xx,plot_y+ph+1,width=.18)
   label(str(xv) if key=="SSI" else format(xv,".1f"),xx-7,plot_y+ph+2,14,7,11.5,align=Qt.AlignHCenter)
  line(px,plot_y,px,plot_y+ph,width=.23)
  line(px,plot_y+ph,px+pw,plot_y+ph,width=.23)
  for row in points:
   xv=float(row[key]);yv=float(row["LST_mean_C"])
   assert config["xmin"]<=xv<=config["xmax"] and ymin<=yv<=ymax
   xx=px+(xv-config["xmin"])/(config["xmax"]-config["xmin"])*pw
   yy=plot_y+ph-(yv-ymin)/(ymax-ymin)*ph
   # Equal symbol size for every observation; alpha exposes overlap without moving points.
   it=shape(xx-.38,yy-.38,.76,.76,"82,127,113,100",True,"point_"+key+"_"+row["Grid_ID"])
   point_audit.append({"panel":key,"Grid_ID":row["Grid_ID"],"x_value":xv,"LST_C":yv,"layout_x_mm":xx,"layout_y_mm":yy})
  label(config["xlabel"],px-4,115,pw+8,8,11.5,align=Qt.AlignHCenter,item_id="panel_"+key+"_x_title")
 label("c  分片区重复比较",24,135,176,8,12.5,True,item_id="matrix_heading")
 # A numerical matrix with row tint only; no unlabelled heatmap color scale.
 cols=["NW","NE","SW","SE"];cn={"NW":"西北","NE":"东北","SW":"西南","SE":"东南"}
 table_x=24;table_y=147;label_w=56;cell_w=30
 for i,q in enumerate(cols):
  n=int(lookup[(q,"SSI")]["n_grid_pairs"])
  label(cn[q]+"\nn = "+str(n),table_x+label_w+i*cell_w,table_y,cell_w,16,11.5,align=Qt.AlignHCenter,item_id="header_"+q)
 line(table_x,table_y+16,200,table_y+16,PALETTE["grid"],.2)
 for j,key in enumerate(["SSI","E_fraction"]):
  yy=table_y+16+j*12
  shape(table_x,yy,176,12,PALETTE["positive_row"] if j==0 else PALETTE["negative_row"],item_id="matrix_row_"+key)
  label("源汇平均距离 SSI" if j==0 else "生态空间比例 E/(E+C)",table_x+3,yy,label_w-3,12,11.5,item_id="row_label_"+key)
  for i,q in enumerate(cols):
   value=float(lookup[(q,key)]["spearman_rho"])
   text=("−" if value<0 else "")+format(abs(value),".3f")
   label(text,table_x+label_w+i*cell_w,yy,cell_w,12,13,True,PALETTE["positive_text"] if j==0 else PALETTE["negative_text"],Qt.AlignHCenter,
    item_id="rho_"+q+"_"+key)
 line(table_x,table_y+40,200,table_y+40,PALETTE["grid"],.2)
 label("每点为1个1 km方格。E为生态空间，C为建设空间；",10,196,190,8,11.5,item_id="note_1")
 label("ρ为Spearman秩相关系数，描述同期关联，不表示因果效应。",10,205,190,8,11.5,item_id="note_2")
 label("四片区按研究范围包络中点与方格质心划分。",10,214,190,8,11.5,item_id="note_3")
 project.layoutManager().addLayout(layout)
 # Fix stack levels explicitly; QGIS can otherwise rebuild same-level scene
 # order differently when a saved print layout is read without a GUI.
 layout.pageCollection().pages()[0].setZValue(-1000)
 for item in native_item_refs:
  if isinstance(item,QgsLayoutItemLabel):item.setZValue(100)
  elif isinstance(item,QgsLayoutItemPolyline):item.setZValue(10)
  elif item.id().startswith("point_"):item.setZValue(20)
  else:item.setZValue(2)
 layout.refresh();app.processEvents()
 qgz=OUT/"热环境补充图.qgz";assert project.write(str(qgz))
 exporter=QgsLayoutExporter(layout)
 exportdir=Path("D:/ER219_work/figure6_exports");exportdir.mkdir(exist_ok=True)
 settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=300
 assert exporter.exportToImage(str(exportdir/"fig6.png"),settings)==QgsLayoutExporter.Success
 pdf=QgsLayoutExporter.PdfExportSettings();pdf.dpi=300;pdf.forceVectorOutput=True
 assert exporter.exportToPdf(str(exportdir/"fig6.pdf"),pdf)==QgsLayoutExporter.Success
 svg=QgsLayoutExporter.SvgExportSettings();svg.dpi=300;svg.exportAsLayers=True
 assert exporter.exportToSvg(str(exportdir/"fig6.svg"),svg)==QgsLayoutExporter.Success
 exported=[]
 for ext in ["png","pdf","svg"]:
  dest=OUT/("图6_灰绿配置与热环境."+ext);shutil.copy2(exportdir/("fig6."+ext),dest)
  exported.append({"path":str(dest.relative_to(ROOT)),"bytes":dest.stat().st_size,"sha256":digest(dest)})
 for item in item_bounds:
  assert item["x"]>=0 and item["y"]>=0 and item["x"]+item["width"]<=210.01 and item["y"]+item["height"]<=228.01
  assert item["font_pt"]>=11.5
 with (QA/"native_layout_points.csv").open("w",encoding="utf-8-sig",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=list(point_audit[0]));writer.writeheader();writer.writerows(point_audit)
 receipt={"status":"NATIVE_QGIS_EXPORTED_PENDING_VISUAL_REVIEW","engine":"QGIS "+Qgis.QGIS_VERSION,
 "layout_size_mm":[210,228],"scatter_n_each_panel":1268,"native_point_items":len(point_audit),"source_csv":str(SCATTER.relative_to(ROOT)),
 "source_sha256":digest(SCATTER),"stats_sha256":digest(STATS),"editable_project":str(qgz.relative_to(ROOT)),
 "implementation":"QGIS-native shape/line/label print-layout items; source CSV tables included in project; no image synthesis or matplotlib.",
 "point_geometry":"All data points linearly mapped from real numerical values, equal 0.76 mm diameter, no jitter/fit/outlier removal.",
 "axes":{"SSI":[0,1000],"E_fraction":[0,1],"LST_C":[30,50]},"palette":PALETTE,"point_alpha":100,
 "matrix":"Numerical rho matrix with row tint only; values and signs are explicit. No magnitude encoded by arbitrary hue.",
 "font":"Microsoft YaHei, loaded from C:/Windows/Fonts/msyh.ttc",
 "typography":{"target_manuscript_width_mm":146.4,"native_min_font_pt":11.5,"minimum_font_at_target_width_pt":11.5*146.4/210,"notes_lines":3,"prior_point_positions_unchanged":True},
 "label_items":item_bounds,"exports":exported,"project_relative_paths":True}
 (QA/"figure6_native_receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf8")
 print("FIGURE6_QGIS_EXPORTED",flush=True)
build()
QgsProject.instance().clear();gc.collect();app.exitQgis()
