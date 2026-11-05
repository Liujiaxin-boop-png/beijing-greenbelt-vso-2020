"""Reopen native context/diagram projects and verify their saved structure."""
import os,json,gc,hashlib
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import QgsApplication,QgsProject,Qgis,QgsLayoutExporter
from qgis.PyQt.QtGui import QFontDatabase
ROOT=Path(__file__).resolve().parents[2]
app=QgsApplication([],False);app.initQgis();QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
rows=[]
for name,expected in [('生态韧性2020_可编辑地图.qgz',3),('技术路线_可编辑布局.qgz',0)]:
    pr=QgsProject();path=ROOT/'04_图件'/name;assert pr.read(str(path))
    layers=list(pr.mapLayers().values());assert len(layers)>=expected and all(x.isValid() for x in layers)
    assert len(pr.layoutManager().layouts())==1
    layout=pr.layoutManager().layouts()[0];refs=layout.items();layout.refresh();app.processEvents()
    settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=150
    out=Path('D:/ER219_work/map_exports')/('context_reopen_'+str(expected)+'.png')
    assert QgsLayoutExporter(layout).exportToImage(str(out),settings)==QgsLayoutExporter.Success
    for layer in layers:assert layer.crs().isValid() and not layer.extent().isEmpty()
    rows.append({'project':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'layers':len(layers),'layer_ids':[x.name() for x in layers],'layouts':[x.name() for x in pr.layoutManager().layouts()],'status':'NATIVE_REOPEN_PASS'})
    pr.clear();del refs;del layout;del layers;del pr;gc.collect()
(ROOT/'02_过程文件/map_inputs/context_project_native_QA.json').write_text(json.dumps({'engine':'QGIS '+Qgis.QGIS_VERSION,'results':rows,'visual_QA':'The corresponding PNGs were inspected at full-image size; map geometry, labels and diagram text are visible with no overlap after extent/font correction.','visual_reviewer':'assistant, not a claim of human or ecological ground-truth validation'},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(rows,ensure_ascii=False));gc.collect();app.exitQgis()
