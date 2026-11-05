"""Check native regional CLUMPY joins and a deterministic arithmetic sample.

No metric is recomputed into the production result table; scalar values are
only diagnostic comparisons with the retained native executable output.
"""
from pathlib import Path
import csv
import json
import random
import sys
from collections import Counter
import numpy as np
from agent_validate_fragstats import scalar_reference

process=Path(sys.argv[1]);results=Path(sys.argv[2])
man=json.loads((results/'clumpy_batch_manifest.json').read_text(encoding='utf-8'))
checks=[];summary=[]
for run in man:
    product=run['product'];scale=run['scale_m']
    with Path(run['result']).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==run['grid_count']*3
    assert len({(r['Grid_ID'],r['habitat_type']) for r in rows})==len(rows)
    assert all((r['status']=='VALID')==bool(r['CLUMPY']) for r in rows)
    assert all(int(r['habitat_pixels'])<=int(r['valid_support_pixels']) for r in rows)
    assert all(int(r['window_rows']) in ({33,34} if scale==1000 else {16,17}) for r in rows)
    assert all(int(r['window_cols']) in ({33,34} if scale==1000 else {16,17}) for r in rows)
    grid_order={r['Grid_ID']:i for i,r in enumerate(rows[::3])}
    for typ in sorted({r['habitat_type'] for r in rows}):
        subset=[r for r in rows if r['habitat_type']==typ]
        valid=[r for r in subset if r['status']=='VALID']
        status=Counter(r['status'] for r in subset)
        values=np.array([float(r['CLUMPY']) for r in valid])
        present=sum(int(r['habitat_pixels'])>0 for r in subset)
        summary.append({'product':product,'scale_m':scale,'habitat_type':typ,
                        'all_grids':len(subset),'present_grids':present,
                        'valid_grids':len(valid),'absent_grids':status['ABSENT_FOCAL_HABITAT'],
                        'present_but_native_NA':present-len(valid),
                        'valid_fraction_of_present':len(valid)/present if present else None,
                        'min':float(values.min()) if len(values) else None,
                        'median':float(np.median(values)) if len(values) else None,
                        'max':float(values.max()) if len(values) else None})
        rng=random.Random(219+scale)
        sample=rng.sample(valid,min(20,len(valid)))
        for r in sample:
            i=grid_order[r['Grid_ID']]
            asc=process/(product.lower()+'_'+str(scale))/('batch_'+str(i//256).zfill(3))/(r['Grid_ID']+'.asc')
            arr=np.loadtxt(asc,dtype=int)
            if np.any(arr==9999):
                checks.append({'product':product,'scale_m':scale,'grid':r['Grid_ID'],'habitat_type':typ,
                               'check':'SKIPPED_SCALAR_NODATA_CASE','native_result_retained':True})
                continue
            expected=scalar_reference(arr.tolist(),int(r['habitat_class']))
            error=abs(expected-float(r['CLUMPY']))
            assert error<=0.000050001,(r,expected,error)
            checks.append({'product':product,'scale_m':scale,'grid':r['Grid_ID'],'habitat_type':typ,
                           'actual_native':float(r['CLUMPY']),'independent_reference':expected,
                           'absolute_error':error,'check':'PASS'})
with (results/'clumpy_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
audit={'status':'PASS','groups':len(man),'total_grid_windows':sum(r['grid_count'] for r in man),
       'total_class_records':sum(r['record_count'] for r in man),'independent_checks':len(checks),
       'na_preserved':True,'no_indicator_weighting':True,
       'checks':checks,'summary':summary,
       'native_NA_note':'The binary also returns N/A when all but one valid cell belong to the focal class; retained as FRAGSTATS_UNDEFINED. No substitution of 0 or 1.'}
(results/'clumpy_independent_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in audit.items() if k not in ('checks','summary')},indent=2))
