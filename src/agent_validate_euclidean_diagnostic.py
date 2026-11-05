"""Compare exact KD-tree distances to retained native EucDistance test data."""
import copy
import json
import sys
from pathlib import Path
import numpy as np
import rasterio
from agent_mcr_arcpy import _selected_destination_euclidean

roots=[Path(p) for p in sys.argv[1:]]
checks=[]
for root in roots:
    receipt=json.loads((root/'mcr_run_receipt.json').read_text(encoding='utf-8'))
    old=json.loads((root/'mcr_patch_records.json').read_text(encoding='utf-8'))
    with rasterio.open(receipt['config']['source_parent_raster']) as ras:
        src=ras.read(1);ch=abs(ras.transform.e);cw=ras.transform.a
    exact=_selected_destination_euclidean(src,copy.deepcopy(old),ch,cw)
    for before,after in zip(old,exact):
        if after['status']!='VALID':continue
        rr=after['nearest_euclidean_source_row'];cc=after['nearest_euclidean_source_col']
        assert src[rr,cc]==after['destination_parent_id']
        distance=np.hypot((rr-after['origin_row'])*ch,(cc-after['origin_col'])*cw)
        assert distance==after['euclidean_m']
        error=abs(before['euclidean_m']-after['euclidean_m'])
        assert error<0.0001
        checks.append({'test':str(root),'parent_id':after['parent_id'],
                       'native_euclidean_m':before['euclidean_m'],'exact_euclidean_m':after['euclidean_m'],
                       'absolute_error_m':error,'nearest_source_row':rr,'nearest_source_col':cc})
report={'status':'PASS_KDTREE_VS_NATIVE_EUCDISTANCE','synthetic_only':True,
        'checks':checks,'count':len(checks),'max_abs_error_m':max(c['absolute_error_m'] for c in checks),
        'meaning':'Shortest planar origin-to-selected-parent-core-cell-centre distance; not necessarily the least-cost-path endpoint.'}
output=roots[0].parent/'euclidean_kdtree_validation.json'
output.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
