"""2015–2025 native InVEST degradation and peer-equivalent quality at one common k."""
import argparse, concurrent.futures, csv, json, os, shutil, subprocess, time
import numpy as np
import rasterio
from pathlib import Path
from fetch_annual_roads import ROOT, dump, sha
YEAR_DIR=ROOT.parent/'years'/'model'
REF=Path('D:/ER219_work/spatial/clcd2020.tif')
EXE=Path('D:/Apps/InVEST-3.20.2/invest.exe')
ORIG_T=Path('D:/ER219_work/indicator_rebuild_20261107/pilot_hq2020/inputs/sensitivity_3threat.csv')
sens=ROOT/'sensitivity_3threat.csv'
if not sens.exists():shutil.copyfile(ORIG_T,sens)
assert sha(sens)==sha(ORIG_T)
with sens.open(encoding='utf8') as inp: params={int(r['lucode']):{v:float(r[v]) for v in ['habitat','crop','built','road']} for r in csv.DictReader(inp)}
H=np.full(256,np.nan)
for i,v in params.items():H[i]=v['habitat']
for d in ['native','degradation','results','threat','data_stacks','logs']: (ROOT/d).mkdir(exist_ok=True)
def verify_alignment(f,g):
 assert f.shape==g.shape and f.crs==g.crs and np.max(np.abs(np.array(f.transform)-g.transform))<.000001
def write(path,a,prof,nodata,tags=None):
 pro=prof.copy();pro.update(driver='GTiff',count=1,dtype=str(a.dtype),nodata=nodata,tiled=True,blockxsize=256,blockysize=256,compress='deflate')
 tmp=path.with_name(path.stem+'_writing.tif')
 with rasterio.open(tmp,'w',**pro) as ds:
  ds.write(a,1)
  if tags:ds.update_tags(**tags)
 os.replace(tmp,path)
def native(yr,lcfile,road,ws,k):
 paths=[('built',10000,1,ROOT/'threat'/f'built_{yr}.tif'),('road',3000,1,road),('crop',8000,.7,ROOT/'threat'/f'crop_{yr}.tif')]
 tp=ROOT/'data_stacks'/f'{ws.name}_threats.csv'
 with tp.open('w',newline='',encoding='ascii') as dest:
  cw=csv.writer(dest);cw.writerow(['threat','max_dist','weight','decay','cur_path']);cw.writerows([(kind,dist,weight,'linear',str(path)) for kind,dist,weight,path in paths])
 args={'workspace_dir':str(ws),'lulc_cur_path':str(lcfile),'threats_table_path':str(tp),'sensitivity_table_path':str(sens),'half_saturation_constant':float(k),'n_workers':-1,'results_suffix':''}
 dat=ROOT/'data_stacks'/f'{ws.name}.json';dump(dat,{'invest_version':'3.20.2','model_id':'habitat_quality','model_name':'natcap.invest.habitat_quality.habitat_quality','args':args})
 cmd=[str(EXE),'run','habitat_quality','-d',str(dat),'--no-report']
 log=ROOT/'logs'/f'{ws.name}.log'
 print('NATIVE_START',yr,ws,flush=True)
 with log.open('wb') as fp:status=subprocess.run(cmd,stdout=fp,stderr=subprocess.STDOUT).returncode
 if status:raise RuntimeError(log.read_text(encoding='utf8',errors='replace')[-2800:])
 return dat
