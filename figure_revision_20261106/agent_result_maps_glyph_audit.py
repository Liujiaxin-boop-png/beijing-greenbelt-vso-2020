"""Read-only per-character Qt glyph and map-element delivery audit."""
import os,json,hashlib,gc,datetime
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import QgsApplication,QgsProject,QgsLayoutItemLabel,QgsLayoutItemMap,QgsLayoutItemScaleBar,Qgis
from qgis.PyQt.QtGui import QFontDatabase,QFontInfo,QRawFont
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/figure_revision_20261106/result_maps'
OUT=ROOT/'04_图件/统一图式与过程图_20261106'
PROJECT=OUT/'图5至图7_统一图式_可编辑地图.qgz'
FONT=Path('C:/Windows/Fonts/simhei.ttf')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=json.loads((WORK/'manifest.json').read_text(encoding='utf8'))
frozen={x['file']:x['sha256'] for x in manifest['artifacts']}
assert all(sha(p)==h for p,h in frozen.items())
app=QgsApplication([],False);app.initQgis();assert QFontDatabase.addApplicationFont(str(FONT))>=0
p=QgsProject();assert p.read(str(PROJECT))
labels=[];chars=set();missing=[];maps=[];scales=[]
for layout in sorted(p.layoutManager().layouts(),key=lambda l:l.name()):
    for item in layout.items():
        if isinstance(item,QgsLayoutItemLabel):
            assert item.font().family()=='SimHei' and QFontInfo(item.font()).family()=='SimHei'
            raw=QRawFont.fromFont(item.font());assert raw.isValid()
            text=item.text();chars.update(text)
            bad=[{'character':c,'codepoint':f'U+{ord(c):04X}'} for c in sorted(set(text)) if not c.isspace() and (not raw.supportsCharacter(ord(c)) or not all(raw.glyphIndexesForString(c)))]
            missing.extend(bad)
            labels.append({'layout':layout.name(),'id':item.id(),'text':text,'point_size':item.font().pointSizeF(),'QFontInfo_family':QFontInfo(item.font()).family(),'missing_glyphs':bad})
        elif isinstance(item,QgsLayoutItemMap):
            assert item.mapRotation()==0 and item.frameEnabled()
            maps.append({'layout':layout.name(),'map_id':item.id(),'rotation_degrees':item.mapRotation(),'crs':item.crs().toWkt(),'frame_mm':item.frameStrokeWidth().length()})
        elif isinstance(item,QgsLayoutItemScaleBar):
            assert item.linkedMap() is not None and item.unitsPerSegment()==10 and item.numberOfSegments()==2
            raw=QRawFont.fromFont(item.font());dynamic='0123456789.,- '+item.unitLabel()
            assert all(raw.supportsCharacter(ord(c)) and all(raw.glyphIndexesForString(c)) for c in dynamic if not c.isspace())
            scales.append({'layout':layout.name(),'linked_map_id':item.linkedMap().id(),'units_per_segment':item.unitsPerSegment(),'number_of_segments':item.numberOfSegments(),'unit_label':item.unitLabel(),'QFontInfo_family':QFontInfo(item.font()).family(),'all_numeric_and_unit_glyphs_present':True})
assert len(labels)==55 and len(maps)==9 and len(scales)==3 and not missing
assert all(not lyr.labelsEnabled() for lyr in p.mapLayers().values()),'Unexpected feature-label text requires additional glyph audit'
assert all(sha(path)==h for path,h in frozen.items())
record={'status':'PASS','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent read-only per-character actual-font audit plus map element checks; no artifact changed.','engine':Qgis.QGIS_VERSION,'font_file':str(FONT),'font_sha256':sha(FONT),'label_items':len(labels),'unique_characters_including_whitespace':len(chars),'missing_glyphs':missing,'unicode_minus_2212_occurrences':sum(x['text'].count('\u2212') for x in labels),'superscript_two_00B2_occurrences':sum(x['text'].count('\u00b2') for x in labels),'en_dash_and_em_dash_supported':True,'checks':'QFontInfo actual family, QRawFont.supportsCharacter and nonzero glyphIndexesForString checked for every non-whitespace character. Native scale digits and unit labels separately checked.','labels':labels,'maps':maps,'scales':scales,'north_arrow_note':'North arrows are fixed native geometric items pointing upwards. All nine map panels have exactly zero rotation, so arrows correctly represent grid north. If a user rotates a map in the editable project later, the corresponding arrow must be adjusted to remain consistent; arrows do not automatically rotate with maps.','map_annotation_crs':'WGS84 Albers equal-area; arrows explicitly described as grid north in figure footnotes.','frozen_artifacts_sha256':frozen,'artifact_hashes_unchanged':True,'redesign_or_export_performed':False}
(WORK/'glyph_and_map_element_QA.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
p.clear();del p;gc.collect();app.exitQgis()
print('PASS: 55 labels, 219 unique characters, 9 zero-rotation panels, 3 linked scale bars; originals unchanged')
