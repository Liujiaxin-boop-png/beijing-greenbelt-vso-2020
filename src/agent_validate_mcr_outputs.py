"""Audit synthetic native Esri outputs without initializing an ArcGIS licence.

Usage: Python312 agent_validate_mcr_outputs.py SYNTHETIC_TEST_DIRECTORY
This audits toy rasters only; it does not create research observations.
"""
from pathlib import Path
import json
import sys
import numpy as np
import rasterio
from agent_mcr_arcpy import _dijkstra, _patch_minima

root=Path(sys.argv[1])
config_name=sys.argv[2] if len(sys.argv)>2 else 'synthetic_config.json'
conf=json.loads((root/config_name).read_text(encoding='utf-8-sig'))
out=Path(conf['out_dir'])
report=json.loads((out/'mcr_run_receipt.json').read_text(encoding='utf-8'))
def read(p):
    with rasterio.open(p) as src:
        return src.read(1)
p=read(conf['parent_raster']);s=read(conf['source_parent_raster']);c=read(conf['cost_raster'])
costs=read(report['outputs']['pixel_cost'])
dest=read(report['outputs']['pixel_destination'])
patchcost=read(report['outputs']['patch_minimum_cost'])
records=json.loads((out/'mcr_patch_records.json').read_text(encoding='utf-8'))
fast_records,fast_min,fast_dest,packed=_patch_minima(p,costs,dest)
assert np.array_equal(fast_min,patchcost)
assert np.array_equal(fast_dest,read(report['outputs']['patch_destination']))
qa=[]
for pid in np.unique(p[p>0]):
    expected=_dijkstra(c,(s>0)&(s!=pid))
    error=float(np.max(np.abs(costs[p==pid]-expected[p==pid])))
    assert error<0.001, 'Native cost differs from independent eight-neighbour graph'
    assert np.all(dest[p==pid]!=pid), 'Same parent retained as a destination'
    assert np.all(patchcost[p==pid]==np.min(costs[p==pid]))
    rec=next(r for r in records if r['parent_id']==int(pid))
    rr,cc=np.where(s==rec['destination_parent_id'])
    ed=30*np.sqrt((rr-rec['origin_row'])**2+(cc-rec['origin_col'])**2).min()
    assert abs(rec['euclidean_m']-float(ed))<0.001
    qa.append({'parent_id':int(pid),'cells':int(np.sum(p==pid)),
               'max_abs_cost_error':error,'native_patch_minimum':rec['cost'],
               'destination_parent_id':rec['destination_parent_id'],
               'native_euclidean_m':rec['euclidean_m']})
result={'status':'PASS_NATIVE_OUTPUTS_VS_INDEPENDENT_DIJKSTRA',
        'engine':report['engine'],'not_research_observations':True,
        'checks':['per-cell native cost','same-parent exclusion','patch minimum',
                  'selected-destination Euclidean distance','vectorized patch-minimum equivalence'],
        'per_parent':qa,
        'runtime_caveat':('Original explicit CheckInExtension run exited 1 after outputs; see subsequent clean propy run.' if config_name=='synthetic_config.json' else 'propy.bat natural interpreter exit returned 0; subsequent independent process checked out Spatial and returned 0.')}
(out/'synthetic_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
