"""2020 support-faithful EOG/WorldPop extraction. Inputs land in raw. Fully square 500 m support.
Spherical mesh quadrilaterals projected into the equal-area analysis CRS; native values never resampled."""
from pathlib import Path
import rasterio as rio,numpy as np,pandas as pd,geopandas as gpd,shapely as sh
from rasterio import windows as rw
from pyproj import Transformer
from datetime import datetime,timezone
import json,sys,time,hashlib,shutil
D=Path(__file__).resolve().parent
G=next(D.parents[2].rglob('annual_grid_500.gpkg'))
SRC=D/'raw'/'EOG2020_原生窗口'
if not SRC.is_dir():SRC=Path('D:/ER219_work/aggregation/ntl_native')
W=500
FRAME=gpd.read_file(G,layer='grid500').sort_values(['iy','ix']).reset_index(drop=True)
IX=FRAME.ix.to_numpy();IY=FRAME.iy.to_numpy()
assert FRAME.grid_id.is_unique and len(FRAME)==4478
BASE=FRAME[['grid_id','ix','iy','area']].rename(columns={'area':'intersection_m2'})
TR=Transformer.from_crs(FRAME.crs,4326,always_xy=True)
FWD=Transformer.from_crs(4326,FRAME.crs,always_xy=True)
XS=IX[:,None]*W+np.array([0,W,W,0])
YS=IY[:,None]*W+np.array([0,0,W,W])
LON,LAT=TR.transform(XS,YS)
GRIDBOX=sh.box(IX*W,IY*W,(IX+1)*W,(IY+1)*W)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(2**20),b''):h.update(c)
 return h.hexdigest()
def cross(ds):
 t=ds.transform;dx=t.a;dy=t.e
 assert ds.crs.to_epsg()==4326 and t.b==0 and t.d==0 and dx>0 and dy<0
 cc0=np.floor((LON.min(axis=1)-t.c)/dx).astype(int)-1
 cc1=np.floor((LON.max(axis=1)-t.c)/dx).astype(int)+2
 rr0=np.floor((LAT.max(axis=1)-t.f)/dy).astype(int)-1
 rr1=np.floor((LAT.min(axis=1)-t.f)/dy).astype(int)+2
 c0=max(cc0.min(),0);c1=min(cc1.max(),ds.width);r0=max(rr0.min(),0);r1=min(rr1.max(),ds.height)
 win=rw.Window(int(c0),int(r0),int(c1-c0),int(r1-r0))
 xx,yy=np.meshgrid(t.c+(np.arange(c0,c1+1))*dx,t.f+(np.arange(r0,r1+1))*dy)
 x,y=FWD.transform(xx,yy);del xx,yy
 inds=[];rs=[];cs=[]
 for i,(a,b,c,d) in enumerate(zip(cc0,cc1,rr0,rr1)):
  cols,rows=np.meshgrid(np.arange(max(c0,a)-c0,min(c1,b)-c0),np.arange(max(r0,c)-r0,min(r1,d)-r0))
  inds.append(np.full(cols.size,i));cs.append(cols.ravel());rs.append(rows.ravel())
 i=np.concatenate(inds);r=np.concatenate(rs);c=np.concatenate(cs);ai=[];ar=[];ac=[];ap=[];ag=[]
 for j in range(0,len(i),20000):
  sl=slice(j,j+20000); u=r[sl];v=c[sl];k=i[sl]
  poly=sh.polygons(np.stack([np.stack([x[u,v],y[u,v]],axis=1),np.stack([x[u,v+1],y[u,v+1]],axis=1),np.stack([x[u+1,v+1],y[u+1,v+1]],axis=1),np.stack([x[u+1,v],y[u+1,v]],axis=1)],axis=1))
  overlap=sh.area(sh.intersection(poly,GRIDBOX[k])); sel=overlap>1e-8
  ai.append(k[sel]);ar.append(u[sel]);ac.append(v[sel]);ap.append(sh.area(poly[sel]));ag.append(overlap[sel])
 i,r,c,pa,a=map(np.concatenate,[ai,ar,ac,ap,ag])
 return win,i,r,c,pa,a
