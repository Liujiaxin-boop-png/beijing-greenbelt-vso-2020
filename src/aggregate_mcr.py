"""Aggregate native patch-level MCR to exact full squares.

Partial valid habitat is reported but never silently accepted as the whole
habitat mean. Incomplete scenarios remain explicitly pending.
"""
from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
import rasterio
from aggregate_basics import window_area
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'03_结果文件/indicators';WORK=ROOT/'02_过程文件/aggregation'

def main():
    queue=json.loads((ROOT/'02_过程文件/mcr_inputs/regional_queue.json').read_text(encoding='utf8'))
    grids=json.loads((ROOT/'02_过程文件/spatial/grid_identity.json').read_text(encoding='utf8'))['grids']
    allrows=[];pending=[];completed=[]
    for task in queue['tasks']:
        scenario=task['scenario'];out=ROOT/'02_过程文件/mcr_native'/scenario
        rp=out/'mcr_run_receipt.json'
        if not rp.exists():pending.append(scenario);continue
        receipt=json.loads(rp.read_text(encoding='utf8'))
        if receipt['status']!='COMPLETE':pending.append(scenario);continue
        cfg=json.loads(Path(task['config']).read_text(encoding='utf8'))
        product=cfg['product'];habitat=cfg['habitat']
        with rasterio.open(cfg['parent_raster']) as ds:p=ds.read(1);aff=ds.transform
        with rasterio.open(out/'mcr_patch_min_cost.tif') as ds:cost=ds.read(1);nd=ds.nodata;assert ds.transform==aff and ds.shape==p.shape
        with rasterio.open(out/'mcr_patch_destination_parent.tif') as ds:dest=ds.read(1)
        with rasterio.open(out/'mcr_patch_euclidean_m.tif') as ds:distance=ds.read(1)
        catalog=pd.read_csv(Path(cfg['parent_raster']).parent/'parent_catalog.csv')
        truncated=catalog.loc[catalog.background_truncated==True,'parent_id'].to_numpy()
        tmask=np.isin(p,truncated);dmask=np.isin(dest,truncated)
        assert not np.any((dest>0)&(dest==p))
        records=json.loads((out/'mcr_patch_records.json').read_text(encoding='utf8'))
        valid_records={r['parent_id']:r for r in records if r['status']=='VALID'}
        for k,grid in enumerate(grids):
            a,w,sl=window_area(p,aff,grid['bounds']);h=a>0;ha=float(w[h].sum())
            cv=cost[sl];dv=distance[sl];good=h&np.isfinite(cv)&(cv!=nd)&(dest[sl]>0)
            va=float(w[good].sum());ratio=va/ha if ha else np.nan
            complete=ha>0 and np.isclose(va,ha,atol=1e-5,rtol=1e-10)
            row={'grid_id':grid['grid_id'],'scale_m':grid['scale_m'],'product':product,'habitat':habitat,'scenario':scenario,'habitat_m2':ha,'MCR_valid_m2':va,'MCR_valid_fraction':ratio,'MCR':float((cv[good]*w[good]).sum()/ha) if complete else np.nan,'MCR_partial_mean':float((cv[good]*w[good]).sum()/va) if va else np.nan,'MCR_euclidean_m':float((dv[good]*w[good]).sum()/ha) if complete else np.nan,'target_truncated_fraction':float(w[h&tmask[sl]].sum()/ha) if ha else np.nan,'destination_truncated_fraction':float(w[good&dmask[sl]].sum()/va) if va else np.nan,'MCR_status':'VALID' if complete else 'NO_FOCAL_HABITAT' if not ha else 'PARTIAL_OR_NO_ALTERNATIVE_SOURCE'}
            # Independent grouping identity for selected, deterministic windows.
            if complete and k%137==0:
                total=0.
                for pid in np.unique(a[h]):total+=valid_records[int(pid)]['cost']*float(w[a==pid].sum())
                assert abs(row['MCR']-total/ha)<max(1e-3,abs(row['MCR'])*1e-7)
            allrows.append(row)
        completed.append(scenario)
    frame=pd.DataFrame(allrows)
    if len(frame):frame.to_csv(OUT/'mcr_by_grid.csv',index=False,encoding='utf-8-sig')
    report={'status':'COMPLETE' if not pending else 'PARTIAL_SCENARIOS_PENDING','completed':completed,'pending':pending,'rows':len(frame),'meaning':'patch-minimum over full modeled parent; sources of the same parent excluded','partial_habitat_policy':'reported separately; not used in complete MCR or composite','background_truncation':'full modeled background only; source and destination outer-frame flags retained','independent_check':'every137th window grouped by patch-record costs and exact area weights'}
    (WORK/'mcr_aggregation_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'status':report['status'],'completed':len(completed),'pending':len(pending),'rows':len(frame)}))

if __name__=='__main__':main()
