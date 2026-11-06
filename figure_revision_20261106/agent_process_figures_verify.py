"""Read-only native reopen, data-field and artifact QA for process figures."""
import os,json,csv,math,hashlib,gc,zipfile,subprocess
from pathlib import Path
from xml.etree import ElementTree as ET
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QFontDatabase,QImage,QPainter,QColor
from qgis.PyQt.QtCore import QSize,Qt
from qgis.PyQt.QtSvg import QSvgRenderer
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/figure_revision_20261106'
OUT=ROOT/'04_图件/统一图式与过程图_20261106'
ASCII=Path(r'D:\ER219_work\figure_revision_20261106\exports_process')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((WORK/'process_figures_data_manifest.json').read_text(encoding='utf-8'))
assert all(sha(Path(p))==h for p,h in meta['input_sha256'].items())
assert sha(Path(meta['output_gpkg']))==meta['output_sha256']
rows={}
with (ROOT/'03_结果文件/evaluation/scores_classified.csv').open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        if r['scenario']=='baseline' and r['product']=='clcd' and float(r['scale_m'])==1000:
            key=(r['habitat'],r['grid_id']);assert key not in rows;rows[key]=r
fields=['HQ_H','NTL','CLUMPY','MCR','SSI','E_fraction','V_score','S_score','O_score']
app=QgsApplication([],False);app.initQgis();assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/simhei.ttf')>=0
receipts=[]
def run(kind,stem,nmaps):
    p=QgsProject.instance();p.clear();qgz=OUT/(stem+'_可编辑.qgz');assert p.read(str(qgz))
    assert all(l.isValid() for l in p.mapLayers().values())
    lay=p.layoutManager().layouts()[0];maps=[i for i in lay.items() if isinstance(i,QgsLayoutItemMap)]
    labels=[i for i in lay.items() if isinstance(i,QgsLayoutItemLabel)]
    assert len(maps)==nmaps
    assert all(i.font().family()=='SimHei' and i.font().pointSizeF()>=10 for i in labels)
    assert any(i.text()=='N' for i in labels)
    assert all(m.mapRotation()==0 for m in maps)
    assert len([i for i in lay.items() if isinstance(i,QgsLayoutItemScaleBar)])==1
    checked=set();data_checks=[]
    for layer in p.mapLayers().values():
        if layer.fields().indexFromName('baseline_valid')<0:continue
        habitat=layer.source().split('layername=')[-1]
        if habitat in checked:continue
        checked.add(habitat);valid=0;nulls=0
        for ft in layer.getFeatures():
            key=(habitat,str(ft['grid_id']))
            if ft['baseline_valid']==1:
                valid+=1;assert key in rows
                for field in fields:
                    assert float(ft[field])==float(rows[key][field]),(key,field,ft[field],rows[key][field])
                for field in ['V_score','S_score','O_score']:
                    assert float(ft['display_'+field])==float(ft[field])
                if habitat=='forest_shrub':
                    for spec in meta['raw_specs']:
                        v=float(ft[spec['field']]);lo=spec['display_min_raw'];hi=spec['display_max_raw']
                        if spec['display_transform']=='log10_1p':want=(math.log10(1+v)-math.log10(1+lo))/(math.log10(1+hi)-math.log10(1+lo))
                        else:want=(v-lo)/(hi-lo)
                        assert abs(float(ft[spec['color_field']])-want)<1e-13
            else:
                nulls+=1;assert key not in rows
                for field in fields:assert QgsVariantUtils.isNull(ft[field]),(key,field,ft[field])
        assert valid=={'forest_shrub':840,'grassland':153,'water_wetland':532}[habitat]
        data_checks.append({'habitat':habitat,'valid_n':valid,'missing_n':nulls,'exact_raw_fields_checked':fields,'display_fields_match':True})
    with zipfile.ZipFile(qgz) as z:
        xml=ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.qgs'))))
        ds=[el.text for el in xml.findall('.//projectlayers/maplayer/datasource')]
        assert all(s.startswith('../../') for s in ds),ds
    ex=QgsLayoutExporter(lay);st=QgsLayoutExporter.ImageExportSettings();st.dpi=150
    preview=ASCII/(kind+'_reopened.png');assert ex.exportToImage(str(preview),st)==QgsLayoutExporter.Success
    im=QImage(str(preview));assert not im.isNull();png=QImage(str(OUT/(stem+'.png')));assert png.width()>4000 and png.height()>6000
    subprocess.run(['C:/Users/LJX/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe','-r','150','-png','-singlefile',str(ASCII/('fig3.pdf' if kind=='raw' else 'fig4.pdf')),str(ASCII/(kind+'_pdf'))],check=True)
    assert not QImage(str(ASCII/(kind+'_pdf.png'))).isNull()
    svg=QSvgRenderer(str(OUT/(stem+'.svg')));assert svg.isValid()
    simg=QImage(1122,1583,QImage.Format_ARGB32);simg.fill(Qt.white);painter=QPainter(simg);svg.render(painter);painter.end();assert simg.save(str(ASCII/(kind+'_svg.png')))
    ms=QgsMapSettings();vis=[node.layer() for node in p.layerTreeRoot().findLayers() if node.itemVisibilityChecked()];ms.setLayers(vis);ms.setDestinationCrs(p.crs());ms.setExtent(p.viewSettings().defaultViewExtent());ms.setOutputSize(QSize(900,900));ms.setBackgroundColor(QColor('white'))
    job=QgsMapRendererParallelJob(ms);job.start();job.waitForFinished();assert job.renderedImage().save(str(ASCII/(kind+'_default_canvas.png')))
    rec={'status':'NATIVE_REOPEN_AND_VALUES_PASS_VISUAL_PENDING','kind':kind,'qgz_sha256':sha(qgz),'native_qgis':Qgis.QGIS_VERSION,'map_n':len(maps),'relative_data_sources':ds,'actual_saved_fonts':sorted(set((i.font().family(),i.font().pointSizeF()) for i in labels)),'data_checks':data_checks,'png_pixels':[png.width(),png.height()],'previews':[str(preview),str(ASCII/(kind+'_svg.png')),str(ASCII/(kind+'_default_canvas.png'))]}
    receipts.append(rec);p.clear();gc.collect()
for args in [('raw','图3_六项原始指标空间分布',6),('dimensions','图4_三维得分空间分解',9)]:run(*args)
(WORK/'process_figures_independent_reopen_QA.json').write_text(json.dumps({'status':'NATIVE_REOPEN_AND_VALUES_PASS_VISUAL_PENDING','source_hashes_unchanged':True,'figures':receipts},ensure_ascii=False,indent=2),encoding='utf-8')
print('INDEPENDENT_REOPEN_AND_FIELDS_PASS',flush=True)
QgsProject.instance().clear();gc.collect();app.exitQgis()
