from pathlib import Path
from hashlib import file_digest
from contextlib import ExitStack
import numpy as np, rasterio as r,json
from rasterio.merge import merge
from rasterio.warp import reproject,Resampling
from scipy import ndimage as nd
from clcd_native import original_model
out=Path(__file__).parent/'model'
sources=sorted(next(Path(r'D:\ER219_raw').glob('NASADEM*完整*')).glob('*.tif'))
sha=lambda f:file_digest(f.open('rb'),'sha256').hexdigest()
with ExitStack() as st:
 old=st.enter_context(r.open(out/'CLCD_2020.tif'))
 src=[st.enter_context(r.open(f)) for f in sources]
 merged,t=merge(src,nodata=-9999,dtype='float32')
 dem=np.full(old.shape,-9999,dtype='float32')
 reproject(merged[0],dem,src_transform=t,src_crs=src[0].crs,src_nodata=-9999,dst_transform=old.transform,dst_crs=old.crs,dst_nodata=-9999,resampling=Resampling.bilinear)
 del merged
 profile=old.profile.copy();profile.update(dtype='float32',nodata=-9999)
 missing=dem==-9999
 if missing.any():inds=nd.distance_transform_edt(missing,return_distances=False,return_indices=True);fill=dem[tuple(inds)];del inds
 else:fill=dem
 gy,gx=np.gradient(fill,30,30);sl=np.rad2deg(np.arctan(np.hypot(gx,gy)));del gx,gy
 bad=nd.binary_dilation(missing,np.array([[0,1,0],[1,1,1],[0,1,0]]))
 sl[bad]=-9999
 for filename,a in [('NASA_elevation_m',dem),('NASA_degrees_slope',sl)]:
  tmp=out/(filename+'.partial.tif'); dest=out/(filename+'.tif')
  with r.open(tmp,'w',**profile) as d:d.write(a,1)
  tmp.replace(dest)
 receipt=dict(sources=[dict(path=str(f),sha256=sha(f)) for f in sources],dem_invalid=int(missing.sum()),slope_invalid=int(bad.sum()),total=dem.size,method='Identical to 2020 initial pilot: merge NADASEM tiles and reproject bilinear into common CLCD native CRS, 30 m central finite differences; invalidate any slope pixel neighbouring no-DEM axially; same surface every year',bbox=old.bounds,cell=30)
 print(receipt['dem_invalid'],receipt['slope_invalid'])
 (out/'NASADEM_source_and_methods.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf8')
