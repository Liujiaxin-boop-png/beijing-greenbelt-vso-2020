"""Exact means of piecewise constant raster pixels inside full squares, on all 12 grids."""
from pathlib import Path
import sys,json,time,concurrent.futures,os,argparse,hashlib
import numpy as np,rasterio as rio
A=Path(__file__).resolve().parents[1]; OUT=A/'surfaces'
YEARS=range(2015,2026)
def source(y,name):
 if name=='MCR':return A/'mcr'/str(y)/f'MCR_{y}.tif'
 if name=='HQI':return A/'hq/results'/f'HQI_{y}.tif'
 if name=='HQI_commonroad':return A/'hq/results'/f'HQI_{y}_commonroad.tif'
 return A/'mcr_checks'/str(y)/(name+'.tif')
def grid_limits(s,sh,y=2020):
 p=A/'landscape'/str(y)/f'fields_{s}_{sh}.bin'
 with p.open('rb') as f:return np.fromfile(f,'<i4',4)
def grids_mean(pref,tr,limits,s,sh):
 x0,y0,x1,y1=limits;ox=(sh&1)*s/2;oy=(sh>>1)*s/2
 xx=(np.arange(x0,x1+1)*s+ox-tr.c)/30; yy=(tr.f-(np.arange(y0,y1+1)*s+oy))/30
 ix=xx.astype(int); iy=yy.astype(int);wx=xx-ix;wy=(yy-iy)[:,None]
 z0=(1-wx)*pref[np.ix_(iy,ix)]+wx*pref[np.ix_(iy,ix+1)]
 z1=(1-wx)*pref[np.ix_(iy+1,ix)]+wx*pref[np.ix_(iy+1,ix+1)]
 z=z0+wy*(z1-z0)
 return -(z[1:,1:]-z[:-1,1:]-z[1:,:-1]+z[:-1,:-1])*(30./s)**2
def run(y,name):
 path=source(y,name);out=OUT/str(y);out.mkdir(exist_ok=True,parents=True)
 dims=[(500,0)] if name not in ('HQI','MCR') else [(s,j) for s in (500,1000,200) for j in range(4)]
 if all((out/f'{name}_{s}_{sh}.npz').exists() and (out/f'{name}_{s}_{sh}.npz').stat().st_mtime_ns >= path.stat().st_mtime_ns for s,sh in dims):return
 with rio.open(path) as f:
  v=f.read(1);tr=f.transform; nr,nc=f.shape
  nod=f.nodata; assert np.isfinite(v).all() and (v>=-1e-8).all(),(path,float(v.min()),nod)
 pref=np.zeros((nr+1,nc+1),np.float64)
 np.cumsum(v,axis=0,out=pref[1:,1:],dtype=np.float64);np.cumsum(pref[1:,1:],axis=1,out=pref[1:,1:])
 low,high=float(v.min()),float(v.max());del v
 for s,sh in dims:
  item=out/f'{name}_{s}_{sh}.npz';lim=grid_limits(s,sh);m=grids_mean(pref,tr,lim,s,sh)
  assert m.min()>=low-1.e-5 and m.max()<=high+1.e-5
  tmp=item.with_suffix('.part.npz');np.savez_compressed(tmp,arr=m,limits=lim);os.replace(tmp,item)
 if name=='MCR' and y==2020:
  import pandas as pd
  old=pd.read_csv(r'D:\ER219_work\feng_round2\pilot\Feng_six_500m.csv')
  data=np.load(out/'MCR_500_0.npz');lim=data['limits'];m=data['arr'];ij=np.array([[int(t.split('_')[1])+1842,int(t.split('_')[2])+8618] for t in old.grid_id]);err=float(abs(m[ij[:,1]-lim[1],ij[:,0]-lim[0]]-old.MCR).max());assert err<.005
  (out/'verification_9001_grids.json').write_text(json.dumps({'maximum_difference':err,'variable':'MCR','source':'2020 previous Feng trial 9001 matching full 500m grids'}))
def main():
 todo={(y,n) for y in YEARS for n in ('MCR','HQI','MCR_half500','MCR_half2000')}
 todo|={(y,n) for y in [2015,2025] for n in ('MCR_expand10200','HQI_commonroad')}
 while todo:
  work=[]
  for y,n in sorted(todo,key=lambda k:(k[1]!='MCR', k[1]!='HQI',k[0] not in (2015,2025),k[0])):
   if source(y,n).exists():work.append((y,n))
  for y,n in work:
   run(y,n);todo.remove((y,n))
  if todo:time.sleep(3)
if __name__=='__main__':main()
