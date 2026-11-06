"""Native QGIS process figures; only styles frozen real result fields."""
import os,json,gc,hashlib,math,shutil
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import *
from qgis.PyQt.QtGui import QColor,QFont,QFontDatabase,QImage
from qgis.PyQt.QtCore import Qt

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/figure_revision_20261106'
OUT=ROOT/'04_图件/统一图式与过程图_20261106'
STYLE=json.loads((ROOT/'05_代码/figure_revision_20261106/figure_style.json').read_text(encoding='utf-8'))
DATA=json.loads((WORK/'process_figures_data_manifest.json').read_text(encoding='utf-8'))
HAB=[('forest_shrub','林灌',840),('grassland','草地',153),('water_wetland','水体湿地',532)]
app=QgsApplication([],False);app.initQgis()
assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/simhei.ttf')>=0
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PAL=[QColor(c) for c in STYLE['palette']['sequential']]

def font(size):
    q=QFont(STYLE['font_family']);q.setPointSizeF(float(size));return q

def fill(color,edge='transparent',width=0):
    return QgsFillSymbol.createSimple({'color':color,'outline_color':edge,'outline_width':str(width),'outline_style':'no' if width==0 else 'solid'})

def color_at(t):
    t=max(0,min(1,t));i=min(3,int(t*4));f=t*4-i
    a,b=PAL[i],PAL[i+1]
    return QColor(round(a.red()+(b.red()-a.red())*f),round(a.green()+(b.green()-a.green())*f),round(a.blue()+(b.blue()-a.blue())*f)).name()

def continuous_expression(field):
    branches=[]
    for i in range(4):
        a,b=PAL[i],PAL[i+1];f='((@t-'+str(i/4)+')*4)'
        channels=[str(x)+'+('+str(y-x)+')*'+f for x,y in [(a.red(),b.red()),(a.green(),b.green()),(a.blue(),b.blue())]]
        branches.append('WHEN @t <= '+str((i+1)/4)+' THEN color_rgb('+','.join(channels)+')')
    return 'CASE WHEN "'+field+'" IS NULL THEN \''+STYLE['palette']['missing']+'\' ELSE with_variable(\'t\',clamp(0,"'+field+'",1),CASE '+' '.join(branches)+' END) END'

