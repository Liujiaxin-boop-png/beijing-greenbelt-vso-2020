from pathlib import Path
import shutil,json
w=Path(__file__).resolve().parent
out=Path('D:/ER219_figures/年度评价_论文图版/附图_距离与镇街')
out.mkdir(exist_ok=True)
def dump(c,name,key):
 c['dpi']=450;c['output_mxd']=str((out/(name+'.mxd')).resolve());c['export_stem']=str(w/key)
 (w/(key+'.json')).write_text(json.dumps(c,ensure_ascii=False,indent=1),'utf8')
def shift(c,dx,dy):
 for e in c['maps']+c['elements']+c.get('scales',[]):
  if 'x' in e:e['x']+=dx
  if 'y' in e:e['y']+=dy
  if 'points' in e:e['points']=[[x+dx,y+dy] for x,y in e['points']]
c=json.loads(Path('D:/ER219_work/six_final11/experiment/fig_how.json').read_text('utf8'))
c['elements']=[e for e in c['elements'] if e['name'] not in ['图框','图名','研究范围与时段','读法','算法','跨界']]
for e in c['elements']:
 if e['name'] in ['组名0','组名1']:e['text']=['(a)  集中分布','(b)  分散分布'][int(e['name'][-1])]
shift(c,-.30,-2.02);c['page'].update(width_cm=15.0,height_cm=4.36)
dump(c,'A1_蓝绿空间平均距离示例','distance')
c=json.loads(Path('D:/ER219_work/six_final11/annual/figures/map_town.json').read_text('utf8'))
db=Path(c['maps'][0]['layers'][0]['gdb']);ndb=(out/'data'/db.name).resolve();ndb.parent.mkdir(exist_ok=True)
if not ndb.exists():shutil.copytree(db,ndb,ignore=shutil.ignore_patterns('*.lock'))
for l in c['maps'][0]['layers']:l['gdb']=str(ndb)
c['elements']=[e for e in c['elements'] if e['name'] not in ['title','subtitle','white','town_head','site0','site1','val0','val1','site2','site3','q1','q2','note1','note2']]
for e in c['elements']:
 if e['name']=='loc0':e.update(text='金盏乡',align='left',size=8.5,x=e['x']+.05,y=e['y']+.16)
 if e['name']=='loc1':e.update(text='原长辛店镇',align='center',size=8.5,y=e['y']+.16)
 if e['name']=='legend_h':e['text']='镇街指数变化'
shift(c,-.13,-1.43);c['page'].update(width_cm=15.8,height_cm=10.7)
dump(c,'A8_镇街生态韧性首末年差值','townmap')

