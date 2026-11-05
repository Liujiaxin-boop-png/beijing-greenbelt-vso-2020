"""Check nested source-threshold MCR monotonicity after all native runs."""
from pathlib import Path
import json
import sys
import numpy as np
import rasterio

manifest_path=Path(sys.argv[1]);manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
cfgs={t['scenario']:json.loads(Path(t['config']).read_text(encoding='utf-8')) for t in manifest['tasks']}
def read(path):
    with rasterio.open(path) as src:return src.read(1)
checks=[]
for habitat in ['forest_shrub','grassland','water_wetland']:
    for low,high in [(10,35),(35,100),(10,100)]:
        lowcfg=cfgs['clcd_'+habitat+'_core'+str(low)+'_land_road']
        highcfg=cfgs['clcd_'+habitat+'_core'+str(high)+'_land_road']
        assert lowcfg['cost_raster']==highcfg['cost_raster']
        assert lowcfg['parent_raster']==highcfg['parent_raster']
        s1=read(lowcfg['source_parent_raster']);s2=read(highcfg['source_parent_raster'])
        assert np.all(s1[s2>0]==s2[s2>0]),'Higher-threshold source set is not nested'
        del s1,s2
        a=read(Path(lowcfg['out_dir'])/'mcr_patch_min_cost.tif')
        b=read(Path(highcfg['out_dir'])/'mcr_patch_min_cost.tif')
        valid=(a!=-9999)&(b!=-9999)
        av=a[valid];bv=b[valid]
        delta=av.astype(np.float64)-bv.astype(np.float64)
        tolerance=4*np.maximum(np.spacing(av),np.spacing(bv))
        wrong=delta>tolerance
        check={'habitat':habitat,'lower_threshold_ha':low,'higher_threshold_ha':high,
               'common_valid_pixels':int(valid.sum()),'lower_only_valid_pixels':int(np.sum((a!=-9999)&(b==-9999))),
               'raw_reverse_difference_pixels':int(np.sum(delta>0)),
               'violations_above_four_float32_ulp':int(wrong.sum()),
               'maximum_reverse_difference':float(np.maximum(delta,0).max()) if len(delta) else None,
               'source_masks_nested':True,'cost_surface_identical':True}
        checks.append(check)
        assert not np.any(wrong),check
        print('MONOTONICITY_PASS',habitat,low,high,flush=True)
result={'status':'PASS','checks':checks,
        'principle':'Removing eligible sources cannot lower minimum cumulative cost to other-parent sources on the same positive-cost graph.',
        'tolerance':'Four float32 ULP solely for stored-raster numerical precision; raw reverse differences also reported.'}
out=manifest_path.parent.parent/'mcr_queue'/'cross_scenario_qa.json'
out.write_text(json.dumps(result,indent=2),encoding='utf-8')
