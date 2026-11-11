from pathlib import Path
from hashlib import sha256
import json
import geopandas as gp,numpy as np,pandas as pd,shapely as sh,rasterio as rio
from rasterio.features import rasterize
from shapely.geometry import box
W=Path(__file__).resolve().parent;A=Path('D:/ER219_work/annual_actual')
SRC=Path('D:/ER219_project/GIS数据/GIS数据/二道绿隔范围.shp')
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),'utf8')
def build():
 with rio.open(A/'years/model/CLCD_2020.tif') as d:crs,tr,height,width=d.crs,d.transform,d.height,d.width
 source=gp.read_file(SRC).to_crs(crs);assert source.is_valid.all();U=sh.union_all(source.geometry.to_numpy());sh.prepare(U)
 assert abs(U.area/1e6-922.186011)<1e-5
 gp.GeoDataFrame({'scope':['原始GIS二道绿隔范围.shp'],'km2':[U.area/1.e6]},geometry=[U],crs=crs).to_file(W/'scope.gpkg',layer='planning_scope',driver='GPKG')
 def grid(s,j=0):
  ox=(j&1)*s/2;oy=(j>>1)*s/2
  x0,y0,x1,y1=U.bounds
  x,y=np.meshgrid(np.arange(np.floor((x0-ox)/s),np.ceil((x1-ox)/s),dtype=int),np.arange(np.floor((y0-oy)/s),np.ceil((y1-oy)/s),dtype=int));x=x.ravel();y=y.ravel()
  g=sh.box(x*s+ox,y*s+oy,(x+1)*s+ox,(y+1)*s+oy);ok=sh.intersects(U,g);x=x[ok];y=y[ok];g=g[ok];inside=sh.covers(U,g)
  g[~inside]=sh.intersection(U,g[~inside]);area=sh.area(g);keep=area>1e-6
  df=pd.DataFrame({'ix':x[keep],'iy':y[keep],'area':area[keep]})
  assert abs(df.area.sum()-U.area)<.002
  df.to_csv(W/f'cells_{s}_{j}.csv',index=False)
  if s==500 and j==0:
   assert len(df)==4478
   layer=gp.GeoDataFrame(df.copy(),geometry=g[keep],crs=crs);layer['grid_id']=[f'{s}_{a}_{b}' for a,b in zip(df.ix,df.iy)]
   layer.to_file(W/'annual_grid_500.gpkg',layer='grid500',driver='GPKG')
  print(s,j,len(df),flush=True)
 for s in (500,1000,200):grid(s)
 with rio.open(A/'years/model/CLCD_2020.tif') as ds:
  win=ds.window(*U.bounds); from rasterio.windows import Window
  win=Window(np.floor(win.col_off)-1,np.floor(win.row_off)-1,np.ceil(win.width)+3,np.ceil(win.height)+3)
  mask=rasterize([(U,1)],out_shape=(int(win.height),int(win.width)),transform=ds.window_transform(win),dtype='uint8',all_touched=False).astype(bool)
 highs={};cnt={}
 for yr in range(2015,2026):
  with rio.open(A/f'years/model/CLCD_{yr}.tif') as ds,rio.open(A/f'hq/degradation/D_{yr}.tif') as deg:
   land=ds.read(1,window=win); D=deg.read(1,window=win);valid=mask & np.isin(land,[2,3,4,5,9]) & (D!=deg.nodata);highs[yr]=float(D[valid].max());cnt[yr]=int(valid.sum())
 k=max(highs.values())/2
 files={p.name:sha256(p.read_bytes()).hexdigest() for p in SRC.parent.glob(SRC.stem+'.*') if p.suffix.lower() in {'.shp','.shx','.dbf','.prj'}}
 dump(W/'domain.json',{'source':str(SRC),'sha256':files,'n_source_shapes':len(source),'area_km2':U.area/1e6,'n_30m_centres':int(mask.sum()),'new_hq_k':k,'D_max_by_year':highs,'bluegreen_pixel_centres_by_year':cnt,'original_k':json.loads((A/'hq/full_scope_frozen_k.json').read_text())['k'],'native_crs':crs.to_wkt()})
if __name__=='__main__':build()
