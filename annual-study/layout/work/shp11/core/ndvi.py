"""Extract MOD13Q1 source windows for the five full summer composites and integrate clipped 500 m cells."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import datetime, hashlib, json, math, time, warnings
import requests
import numpy as np, pandas as pd, geopandas as gp, shapely, rasterio, tifffile
from rasterio.warp import transform_bounds
from rasterio.windows import Window
from scipy.sparse import coo_matrix
from pyproj import Transformer

here=Path(__file__).resolve().parent
root=Path(r'D:/ER219_results/年度评价_2015_2025')
raw=Path(r'D:/ER219_raw/年度分析_2015_2025/MOD13Q1_2020_夏季独立观测')
raw.mkdir(parents=True,exist_ok=True)
import json
grid=gp.read_file(here/'annual_grid_500.gpkg',layer='grid500')[['ix','iy','geometry']].reset_index(drop=True)
assert len(grid)==4478 and grid.crs.is_projected
items=json.loads((raw/'STAC_10_items.json').read_text('utf8'))
assert len(items)==10
area=grid.area.values;area_good=np.zeros(len(grid));area_total=np.zeros(len(grid));weighted=np.zeros(len(grid))
for tile in ['h26v04','h26v05']:
    images=sorted([f for f in items if tile in f['id']],key=lambda f:f['id'])
    cube=[]
    for f in images:
        with rasterio.open(raw/(f['id']+'_NDVI.tif')) as z,rasterio.open(raw/(f['id']+'_QA.tif')) as q:
            assert z.transform==q.transform and z.shape==q.shape
            a=z.read(1);qa=q.read(1);aff=z.transform;native=z.crs;nr,nc=z.shape
            cube.append(np.where((qa==0)&(a>=-2000)&(a<=10000),a*1e-4,np.nan))
    stack=np.stack(cube);good=np.isfinite(stack).sum(axis=0)>=3
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning)
        median=np.nanmedian(stack,axis=0)
    rr,cc=np.indices((nr,nc));X=aff.c+aff.a*cc.ravel();Y=aff.f+aff.e*rr.ravel()
    boxes=shapely.box(X,Y+aff.e,X+aff.a,Y)
    # The upper/lower edge of a sinusoidal pixel is curved after projection; densify before transformation.
    tr=Transformer.from_crs(native,grid.crs,always_xy=True)
    boxes=shapely.transform(shapely.segmentize(boxes,60),tr.transform,interleaved=False)
    i,j=shapely.STRtree(boxes).query(grid.geometry.values,predicate='intersects')
    ar=shapely.area(shapely.intersection(grid.geometry.values[i],boxes[j]));M=coo_matrix((ar,(i,j)),shape=(len(grid),len(boxes))).tocsr()
    area_total+=np.asarray(M.sum(axis=1)).ravel();area_good+=M@good.ravel().astype(float)
    weighted+=M@np.where(good,median,0).ravel()
ratio=area_total/area
assert np.max(np.abs(ratio-1))<1e-4,(ratio.min(),ratio.max())
res=pd.DataFrame(grid.drop(columns='geometry'))
res['ndvi']=np.divide(weighted,area_good,out=np.full(len(grid),np.nan),where=area_good>0)
res['valid_fraction']=np.clip(area_good/area,0,1);res['area_km2']=area/1e6
res.to_csv(here/'ndvi500.csv',index=False,encoding='utf-8-sig',float_format='%.10g')
metadata=dict(source='NASA MOD13Q1 V061, Terra, NASA DOI 10.5067/MODIS/MOD13Q1.061, Microsoft Planetary Computer COG archive',sixteen_day_periods=['2020-06-09','2020-06-25','2020-07-11','2020-07-27','2020-08-12'],quality='pixel reliability == 0, raw NDVI -2000 to 10000, scale .0001; >=3 of 5 good composites in native nominal 250m pixel; pixel median then area-weighted grid mean on clipped plan area',n=len(grid),n80=int(sum(res.valid_fraction>=.8)),area80_km2=float(res.loc[res.valid_fraction>=.8,'area_km2'].sum()),pixel_overlap_area_ratio_range=[float(ratio.min()),float(ratio.max())])
(here/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
print(metadata)
