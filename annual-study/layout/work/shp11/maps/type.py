from common import *
from shapely import get_parts
c=json.loads(Path('D:/ER219_work/litlogic11/typemap/townclass.json').read_text('utf8')); m=c['maps'][0]
tab=pd.read_csv(T/'82镇街首末年分型与敏感性.csv',dtype={'town_id':str})
tt=gp.read_file(T/'planning_towns.gpkg',layer='towns')
qq=tt[['town_seq','geometry']].merge(tab[['town_seq','display_name','district','km2','delta','decline_pct','base_type','nominated_1km2']],on='town_seq',validate='1:1')
assert len(qq)==82
for k in ['nominated_1km2','town_seq']:qq[k]=qq[k].astype('int32')
sh=gp.read_file(D/'scope.gpkg')[['geometry']];geo('A8','scope',sh);geo('A8','town_type',qq);geo('A8','town_edge',tt[['geometry']])
for ly in m['layers']:ly['gdb']=str(db('A8'));ly['name']=ly['name'].replace('重建','').replace('规划范围','项目研究范围')
m['extent']=ext(sh,m['w'],m['h']);x,y,X,Y=m['extent'];caps=qq.groupby('base_type').size().to_dict();select=qq[qq.nominated_1km2>0].set_index('base_type')
txt={'A':'普遍下降型','B':'普遍上升型','C':'局部上升主导型','D':'局部下降主导型'}
for k in select.index:
 r=select.loc[k];xy=max(get_parts(r.geometry),key=lambda z:z.area).representative_point()
 px=m['x']+m['w']*(xy.x-x)/(X-x);py=m['y']+m['h']*(xy.y-y)/(Y-y)
 dx,dy={'A':(-.50,-.54),'B':(.52,-.50),'C':(-.46,.45),'D':(.50,.69)}[k];xx=px+dx;yy=py+dy
 for e in c['elements']:
  name=e.get('name','')
  if name=='casename'+k:e.update(text=r.display_name,x=xx,y=yy,align='left' if dx>0 else 'right')
  elif name=='casepoint'+k:e.update(x=px,y=py)
  elif name=='caselead'+k:e.update(points=[[px,py],[xx,yy-.1]],color='#38483F')
  elif name=='type'+k:e['text']=f'{k}  {txt[k]}（{caps[k]}）'
config('A8',c);save_data(tab,'A8','镇街类型与核查依据.csv')
