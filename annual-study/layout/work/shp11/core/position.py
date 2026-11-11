"""2020 within-cell paired placement test. Construction, class areas, partial boundary pixels and the surroundings stay fixed."""
from pathlib import Path
import json, hashlib
import numpy as np, pandas as pd, rasterio
from scipy import ndimage as nd

out=Path(__file__).resolve().parent
root=Path(r'D:/ER219_work/annual_actual')
from compute import cells,field
d=cells(500);d['SSI']=field(root/'landscape/2020/fields_500_0.bin',d)[:,4];d=d.sort_values(['iy','ix'])
src=root/'years/model/CLCD_2020.tif'
with rasterio.open(src) as f:
    land=f.read(1); tr=f.transform
eco=np.isin(land,[2,3,4,5,9])
def cut(ix,iy):
    x0=(ix*500-tr.c)/30; x1=x0+500/30
    y0=(tr.f-(iy+1)*500)/30; y1=y0+500/30
    left,right=int(np.floor(x0)),int(np.ceil(x1)); top,bottom=int(np.floor(y0)),int(np.ceil(y1))
    mx=np.arange(left,right);my=np.arange(top,bottom)
    width=np.maximum(0,np.minimum(mx+1,x1)-np.maximum(mx,x0))
    height=np.maximum(0,np.minimum(my+1,y1)-np.maximum(my,y0))
    return np.s_[top:bottom,left:right],900*height[:,None]*width[None,:]
rng=np.random.default_rng(11062020)
results=[]; num=19; maxerr=0
for row in d.itertuples(index=False):
    sl,w=cut(row.ix,row.iy); raster=land[sl]; grey=(raster==8)&(w>1e-8)
    full=(w>900-1e-7)&(~grey); ids=np.flatnonzero(full); vals=raster.ravel()[ids]
    active=(grey.any() and np.any(np.isin(vals,[2,3,4,5,9])) and np.any(np.isin(vals,[1,7])))
    if not active:continue
    # A movable green pixel is guaranteed inside. Any exterior pixel more than the full square diagonal
    # away can never be nearest to a construction pixel in this cell.
    pad=28;top,bottom=sl[0].start,sl[0].stop;left,right=sl[1].start,sl[1].stop
    env=eco[top-pad:bottom+pad,left-pad:right+pad].copy()
    inner=np.s_[pad:pad+raster.shape[0],pad:pad+raster.shape[1]]
    patches,n=nd.label(grey,np.ones((3,3)));lab=np.arange(1,n+1)
    def distance(x):
        dst=nd.distance_transform_edt(~x)[inner]*30
        return float(nd.minimum(dst,labels=patches,index=lab).mean()),float(np.average(dst[grey],weights=w[grey])),float(np.average(dst,weights=w))
    original,pixel,field=distance(env)
    assert np.isfinite(row.SSI)
    maxerr=max(maxerr,abs(original-row.SSI))
    assert abs(original-row.SSI)<.001,(row.grid_id,original,row.SSI)
    target0=np.bincount(raster.ravel(),weights=w.ravel(),minlength=10)
    sims=[];wp=[];wf=[]
    for _ in range(num):
        sample=raster.copy();sample.ravel()[ids]=rng.permutation(vals)
        assert np.allclose(np.bincount(sample.ravel(),weights=w.ravel(),minlength=10),target0,rtol=0,atol=1e-7)
        env[inner]=np.isin(sample,[2,3,4,5,9])
        val,vp,vf=distance(env);sims.append(val);wp.append(vp);wf.append(vf)
    sims=np.array(sims);wp=np.array(wp);wf=np.array(wf)
    results.append(dict(grid_id=row.grid_id,ix=row.ix,iy=row.iy,area_km2=row.area_km2,
      observed_patch=original,observed_pixel=pixel,median_patch=np.median(sims),median_pixel=np.median(wp),
      range_patch=np.ptp(sims),range_pixel=np.ptp(wp),median_abs_patch=np.median(abs(sims-original)),
      median_abs_pixel=np.median(abs(wp-pixel)),any_patch=int(np.max(abs(sims-original))>1e-6),
      any_pixel=int(np.max(abs(wp-pixel))>1e-6),observed_field=field,median_field=np.median(wf),
      median_abs_field=np.median(abs(wf-field)),any_field=int(np.max(abs(wf-field))>1e-6)))
t=pd.DataFrame(results)
record=dict(total=len(d),eligible=len(t),area_km2=t.area_km2.sum(),replicates=num,seed=11062020,
    construction_positions_fixed=True,area_by_fine_class_m2_preserved=True,outer_landscape_fixed=True,
    positive_patch_n=int(t.any_patch.sum()),positive_pixel_n=int(t.any_pixel.sum()),positive_field_n=int(t.any_field.sum()),
    across_cell_median_of_median_abs_field_m=float(t.median_abs_field.median()),
    across_cell_median_of_median_abs_patch_m=float(t.median_abs_patch.median()),
    across_cell_median_of_median_abs_pixel_m=float(t.median_abs_pixel.median()),
    cells_w_median_absolute_change_ge_one_source_pixel=int((t.median_abs_patch>=30-.000001).sum()),
    baseline_reproduction_max_m=maxerr,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
t.to_csv(out/'2020固定地类面积和建设位置的灰绿配置置换.csv',index=False,encoding='utf-8-sig')
(out/'灰绿配置检验.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(record,ensure_ascii=False))
