from pathlib import Path
import numpy as np,rasterio as rio,json,pandas as pd
from rasterio.windows import Window
D=Path(__file__).resolve().parent
base=next(z for z in Path.cwd().rglob('EOG2020官方原件') if z.is_dir())
files=list(base.glob('*.dat.tif'));orig=Path('D:/ER219_work/aggregation/ntl_native')
results=[]
for f in files:
 kind='average_masked' if 'average_masked' in f.name else ('cf_cvg' if 'cf_cvg' in f.name else None)
 if not kind:continue
 loc=next(orig.glob('*'+kind+'*.tif'))
 with rio.open(loc) as l,rio.open(f) as s:
  assert l.crs==s.crs and np.allclose(l.res,s.res)
  row,col=s.index(*l.xy(0,0));w=Window(col,row,l.width,l.height);gt=s.read(1,window=w)
  assert np.array_equal(l.read(1),gt)
  results.append({'layer':kind,'all_pixels_identical':True,'shape':list(gt.shape),'local_native_file':str(loc),'official_global_file':str(f.resolve()),'url':l.tags().get('source_url')})
print(results)
(D/'EOG_global_original_window_check.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf8')
