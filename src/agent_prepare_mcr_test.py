"""Make tiny synthetic inputs using GDAL/rasterio, for native ArcMap tests."""
from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.transform import from_origin

root=Path('D:/ER219_work/native_tests/synthetic_mcr_gdal')
root.mkdir(parents=True,exist_ok=True)
p=np.zeros((9,11),dtype=np.int32)
p[1:4,1:4]=10;p[5:8,8:10]=20;p[6:8,1:3]=30
s=np.zeros_like(p);s[2,2]=10;s[6,9]=20
c=np.ones_like(p,dtype=np.float32);c[1:8,5]=10
conf={'out_dir':str(root/'run'),'synthetic_only':True}
for arr,key,filename,nd in [(p,'parent_raster','parent.tif',0),(s,'source_parent_raster','source.tif',0),(c,'cost_raster','cost.tif',-9999)]:
    path=root/filename
    with rasterio.open(path,'w',driver='GTiff',height=9,width=11,count=1,dtype=arr.dtype,
                       transform=from_origin(500000,4400270,30,30),crs='EPSG:32650',nodata=nd) as dst:
        dst.write(arr,1)
    conf[key]=str(path)
(root/'synthetic_config.json').write_text(json.dumps(conf,indent=2),encoding='utf-8')
print(root/'synthetic_config.json')
