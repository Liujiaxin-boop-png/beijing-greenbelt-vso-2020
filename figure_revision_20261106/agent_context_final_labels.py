"""Native post-layout label normalization; scientific points/renderers remain unchanged."""
import os,json,re,hashlib,shutil,gc
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QFontDatabase
W=Path('D:/ER219_work/figure_revision_20261106');O=Path('D:/ER219_figures/统一图式与过程图_20261106');T=W/'exports_ctx'
app=QgsApplication([],False);app.initQgis();assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/simhei.ttf')>=0
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for key,short in [('图8_灰绿配置与热环境','fig8'),('图S1_四项原始指标空间分布','figS1')]:
 path=O/(key+'.qgz');p=QgsProject();assert p.read(str(path.resolve()));lay=p.layoutManager().layouts()[0]
 mpath=W/(key+'_manifest.json');m=json.loads(mpath.read_text(encoding='utf8'));changes=[]
 for item in lay.items():
  if isinstance(item,QgsLayoutItemLabel):
   before=item.text();after=re.sub(r'^([a-h])\s{2,}',r'(\1)  ',before)
   if before!=after:item.setText(after);changes.append({'old':before,'new':after})
 for label in m['labels']:label['text']=re.sub(r'^([a-h])\s{2,}',r'(\1)  ',label['text'])
 assert len(changes)==(3 if short=='fig8' else 8),changes
 assert p.write(str(path.resolve()));m['new_project_sha256']=sha(path);m['panel_labels_normalized']=changes
 exp=QgsLayoutExporter(lay);exports=[]
 for suffix,setting,fn in [('png',QgsLayoutExporter.ImageExportSettings(),exp.exportToImage),('pdf',QgsLayoutExporter.PdfExportSettings(),exp.exportToPdf),('svg',QgsLayoutExporter.SvgExportSettings(),exp.exportToSvg)]:
  setting.dpi=600
  if suffix=='pdf':setting.forceVectorOutput=True
  if suffix=='svg':setting.exportAsLayers=True
  native=T/(short+'_final.'+suffix);assert fn(str(native),setting)==QgsLayoutExporter.Success and native.stat().st_size>1000
  dest=O/(key+'.'+suffix);shutil.copy2(native,dest);assert sha(native)==sha(dest)
  exports.append({'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size})
 m['exports']=exports;preview=T/(short+'_final_preview.png');s=QgsLayoutExporter.ImageExportSettings();s.dpi=180
 assert exp.exportToImage(str(preview),s)==QgsLayoutExporter.Success
 shutil.copy2(preview,Path(m['preview']));mpath.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
 print('PANEL_LABELS_FINAL',key,flush=True);p.clear();del lay,p;gc.collect()
app.exitQgis()
