from pathlib import Path
import sys
import numpy as np, pandas as pd,geopandas as gp,rasterio as rio,shapely
base=Path('D:/ER219_work/annual_actual'); w=Path(__file__).resolve().parent
sys.path.insert(0,str(base/'analysis/geo'))
from exactextract import exact_extract
g=gp.read_file(w.parent/'core/annual_grid_500.gpkg',layer='grid500',ignore_geometry=True)
previous=Path('D:/ER219_work/towndisc11/evidence')
root=base/'mcr'
out=[]
with rio.open(root/'2015'/'MCR_2015.tif') as ds:
    geo=gp.GeoDataFrame({'grid_id':g.grid_id,'geometry':shapely.box(g.ix.to_numpy()*500,g.iy.to_numpy()*500,(g.ix.to_numpy()+1)*500,(g.iy.to_numpy()+1)*500)},crs=ds.crs)
    masks=exact_extract(ds,geo,['cell_id','coverage'],include_cols=['grid_id'],output='pandas')
sources={}
for t,fn in [((0,0),root/'2015/surface_dpc.f32'),((1,1),root/'2025/surface_dpc.f32'),((0,1),previous/'mcr_resistance2015_source2025/surface_dpc.f32'),((1,0),previous/'mcr_resistance2025_source2015/surface_dpc.f32')]:
    sources[t]=np.memmap(fn,mode='r',dtype='float32')
for r in masks.itertuples():
    c=np.asarray(r.cell_id,int);a=np.asarray(r.coverage,float)
    v={k:np.average(y[c],weights=a) for k,y in sources.items()}
    resistance=((v[1,0]-v[0,0])+(v[1,1]-v[0,1]))/2
    source=((v[0,1]-v[0,0])+(v[1,1]-v[1,0]))/2
    delta=v[1,1]-v[0,0]
    assert abs(delta-source-resistance)<1e-8
    out.append(dict(grid_id=r.grid_id,mcr2015=v[0,0],mcr2025=v[1,1],delta_MCR_raw=delta,resistance=resistance,source=source))
pd.DataFrame(out).to_csv(w/'全区各格MCR源地与阻力面双方案分解.csv',index=False,encoding='utf-8-sig')
