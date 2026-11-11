# -*- coding: utf-8 -*-
"""Isolated model replay. New artifacts can be written only under a marked ASCII-named run root."""
import argparse,sys,os,warnings,hashlib,json,gzip,csv,subprocess,shutil
from pathlib import Path
import numpy as np
import rasterio as rio
import pandas as pd
from rasterio.windows import Window
from scipy.ndimage import distance_transform_edt
warnings.filterwarnings('ignore',category=DeprecationWarning);sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
RAW=Path('D:/ER219_raw');W=Path('D:/ER219_work'); A=W/'annual_actual'; C=W/'shp11/core'; BACK=W/'feng_round2/source_mcr'
INV=Path('D:/Apps/InVEST-3.20.2/invest.exe');ARC=Path('F:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe')
Y=range(2015,2026)
def jread(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jwrite(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),'utf-8')
def ready_yr(root,y):return root/f'year{y}'
def confined(root):
 root=root.resolve()
 # Hard requirement: new directory / our own marker; reject ancestors or descendants of all archive trees.
 protected=[x.resolve() for x in [RAW,W,C,Path('D:/ER219_results'),Path('D:/ER219_code'),Path('D:/ER219_figures'),Path('D:/ER219_project')]]
 if any(root==p or p in root.parents or root in p.parents for p in protected) or len(root.parts)<2 or not str(root).isascii():raise ValueError('请选择独立的英文路径，如 D:/ER_Replay_study；不能使用原档目录。')
 marker=root/'greenbelt_replay_v1.marker'
 if root.exists() and not marker.exists():raise ValueError('已有目录且无复算标识，不写入；请选择一个尚不存在的新目录。')
 root.mkdir(parents=True,exist_ok=True);marker.touch();return root
def write(p,v,prof,nodata):
 q=prof.copy();q.update(driver='GTiff',count=1,dtype=str(v.dtype),nodata=nodata,compress='deflate',tiled=True,blockxsize=256,blockysize=256)
 with rio.open(p,'w',**q) as f:f.write(v,1)
