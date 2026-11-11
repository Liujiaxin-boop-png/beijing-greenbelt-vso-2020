"""Actual planning area, native cell fractions, and support of habitat transitions for the three grid sizes."""
from pathlib import Path
import sys,json,time
import numpy as np,pandas as pd,rasterio as rio,geopandas as gpd,shapely as sg
from scipy.sparse import csr_matrix,save_npz,load_npz
from surfaces import A,grid_limits
sys.path.insert(0,str(Path(__file__).resolve().parent/'geo'))
from exactextract import exact_extract
from exactextract.raster import NumPyRasterSource
OUT=A/'support';OUT.mkdir(exist_ok=True)
SCOPE=A/'boundary/beijing_greenbelt_full.gpkg'
def scope():
 return gpd.read_file(SCOPE,layer='planning_scope')[['geometry']].dissolve()
def parts(geo,raster):
 return exact_extract(raster,geo,['cell_id','coverage'],output='pandas')
def make_cells(s,ox,oy,limits,g,base):
 x0,y0,x1,y1=map(int,limits);w=x1-x0;h=y1-y0
 rr=NumPyRasterSource(np.ones((h,w),'uint8'),x0*s+ox,y0*s+oy,x1*s+ox,y1*s+oy,srs_wkt=g.crs.to_wkt())
 res=parts(g,rr).iloc[0];ids=np.asarray(res.cell_id); ix=x0+ids%w;iy=y1-1-ids//w
 area=np.asarray(res.coverage,dtype='float64')*s*s
 tab=pd.DataFrame({'ix':ix,'iy':iy,'area':area});tab=tab[tab.area>0].sort_values(['iy','ix']).reset_index(drop=True)
 assert abs(tab.area.sum()-g.area.sum())<100., (s,tab.area.sum(),g.area.sum())
 tab.to_csv(base,index=False)
 return tab
def polygons(tab,s,g):
 x=tab.ix.to_numpy()*s;y=tab.iy.to_numpy()*s;geom=sg.box(x,y,x+s,y+s)
 partial=np.flatnonzero(tab.area.values<s*s-1e-5)
 tiles=np.column_stack((x[partial]//2000,y[partial]//2000))
 lng=g.geometry.iloc[0]
 for (tx,ty) in np.unique(tiles,axis=0):
  ids=partial[(tiles[:,0]==tx)&(tiles[:,1]==ty)]
  local=lng.intersection(sg.box(tx*2000,ty*2000,(tx+1)*2000,(ty+1)*2000))
  geom[ids]=sg.intersection(geom[ids],local)
 return gpd.GeoDataFrame(tab.copy(),geometry=geom,crs=g.crs)
def transition(s,g):
 cov=pd.read_csv(OUT/f'cells_{s}_0.csv'); polys=polygons(cov,s,g)
 with rio.open(A/'years/model/CLCD_2020.tif') as f:
  nr,nc=f.shape;wkt=f.crs.to_wkt();bounds=f.bounds
 src=NumPyRasterSource(np.zeros((nr,nc),'uint8'),*bounds,srs_wkt=wkt)
 dest=OUT/f'native_weights_{s}.npz'
 if not dest.exists():
  v=parts(polys,src);idx=np.concatenate(v.cell_id).astype('int32')
  wg=np.concatenate(v.coverage).astype(float)*900
  sizes=np.array([len(x) for x in v.cell_id]);off=np.r_[0,np.cumsum(sizes)]
  mat=csr_matrix((wg,idx,off),shape=(len(polys),nr*nc));save_npz(dest,mat)
 else:mat=load_npz(dest)
 geomarea=polys.area.to_numpy()
 assert abs(mat.sum()-g.area.sum())<300 and np.max(np.abs(mat.sum(axis=1).A1-geomarea))<20
 # Store the actual intersected finest grid geometry only in public layers when needed.
 if s==500:polys.to_file(OUT/'annual_grid_500.gpkg',layer='grid500',driver='GPKG')
 ref=None; outcomes={}
 for y in range(2015,2026):
  with rio.open(A/'years/model'/f'CLCD_{y}.tif') as f:v=f.read(1).ravel()
  cats=np.zeros_like(v);cats[np.isin(v,[2,3])]=1;cats[v==4]=2;cats[np.isin(v,[5,9])]=3
  vals={'vegetated':mat@np.isin(cats,[1,2]).astype('float32'),'wood':mat@(cats==1).astype('float32'),'grass':mat@(cats==2).astype('float32'),'water':mat@(cats==3).astype('float32')}
  if ref is not None:
   for name,mask in [('converted',(cats!=ref)&((cats>0)|(ref>0))),('new_green',(cats<=2)&(cats>0)&((ref==0)|(ref==3))),('lost_green',(ref<=2)&(ref>0)&((cats==0)|(cats==3)))]:
    vals[name]=mat@mask.astype('float32')
  for k,a in vals.items():outcomes[f'{k}_{y}']=a
  ref=cats
 np.savez_compressed(OUT/f'habitat_m2_{s}.npz',**outcomes)
if __name__=='__main__':
 g=scope()
 for s in [500,1000,200]:
  for j in range(4):
   make_cells(s,(j&1)*s//2,(j>>1)*s//2,grid_limits(s,j),g,OUT/f'cells_{s}_{j}.csv')
  # Half-grid overlay for exact same-position comparison of re-originated results.
  lim=np.array(grid_limits(s,0))*2
  make_cells(s//2,0,0,lim,g,OUT/f'halfcells_{s}.csv')
  print('scope area by origins',s,flush=True)
  transition(s,g);print('overlays and annual transitions complete',s,flush=True)
