"""Restyle four frozen figures with native QGIS 3.28; no scientific recalculation."""
import os,json,csv,gc,hashlib,math,sys,shutil,re
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QColor,QFont,QFontInfo,QFontDatabase,QPolygonF,QRawFont
from qgis.PyQt.QtCore import Qt,QPointF

CODE=Path('D:/ER219_code/figure_revision_20261106')
WORK=Path('D:/ER219_work/figure_revision_20261106');WORK.mkdir(exist_ok=True)
OUT=Path('D:/ER219_figures/统一图式与过程图_20261106');OUT.mkdir(exist_ok=True)
OLD=Path('D:/ER219_figures');W=Path('D:/ER219_work');R=Path('D:/ER219_results')
STYLE=json.loads((CODE/'figure_style.json').read_text(encoding='utf8'))
FONT=STYLE['font_family'];SIZES=STYLE['sizes_pt'];TEXT=STYLE['text_color'];FRAME=STYLE['frame']['color']
app=QgsApplication([],False);app.initQgis()
assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/simhei.ttf')>=0
assert QFontInfo(QFont(FONT)).family()==FONT,QFontInfo(QFont(FONT)).family()

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readcsv(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writejson(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def font(role):
 f=QFont(FONT);f.setPointSizeF(SIZES[role]);f.setBold(False);return f
def sources(project):
 return [{'name':l.name(),'source':l.source(),'valid':l.isValid(),'count':l.featureCount() if isinstance(l,QgsVectorLayer) else None} for l in project.mapLayers().values()]

class Figure:
 def __init__(self,key,title,height,old):
  self.key=key;self.title=title;self.old=OLD/old;self.old_hash=digest(self.old)
  self.project=QgsProject();assert self.project.read(str(self.old.resolve()))
  self.original_sources=sources(self.project);assert all(x['valid'] for x in self.original_sources)
  self.old_layouts=[{'name':l.name(),'items':len(l.items())} for l in self.project.layoutManager().layouts()]
  self.old_maps={}
  for layout in self.project.layoutManager().layouts():
   for item in layout.items():
    if isinstance(item,QgsLayoutItemMap):self.old_maps[item.id()]=[l.id() for l in item.layers()]
  for layout in list(self.project.layoutManager().layouts()):self.project.layoutManager().removeLayout(layout)
  self.project.setFilePathStorage(Qgis.FilePathType.Relative)
  self.layout=QgsPrintLayout(self.project);self.layout.initializeDefaults();self.layout.setName(title)
  self.layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(190,height));self.height=height
  self.refs=[];self.labels=[];self.maps=[];self.scale_refs=[];self.science={};self.input_paths=[]
  self.rect(2,2,186,height-4,'255,255,255,0',FRAME,.22,'neatline',-50)
 def label(self,text,x,y,w,h,role='map_label',align=Qt.AlignLeft,color=None,id=None):
  text=text.replace('−','-')  # SimHei does not contain Unicode mathematical minus; retain the sign using ASCII.
  text=re.sub(r'^([a-h])\s{2,}',r'(\1)  ',text)
  item=QgsLayoutItemLabel(self.layout);item.setText(text);item.setFont(font(role));item.setFontColor(QColor(color or TEXT))
  item.setMargin(0);item.setHAlign(align);item.setVAlign(Qt.AlignVCenter)
  self.layout.addLayoutItem(item);item.attemptMove(QgsLayoutPoint(x,y));item.attemptResize(QgsLayoutSize(w,h));item.setZValue(100)
  if id:item.setId(id)
  self.refs.append(item);self.labels.append({'text':text,'role':role,'font_pt':SIZES[role],'actual_font':QFontInfo(item.font()).family(),'position_mm':[x,y,w,h],'id':id})
  assert x>=0 and y>=0 and x+w<=190.01 and y+h<=self.height+.01,(text,x,y,w,h)
  return item
 def rect(self,x,y,w,h,fill,border=None,width=.22,id=None,z=2,ellipse=False):
  i=QgsLayoutItemShape(self.layout);i.setShapeType(QgsLayoutItemShape.Ellipse if ellipse else QgsLayoutItemShape.Rectangle)
  cfg={'color':fill,'outline_color':border or FRAME,'outline_width':str(width),'joinstyle':'miter'}
  if border is None:cfg['outline_style']='no'
  i.setSymbol(QgsFillSymbol.createSimple(cfg));self.layout.addLayoutItem(i);i.attemptMove(QgsLayoutPoint(x,y));i.attemptResize(QgsLayoutSize(w,h));i.setZValue(z)
  if id:i.setId(id)
  self.refs.append(i);return i
 def line(self,x1,y1,x2,y2,color=None,width=.22,z=10):
  i=QgsLayoutItemPolyline(QPolygonF([QPointF(x1,y1),QPointF(x2,y2)]),self.layout)
  i.setSymbol(QgsLineSymbol.createSimple({'line_color':color or FRAME,'line_width':str(width),'line_width_unit':'MM'}));self.layout.addLayoutItem(i);i.setZValue(z);self.refs.append(i);return i
 def north(self,x,y):
  self.label('N',x-3,y-1,7,5,'axis_tick',Qt.AlignHCenter)
  self.line(x+.5,y+5,x+.5,y+12,FRAME,.3,50)
  p=QgsLayoutItemPolygon(QPolygonF([QPointF(x+.5,y+4),QPointF(x-1.2,y+7),QPointF(x+2.2,y+7)]),self.layout)
  p.setSymbol(QgsFillSymbol.createSimple({'color':FRAME,'outline_style':'no'}));self.layout.addLayoutItem(p);p.setZValue(50);self.refs.append(p)
 def map(self,x,y,w,h,layers,scope,id):
  mp=QgsLayoutItemMap(self.layout);self.layout.addLayoutItem(mp);mp.attemptMove(QgsLayoutPoint(x,y));mp.attemptResize(QgsLayoutSize(w,h))
  mp.setCrs(scope.crs());mp.setLayers(layers);mp.setKeepLayerSet(True);mp.setKeepLayerStyles(True)
  ex=QgsRectangle(scope.extent());ex.scale(1.045);cx,cy=ex.center().x(),ex.center().y()
  ew=max(ex.width(),ex.height()*w/h);eh=ew*h/w;mp.setExtent(QgsRectangle(cx-ew/2,cy-eh/2,cx+ew/2,cy+eh/2))
  mp.setFrameEnabled(True);mp.setFrameStrokeColor(QColor(FRAME));mp.setFrameStrokeWidth(QgsLayoutMeasurement(.22));mp.setZValue(10);mp.setId(id)
  self.refs.append(mp);self.maps.append(mp);return mp
 def scale(self,mp,x,y,segment=10):
  s=QgsLayoutItemScaleBar(self.layout);s.setStyle('Single Box');s.setLinkedMap(mp);s.setUnits(QgsUnitTypes.DistanceKilometers)
  s.setUnitsPerSegment(segment);s.setNumberOfSegments(2);s.setNumberOfSegmentsLeft(0);s.setUnitLabel('km');s.setFont(font('axis_tick'));s.setHeight(1.4)
  s.setLineWidth(.18);self.layout.addLayoutItem(s);s.attemptMove(QgsLayoutPoint(x,y));s.setZValue(60);self.refs.append(s);self.scale_refs.append(s);return s
 def save(self):
  self.project.layoutManager().addLayout(self.layout);self.layout.pageCollection().pages()[0].setZValue(-1000)
  if self.maps:self.project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(self.maps[0].extent(),self.project.crs()))
  self.layout.refresh();app.processEvents();qgz=OUT/(self.key+'.qgz');assert self.project.write(str(qgz.resolve()))
  exp=QgsLayoutExporter(self.layout);exports=[]
  temp=WORK/'exports_ctx';temp.mkdir(exist_ok=True)
  ascii_key={'图1_研究范围与土地覆盖':'fig1','图2_研究技术路线':'fig2','图8_灰绿配置与热环境':'fig8','图S1_四项原始指标空间分布':'figS1'}[self.key]
  for suffix,setting,fn in [('png',QgsLayoutExporter.ImageExportSettings(),exp.exportToImage),('pdf',QgsLayoutExporter.PdfExportSettings(),exp.exportToPdf),('svg',QgsLayoutExporter.SvgExportSettings(),exp.exportToSvg)]:
   setting.dpi=600
   if suffix=='pdf':setting.forceVectorOutput=True
   if suffix=='svg':setting.exportAsLayers=True
   path=OUT/(self.key+'.'+suffix);native=temp/(ascii_key+'.'+suffix)
   assert fn(str(native),setting)==QgsLayoutExporter.Success and native.is_file() and native.stat().st_size>1000
   signature=native.read_bytes()[:100]
   if suffix=='png':assert signature[:8]==b'\x89PNG\r\n\x1a\n'
   if suffix=='pdf':assert signature.startswith(b'%PDF-')
   if suffix=='svg':assert b'<' in signature
   shutil.copy2(native,path);assert digest(native)==digest(path)
   exports.append({'path':str(path),'sha256':digest(path),'bytes':path.stat().st_size})
  preview=WORK/(self.key+'_wordwidth_preview.png');im=QgsLayoutExporter.ImageExportSettings();im.dpi=180
  native_preview=temp/(ascii_key+'_preview.png');assert exp.exportToImage(str(native_preview),im)==QgsLayoutExporter.Success
  shutil.copy2(native_preview,preview)
  record={'status':'NATIVE_EXPORT_PENDING_REOPEN_AND_VISUAL_QA','engine':Qgis.QGIS_VERSION,'figure':self.key,'layout_mm':[190,self.height],
   'old_project':str(self.old),'old_project_sha256':self.old_hash,'old_project_unchanged':digest(self.old)==self.old_hash,'original_layers':self.original_sources,
   'new_project':str(qgz),'new_project_sha256':digest(qgz),'new_layers':sources(self.project),'all_text_font':FONT,'font_roles':SIZES,'font_bold':False,
   'font_source_sha256':digest('C:/Windows/Fonts/simhei.ttf'),'labels':self.labels,'minimum_at_word_146_4_mm_pt':min(x['font_pt'] for x in self.labels)*146.4/190,
   'maps':[{'id':m.id(),'extent':m.extent().toString(),'rotation':m.mapRotation(),'crs_wkt':m.crs().toWkt(),'frame_mm':.22} for m in self.maps],
   'scale_bars':[{'map_id':s.linkedMap().id(),'segment_km':s.unitsPerSegment(),'segments':s.numberOfSegments(),'font':QFontInfo(s.font()).family(),'font_pt':s.font().pointSizeF()} for s in self.scale_refs],
   'scientific_preservation':self.science,'frozen_inputs':[{'path':str(p),'sha256':digest(p)} for p in self.input_paths],'exports':exports,'preview':str(preview)}
  assert all(x['actual_font']==FONT for x in self.labels)
  raw=QRawFont.fromFont(font('note'));missing=sorted({ch for x in self.labels for ch in x['text'] if ch not in '\n\r\t ' and not raw.supportsCharacter(ord(ch))})
  record['unsupported_glyphs']=missing;assert not missing,missing
  writejson(WORK/(self.key+'_manifest.json'),record);print('EXPORTED',self.key,flush=True)
  return record