def build(kind):
    project=QgsProject.instance();project.clear();project.setFilePathStorage(Qgis.FilePathType.Relative)
    scope=QgsVectorLayer(str(ROOT/'02_过程文件/spatial/scope.gpkg')+'|layername=study_scope','研究范围','ogr')
    assert scope.isValid();scope.renderer().setSymbol(fill('transparent','#707A76',.10));project.addMapLayer(scope);project.setCrs(scope.crs())
    layout=QgsPrintLayout(project);layout.initializeDefaults();layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(190,268))
    title='六项原始指标空间分布' if kind=='raw' else '三维得分的空间分解'
    stem='图3_六项原始指标空间分布' if kind=='raw' else '图4_三维得分空间分解'
    layout.setName(stem);live=[];maps=[];labels=[];layer_specs=[];data_layers=[]
    def label(text,x,y,w,h,pt=11,align=Qt.AlignLeft):
        o=QgsLayoutItemLabel(layout);o.setText(text);o.setFont(font(pt));o.setFontColor(QColor(STYLE['text_color']));o.setHAlign(align)
        layout.addLayoutItem(o);o.attemptMove(QgsLayoutPoint(x,y));o.attemptResize(QgsLayoutSize(w,h));o.setZValue(100)
        live.append(o);labels.append(o);return o
    def rect(x,y,w,h,color,edge='transparent',width=0,z=20):
        o=QgsLayoutItemShape(layout);o.setShapeType(QgsLayoutItemShape.Rectangle);o.setSymbol(fill(color,edge,width));layout.addLayoutItem(o)
        o.attemptMove(QgsLayoutPoint(x,y));o.attemptResize(QgsLayoutSize(w,h));o.setZValue(z);live.append(o);return o
    rect(2,2,186,264,'transparent',STYLE['frame']['color'],STYLE['frame']['width_mm'],0)
    label(title,7,4,171,9,16)
    subtitle='2020年  |  林灌基线840格的同一有效范围' if kind=='raw' else '2020年  |  三维得分均以高值为有利'
    label(subtitle,7,14,159,7,10)
    northlabel=label('N',177,11,7,5,11,Qt.AlignHCenter);northlabel.setZValue(2000);northlabel.setBackgroundEnabled(False)
    rect(180.35,18,0.3,3.5,STYLE['text_color'],z=2000)
    arrow=QgsLayoutItemShape(layout);arrow.setShapeType(QgsLayoutItemShape.Triangle)
    arrow.setSymbol(fill(STYLE['text_color']));layout.addLayoutItem(arrow)
    arrow.attemptMove(QgsLayoutPoint(179,16));arrow.attemptResize(QgsLayoutSize(3,3));arrow.setZValue(2000);arrow.setBackgroundEnabled(False);live.append(arrow)
    def make_map(h,field,legendname,x,y,w,hgt,letter):
        lyr=QgsVectorLayer(str(WORK/'process_figure_sources.gpkg')+'|layername='+h,legendname,'ogr');assert lyr.isValid()
        sym=fill(STYLE['palette']['missing']);expr=continuous_expression(field)
        assert not QgsExpression(expr).hasParserError(),expr
        sym.symbolLayer(0).setDataDefinedProperty(QgsSymbolLayer.PropertyFillColor,QgsProperty.fromExpression(expr))
        lyr.setRenderer(QgsSingleSymbolRenderer(sym));project.addMapLayer(lyr);data_layers.append(lyr)
        mp=QgsLayoutItemMap(layout);layout.addLayoutItem(mp);mp.attemptMove(QgsLayoutPoint(x,y));mp.attemptResize(QgsLayoutSize(w,hgt));mp.setCrs(scope.crs())
        mp.setLayers([scope,lyr]);mp.setKeepLayerSet(True);mp.setKeepLayerStyles(True)
        ex=QgsRectangle(scope.extent());ex.scale(1.055);cx=ex.center().x();cy=ex.center().y()
        eh=max(ex.height(),ex.width()*hgt/w);ew=eh*w/hgt;mp.setExtent(QgsRectangle(cx-ew/2,cy-eh/2,cx+ew/2,cy+eh/2))
        mp.setFrameEnabled(True);mp.setFrameStrokeColor(QColor(STYLE['frame']['color']));mp.setFrameStrokeWidth(QgsLayoutMeasurement(STYLE['frame']['width_mm']))
        mp.setZValue(10);live.append(mp);maps.append(mp)
        if letter:label('('+letter+')',x+1,y+1,9,6,11)
        layer_specs.append({'habitat':h,'color_field':field,'layer_name':legendname,'feature_n':lyr.featureCount(),'map_width_mm':w,'map_height_mm':hgt,'extent':mp.extent().toString(),'rotation':mp.mapRotation()})
        return mp
    def colorbar(x,y,w,ticks):
        # Native editable shapes form a 128-step approximation to the continuous
        # data-defined color ramp; these are rendering steps, not ecological classes.
        for i in range(128):rect(x+w*i/128,y,w/128+.006,2.6,color_at((i+.5)/128))
        for t,txt in ticks:
            xx=x+t*w
            rect(xx-.06,y+2.6,.12,.8,STYLE['text_color'])
            if t==0:label(txt,x,y+3,w/4,6,11,Qt.AlignLeft)
            elif t==1:label(txt,x+w-w/4,y+3,w/4,6,11,Qt.AlignRight)
            else:label(txt,xx-12,y+3,24,6,11,Qt.AlignHCenter)
    def scale(x,y):
        sb=QgsLayoutItemScaleBar(layout);sb.setStyle('Single Box');sb.setLinkedMap(maps[0]);sb.setUnits(QgsUnitTypes.DistanceKilometers)
        sb.setUnitsPerSegment(10);sb.setNumberOfSegments(2);sb.setNumberOfSegmentsLeft(0);sb.setUnitLabel('km');sb.setFont(font(11));sb.setHeight(1.0)
        layout.addLayoutItem(sb);sb.attemptMove(QgsLayoutPoint(x,y));sb.setZValue(100);live.append(sb)
    if kind=='raw':
        for i,sp in enumerate(DATA['raw_specs']):
            x=7+(i%2)*91;y=24+(i//2)*72
            label('('+'abcdef'[i]+')  '+sp['title'],x,y,84,6,13)
            units=sp['unit'].replace('²','^2')+('；对数色标' if sp['display_transform']=='log10_1p' else '')
            label(units,x,y+6,84,6,11.5)
            make_map('forest_shrub',sp['color_field'],sp['title']+'（原值）',x,y+13,84,44,None)
            lo,hi=sp['display_min_raw'],sp['display_max_raw']
            if sp['field']=='NTL':
                val=[lo,1,5,20,hi];txt=['0','1','5','20','56.79']
            elif sp['field']=='MCR':
                val=[lo,3000,30000,hi];txt=['200.9','3000','30000','247498']
            elif sp['field']=='HQ_H':val=[lo,(lo+hi)/2,hi];txt=[f'{lo:.3f}',f'{(lo+hi)/2:.3f}',f'{hi:.3f}']
            elif sp['field']=='SSI':val=[lo,(lo+hi)/2,hi];txt=['30',f'{(lo+hi)/2:.0f}',f'{hi:.0f}']
            elif sp['field']=='CLUMPY':val=[-1,0,1];txt=['-1','0','1']
            else:val=[0,.5,1];txt=['0','0.5','1']
            if sp['display_transform']=='log10_1p':pos=[(math.log10(1+v)-math.log10(1+lo))/(math.log10(1+hi)-math.log10(1+lo)) for v in val]
            else:pos=[(v-lo)/(hi-lo) for v in val]
            colorbar(x,y+59,84,list(zip(pos,txt)))
        scale(143,241)
        label('林灌840格统一示例；深色表示原值较高，不等于更有利。',7,242,131,6,10)
        label('夜光与MCR色彩采用log10(1+x)，刻度保留原单位。',7,248,131,6,10)
        label('完整1 km方格取值，制图裁区；灰色未评价不等于低值。',7,254,177,6,10)
        label('WGS84 Albers等积投影；N为格网北。',7,260,130,6,10)
        rect(147,259,4,3,STYLE['palette']['missing'],'#A8AEAB',.1);label('未评价',153,257,31,7,11)
    else:
        cols=[('V_score','脆弱性 V'),('S_score','敏感性 S'),('O_score','自组织 O')]
        for c,(_,name) in enumerate(cols):label(name,7+c*60,24,55,7,13,Qt.AlignHCenter)
        for row,(h,name,n) in enumerate(HAB):
            top=35+row*66
            label(name+'（n = '+str(n)+'）',7,top,177,7,13)
            for c,(field,title0) in enumerate(cols):make_map(h,'display_'+field,name+' · '+title0,7+c*60,top+8,55,48,'abcdefghi'[row*3+c])
        label('三维有利度',7,226,80,7,11.5)
        colorbar(7,235,103,[(0,'0'),(.5,'0.5'),(1,'1')])
        scale(135,231)
        rect(136,245,4,3,STYLE['palette']['missing'],'#A8AEAB',.1);label('未评价',142,243,42,7,11)
        label('三类生境分别标准化；同类内部比较，不能跨生境排名。',7,250,177,6,10)
        label('完整1 km方格取值，地图裁区；灰色未评价不等于低值。',7,256,177,6,10)
        label('WGS84 Albers等积投影；N为格网北。',7,262,177,5,10)
    project.layoutManager().addLayout(layout)
    tree=project.layerTreeRoot();visible={scope.id(),data_layers[0].id()}
    for node in tree.findLayers():node.setItemVisibilityChecked(node.layerId() in visible);node.setExpanded(False)
    tree.setHasCustomLayerOrder(True);tree.setCustomLayerOrder([scope]+data_layers)
    ext=QgsRectangle(scope.extent());ext.scale(1.08);project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(ext,scope.crs()))
    layout.refresh();app.processEvents();qgz=OUT/(stem+'_可编辑.qgz');assert project.write(str(qgz))
    ex=QgsLayoutExporter(layout)
    ascii_out=Path(r'D:\ER219_work\figure_revision_20261106\exports_process');ascii_out.mkdir(parents=True,exist_ok=True)
    for suffix,setting,method in [('png',QgsLayoutExporter.ImageExportSettings(),ex.exportToImage),('pdf',QgsLayoutExporter.PdfExportSettings(),ex.exportToPdf),('svg',QgsLayoutExporter.SvgExportSettings(),ex.exportToSvg)]:
        setting.dpi=600
        if suffix=='svg':setting.exportAsLayers=True
        tmp=ascii_out/('fig3' if kind=='raw' else 'fig4');tmp=tmp.with_suffix('.'+suffix)
        assert method(str(tmp),setting)==QgsLayoutExporter.Success
        assert tmp.is_file() and tmp.stat().st_size>1000
        if suffix=='png':
            im=QImage(str(tmp));assert not im.isNull() and im.width()>4000 and im.height()>6000
        elif suffix=='pdf':assert tmp.read_bytes().startswith(b'%PDF-')
        else:assert b'<svg' in tmp.read_bytes()[:1000]
        shutil.copy2(tmp,OUT/(stem+'.'+suffix))
    receipt={'status':'NATIVE_EXPORTED_REOPEN_VISUAL_PENDING','engine':Qgis.QGIS_VERSION,'kind':kind,'stem':stem,'qgz':str(qgz),
             'source_manifest_sha256':sha(WORK/'process_figures_data_manifest.json'),'style_sha256':sha(ROOT/'05_代码/figure_revision_20261106/figure_style.json'),
             'layout_mm':[190,268],'dpi':600,'labels':[{'text':o.text(),'font':o.font().family(),'pt':o.font().pointSizeF()} for o in labels],
             'layers':layer_specs,'map_n':len(maps),'default_visible_layers':[scope.name(),data_layers[0].name()],
             'source_values_unchanged':True,'new_classification':False,'native_scale_bar_map_linked':True,
             'artifacts':[{ 'file':str((OUT/(stem+'.'+e)).relative_to(ROOT)),'sha256':sha(OUT/(stem+'.'+e))} for e in ['png','pdf','svg']]}
    (WORK/('process_'+kind+'_native_receipt.json')).write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(stem+' EXPORTED',flush=True)
    project.clear();live.clear();labels.clear();maps.clear();data_layers.clear();gc.collect()

for kind in ['raw','dimensions']:build(kind)
QgsProject.instance().clear();gc.collect();app.exitQgis()