def run(cmd,wd):
 print('运行：',str(cmd[0]),'；日志：',wd/'console.log',flush=True)
 with (wd/'console.log').open('ab') as f:r=subprocess.run([str(a) for a in cmd],cwd=wd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError(f'运行失败，退出码{r.returncode}，详见 {wd}/console.log')
def prep(y,d):
 dest=d/'CLCD.tif'; rr=jread(RAW/f'CLCD_v105_2015_2025/CLCD_{y}_source.json')
 r,c,_,_=rr['large_window_rcwh'];x,y0,w,h=rr['model_window_colrowwh']
 with rio.open(RAW/f'CLCD_v105_2015_2025/CLCD_{y}_Beijing_native.tif') as s:
  win=Window(x-c,y0-r,w,h);land=s.read(1,window=win);pf=s.profile;pf.update(width=w,height=h,transform=s.window_transform(win))
 assert hashlib.sha256(land.tobytes()).hexdigest()==rr['model_native_pixel_sha256']
 write(dest,land,pf,0);print('CLCD原生窗口验证通过',y,'行列=',land.shape);return dest
def roads_gdf(y,crs):
 import geopandas as gpd
 from shapely.geometry import shape
 stamp=f'{y}-12-31T15:59:59Z'
 fn=RAW/f'年度分析_2015_2025/OSM年末主要道路/ohsome_{y}_Beijing_clock_235959.geojson.gz'
 with gzip.open(fn,'rt',encoding='utf8') as f:features=json.load(f)['features']
 rows=[]
 for ft in features:
  p=ft['properties']
  if not (p['@validFrom']<=stamp<p['@validTo']):continue
  z=shape(ft['geometry'])
  if z.geom_type not in ('LineString','MultiLineString') or z.is_empty or z.length<=0:continue
  if p.get('highway') not in ['motorway','trunk','primary','motorway_link','trunk_link','primary_link']:continue
  rows.append({'osm_id':p['@osmId'],'highway':p['highway'],'ref':p.get('ref'),'name':p.get('name'),'geometry':z})
 df=gpd.GeoDataFrame(rows,crs=4326);ref=jread(fn.with_name(f'ohsome_{y}_provenance.json'));assert len(df)==ref['unique_line_features'] and df.osm_id.is_unique
 return df.to_crs(crs)
def roads(y,d):
 import geopandas as gp
 from shapely.geometry import box
 land=d/'CLCD.tif'
 with rio.open(land) as ds:crs=ds.crs;pf=ds.profile;bounds=ds.bounds
 def rast(g,n):
  s=g[['geometry']].copy();s['roadval']=np.ones(len(s),np.int32);sp=d/(n+'.shp');s.to_file(sp,encoding='utf8',engine='pyogrio')
  dest=d/(n+'_arc.tif')
  if dest.exists():raise ValueError('已有该层。请使用另一全新 --root，或仅调用后续阶段，避免混合两次运行。')
  run([ARC,A/'hq/rasterize_arcmap.py',sp,land,dest],d)
  with rio.open(dest) as old:
   assert old.shape==(pf['height'],pf['width']) and old.transform.almost_equals(pf['transform'])
   return old.read(1,masked=True).filled(0)==1
 g=roads_gdf(y,crs);a=rast(g[g.intersects(box(*bounds))],'roads')
 if y==2016:
  g17=roads_gdf(2017,crs);sel=g17[(g17.highway=='motorway')&(g17.ref=='G3')&(g17.name=='京台高速')].copy()
  # This auxiliary mask is the original geometry used when the historical omission was corrected, not the final report boundary.
  mat=gp.read_file(A/'boundary/beijing_greenbelt_full.gpkg').to_crs(crs).geometry.union_all().buffer(5500)
  lines=sel.geometry.intersection(mat);sel=sel[lines.length>0].copy();sel['geometry']=lines[lines.length>0]
  ad=rast(sel,'jingtai');assert np.count_nonzero(ad & ~a)==920;a|=ad
 dest=d/'road.tif';write(dest,a.astype('uint8'),pf,255)
 old=A/(f'hq/road/roads_{y}.tif' if y!=2016 else 'hq/correction_2016/roads_2016_open_confirmed.tif')
 with rio.open(old) as s:assert np.array_equal(a,s.read(1)==1)
 print('主要道路像元与归档完全一致。')
def hq(y,d):
 k_fixed=jread(C/'domain.json')['new_hq_k']
 with rio.open(d/'CLCD.tif') as s:lc=s.read(1);pf=s.profile
 for code,n in [(1,'crop'),(8,'built')]:write(d/(n+'.tif'),(lc==code).astype('uint8'),pf,255)
 with (d/'threat.csv').open('w',newline='',encoding='ascii') as f:
  t=csv.writer(f);t.writerow(['threat','max_dist','weight','decay','cur_path'])
  for n,dist,w in [('built',10000,1),('road',3000,1),('crop',8000,.7)]:t.writerow([n,dist,w,'linear',str(d/(n+'.tif'))])
 args={'workspace_dir':str(d/'invest'),'lulc_cur_path':str(d/'CLCD.tif'),'threats_table_path':str(d/'threat.csv'),'sensitivity_table_path':str(A/'hq/sensitivity_3threat.csv'),'half_saturation_constant':k_fixed,'n_workers':-1,'results_suffix':''}
 jwrite(d/'inputs.json',{'invest_version':'3.20.2','model_id':'habitat_quality','model_name':'natcap.invest.habitat_quality.habitat_quality','args':args})
 run([INV,'run','habitat_quality','-d',d/'inputs.json','--no-report'],d)
 with rio.open(d/'invest/deg_sum_c.tif') as f,rio.open(A/f'hq/degradation/D_{y}.tif') as rf:
  a=f.read(1);b=rf.read(1);ok=b!=rf.nodata;assert abs(a[ok].astype(float)-b[ok]).max()<2e-6
 with rio.open(d/'invest/quality_c.tif') as f,rio.open(A/f'hq/results/HQI_{y}.tif') as ref:
  x=f.read(1);v=ref.read(1);ok=v!=ref.nodata;er=abs(x[ok].astype(float)-v[ok]).max()
 assert er<2e-6;print('HQI 逐像元最大绝对差',er)
def mcr(y,d):
 out=d/'mcr';out.mkdir(exist_ok=True)
 # Copy scripts into isolated work area; their only external write directory D becomes this new directory.
 orig=(BACK/'prepare.py').read_text('utf8')
 token="P=Path(r'D:\\ER219_work\\spatial\\clcd2020.tif')"
 assert token in orig
 (out/'prepare.py').write_text(orig.replace(token,"P=Path("+repr(str(d/'CLCD.tif'))+")"),'utf8')
 shutil.copyfile(BACK/'sources.py',out/'sources.py')
 for f in ['prepare.py','sources.py']:run([sys.executable,out/f],out)
 with rio.open(d/'CLCD.tif') as f:pf=f.profile;ny,nx=f.shape
 run([BACK/'TwoSource.exe',out,'dpc',nx,ny,'30'],out)
 a=np.memmap(out/'surface_dpc.f32',mode='r',dtype='float32',shape=(ny,nx));write(out/'MCR.tif',np.asarray(a),pf,-9999)
 with rio.open(A/f'mcr/{y}/MCR_{y}.tif') as z:
  err=max(float(np.max(np.abs(z.read(1,window=win).astype(float)-a[win.toslices()]))) for _,win in z.block_windows(1))
 print('MCR 逐像元对照最大绝对差',err);assert err<0.01
def landscape(y,d):
 o=d/'landscape';o.mkdir(exist_ok=True)
 with rio.open(d/'CLCD.tif') as f: a=f.read(1);t=f.transform
 a.tofile(o/'land.raw');distance_transform_edt(~np.isin(a,[2,3,4,5,9]),sampling=30).astype('<f4').tofile(o/'distance.raw')
 run([A/'analysis/Landscape.exe',o/'land.raw',o/'distance.raw',a.shape[1],a.shape[0],t.c,t.f,o,915000,4303000,997000,4391000],o)
 for n in ['distance.raw','fields_200_0.bin','fields_500_0.bin','fields_1000_0.bin']:
  with (o/n).open('rb') as x,(A/f'landscape/{y}'/n).open('rb') as ref:assert hashlib.file_digest(x,'sha256').digest()==hashlib.file_digest(ref,'sha256').digest(),n
 print('三种尺度景观分量、距离场逐字节完全一致。')
def score(root,archived=False):
 """Main manuscript grid panel from eleven newly rebuilt annual inputs. All outputs are inside user's root."""
 import importlib.util
 def module(path,name):
  spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 for y in ([] if archived else Y):
  for stage in ['prep','road','hq','mcr','landscape']:
   if not (ready_yr(root,y)/(stage+'.ok')).is_file():raise ValueError(f'{y}/{stage} 未完成；全期必须先完成11年的五个阶段。')
 st=root/('prepared_archived' if archived else 'prepared');out=root/('panel_archived' if archived else 'panel');out.mkdir(exist_ok=True)
 def link(src,dst):
  dst.parent.mkdir(parents=True,exist_ok=True)
  if dst.exists():
   if not os.path.samefile(src,dst):
    if not archived or src.stat().st_size!=dst.stat().st_size:raise ValueError(f'请换独立工作目录：已有同名非配对文件 {dst}')
    with src.open('rb') as a,dst.open('rb') as b:
     if hashlib.file_digest(a,'sha256').digest()!=hashlib.file_digest(b,'sha256').digest():raise ValueError(f'隔离副本不匹配：{dst}')
  elif archived:shutil.copyfile(src,dst)  # this copy can be edited without touching any archived original
  else:os.link(src,dst)  # both endpoints are inside the same new reproduction root
 for y in Y:
  d=ready_yr(root,y)
  link(A/f'years/model/CLCD_{y}.tif' if archived else d/'CLCD.tif',st/f'years/model/CLCD_{y}.tif')
  link(A/f'hq/degradation/D_{y}.tif' if archived else d/'invest/deg_sum_c.tif',st/f'hq/degradation/D_{y}.tif')
  link(A/f'mcr/{y}/MCR_{y}.tif' if archived else d/'mcr/MCR.tif',st/f'mcr/{y}/MCR_{y}.tif')
  ld=A/f'landscape/{y}' if archived else d/'landscape'
  for src in [*list(ld.glob('fields_*.bin')),ld/'distance.raw']:
   link(src,st/f'landscape/{y}'/src.name)
 # original_k is documentary only; the working k is recalculated below from all locally rebuilt Ds.
 jwrite(st/'hq/full_scope_frozen_k.json',{'k':jread(C/'domain.json')['original_k']})
 dom=module(C/'domain.py','replay_domain');dom.W=out;dom.A=st;dom.build()
 k=jread(out/'domain.json')['new_hq_k'];sens=pd.read_csv(A/'hq/sensitivity_3threat.csv')
 lookup=np.zeros(256);lookup[sens.lucode.to_numpy()]=sens.habitat
 (st/'hq/results').mkdir(exist_ok=True)
 for y in Y:
  d=ready_yr(root,y)
  with rio.open(st/f'years/model/CLCD_{y}.tif') as c,rio.open(st/f'hq/degradation/D_{y}.tif') as dg:
   land=c.read(1);D=dg.read(1);pf=dg.profile
  if y!=2016:q=(lookup[land]*k**2.5/(D.astype('float64')**2.5+k**2.5)).astype('float32')
  else:
   with rio.open(A/f'hq/results/HQI_{y}.tif' if archived else d/'invest/quality_c.tif') as qq:q=qq.read(1)
  write(st/f'hq/results/HQI_{y}.tif',q,pf,-9999)
 sf=module(A/'analysis/surfaces.py','replay_surfaces');sf.A=st;sf.OUT=st/'surfaces'
 for y in Y:
  for name in ['HQI','MCR']:sf.run(y,name)
 co=module(C/'compute.py','replay_compute');co.W=out;co.A=st;co.main()
 ref=pd.read_csv(C/'区域六项逐年指数与分项.csv').set_index('year');trial=pd.read_csv(out/'区域六项逐年指数与分项.csv').set_index('year')
 print('全区11年ER最大绝对差',float(abs(ref.ER6-trial.ER6).max()))
 check=abs(ref.ER6-trial.ER6).max()<2e-6 and len(trial)==11
 if not check:raise ValueError('年度面板差异超限，请复核。')
 print('全期原值、贡献、指标权重、尺度对照见',out)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['prep','road','hq','mcr','landscape','all','score','score-audit']);p.add_argument('--year',type=int,default=2020);p.add_argument('--root',type=Path,default=Path('D:/ER_Replay_study'));o=p.parse_args()
 if o.year not in Y:raise ValueError('年份只能2015至2025')
 wr=confined(o.root)
 if o.stage in ['score','score-audit']:score(wr,archived=o.stage=='score-audit');return
 d=ready_yr(wr,o.year);d.mkdir(exist_ok=True)
 for n in (['prep','road','hq','mcr','landscape'] if o.stage=='all' else [o.stage]):
  flag=d/(n+'.ok')
  if flag.exists():print('已有通过标志，跳过',n);continue
  print('阶段',n,'输出',d,flush=True);{'prep':prep,'road':roads,'hq':hq,'mcr':mcr,'landscape':landscape}[n](o.year,d);flag.write_text('PASS','ascii')
if __name__=='__main__':main()




