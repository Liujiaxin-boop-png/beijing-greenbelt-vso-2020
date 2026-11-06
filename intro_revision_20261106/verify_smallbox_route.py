"""Native reopen and content/font validation of the three-column workflow."""
import os,json,hashlib,gc
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QFontDatabase,QFontInfo,QRawFont,QFont,QImage
W=Path('D:/ER219_work/intro_revision_20261106');M=W/'route_smallbox_manifest.json';m=json.loads(M.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
app=QgsApplication([],False);app.initQgis();assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/simhei.ttf')>=0
p=QgsProject();assert p.read(str(Path(m['project']).resolve()));assert len(p.mapLayers())==0
assert len(p.layoutManager().layouts())==1
layout=p.layoutManager().layouts()[0];items=layout.items();labels=[x for x in items if isinstance(x,QgsLayoutItemLabel)]
assert not any(isinstance(x,(QgsLayoutItemMap,QgsLayoutItemScaleBar)) for x in items)
assert len(labels)==len(m['labels']);font_records=[];raw=QRawFont.fromFont(QFont('SimHei',10))
for label in labels:
 f=label.font();assert QFontInfo(f).family()=='SimHei' and f.pointSizeF()>=10 and not f.bold()
 assert all(raw.supportsCharacter(ord(c)) for c in label.text() if not c.isspace())
 font_records.append({'text':label.text(),'family':QFontInfo(f).family(),'pt':f.pointSizeF()})
text='\n'.join(x['text'] for x in font_records)
assert layout.itemById('method2_1_text').text()=='分生境标准化'
for token in ['研究目标','研究过程','研究方法','V 脆弱性','S 敏感性','O 自组织','HQ','NTL','CLUMPY','MCR','SSI','E/(E+C)','1 km正方形','林灌 / 草地 / 水体湿地分别评价','六项均有效','固定标准化','熵权加权','500 m尺度','成对有效格网对照','七方案均有效格网','乡镇加权统计','温度仅作辅助，不进入综合指数']:
 assert token in text,token
assert all(token not in text for token in ['访谈','问卷','Citespace','社会韧性'])
for path,digest in m['frozen_source_hashes'].items():assert sha(path)==digest
for export in m['exports']:
 assert sha(export['path'])==export['sha256'];header=Path(export['path']).read_bytes()[:8]
 if export['path'].endswith('.png'):assert header==b'\x89PNG\r\n\x1a\n'
 if export['path'].endswith('.pdf'):assert header.startswith(b'%PDF-')
png=next(x['path'] for x in m['exports'] if x['path'].endswith('.png'));image=QImage(png);assert not image.isNull()
dpi=image.dotsPerMeterX()*.0254;assert abs(dpi-600)<.1
assert abs(image.width()-190/25.4*600)<2 and abs(image.height()-270/25.4*600)<2
preview=W/'exports_route/route_smallbox_native_reopened.png';setting=QgsLayoutExporter.ImageExportSettings();setting.dpi=180
assert QgsLayoutExporter(layout).exportToImage(str(preview),setting)==QgsLayoutExporter.Success
record={'status':'NATIVE_REOPEN_CONTENT_FONTS_PASS_VISUAL_PENDING','engine':Qgis.QGIS_VERSION,'project_sha256':sha(m['project']),'native_label_count':len(labels),'fonts':font_records,'all_glyphs_supported':True,'PNG_dimensions':[image.width(),image.height()],'PNG_dpi':dpi,'minimum_font_in_Word_pt':10*146.4/190,'original_QGZ_and_reference_image_unchanged':True,'scientific_content_checks':'All six indicators, VSO, independent habitats,1km/500m,entropy,pairwise/common-domain distinction, township,LST auxiliary passed; no reference social-resilience content copied.','native_reopened_preview':str(preview),'native_reopened_preview_sha256':sha(preview)}
(W/'route_smallbox_native_QA.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print('SMALLBOX_NATIVE_QA_PASS',flush=True)
p.clear();gc.collect();app.exitQgis()
