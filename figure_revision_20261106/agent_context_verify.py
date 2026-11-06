"""Independent native reopen, scientific-content checks and preview of context figures."""
import os,json,hashlib,csv,gc,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QFont,QFontInfo,QFontDatabase,QRawFont
WORK=Path('D:/ER219_work/figure_revision_20261106');OUT=Path('D:/ER219_figures/统一图式与过程图_20261106')
app=QgsApplication([],False);app.initQgis();assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/simhei.ttf')>=0
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readcsv(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
keys=['图1_研究范围与土地覆盖','图2_研究技术路线','图8_灰绿配置与热环境','图S1_四项原始指标空间分布']
reports=[]
for no,key in enumerate(keys):
 if len(sys.argv)>1 and str(no+1) not in sys.argv[1:]:continue
 manifest=json.loads((WORK/(key+'_manifest.json')).read_text(encoding='utf8'))
 assert sha(manifest['old_project'])==manifest['old_project_sha256']
 for source in manifest['frozen_inputs']:assert sha(source['path'])==source['sha256']
 p=QgsProject();assert p.read(str((OUT/(key+'.qgz')).resolve()))
 layers=list(p.mapLayers().values());assert all(l.isValid() for l in layers)
 layouts=p.layoutManager().layouts();assert len(layouts)==1;layout=layouts[0];items=layout.items()
 labels=[i for i in items if isinstance(i,QgsLayoutItemLabel)];maps=[i for i in items if isinstance(i,QgsLayoutItemMap)];scales=[i for i in items if isinstance(i,QgsLayoutItemScaleBar)]
 assert len(labels)==len(manifest['labels']);fonts=[{'text':i.text(),'family':QFontInfo(i.font()).family(),'pt':i.font().pointSizeF(),'bold':i.font().bold()} for i in labels]
 assert all(x['family']=='SimHei' and x['pt']>=10 and not x['bold'] for x in fonts)
 raw=QRawFont.fromFont(QFont('SimHei',10));missing=sorted({c for x in fonts for c in x['text'] if not c.isspace() and not raw.supportsCharacter(ord(c))});assert not missing,missing
 assert all(m.frameEnabled() and m.mapRotation()==0 for m in maps)
 for scale in scales:assert scale.linkedMap() in maps and scale.unitsPerSegment()==10 and scale.numberOfSegments()==2 and QFontInfo(scale.font()).family()=='SimHei'
 checks={}
 if no==0:
  assert len(maps)==1 and len(scales)==1 and len(layers)==3
  raster=next(l for l in layers if isinstance(l,QgsRasterLayer));assert raster.renderer().type()=='paletted'
  checks={'same_landcover_classes':[int(c.value) for c in raster.renderer().classes()],'original_map_layers_preserved':True}
 if no==1:
  assert not maps and not scales;assert len(layers)==0
  text='\n'.join(x['text'] for x in fonts)
  assert all(k in text for k in ['HQ','NTL','CLUMPY','MCR','SSI','E/(E+C)'])
  checks={'six_original_indices_present':True,'no_cartographic_scale_on_nonmap':True}
 if no==2:
  assert not maps and not scales
  pointitems={i.id():i for i in items if isinstance(i,QgsLayoutItemShape) and i.id().startswith('point_')};data=readcsv(WORK/'图8_native_points.csv');assert len(pointitems)==len(data)==2536
  original={r['Grid_ID']:r for r in readcsv('D:/ER219_results/thermal_association/LC08_L2SP_123032_20200803_02_T1_scatter_real_grid_values.csv')}
  errors=[];error_details=[]
  for row in data:
   assert float(row['x_value'])==float(original[row['Grid_ID']][row['panel']]) and float(row['LST_C'])==float(original[row['Grid_ID']]['LST_mean_C'])
   it=pointitems['point_'+row['panel']+'_'+row['Grid_ID']];xy=it.positionWithUnits();sz=it.sizeWithUnits()
   err=max(abs(xy.x()+sz.width()/2-float(row['layout_x_mm'])),abs(xy.y()+sz.height()/2-float(row['layout_y_mm'])));errors.append(err)
   if err>1e-8:error_details.append({'id':it.id(),'actual_mm':[xy.x(),xy.y(),sz.width(),sz.height()],'expected_center_mm':[float(row['layout_x_mm']),float(row['layout_y_mm'])],'error_mm':err})
  (WORK/'thermal_native_coordinate_diagnostic.json').write_text(json.dumps({'max_error':max(errors),'failures':error_details[:20]},ensure_ascii=False,indent=2),encoding='utf8')
  # QGIS 3.28 stores layout position as six significant digits in native QGS.
  # At positions >=100 mm this rounds by at most 0.0005 mm (0.012 pixel at 600 dpi).
  # Numerical source values above are compared exactly and are never rounded.
  assert max(errors)<=0.0005001
  stats=readcsv('D:/ER219_results/thermal_association/graygreen_LST_spearman_descriptive.csv');lookup={(r['domain'],r['predictor']):r for r in stats if r['date']=='20200803'}
  for q in ['ALL','NW','NE','SW','SE']:
   for field in ['SSI','E_fraction']:
    rho=float(lookup[(q,field)]['spearman_rho']);expected=('-' if rho<0 else '')+format(abs(rho),'.3f');actual=layout.itemById('rho_'+q+'_'+field).text();assert expected in actual
  checks={'actual_native_points':2536,'points_per_panel':1268,'source_xy_values_exact':True,'maximum_native_coordinate_difference_mm':max(errors),'native_position_precision':'QGIS six significant decimal digits; maximum 0.0005 mm rounding, less than 0.012 pixel at 600 dpi','all_10_rho_labels_match_frozen_stats':True,'axes':[0,1000,0,1,30,50],'no_geographic_scale_on_scatter':True}
 if no==3:
  assert len(maps)==8 and len(scales)==1 and len(layers)==9;assert len({m.extent().toString() for m in maps})==1
  values={r['grid_id']:r for r in readcsv('D:/ER219_work/map_inputs_s1/S1_raw_indicator_values.csv')};checks={'fields':[]}
  for panel in manifest['scientific_preservation']['panels']:
   field=panel['field'];lyr=p.mapLayer(panel['layer_id']);count=0;missing_count=0
   for feat in lyr.getFeatures():
    expected=values[feat['grid_id']][field];actual=feat[field]
    if expected=='':assert actual is None or actual==NULL;missing_count+=1
    else:assert abs(float(expected)-float(actual))<1e-10
    count+=1
   assert count==2478;checks['fields'].append({'field':field,'count':count,'NA':missing_count,'source_values_identical':True})
 preview=WORK/'exports_ctx'/('reopened_'+str(no+1)+'.png');settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=180
 assert QgsLayoutExporter(layout).exportToImage(str(preview),settings)==QgsLayoutExporter.Success
 result={'figure':key,'status':'NATIVE_REOPEN_SCIENCE_FONTS_PASS_VISUAL_PENDING','engine':Qgis.QGIS_VERSION,'project_sha256':sha(OUT/(key+'.qgz')),'valid_layers':len(layers),'map_count':len(maps),'scale_count':len(scales),'font_glyphs_all_supported':True,'font_roles':sorted(set((x['family'],x['pt']) for x in fonts)),'checks':checks,'reopened_preview':str(preview),'preview_sha256':sha(preview)}
 (WORK/(key+'_native_QA.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');reports.append(result);print('NATIVE_QA_PASS',key,flush=True)
 p.clear();del items,labels,maps,scales,layouts,layout,layers,p;gc.collect()
app.exitQgis()
