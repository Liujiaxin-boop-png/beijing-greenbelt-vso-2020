from pathlib import Path
import glob,numpy as np,rasterio as rio,json
from prepare import D
p=D/'native_verify_pro'
ids=json.loads((D/'native_verify'/'ids.json').read_text())
refs=[rio.open(p/f'cd_{k}.tif') for k in ids]
test=rio.open(D/'MCR_dpc_2020.tif')
assert all(z.shape==test.shape and np.allclose(list(z.transform)[:6],list(test.transform)[:6]) and z.crs==test.crs for z in refs)
total=0;max_abs=0;max_rel=0;sumabs=0.;fractions=[]
for row in range(0,test.height,96):
 win=rio.windows.Window(0,row,test.width,min(96,test.height-row))
 vals=np.stack([z.read(1,window=win) for z in refs])
 vals.sort(axis=0)
 ground=vals[0].astype('float64')+vals[1];obt=test.read(1,window=win)
 assert np.all(np.isfinite(ground)) and np.all(obt>=0) and np.all(ground>=0)
 er=np.abs(ground-obt);rel=er/np.maximum(1.,ground)
 max_abs=max(max_abs,er.max());max_rel=max(max_rel,rel.max());sumabs+=er.sum();total+=er.size
 assert np.allclose(ground,obt,rtol=5e-6,atol=.01)
r=dict(PASS=True,pairs_solved_independently_by_arcgis=len(refs),engine=json.loads((p/'arc_native_done.json').read_text())['ProductName']+' '+json.loads((p/'arc_native_done.json').read_text())['Version'],pixel_count=total,max_abs_cost_m=float(max_abs),max_rel=float(max_rel),mean_abs_cost_m=float(sumabs/total),tolerance={'relative':5e-6,'absolute':.01},arcmap108_check='NotInitialized; ArcGIS Pro 3.1.6 native seven source-specific solves used instead',model_validation='computational equality only')
print(json.dumps(r,indent=2),flush=True)
(p/'mcr_native_comparison.json').write_text(json.dumps(r,indent=2),encoding='utf8')
