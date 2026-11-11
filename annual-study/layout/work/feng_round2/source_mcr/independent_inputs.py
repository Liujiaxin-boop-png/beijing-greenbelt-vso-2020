from pathlib import Path
import csv,numpy as np,rasterio as rio,json
from prepare import D,save
p=D/'native_verify';p.mkdir(exist_ok=True)
with rio.open(D/'sources_dpc.tif') as s:a=s.read(1);pr=s.profile
ids=np.unique(a[a>0]).tolist()
for k in ids:
 q=pr.copy();q.update(dtype='uint8',nodata=0,compress='lzw')
 with rio.open(p/('src_'+str(k)+'.tif'),'w',**q) as t:t.write((a==k).astype('uint8'),1)
(p/'ids.json').write_text(json.dumps(ids))
