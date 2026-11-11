"""Re-use the registered Feng 2020 MSPA/PC algorithm and two-distinct-source Dijkstra for annual land use."""
from pathlib import Path
import json,sys,os,subprocess,hashlib,time,argparse,types,shutil,concurrent.futures
import numpy as np,rasterio as rio
A=Path(__file__).resolve().parents[1]
BACK=Path(r'D:\ER219_work\feng_round2\source_mcr')
OUT=A/'mcr'
def h(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def grid_write(p,a,profile):
 pr=profile.copy();pr.update(driver='GTiff',dtype='float32',count=1,nodata=-9999,compress='deflate',predictor=3,tiled=True,blockxsize=256,blockysize=256)
 with rio.open(p,'w',**pr) as f:f.write(a,1)
def run(y):
 land=A/'years'/'model'/f'CLCD_{y}.tif'
 ws=OUT/str(y);ws.mkdir(parents=True,exist_ok=True)
 out=ws/f'MCR_{y}.tif';receipt=ws/'verified.json'
 if out.exists() and receipt.exists() and h(land)==json.loads(receipt.read_text())['land_file_sha']:return
 with rio.open(land) as s, rio.open(r'D:\ER219_work\spatial\clcd2020.tif') as old:
  assert s.shape==old.shape and s.crs==old.crs and s.transform.almost_equals(old.transform,precision=.00001)
  pr=s.profile;nr,nc=s.shape
  exact=(y==2020 and np.array_equal(s.read(1),old.read(1)))
 extra={'source_program_hashes':{n:h(BACK/n) for n in ['prepare.py','sources.py','TwoSource.exe']},'year':y,'land_file_sha':h(land)}
 if exact:
  for p in ['source_dPC.csv','MCR_dpc_2020.tif','sources_dpc.tif','sources_area.tif','edge_distances_m.csv']:
   osp=ws/p if p!='MCR_dpc_2020.tif' else out
   shutil.copy2(BACK/p,osp)
  extra['baseline_match']='identical 2020 input pixels, common native Albers transform and identical model parameters'
 else:
  prep=(BACK/'prepare.py').read_text(encoding='utf8').replace("D=Path(__file__).resolve().parent","D=annual_dir").replace("P=Path(r'D:\\ER219_work\\spatial\\clcd2020.tif')","P=annual_land")
  assert 'P=annual_land' in prep
  mod=types.ModuleType('prepare');mod.__dict__.update(__name__='__main__',__file__=str(BACK/'prepare.py'),annual_dir=ws,annual_land=land)
  exec(compile(prep,'prepare.py','exec'),mod.__dict__)
  sys.modules['prepare']=mod
  exec(compile((BACK/'sources.py').read_text(encoding='utf8'),'sources.py','exec'),{'__name__':'__main__','__file__':str(BACK/'sources.py')})
  subprocess.run([str(BACK/'TwoSource.exe'),str(ws),'dpc',str(nc),str(nr),'30'],check=True)
  cost=np.memmap(ws/'surface_dpc.f32',mode='r',dtype='float32',shape=(nr,nc))
  grid_write(out,cost,pr)
 with rio.open(out) as s:
  v=s.read(1,masked=True);assert v.count()==nr*nc and v.min()>=0
  extra.update(shape=s.shape,min=float(v.min()),max=float(v.max()),mcr_hash=h(out))
 receipt.write_text(json.dumps(extra,indent=2),encoding='utf8')
 print('VERIFIED MCR',y,flush=True)
def main():
 OUT.mkdir(exist_ok=True)
 if len(sys.argv)>1 and sys.argv[1]!='watch':run(int(sys.argv[1]));return
 todo=set(range(2015,2026));busy={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  while todo or busy:
   for y,f in list(busy.items()):
    if f.done():
     rc=f.result();del busy[y]
     if rc: raise RuntimeError(f'{y} failed, see log')
   for y in sorted(todo,key=lambda x:(x!=2020,x)):
    if len(busy)>=2:break
    p=A/'years'/'model'/f'CLCD_{y}.tif'
    if not p.exists():continue
    try:
     with rio.open(p) as ds:ds.read(1,window=rio.windows.Window(ds.width-8,ds.height-8,8,8))
    except Exception:continue
    def job(year):
     with (OUT/f'run_{year}.log').open('w',encoding='utf8') as f:return subprocess.run([sys.executable,'-u',__file__,str(year)],stdout=f,stderr=subprocess.STDOUT).returncode
    busy[y]=pool.submit(job,y);todo.remove(y)
   if todo or busy:time.sleep(3)
if __name__=='__main__':main()
