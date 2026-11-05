"""Sequential native regional MCR queue, immutable inputs and checked outputs.

Usage: Python312 agent_mcr_queue.py MANIFEST PROPY_BAT
Each scenario runs in its own licensed Pro interpreter and exits naturally.
The execution copy adds only the approved exact Euclidean diagnostic engine.
"""
from pathlib import Path
import csv
import gc
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import traceback
import numpy as np
import rasterio
from agent_mcr_arcpy import _patch_minima

def dump(path,value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temp,path)

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def read(path):
    with rasterio.open(path) as s:return s.read(1),s.profile

def qa(cfg,source_count):
    out=Path(cfg['out_dir']);report=json.loads((out/'mcr_run_receipt.json').read_text(encoding='utf-8'))
    assert report['status']=='COMPLETE'
    assert report['destination_same_parent_count']==0
    assert len(report['source_parent_ids'])==source_count
    p,pr=read(cfg['parent_raster']);src,_=read(cfg['source_parent_raster'])
    arrays={}
    for key,path in report['outputs'].items():
        arr,profile=read(path)
        assert arr.shape==p.shape
        assert np.allclose(tuple(profile['transform']),tuple(pr['transform']),rtol=0,atol=1e-6) and profile['crs']==pr['crs']
        arrays[key]=arr
    pixel=arrays['pixel_cost'];dest=arrays['pixel_destination']
    valid=(p>0)&(pixel!=-9999)&(dest>0)
    assert np.all((pixel!=-9999)==(dest>0))
    assert np.all(np.isfinite(pixel[valid])) and np.all(pixel[valid]>=0)
    assert not np.any(dest[valid]==p[valid])
    ids=np.unique(src[src>0]);assert len(ids)==source_count
    assert np.all(np.isin(dest[valid],ids))
    records=json.loads((out/'mcr_patch_records.json').read_text(encoding='utf-8'))
    recomputed,mins,destinations,packed=_patch_minima(p,pixel,dest)
    assert np.array_equal(mins,arrays['patch_minimum_cost'])
    assert np.array_equal(destinations,arrays['patch_destination'])
    assert len(records)==len(recomputed)==report['target_parent_count']
    euclidean_checks=0
    for a,b in zip(records,recomputed):
        for k,v in b.items():assert a[k]==v,(k,a[k],v)
        if a['status']!='VALID':continue
        rr=a['nearest_euclidean_source_row'];cc=a['nearest_euclidean_source_col']
        assert src[rr,cc]==a['destination_parent_id']
        expected=math.hypot((rr-a['origin_row'])*abs(pr['transform'].e),(cc-a['origin_col'])*pr['transform'].a)
        assert abs(expected-a['euclidean_m'])<1e-8
        euclidean_checks+=1
    valid_parents=sum(r['status']=='VALID' for r in records)
    result={'status':'PASS','source_parents':source_count,'target_parents':len(records),
            'valid_target_parents':valid_parents,'undefined_target_parents':len(records)-valid_parents,
            'valid_pixel_count':int(valid.sum()),'same_parent_destination_count':0,
            'euclidean_point_pair_checks':euclidean_checks,'native_runs':len(report['runs']),
            'elapsed_native_seconds':report['elapsed_seconds'],
            'outputs':{key:{'path':str(path),'bytes':Path(path).stat().st_size,'sha256':sha(path)} for key,path in report['outputs'].items()},
            'checks':['input/output grid identity','validity masks','finite nonnegative cost',
                      'source membership','complete-parent exclusion','patch minimum/row-major origin',
                      'selected-source Euclidean coordinate pairs'],
            'no_inference_from_missing':'No-other-source parents remain NoData; no zeros substituted.'}
    dump(out/'regional_qa.json',result)
    return result

