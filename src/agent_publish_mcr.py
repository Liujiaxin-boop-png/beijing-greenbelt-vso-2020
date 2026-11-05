"""Publish QA-passed final MCR artifacts, preserving all native process files."""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import sys

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

manifest=Path(sys.argv[1]);root=manifest.parent.parent
queue=json.loads((root/'mcr_queue'/'queue_checkpoint.json').read_text(encoding='utf-8'))
assert queue['status']=='COMPLETE' and len(queue['completed'])==queue['total_tasks']==15
cross=json.loads((root/'mcr_queue'/'cross_scenario_qa.json').read_text(encoding='utf-8'))
assert cross['status']=='PASS'
dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
assert dest.resolve().is_relative_to(root.resolve().parent/'03_结果文件')
published=[];summary=[]
for task in queue['completed']:
    config=json.loads(Path(task['config']).read_text(encoding='utf-8'))
    source=Path(config['out_dir']);receipt=json.loads((source/'mcr_run_receipt.json').read_text(encoding='utf-8'))
    qa=json.loads((source/'regional_qa.json').read_text(encoding='utf-8'))
    assert qa['status']=='PASS'
    target=dest/task['scenario'];target.mkdir(parents=True,exist_ok=True)
    files=[Path(p) for p in receipt['outputs'].values()]
    files += [source/n for n in ['mcr_patch_records.json','mcr_run_receipt.json','regional_qa.json','queue_input_signature.json']]
    files += [root/'mcr_queue'/(task['scenario']+'_execution.json')]
    artifacts=[]
    for path in files:
        out=target/path.name;expected=sha(path)
        if out.exists():assert sha(out)==expected,'Never overwrite inconsistent published result'
        else:shutil.copy2(path,out)
        assert sha(out)==expected
        artifacts.append({'process_original':str(path),'published':str(out),'sha256':expected,'bytes':out.stat().st_size})
    published.append({'scenario':task['scenario'],'qa':'PASS','artifacts':artifacts})
    summary.append({'scenario':task['scenario'],'product':config['product'],'habitat':config['habitat'],
                    'core_area_threshold_ha':config['threshold']['threshold_ha'],
                    'resistance_variant':config['resistance_variant'],'source_parents':qa['source_parents'],
                    'full_background_target_parents':qa['target_parents'],
                    'valid_target_parents':qa['valid_target_parents'],'undefined_target_parents':qa['undefined_target_parents'],
                    'full_background_valid_pixels':qa['valid_pixel_count'],
                    'native_groups':qa['native_runs'],'native_seconds':qa['elapsed_native_seconds']})
with (dest/'scenario_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
report={'status':'COMPLETE_VERIFIED_PUBLISHED_COPY','scenarios':published,
        'scope':'Full modeling background. Study-area statistics require the approved reporting-mask/town-grid intersection weights.',
        'undefined':'No-other-reachable-source values are NoData, never zero resistance.',
        'euclidean':'Origin to nearest core-cell centre of the selected destination parent; not necessarily the least-cost-path endpoint.',
        'original_process_files_preserved':True,'cross_scenario_qa':cross}
(dest/'published_mcr_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PUBLISHED_VERIFIED',len(published),flush=True)
