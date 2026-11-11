from pathlib import Path
import sys,time,os,subprocess,concurrent.futures,json,hashlib
import numpy as np,rasterio as rio
from scipy.ndimage import distance_transform_edt
A=Path(__file__).resolve().parents[1];OUT=A/'landscape';S=Path(__file__).resolve().parent
BOX=(915000,4303000,997000,4391000)
# This rectangle is only a computation cache; the verified planning shape defines all tabulations.
def get(y):
 raw=A/'years'/'model'/f'CLCD_{y}.tif';d=OUT/str(y);d.mkdir(parents=True,exist_ok=True)
 if (d/'finished.json').exists():return
 with rio.open(raw) as f:
  a=f.read(1); t=f.transform
 if int(a.max())>9:raise RuntimeError('unexpected land cover code')
 eco=np.isin(a,[2,3,4,5,9]);dst=distance_transform_edt(~eco,sampling=30).astype('float32')
 p=d/'land.raw';q=d/'distance.raw';a.tofile(p);dst.tofile(q)
 subprocess.run([str(S/'Landscape.exe'),str(p),str(q),str(a.shape[1]),str(a.shape[0]),repr(t.c),repr(t.f),str(d),*[str(v) for v in BOX]],check=True)
 with (d/'fields_500_0.bin').open('rb') as f:
  x0,y0,x1,y1=np.fromfile(f,dtype='<i4',count=4);v=np.fromfile(f,dtype='<f8').reshape(y1-y0,x1-x0,10)
 assert (np.isfinite(v[...,0])).all() and np.nanmax(v[...,9])<1.000001
 if y==2020:
  import pandas as pd
  old=pd.read_csv(r'D:\ER219_work\feng_round2\pilot\Feng_six_500m.csv')
  idx=old.grid_id.str.split('_');ox=int(921000/500);oy=int(4309000/500)
  ij=np.array([[int(q[1])+ox-x0,int(q[2])+oy-y0] for q in idx]);rows=v[ij[:,1],ij[:,0]]
  for i,c in enumerate(['LDI','FN_density_per_km2','SPLIT','DIVISION','SSI','LRI']):
   if c!='SSI':
    assert np.allclose(rows[:,i],old[c].to_numpy(),atol=1e-5,rtol=1e-6,equal_nan=True),c
   else:
    from scipy import ndimage as nd
    sys.path.insert(0,r'D:\ER219_work\feng_round2\pilot')
    from five_indices import get_window
    v_old=old[c].to_numpy();diff=np.abs(rows[:,i]-v_old)
    assert np.array_equal(np.isnan(v_old),np.isnan(rows[:,i]))
    bad=np.flatnonzero(diff>1e-4)
    for j in np.unique(np.r_[bad,np.arange(0,len(rows),127)]):
     ix,iy=ij[j,0]+x0,ij[j,1]+y0
     sl,ar,cent=get_window([ix*500,iy*500,(ix+1)*500,(iy+1)*500],t)
     patches,n=nd.label((a[sl]==8)&(ar>1e-8),np.ones((3,3)))
     vv=nd.minimum(dst[sl],labels=patches,index=np.arange(1,n+1)).mean() if n else np.nan
     assert np.isclose(rows[j,i],vv,atol=1e-4,equal_nan=True)
    (d/'ssi_accuracy.json').write_text(json.dumps({'native_vs_exact_EDT_mean_patch_grid_max_m':float(np.nanmax(diff)),'n_paired':int(np.isfinite(v_old).sum()),'n_deviation_over_0.1mm':len(bad),'checked_against_independent_scipy_label_and_minimum':True},indent=2))
 (d/'finished.json').write_text(json.dumps({'year':y,'cache_box':BOX,'pilot_grid_crosscheck_9001_cells_see_SSI_accuracy':True if y==2020 else None,'sha256':hashlib.file_digest(raw.open('rb'),'sha256').hexdigest()},indent=2))
def batch():
 OUT.mkdir(exist_ok=True); todo=set(range(2015,2026));fut={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  while todo or fut:
   for y,f in list(fut.items()):
    if f.done():
     del fut[y]
     if f.result():raise RuntimeError(str(y)+' failed')
   for y in sorted(todo,key=lambda x:(x!=2020,x)):
    if len(fut)>=2:break
    if not (A/'years'/'model'/f'CLCD_{y}.tif').exists():continue
    def job(yr):
     with (OUT/f'{yr}.log').open('w',encoding='utf8') as f:return subprocess.run([sys.executable,'-u',__file__,str(yr)],stdout=f,stderr=subprocess.STDOUT).returncode
    fut[y]=pool.submit(job,y);todo.remove(y)
   if todo or fut:time.sleep(2)
if __name__=='__main__':
 if len(sys.argv)==1:batch()
 else:get(int(sys.argv[1]))
