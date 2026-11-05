"""Independent direct leave-parent-out native check of selected regional IDs.

Run in propy.bat with EXECUTION_CONFIG OUTPUT_DIRECTORY. No licence changes;
normal interpreter exit returns the checked-out licence per Esri guidance.
"""
from pathlib import Path
import json
import sys
import time
import numpy as np
import arcpy
from arcpy.sa import CostDistance,SetNull

cfg=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
assert arcpy.CheckOutExtension('Spatial')=='CheckedOut'
arcpy.env.overwriteOutput=False;arcpy.env.parallelProcessingFactor='0'
arcpy.env.workspace=str(out);arcpy.env.scratchWorkspace=str(out)
cost=cfg['cost_raster'];source=cfg['source_parent_raster']
arcpy.env.snapRaster=cost;arcpy.env.cellSize=cost
meta=arcpy.Describe(cost);arcpy.env.extent=meta.extent;arcpy.env.outputCoordinateSystem=meta.spatialReference
p=arcpy.RasterToNumPyArray(cfg['parent_raster'],nodata_to_value=0)
s=arcpy.RasterToNumPyArray(source,nodata_to_value=0)
ids=np.unique(s[s>0]);assert len(ids)>1
chosen=sorted(set(int(ids[i]) for i in (0,len(ids)//2,len(ids)-1)))
actual=arcpy.RasterToNumPyArray(str(Path(cfg['out_dir'])/'mcr_pixel_cost.tif'),nodata_to_value=-9999)
checks=[]
for sid in chosen:
    start=time.time();only=out/('exclude_parent_'+str(sid)+'.tif')
    SetNull(arcpy.Raster(source)==sid,arcpy.Raster(source)).save(str(only))
    target=out/('native_distance_exclude_'+str(sid)+'.tif')
    CostDistance(str(only),cost).save(str(target))
    direct=arcpy.RasterToNumPyArray(str(target),nodata_to_value=-9999)
    mask=p==sid
    assert np.all((direct[mask]==-9999)==(actual[mask]==-9999))
    av=actual[mask&(actual!=-9999)];dv=direct[mask&(direct!=-9999)]
    error=np.abs(av.astype(np.float64)-dv.astype(np.float64))
    tolerance=4*np.maximum(np.spacing(av),np.spacing(dv))
    assert np.all(error<=tolerance)
    checks.append({'parent_id':sid,'tested_pixels':int(mask.sum()),
                   'max_absolute_error':float(error.max()) if len(error) else None,
                   'exact_equal_pixels':int(np.sum(error==0)),
                   'nonzero_difference_pixels':int(np.sum(error>0)),
                   'four_ulp_tolerance_exceeded_pixels':int(np.sum(error>tolerance)),
                   'seconds':time.time()-start})
    print('REGIONAL_NATIVE_CHECK_PASS',sid,checks[-1]['max_absolute_error'],flush=True)
report={'status':'PASS_NATIVE_DIRECT_VS_PARTITION_REGIONAL','scenario':cfg['scenario'],
        'engine':arcpy.GetInstallInfo(),'checks':checks,
        'selection':'First, middle and last sorted source ParentPatchIDs; full modeling-background target cells.',
        'comparison':'Independent native CostDistance with every same-parent source core removed versus partitioned production raster.',
        'tolerance':'Four float32 ULP; exact/nonzero differences separately retained.'}
(out/'regional_native_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
