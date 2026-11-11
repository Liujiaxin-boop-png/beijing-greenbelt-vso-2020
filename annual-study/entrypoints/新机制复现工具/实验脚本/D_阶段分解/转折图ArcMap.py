from pathlib import Path
import json,subprocess
import numpy as np,pandas as pd,geopandas as gp
B=Path(__file__).resolve().parents[1];F=B/'图件_ArcMap10.8';F.mkdir(exist_ok=True);G=F/'turn.gdb';D=B/'D_阶段分解';A=B.parent/'计算结果与核验'/'01_全区与格网'
t=pd.read_csv(D/'格网阶段与两次转折.csv.gz');g=gp.read_file(A/'annual_grid_500.gpkg')[['grid_id','geometry']].merge(t[['grid_id','t2019','t2021','D2019','D2021']],on='grid_id',validate='1:1');assert len(g)==4478
for y in [2019,2021]:g['K'+str(y)]=g['t'+str(y)].map({'降降':'1','升降':'2','降升':'3','升升':'4'}).fillna('5')
g.to_file(G,layer='grid',driver='OpenFileGDB',layer_options={'TARGET_ARCGIS_VERSION':'ALL'},index=False);gp.read_file(A/'scope.gpkg')[['geometry']].to_file(G,layer='scope',driver='OpenFileGDB',layer_options={'TARGET_ARCGIS_VERSION':'ALL'},index=False)
j=json.loads(Path('D:/ER219_work/shp11/maps/fig3.json').read_text(encoding='utf8'));colors=['#A56347','#E4B58F','#85B8A2','#2D6C59','#DDDCD7'];labels=['持续下降','由升转降','由降转升','持续上升','一期持平']
for m,yr in zip(j['maps'],[2019,2021]):
 m['name']=str(yr)+'年前后';layer=m['layers'][0]
 for l in m['layers']:l['gdb']=str(G)
 layer.update(name=m['name'],field='K'+str(yr),values=[dict(value=str(i+1),label=label,color=colors[i]) for i,label in enumerate(labels)])
el=j['elements'][:6];notes={'long题':'(a)  2019年前后','long全区':'2015—2019年 → 2019—2021年','rise题':'(b)  2021年前后','rise全区':'2019—2021年 → 2021—2025年'}
for e in el:
 if e['name'] in notes:e['text']=notes[e['name']]
for i,lab in enumerate(labels):
 x=1.0+i*3.4;el.extend([dict(name='色块'+str(i),kind='rect',x=x,y=1.08,w=.50,h=.26,fill=colors[i],stroke='#7F867E',width=.22),dict(name='图例'+str(i),kind='text',x=x+.62,y=1.2,text=lab,font='SimHei',size=8,align='left',valign='center',color='#22302A')])
el.append(dict(name='定义',kind='text',x=.45,y=.39,text='每格对比前、后两段的首末得分；两图共用图例。升、降表示得分方向，不表示变化幅度。',font='SimHei',size=7.3,color='#37473F',align='left',valign='center'))
j['elements']=el;j['scales']=[];j['output_mxd']=str(F/'图11_两次转折前后的格网升降.mxd');j['export_stem']=str(F/'图11_两次转折前后的格网升降');j['dpi']=320
m=j['maps'][0];width=10000*m['w']/(m['extent'][2]-m['extent'][0]);xx,yy=6.95,2.42
for n,pts in [('标尺',[[xx,yy],[xx+width,yy]]),('左刻',[[xx,yy],[xx,yy+.085]]),('右刻',[[xx+width,yy],[xx+width,yy+.085]])]:el.append(dict(name=n,kind='line',points=pts,color='#263730',width=.6))
for x,t in [(xx,'0'),(xx+width,'10 km')]:el.append(dict(name='标'+t,kind='text',text=t,x=x,y=yy+.2,font='SimHei',size=6.8,align='center',valign='center',color='#23332C'))
c=F/'版式.json';c.write_text(json.dumps(j,ensure_ascii=False,indent=1),encoding='utf8');p=Path('D:/ER219_code/arcmap_hi_20261106');template=json.loads((p/'context_fig1.json').read_text('utf-8-sig'))['input_template'];cmd=['C:/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(p/'run_native.ps1')]
subprocess.run(cmd+['-InputMxd',template,'-OutputMxd',j['output_mxd'],'-Config',str(c)],check=True);subprocess.run(cmd+['-InputMxd',j['output_mxd'],'-Config',str(c),'-ExportOnly'],check=True)