def main(manifest_path,propy):
    manifest_path=Path(manifest_path);manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    assert manifest['status']=='INPUTS_READY'
    root=manifest_path.parent.parent
    queue=root/'mcr_queue';queue.mkdir(parents=True,exist_ok=True)
    script=Path(__file__).with_name('agent_mcr_arcpy.py')
    code_hash=sha(script)
    state={'status':'PREFLIGHT','manifest':str(manifest_path),'manifest_sha256':sha(manifest_path),
           'module':str(script),'module_sha256':code_hash,'propy':str(propy),
           'started':time.time(),'total_tasks':len(manifest['tasks']),'completed':[],
           'execution_override':{'euclidean_engine':'ckdtree_exact'},'pending':[]}
    for task in manifest['tasks']:
        cfg_path=Path(task['config']);cfg=json.loads(cfg_path.read_text(encoding='utf-8-sig'))
        assert cfg['source_strategy']=='binary_parent_partition'
        assert not cfg.get('synthetic_only',True)
        meta=[]
        for key in ['parent_raster','source_parent_raster','cost_raster']:
            path=Path(cfg[key]);assert path.is_file(),str(path)
            with rasterio.open(path) as src:meta.append((src.height,src.width,src.transform,src.crs))
        assert meta[0]==meta[1]==meta[2]
        out=Path(cfg['out_dir']);assert out.resolve().is_relative_to(root.resolve())
        steps=1+2*(int(task['source_parents'])-1).bit_length() if task['source_parents']>1 else (1 if task['source_parents'] else 0)
        state['pending'].append(dict(task,expected_native_groups=steps,shape=list(meta[0][:2])))
    state['estimated_native_groups']=sum(t['expected_native_groups'] for t in state['pending'])
    state['uncompressed_cost_allocation_pair_gb']=sum(t['expected_native_groups']*t['shape'][0]*t['shape'][1]*8/1e9 for t in state['pending'])
    dump(queue/'queue_checkpoint.json',state)
    print('PREFLIGHT_COMPLETE',state['total_tasks'],state['estimated_native_groups'],flush=True)
    for task in list(state['pending']):
        cfg_path=Path(task['config']);cfg=json.loads(cfg_path.read_text(encoding='utf-8-sig'))
        cfg['euclidean_engine']='ckdtree_exact'
        out=Path(cfg['out_dir']);out.mkdir(parents=True,exist_ok=True)
        execution=queue/(task['scenario']+'_execution.json')
        dump(execution,cfg)
        inputs={key:{'path':cfg[key],'sha256':sha(cfg[key])} for key in ['parent_raster','source_parent_raster','cost_raster']}
        signature={'original_config_sha256':sha(cfg_path),'module_sha256':code_hash,'inputs':inputs}
        signature_path=out/'queue_input_signature.json'
        completed_before=out/'regional_qa.json'
        if completed_before.exists():
            assert json.loads(signature_path.read_text(encoding='utf-8'))==signature
            verified=qa(cfg,task['source_parents'])
            assert verified['status']=='PASS'
            state['completed'].append(dict(task,qa=verified,resumed_verified=True))
            state['pending']=[t for t in state['pending'] if t['scenario']!=task['scenario']]
            continue
        if (out/'mcr_run_receipt.json').exists():
            raise RuntimeError('Incomplete existing scenario requires explicit recovery, not overwrite: '+str(out))
        dump(signature_path,signature)
        assert sha(script)==code_hash,'Native module changed during queue; stop to preserve reproducibility'
        state.update(status='RUNNING',active_scenario=task['scenario'],active_started=time.time())
        log=queue/(task['scenario']+'.log')
        print('SCENARIO_STARTED',task['scenario'],flush=True)
        with log.open('w',encoding='utf-8') as output:
            proc=subprocess.Popen([str(propy),'-u',str(script),str(execution)],stdout=output,stderr=subprocess.STDOUT)
            while proc.poll() is None:
                state.update(active_pid=proc.pid,last_heartbeat=time.time())
                receipt=out/'mcr_run_receipt.json'
                if receipt.exists():
                    try:
                        current=json.loads(receipt.read_text(encoding='utf-8'))
                        state['active_completed_native_groups']=len(current.get('runs',[]))
                        state['active_elapsed_native_groups_seconds']=sum(r['seconds'] for r in current.get('runs',[]))
                    except (ValueError,OSError):pass
                dump(queue/'queue_checkpoint.json',state)
                time.sleep(5)
        assert proc.returncode==0,'Native child failed: '+str(log)
        verified=qa(cfg,task['source_parents'])
        state['completed'].append(dict(task,qa=verified,exit_code=proc.returncode,log=str(log)))
        state['pending']=[t for t in state['pending'] if t['scenario']!=task['scenario']]
        state['completed_count']=len(state['completed'])
        dump(queue/'queue_checkpoint.json',state)
        print('SCENARIO_QA_PASS',task['scenario'],verified['elapsed_native_seconds'],flush=True)
        gc.collect()
    state.update(status='COMPLETE',elapsed_seconds=time.time()-state['started'])
    dump(queue/'queue_checkpoint.json',state)
    print('REGIONAL_MCR_QUEUE_COMPLETE',flush=True)

if __name__=='__main__':
    try:main(*sys.argv[1:3])
    except BaseException:
        dest=Path(sys.argv[1]).parent.parent/'mcr_queue'/'queue_failure.json'
        dump(dest,{'status':'FAILED','traceback':traceback.format_exc(),'time':time.time()})
        raise
