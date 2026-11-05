"""Open the delivered QGIS project natively and verify every scatter point."""
import os,csv,json,gc,sys,shutil,hashlib
from pathlib import Path
os.environ["QT_QPA_PLATFORM"]="offscreen"
from qgis.core import *
from qgis.PyQt.QtGui import QFontDatabase
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"02_过程文件/figure6_QGIS"
app=QgsApplication([],False);app.initQgis()
assert QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")>=0
def validate():
 project=QgsProject.instance()
 assert project.read(str(ROOT/"04_图件/热环境补充图.qgz"))
 layers=list(project.mapLayers().values());assert len(layers)==2 and all(l.isValid() for l in layers)
 assert sorted(l.featureCount() for l in layers)==[30,1268]
 layout=project.layoutManager().layoutByName("图6 灰绿配置与热环境");assert layout
 # Retain all native item wrappers immediately after project read, before any
 # per-item lookup. Dictionary lookup also avoids thousands of sorted scene
 # scans through QGIS itemById().
 layout_items=layout.items()
 by_id={x.id():x for x in layout_items if isinstance(x,QgsLayoutItem)}
 with (QA/"native_layout_points.csv").open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
 assert len(rows)==2536
 errors=[]
 for row in rows:
  it=by_id["point_"+row["panel"]+"_"+row["Grid_ID"]];assert isinstance(it,QgsLayoutItemShape)
  c=it.mapToScene(it.rect().center())
  error=max(abs(c.x()-float(row["layout_x_mm"])),abs(c.y()-float(row["layout_y_mm"])))
  errors.append(error)
 # QGIS 3.28 serializes layout positions with six significant digits.
 # On this 210 mm page the maximum serialization step is 0.001 mm,
 # so half a step is < 0.006 pixel at the 300 dpi export resolution.
 assert max(errors)<0.000501, max(errors)
 # Hold every SIP wrapper until export. In QGIS 3.28 this prevents the Python
 # garbage collector from deleting ungrouped items returned by scene.items().
 ids=[x.id() for x in layout_items if isinstance(x,QgsLayoutItem) and x.id().startswith("point_")]
 assert len(ids)==2536 and len(set(ids))==2536
 assert isinstance(by_id["figure_title"],QgsLayoutItemLabel)
 assert isinstance(by_id["matrix_row_SSI"],QgsLayoutItemShape)
 labels=[x for x in layout_items if isinstance(x,QgsLayoutItemLabel)]
 font_checks=[]
 for item in labels:
  font=item.font();point_size=font.pointSizeF()
  text_width=max(QgsLayoutUtils.textWidthMM(font,line) for line in item.text().splitlines())
  text_height=QgsLayoutUtils.textHeightMM(font,item.text())
  assert point_size>=11.5
  assert text_width<=item.rect().width()+.01,(item.text(),text_width,item.rect().width())
  assert text_height<=item.rect().height()+.01,(item.text(),text_height,item.rect().height())
  font_checks.append({"id":item.id(),"text":item.text(),"native_font_pt":point_size,"font_at_146_4mm_pt":point_size*146.4/210,
   "text_width_mm":text_width,"box_width_mm":item.rect().width(),"text_height_mm":text_height,"box_height_mm":item.rect().height()})
 before=QA/"before_146mm_typography"
 assert hashlib.sha256((before/"native_layout_points.csv").read_bytes()).hexdigest()==hashlib.sha256((QA/"native_layout_points.csv").read_bytes()).hexdigest()
 old=json.loads((before/"figure6_native_receipt.json").read_text(encoding="utf8"))
 current=json.loads((QA/"figure6_native_receipt.json").read_text(encoding="utf8"))
 assert old["source_sha256"]==current["source_sha256"] and old["stats_sha256"]==current["stats_sha256"]
 assert old["axes"]==current["axes"] and old["palette"]==current["palette"] and old["point_alpha"]==current["point_alpha"]
 repair="--repair-layer-order" in sys.argv
 if repair:
  layout.pageCollection().pages()[0].setZValue(-1000)
  for item in layout_items:
   if not isinstance(item,QgsLayoutItem):continue
   if isinstance(item,QgsLayoutItemLabel):item.setZValue(100)
   elif isinstance(item,QgsLayoutItemPolyline):item.setZValue(10)
   elif item.id().startswith("point_"):item.setZValue(20)
   elif isinstance(item,QgsLayoutItemShape):item.setZValue(2)
  assert project.write(str(ROOT/"04_图件/热环境补充图.qgz"))
 layout.refresh();app.processEvents()
 states=[]
 for ident in ["figure_title","matrix_row_SSI","point_SSI_G1000_0_17","panel_SSI_x_title"]:
  item=by_id[ident]
  states.append({"id":ident,"position":[item.pos().x(),item.pos().y()],"rect":[item.rect().x(),item.rect().y(),item.rect().width(),item.rect().height()],"visible":item.isVisible(),"opacity":item.opacity(),"exclude":item.excludeFromExports(),"z":item.zValue(),"parent":str(item.parentItem()),"text":item.text() if isinstance(item,QgsLayoutItemLabel) else None})
 (QA/"figure6_native_object_states.json").write_text(json.dumps(states,ensure_ascii=False,indent=2),encoding="utf8")
 nativeout=Path("D:/ER219_work/figure6_exports/fig6_reopened.png")
 export=QgsLayoutExporter(layout);settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=300
 assert export.exportToImage(str(nativeout),settings)==QgsLayoutExporter.Success
 shutil.copy2(nativeout,QA/"figure6_native_reopened.png")
 shutil.copy2(nativeout,QA/"figure6_native_verified_final.png")
 previews=[]
 for display_dpi in [96,150]:
  preview_settings=QgsLayoutExporter.ImageExportSettings();preview_settings.dpi=display_dpi*146.4/210
  preview_path=Path("D:/ER219_work/figure6_exports")/("fig6_print146_4mm_"+str(display_dpi)+"dpi.png")
  assert export.exportToImage(str(preview_path),preview_settings)==QgsLayoutExporter.Success
  destination=QA/("figure6_print146_4mm_"+str(display_dpi)+"dpi.png");shutil.copy2(preview_path,destination)
  previews.append(str(destination.relative_to(ROOT)))
 typography={"status":"NATIVE_FONT_AND_TEXT_BOX_CHECK_PASS_VISUAL_PENDING","native_min_font_pt":min(x["native_font_pt"] for x in font_checks),
 "minimum_font_at_target_width_pt":min(x["font_at_146_4mm_pt"] for x in font_checks),"target_width_mm":146.4,"label_checks":font_checks,
 "point_csv_byte_identical_to_previous":True,"input_data_and_stats_hashes_unchanged":True,"axes_palette_alpha_unchanged":True,"native_print_size_previews":previews}
 (QA/"figure6_typography_QA.json").write_text(json.dumps(typography,ensure_ascii=False,indent=2),encoding="utf8")
 if repair:
  exportdir=Path("D:/ER219_work/figure6_exports")
  pdf=QgsLayoutExporter.PdfExportSettings();pdf.dpi=300;pdf.forceVectorOutput=True
  assert export.exportToPdf(str(exportdir/"fig6_repaired.pdf"),pdf)==QgsLayoutExporter.Success
  svg=QgsLayoutExporter.SvgExportSettings();svg.dpi=300;svg.exportAsLayers=True
  assert export.exportToSvg(str(exportdir/"fig6_repaired.svg"),svg)==QgsLayoutExporter.Success
  destinations=[]
  for ext,path in [("png",nativeout),("pdf",exportdir/"fig6_repaired.pdf"),("svg",exportdir/"fig6_repaired.svg")]:
   destination=ROOT/"04_图件"/("图6_灰绿配置与热环境."+ext);shutil.copy2(path,destination)
   destinations.append({"path":str(destination.relative_to(ROOT)),"bytes":destination.stat().st_size,"sha256":hashlib.sha256(destination.read_bytes()).hexdigest()})
  source_receipt=json.loads((QA/"figure6_native_receipt.json").read_text(encoding="utf8"))
  source_receipt["exports"]=destinations
  source_receipt["native_order_repair"]="Ungrouped native items; page=-1000, matrix fills=2, lines=10, points=20, labels=100. Resaved and exported through QGIS."
  (QA/"figure6_native_receipt.json").write_text(json.dumps(source_receipt,ensure_ascii=False,indent=2),encoding="utf8")
 record={"status":"LAYOUT_REPAIRED_NEEDS_INDEPENDENT_REOPEN" if repair else "NATIVE_PROJECT_REOPEN_AND_POINT_CHECK_PASSED","engine":Qgis.QGIS_VERSION,
 "source_tables_valid":True,"source_table_rows":sorted(l.featureCount() for l in layers),"point_count":len(ids),
 "maximum_point_coordinate_error_mm":max(errors),"coordinate_tolerance_mm":0.000501,
 "tolerance_basis":"QGIS six-significant-digit layout-position serialization; below 0.006 pixel at 300 dpi", "native_reexport":str((QA/"figure6_native_reopened.png").relative_to(ROOT)),
 "visual_review":"pending manual whole-figure inspection"}
 (QA/"figure6_native_reopen_QA.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf8")
 print("FIGURE6_NATIVE_REOPEN_PASS",flush=True)
validate()
QgsProject.instance().clear();gc.collect();app.exitQgis()
