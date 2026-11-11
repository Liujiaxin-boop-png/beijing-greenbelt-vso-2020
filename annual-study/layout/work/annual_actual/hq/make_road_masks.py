import argparse, pathlib, time, json, os, subprocess, hashlib
import geopandas as gpd
import rasterio, numpy as np
from shapely.geometry import box
from fetch_annual_roads import ROOT, VECTORS, sha, dump
RASTER=ROOT/'road';RASTER.mkdir(exist_ok=True)
TEMPLATE=pathlib.Path(r'D:\ER219_work\spatial\clcd2020.tif')
ARCPY=pathlib.Path(r'F:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe')
def rasterize(yr):
 with rasterio.open(TEMPLATE) as s:
  bounds=s.bounds;crs=s.crs;aff=s.transform;dims=s.shape;profile=s.profile.copy()
 vp=VECTORS/f'OSM_major_{yr}.gpkg'
 od=RASTER/str(yr);od.mkdir(exist_ok=True)
 raw=od/'arc_road.tif';sp=od/'roads.shp';out=RASTER/f'roads_{yr}.tif';rec=od/'receipt.json'
 if out.exists() and rec.exists():return
 g=gpd.read_file(vp)
 assert g.crs==crs
 g=g[g.intersects(box(*bounds))].copy()
 if not sp.exists():
  sh=g[['geometry']].copy();sh['roadval']=np.ones(len(sh),np.int32)
  sh.to_file(sp,driver='ESRI Shapefile',engine='pyogrio',encoding='utf8')
 if not raw.exists():
  cmd=[str(ARCPY),str(pathlib.Path(__file__).with_name('rasterize_arcmap.py')),str(sp),str(TEMPLATE),str(raw)]
  proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (od/'arc_log.txt').write_bytes(proc.stdout)
  if proc.returncode:raise RuntimeError(proc.stdout[-1800:].decode('utf8','replace'))
 with rasterio.open(raw) as a:
  assert a.shape==dims and all(abs(x-y)<1e-7 for x,y in zip(a.transform,aff)),(a.transform,aff,a.shape,dims)
  data=(a.read(1,masked=True).filled(0)==1).astype('uint8')
 assert data.any()
 profile.update(driver='GTiff',dtype='uint8',nodata=255,tiled=True,blockxsize=256,blockysize=256,compress='deflate')
 tmp=out.with_name(out.stem+'_writing.tif')
 with rasterio.open(tmp,'w',**profile) as dst:
  dst.write(data,1);dst.update_tags(reference=str(vp),year=yr,algorithm='ArcGIS Pro 3.1.6 PolylineToRaster MAXIMUM_LENGTH, 1 if assigned a road, aligned 30m')
 os.replace(tmp,out)
 dump(rec,dict(year=yr,lines_intersecting_background=len(g),positive_pixels=int(data.sum()),road=str(out),sha256=sha(out),vector_sha256=sha(vp),shape=dims))
 print('ARC_RASTER',yr,int(data.sum()),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');args=p.parse_args()
 for y in range(2015,2026):
  while not (VECTORS/f'OSM_major_{y}.gpkg').exists() or not (pathlib.Path(r'D:\ER219_raw\年度分析_2015_2025\OSM年末主要道路')/f'ohsome_{y}_provenance.json').exists():
   if not args.wait:raise SystemExit(f'waiting for vector {y}')
   time.sleep(4)
  rasterize(y)