def calc(yr,kind):
 if kind=='ntl':
  if yr!=2020: raise ValueError('2020 EOG v2.1 only; no cross-product splicing')
  fn=next(SRC.glob('*average_masked*.tif'));obs=next(SRC.glob('*cf_cvg*.tif'))
 else:
  fn=D/'raw'/f'worldpop_api_beijing_{yr}.tif'
  if not fn.exists():fn=D/'raw'/f'chn_pop_{yr}_CN_100m_R2025A_v1.tif'
  if not fn.exists():raise FileNotFoundError(fn)
 with rio.open(fn) as ds:
  win,i,r,c,pa,a=cross(ds)
  mat=ds.read(1,window=win,masked=True); vec=mat[r,c];val=vec.astype(float).filled(np.nan)
  if kind=='pop' and fn.name.startswith('chn_pop'):
   cp=D/'raw'/f'worldpop_native_beijing_{yr}.tif'
   profile=dict(driver='GTiff',width=mat.shape[1],height=mat.shape[0],crs=ds.crs,dtype=ds.dtypes[0],count=1,transform=ds.window_transform(win),nodata=ds.nodata,compress='deflate')
   with rio.open(cp,'w',**profile) as out:out.write(mat.filled(ds.nodata),1);out.update_tags(product='WorldPop R2025A v1, no resampling',source=fn.name)
  ok=np.isfinite(val)
  rec={'time_utc':datetime.now(timezone.utc).isoformat(),'source':str(fn),'native_tags':ds.tags(),'input_epsg':ds.crs.to_epsg(),'resolution':list(ds.res),'native_window':str(win),'native_window_shape':list(mat.shape),'grid_frame_complete_n':len(FRAME),'units_support':'full 500 x 500 m square, in project Albers; scope intersection only as reporting weight','local_input_sha256':sha(fn),'source_min_max_local_window':[float(mat.min()),float(mat.max())]}
  def b(w,keep=None):
   if keep is None:return np.bincount(i,weights=w,minlength=len(FRAME))
   return np.bincount(i[keep],weights=w[keep],minlength=len(FRAME))
  res=BASE.copy()
  res['raster_cover']=b(a)/250000
  if kind=='ntl':
   with rio.open(obs) as o:
    assert o.transform==ds.transform and o.bounds==ds.bounds
    cf=o.read(1,window=win,masked=True)[r,c].astype(float).filled(np.nan)
   ok=ok&np.isfinite(cf)&(cf>0)
   area=b(a,ok);res['ntl_valid_fraction']=area/250000
   res['ntl_radiance']=np.divide(b(a*val,ok),area,out=np.full(len(area),np.nan),where=area>249999)
   res['ntl_clear_obs_mean']=np.divide(b(a*cf,ok),area,out=np.full(len(area),np.nan),where=area>0)
   rec['obs_source']=str(obs);rec['obs_hash']=sha(obs);rec['physical_unit']='nW/cm2/sr';rec['valid_definition']='Radiance finite, annual cloud-free observation count >0; valid zero radiance retained; area weighted mean on >= 99.9996% valid full square.'
  else:
   ok=ok & (val>=0);area=b(a,ok);res['pop_valid_fraction']=area/250000
   # WorldPop nodata pixels are NOT automatically treated as unpopulated.
   # Outside non-null population support amounts can be interpreted separately if supported by source semantics.
   mass=b(val*a/pa,ok);res['pop_nonnull_people']=mass
   res['pop_density']=np.where(area>249999,mass/0.25,np.nan)
   rec['physical_unit']='input people per native grid square, output people per km2';rec['valid_definition']='NoData not imputed; only practically full supported squares reported as primary (area >249999 m2). Fractional overlap on native population cell assumed uniform.'
  assert np.max(np.abs(res.raster_cover-1))<1e-5
  rec['distribution']=res.describe().to_dict()
  d=f'{kind}_{yr}_grid500'
  res.to_csv(D/(d+'.csv'),index=False,encoding='utf-8-sig');(D/(d+'.json')).write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding='utf-8')
  print(d,res.describe().to_string(),flush=True)
if __name__=='__main__':calc(int(sys.argv[1]),sys.argv[2])