def degradation(yr):
 path=ROOT/'degradation'/f'D_{yr}.tif';rec=ROOT/'degradation'/f'D_{yr}.json'
 lcfile=YEAR_DIR/f'CLCD_{yr}.tif';road=ROOT/'road'/f'roads_{yr}.tif'
 if rec.exists() and path.exists():
  meta=json.loads(rec.read_text(encoding='utf8'))
  selected_road=Path(meta['road_path']) if 'road_path' in meta else road
  if sha(lcfile)==meta['clcd_sha256'] and sha(selected_road)==meta['road_sha256'] and sha(path)==meta['D_sha256']:return path
  raise RuntimeError('Inputs changed; establish a new workspace')
 with rasterio.open(lcfile) as s,rasterio.open(REF) as t,rasterio.open(road) as a:
  verify_alignment(s,t);verify_alignment(a,t)
  c=s.read(1);prof=s.profile;nodata=s.nodata
  u=set(np.unique(c));unknown=u-set(params)-{nodata};assert not unknown,(yr,unknown)
  for cl,n in [(1,'crop'),(8,'built')]:
   source=np.where(c==nodata,255,(c==cl).astype(np.uint8)).astype(np.uint8)
   write(ROOT/'threat'/f'{n}_{yr}.tif',source,prof,255)
 ws=ROOT/'native'/str(yr)
 stamp=native(yr,lcfile,road,ws,.1)
 with rasterio.open(ws/'deg_sum_c.tif') as ds,rasterio.open(ws/'quality_c.tif') as q,rasterio.open(REF) as t:
  verify_alignment(ds,t);d=ds.read(1);good=(d!=ds.nodata)&np.isfinite(H[c])
  out=np.where(good,d,-9999).astype(np.float32);assert np.min(out[good])>=0
  q0=q.read(1);qs=H[c[good]]*.1**2.5/(d[good].astype(float)**2.5+.1**2.5)
  err=float(abs(qs-q0[good]).max());assert err<1e-6,err
  write(path,out,prof,-9999,dict(provenance='native InVEST 3.20.2 deg_sum_c common projected 30 m extent; China local year-end OSM',year=str(yr)))
 dump(rec,dict(year=yr,source_native=str(ws/'deg_sum_c.tif'),native_stack_sha256=sha(stamp),clcd_sha256=sha(lcfile),road_sha256=sha(road),D_sha256=sha(path),k_invariance='D contains no k. Probe Q verified elementwise using native D and test k=0.1',quality_formula_max_abs_error_probe=err,D_minmax=[float(d[good].min()),float(d[good].max())]))
 print('D_READY',yr,err,flush=True)
 return path
def finalize(maskpath):
 with rasterio.open(maskpath) as ds, rasterio.open(REF) as t:
  verify_alignment(ds,t);ma=ds.read(1);ma=ma==1
 assert ma.any()
 maxima={}; no={}
 for yr in range(2015,2026):
  with rasterio.open(ROOT/'degradation'/f'D_{yr}.tif') as f,rasterio.open(YEAR_DIR/f'CLCD_{yr}.tif') as l:
   d=f.read(1);c=l.read(1);vr=ma & np.isin(c,[2,3,4,5,9]) & (d!=f.nodata);assert vr.any()
   maxima[yr]=float(np.max(d[vr]));no[yr]=int(vr.sum())
 k=max(maxima.values())*.5
 corrected=ROOT/'correction_2016'/'2016_correction.json'
 certified=json.loads(corrected.read_text(encoding='utf8')) if corrected.exists() else {}
 if certified:
  assert certified['common_k']==k and certified['corrected_hq_sha256']==sha(ROOT/'results'/'HQI_2016.tif')
 dump(ROOT/'full_scope_frozen_k.json',dict(documented_road_correction_2016=str(corrected) if certified else None,domain_mask=str(maskpath),domain_mask_sha256=sha(maskpath),domain_pixels=int(ma.sum()),reference_class_codes=[2,3,4,5,9],Dmax_by_year=maxima,reference_count_by_year=no,k=k,transformation='half maximum across all 11 times inside plan body'))
 for yr in range(2015,2026):
  if yr==2016 and certified:continue
  fp=ROOT/'degradation'/f'D_{yr}.tif';dest=ROOT/'results'/f'HQI_{yr}.tif'
  with rasterio.open(fp) as f,rasterio.open(YEAR_DIR/f'CLCD_{yr}.tif') as l:
   d=f.read(1);c=l.read(1);prof=f.profile;good=(d!=f.nodata)&np.isfinite(H[c])
   q=np.full(d.shape,-9999,np.float32);da=d[good].astype(float)
   q[good]=(H[c[good]]*k**2.5/(da**2.5+k**2.5)).astype(np.float32);assert 0<=q[good].min()<=q[good].max()<=1.
   write(dest,q,prof,-9999,dict(provenance='InVEST native D, common k, z=2.5',common_k=str(k),domain_mask_sha256=sha(maskpath),year=str(yr)))
  print('Q_READY',yr,dest,flush=True)
 return k
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--wait',action='store_true');parser.add_argument('--final-mask',type=Path);parser.add_argument('--workers',type=int,default=1);p=parser.parse_args()
 if p.final_mask:
  finalize(p.final_mask);return
 def ready(yr):return (YEAR_DIR/f'CLCD_{yr}.tif').exists() and (ROOT/'road'/str(yr)/'receipt.json').exists()
 pending=set(range(2015,2026));running={}
 with concurrent.futures.ThreadPoolExecutor(p.workers) as ex:
  while pending or running:
   for y,f in list(running.items()):
    if f.done():f.result();del running[y]
   for y in sorted(pending.copy()):
    if len(running)>=p.workers:break
    if ready(y):
     running[y]=ex.submit(degradation,y);pending.remove(y)
   if not running and pending and not p.wait:
    raise RuntimeError('Missing road, CLCD: '+str(sorted(pending)))
   if pending or running:time.sleep(3)
if __name__=='__main__':main()