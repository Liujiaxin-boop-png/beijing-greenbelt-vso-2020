from common import *
import pyogrio
base=Path('D:/ER219_work/townmaps11/comments')
def mk():
 old=B.parent/'四个典型镇街_镇内十年变化_ArcMap10.8/图1/data'
 local=db('1');world=local.parent/'LocationMap.gdb'
 cfg=json.loads((base/'map1.json').read_text('utf8'))
 oldlocal=next(q for q in old.glob('*.gdb') if q.name!='LocationMap.gdb')
 sh=gp.read_file(D/'scope.gpkg');tt=gp.read_file(T/'planning_towns.gpkg',layer='towns')
 districts=gp.read_file(oldlocal,layer='districts');geo('1','districts',districts);geo('1','scope',sh[['geometry']]);geo('1','towns',tt[['display_name','geometry']])
 un=gp.read_file(T/'planning_towns.gpkg',layer='unassigned');geo('1','unassigned',un[['geometry']])
 if not world.exists():shutil.copytree(old/'LocationMap.gdb',world,ignore=shutil.ignore_patterns('*.lock'))
 newext=ext(sh,cfg['maps'][2]['w'],cfg['maps'][2]['h'],1.13);cfg['maps'][2]['extent']=newext
 from shapely.geometry import box
 gp.GeoDataFrame({'tag':['右图范围']},geometry=[box(*newext)],crs=sh.crs).to_file(world,layer='flag_focus',driver='OpenFileGDB',geometry_type='MultiPolygon',promote_to_multi=True,index=False)
 for m in cfg['maps']:
  m['layers']=[l for l in m['layers'] if l['fc']!='fringe']
  for l in m['layers']:
   l['gdb']=str(world if Path(l['gdb']).name=='LocationMap.gdb' else local)
   l['name']=l['name'].replace('规划范围轮廓','项目二道绿隔范围')
 cfg['elements']=[e for e in cfg['elements'] if '边界内侧带' not in e.get('name','')]
 for e in cfg['elements']:
  if e.get('text')=='规划范围':e['text']='项目二道绿隔范围'
 config('1',cfg)
 src=ORIG/'图A1';q=target('A1')
 for f in src.iterdir():
  if f.is_dir():shutil.copytree(f,q/f.name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.lock'))
  elif f.suffix in ['.png','.pdf','.mxd','.csv']:shutil.copy2(f,q/f.name)
if __name__=='__main__':mk()
