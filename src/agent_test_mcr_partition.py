"""Native leave-one-parent-out versus exact binary source partition test.

The test includes seven sparse source IDs, two cores of one complete parent,
one non-source parent, symmetric equal-cost alternatives and nonuniform cost.
Synthetic rasters are only software validation, never research observations.
"""
from pathlib import Path
import json
import subprocess
import sys
import numpy as np
import rasterio
from rasterio.transform import from_origin
from agent_mcr_arcpy import _dijkstra

root=Path(sys.argv[1]);propy=Path(sys.argv[2])
root.mkdir(parents=True,exist_ok=True)
shape=(17,17)
p=np.zeros(shape,np.int32);s=np.zeros(shape,np.int32)
locations=[(3,2,8),(19,8,2),(101,8,14),(420,14,8),(3113,3,3),(100003,13,13),(7000001,3,13)]
for pid,r,c in locations:
    p[r-1:r+2,c-1:c+2]=pid;s[r,c]=pid
# Two source cores belong to one original parent; neither may serve that parent.
s[2,9]=3
p[7:10,7:10]=424242
cost=np.ones(shape,np.float32);cost[7:10,7:10]=2
base={'synthetic_only':True}
for arr,key,name,nd in [(p,'parent_raster','parent.tif',0),(s,'source_parent_raster','source.tif',0),(cost,'cost_raster','cost.tif',-9999)]:
    path=root/name
    with rasterio.open(path,'w',driver='GTiff',height=shape[0],width=shape[1],count=1,
                       dtype=arr.dtype,transform=from_origin(500000,4400510,30,30),crs='EPSG:32650',nodata=nd) as dst:dst.write(arr,1)
    base[key]=str(path)
reports={};outputs={}
script=Path(__file__).with_name('agent_mcr_arcpy.py')
for strategy in ['leave_one_parent_out','binary_parent_partition']:
    cfg=dict(base,source_strategy=strategy,out_dir=str(root/strategy))
    config_path=root/(strategy+'.json');config_path.write_text(json.dumps(cfg,indent=2),encoding='utf-8')
    completed=subprocess.run([str(propy),'-u',str(script),str(config_path)],capture_output=True,text=True,timeout=180)
    (root/(strategy+'.log')).write_text(completed.stdout+'\n'+completed.stderr,encoding='utf-8')
    assert completed.returncode==0,(strategy,completed.returncode,completed.stdout,completed.stderr)
    reports[strategy]=json.loads((root/strategy/'mcr_run_receipt.json').read_text(encoding='utf-8'))
    vals={}
    for key,path in reports[strategy]['outputs'].items():
        with rasterio.open(path) as src:vals[key]=src.read(1)
    outputs[strategy]=vals
    print('NATIVE_COMPLETE',strategy,len(reports[strategy]['runs']),flush=True)

a=outputs['leave_one_parent_out'];b=outputs['binary_parent_partition'];habitat=p>0
cost_difference=float(np.max(np.abs(a['pixel_cost'][habitat]-b['pixel_cost'][habitat])))
assert cost_difference==0, 'Partition and direct native saved costs differ'
assert np.all(a['patch_minimum_cost']==b['patch_minimum_cost'])
source_ids=np.unique(s[s>0])
all_costs={int(pid):_dijkstra(cost,s==pid) for pid in source_ids}
tie_cells=0;destination_differences=0;max_independent_error=0
for r,c in zip(*np.where(habitat)):
    legal=[int(pid) for pid in source_ids if pid!=p[r,c]]
    minimum=min(all_costs[pid][r,c] for pid in legal)
    ties=[pid for pid in legal if abs(all_costs[pid][r,c]-minimum)<1e-9]
    tie_cells+=len(ties)>1
    for strategy in outputs:
        out=outputs[strategy]
        destination=int(out['pixel_destination'][r,c])
        assert destination in legal
        assert abs(all_costs[destination][r,c]-minimum)<.0001
        max_independent_error=max(max_independent_error,abs(float(out['pixel_cost'][r,c])-minimum))
    destination_differences+=a['pixel_destination'][r,c]!=b['pixel_destination'][r,c]
assert tie_cells>0,'Synthetic fixture did not include ties'
assert max_independent_error<.0001
report={'status':'PASS_EXACT_NATIVE_PARTITION_EQUIVALENCE','synthetic_only':True,
        'grid_shape':list(shape),'source_parent_ids':source_ids.tolist(),'nonsource_parent_id':424242,
        'multi_core_parent_id':3,'habitat_cells':int(habitat.sum()),
        'maximum_native_cost_difference':cost_difference,
        'same_parent_destinations':0,'independent_tied_optimum_cells':int(tie_cells),
        'different_but_verified_optimal_destinations':int(destination_differences),
        'maximum_independent_cost_error':float(max_independent_error),
        'native_runs':{key:len(report['runs']) for key,report in reports.items()},
        'tie_rule':reports['binary_parent_partition']['destination_tie_rule'],
        'equivalence_proof':'Distinct dense source-parent codes differ in at least one bit. For each target parent the opposite-bit source subsets contain no same-parent source, and their union includes every other source parent. Minimum over native subset costs equals native minimum over all legal sources.',
        'method_scope':'Exact native execution optimization only; no new ecological indicator or resistance model.'}
(root/'partition_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