def study():
 f=Figure('图1_研究范围与土地覆盖','图1 研究范围与土地覆盖',235,'生态韧性2020_可编辑地图.qgz')
 ly=list(f.project.mapLayers().values());scope=next(l for l in ly if l.name()=='研究范围');towns=next(l for l in ly if l.name()=='乡镇覆盖部分');land=next(l for l in ly if isinstance(l,QgsRasterLayer))
 land.setRenderer(QgsPalettedRasterRenderer(land.dataProvider(),1,[QgsPalettedRasterRenderer.Class(int(k),QColor(v[1]),v[0]) for k,v in STYLE['palette']['landcover'].items()]))
 f.label('研究区范围与2020年土地覆盖',8,5,174,10,'figure_title')
 f.label('35个乡镇覆盖部分  |  研究区面积 1,987.900 平方千米',8,17,174,7,'map_label')
 mp=f.map(8,28,174,144,[scope,towns,land],scope,'study_map');f.north(175,31);f.scale(mp,10,174)
 f.label('土地覆盖',8,188,40,7,'legend_title')
 for i,(k,(name,c)) in enumerate(STYLE['palette']['landcover'].items()):
  x=8+(i%4)*44;y=198+(i//4)*8;f.rect(x,y+1.2,5,3.5,c);f.label(name,x+7,y,35,6,'legend_label')
 f.label('WGS 84 Albers等积投影；N为格网北。',8,217,174,6,'note')
 f.label('乡镇界仅显示研究范围内部分；该范围不等同官方绿隔规划边界。',8,224,174,6,'note')
 f.input_paths=[W/'spatial/scope.gpkg',W/'map_inputs/clcd2020_scope_display.tif']
 f.science={'same_raster_and_vector_sources':True,'no_change_to_landcover_classes_or_geometry':True,'landcover_palette_only_updated':True,'not_ecological_resilience_result':True}
 f.save();return f

def method():
 f=Figure('图2_研究技术路线','图2 研究技术路线',207,'技术路线_可编辑布局.qgz')
 f.label('生态韧性评价与乡镇管护诊断',8,5,174,10,'figure_title')
 f.label('2020年  ·  六项指标  ·  三类生境分别评价',8,17,174,7,'map_label')
 col=[('V  脆弱性相关条件','生境质量 HQ  ＋','地类、道路 → InVEST','夜间灯光 NTL  －','年度辐亮度与有效覆盖'),('S  敏感性相关条件','聚集度 CLUMPY  ＋','同类生境的局部邻接','最小累积阻力 MCR  －','至其他同类源地的成本'),('O  自组织相关条件','源汇平均距离 SSI  －','建设至最近生态空间距离','生态空间比例 E/(E+C)  ＋','生态与建设空间相对规模')]
 for n,(title,a,b,c,d) in enumerate(col):
  x=7+n*60;f.rect(x,29,56,48,'#EFF6F4','#A4BDB4',.22);f.label(title,x+2,31,52,9,'panel_title')
  for txt,y,role in [(a,43,'map_label'),(b,50,'note'),(c,60,'map_label'),(d,67,'note')]:f.label(txt,x+2,y,52,7,role)
 def arrow(y):f.line(95,y,95,y+5);f.line(93.5,y+3,95,y+5);f.line(96.5,y+3,95,y+5)
 arrow(79);f.rect(8,87,174,17,'#F4F7F6','#A4BDB4');f.label('1 km正方形格网',12,89,166,6,'panel_title',Qt.AlignHCenter);f.label('林灌、草地、水体湿地分别评价',12,97,166,6,'map_label',Qt.AlignHCenter)
 arrow(106);f.rect(8,114,174,20,'#EFF6F4','#A4BDB4');f.label('六项均有效 → 固定标准化参照 → 熵权加权',12,116,166,7,'map_label',Qt.AlignHCenter);f.label('形成三维得分与综合生态韧性指数',12,124,166,7,'map_label',Qt.AlignHCenter)
 arrow(136)
 for x,title,a,b in [(8,'空间诊断','格网短板、乡镇内部差异','同时报告有效覆盖范围'),(98,'评价稳定性检查','地类、源地、阻力、尺度','删项与权重对照')]:
  f.rect(x,144,84,28,'#F4F7F6','#A4BDB4');f.label(title,x+3,146,78,7,'panel_title');f.label(a,x+3,155,78,6,'map_label');f.label(b,x+3,163,78,6,'map_label')
 f.label('规划用途：持续低值区域核查、底图与参数核验、分类管护',8,177,174,8,'legend_title')
 f.label('＋/－表示有利方向；各类生境综合得分分别解释。',8,188,174,6,'note')
 f.label('同期地表温度用于灰绿配置的补充对照，不进入综合指数。',8,196,174,6,'note')
 f.science={'approved_six_indicators_unchanged':True,'same_flow_as_original':True,'no_new_algorithm_or_result':True,'layout_only_no_geographic_map':True}
 f.save();return f

def thermal():
 f=Figure('图8_灰绿配置与热环境','图8 灰绿配置与热环境',219,'热环境补充图.qgz')
 data=R/'thermal_association';scatter=data/'LC08_L2SP_123032_20200803_02_T1_scatter_real_grid_values.csv';stats=data/'graygreen_LST_spearman_descriptive.csv'
 points=readcsv(scatter);lookup={(x['domain'],x['predictor']):x for x in readcsv(stats) if x['date']=='20200803'};assert len(points)==1268
 f.label('灰绿配置与同期地表温度',8,5,174,10,'figure_title');f.label('2020年8月3日  ·  完整1 km方格  ·  每幅 n = 1,268',8,17,174,7,'map_label')
 cfgs=[('SSI',20,0,1000,[0,200,400,600,800,1000],'a  源汇平均距离','源汇平均距离 SSI（m）'),('E_fraction',111,0,1,[0,.2,.4,.6,.8,1],'b  生态空间比例','生态空间面积比例 E/(E+C)')]
 pa=[];pw=69;ph=61;py=47
 for key,px,xmin,xmax,ticks,title,xtitle in cfgs:
  f.label(title,px,28,pw,7,'panel_title');f.label('地表温度 LST（℃）',px,37,pw,7,'axis_title')
  rho=float(lookup[('ALL',key)]['spearman_rho']);rho_t=('−' if rho<0 else '')+format(abs(rho),'.3f')
  for yv in [30,35,40,45,50]:
   yy=py+ph-(yv-30)/20*ph;f.line(px,yy,px+pw,yy,'#DFE6E2',.12);f.line(px-1,yy,px,yy);f.label(str(yv),px-11,yy-3,8,6,'axis_tick',Qt.AlignRight)
  for xv in ticks:
   xx=px+(xv-xmin)/(xmax-xmin)*pw;f.line(xx,py+ph,xx,py+ph+1);f.label(str(xv) if key=='SSI' else format(xv,'.1f'),xx-6,py+ph+2,12,6,'axis_tick',Qt.AlignHCenter)
  f.rect(px,py,pw,ph,'255,255,255,0',FRAME,.22,'axis_frame_'+key,12)
  for row in points:
   xv,yv=float(row[key]),float(row['LST_mean_C']);assert xmin<=xv<=xmax and 30<=yv<=50
   xx=px+(xv-xmin)/(xmax-xmin)*pw;yy=py+ph-(yv-30)/20*ph
   f.rect(xx-.34,yy-.34,.68,.68,'82,127,113,100',id='point_'+key+'_'+row['Grid_ID'],z=20,ellipse=True)
   pa.append({'panel':key,'Grid_ID':row['Grid_ID'],'x_value':xv,'LST_C':yv,'layout_x_mm':xx,'layout_y_mm':yy})
  f.label('ρ = '+rho_t,px+3,py+2,pw-6,7,'legend_title',color='#2C6E62',id='rho_ALL_'+key)
  f.label(xtitle,px-5,119,pw+10,8,'axis_title',Qt.AlignHCenter,id='xlabel_'+key)
 f.label('c  分片区重复比较',8,135,174,8,'panel_title');tx=8;ty=146;lw=58;cw=29;cols=['NW','NE','SW','SE'];cn=['西北','东北','西南','东南']
 for i,q in enumerate(cols):f.label(cn[i]+'\nn = '+lookup[(q,'SSI')]['n_grid_pairs'],tx+lw+i*cw,ty,cw,14,'map_label',Qt.AlignHCenter,id='n_'+q)
 for j,key in enumerate(['SSI','E_fraction']):
  y=ty+14+12*j;f.rect(tx,y,174,12,'#EEF4F1' if j==0 else '#EEF4F7');f.label('源汇平均距离 SSI' if j==0 else '生态空间比例 E/(E+C)',tx+2,y,lw-2,12,'map_label')
  for i,q in enumerate(cols):
   rho=float(lookup[(q,key)]['spearman_rho']);text=('−' if rho<0 else '')+format(abs(rho),'.3f');f.label(text,tx+lw+i*cw,y,cw,12,'panel_title',Qt.AlignHCenter,color='#2C6E62' if j==0 else '#365E70',id='rho_'+q+'_'+key)
 f.line(tx,ty+14,182,ty+14);f.line(tx,ty+38,182,ty+38)
 f.label('每点为1个1 km方格；E为生态空间，C为建设空间。',8,190,174,6,'note')
 f.label('ρ为Spearman秩相关系数，仅描述同期关联。',8,198,174,6,'note')
 f.label('四片区按研究范围包络中点与方格质心划分。',8,206,174,6,'note')
 with (WORK/'图8_native_points.csv').open('w',encoding='utf-8-sig',newline='') as h:
  writer=csv.DictWriter(h,fieldnames=list(pa[0]));writer.writeheader();writer.writerows(pa)
 f.input_paths=[scatter,stats];f.science={'scatter_n_each':1268,'point_count':len(pa),'no_jitter_no_fit_no_removal':True,'same_axes':{'SSI':[0,1000],'E_fraction':[0,1],'LST_C':[30,50]},'all_rho_and_n_from_frozen_source':True,'geographical_scalebar_north_not_applicable':True,'LST_not_in_ER':True}
 f.save();return f

def supplement():
 f=Figure('图S1_四项原始指标空间分布','图S1 四项原始指标空间分布',270,'补充图S1_原始指标地图.qgz')
 scope=next(l for l in f.project.mapLayers().values() if l.name()=='研究范围边界')
 fields=[('HQ_FS','a  林灌：生境质量 HQ'),('CLUMPY_FS','e  林灌：聚集度 CLUMPY'),('HQ_G','b  草地：生境质量 HQ'),('CLUMPY_G','f  草地：聚集度 CLUMPY'),('HQ_W','c  水体湿地：生境质量 HQ'),('CLUMPY_W','g  水体湿地：聚集度 CLUMPY'),('SSI','d  源汇平均距离 SSI'),('E_fraction','h  生态空间比例 E/(E+C)')]
 f.label('S1  四项原始指标的空间分布',8,5,168,10,'figure_title');f.label('2020年 · CLCD · 1 km格网',8,17,120,7,'map_label');f.north(177,6)
 maps=[];panels=[]
 old=json.loads((W/'map_inputs_s1/S1_native_receipt.json').read_text(encoding='utf8'));byfield={p['field']:p for p in old['maps']}
 for i,(field,title) in enumerate(fields):
  row,col=divmod(i,2);x=8+90*col;y=34+48*row;f.label(title,x,y-8,84,7,'panel_title')
  original_ids=f.old_maps['map_'+field];layer=next(f.project.mapLayer(id) for id in original_ids if f.project.mapLayer(id).name()!='研究范围边界')
  assert layer.featureCount()==2478;mp=f.map(x,y,84,39,[scope,layer],scope,'map_'+field);maps.append(mp)
  prop=layer.renderer().symbol().symbolLayer(0).dataDefinedProperties().property(QgsSymbolLayer.PropertyFillColor).expressionString()
  assert prop==byfield[field]['fill_expression']
  panels.append({'field':field,'layer_id':layer.id(),'source_count':2478,'fill_expression_unchanged':True,'continuous_min_max':byfield[field]['continuous_min_max']})
 f.scale(maps[0],138,16,10)
 colors=[QColor(c) for c in STYLE['palette']['sequential']]
 def ramp(t):
  z=max(0,min(4,t*4));i=min(3,int(z));u=z-i;return QColor(*[round(getattr(colors[i],c)()*(1-u)+getattr(colors[i+1],c)()*u) for c in ['red','green','blue']]).name()
 def cb(title,x,y,lo,hi):
  f.label(title,x,y,84,6,'legend_title');bx=x+8;bw=67
  for k in range(40):f.rect(bx+k*bw/40,y+7,bw/40+.015,2.5,ramp((k+.5)/40),z=15)
  for frac,v in [(0,lo),(.5,(lo+hi)/2),(1,hi)]:
   txt=format(v,',.0f') if abs(v)>10 else format(v,'.1f').rstrip('0').rstrip('.')
   f.label(txt,bx+frac*bw-8,y+10,16,5,'axis_tick',Qt.AlignHCenter)
 cb('生境质量 HQ',8,220,0,1);cb('聚集度 CLUMPY',98,220,-1,1)
 cb('源汇平均距离 SSI（m）',8,237,30,3394.76157598688);cb('生态空间比例 E/(E+C)',98,237,0,1)
 f.rect(8,257,4,3,STYLE['palette']['missing']);f.label('NA为缺少生境或不满足计算条件；深色仅表示数值较高。',14,254,168,6,'note')
 f.label('各图同比例尺；范围裁剪显示。WGS 84 Albers等积投影；N为格网北。',8,262,174,5,'note')
 f.input_paths=[W/'map_inputs_s1/S1_raw_indicator_cells.gpkg',W/'map_inputs_s1/S1_raw_indicator_values.csv',W/'spatial/scope.gpkg']
 f.science={'panels':panels,'all_original_values_and_color_expressions_unchanged':True,'same_raw_indicator_NA_policy':True,'same_extent_all_panels':len({m.extent().toString() for m in maps})==1,'not_ER_or_new_analysis':True,'SSI_E_color_mapping':'same five sequential anchors; SSI original range30..3394.76157598688; E0..1'}
 f.save();return f

if __name__=='__main__':
 requested=sys.argv[1:] or ['study','method','thermal','supplement']
 for name in requested:
  obj=globals()[name]();obj.project.clear();del obj;gc.collect()
 app.exitQgis()
