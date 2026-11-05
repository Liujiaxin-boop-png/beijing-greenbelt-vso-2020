"""Run root-authored aggregation and indicator join after verified MCR publish.

No evaluation/composite score is called. Root scripts are read and executed,
never edited. A missing NTL remains missing in the joined table.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time
import traceback

work=Path(sys.argv[1]);here=Path(__file__).parent;queue=work/'mcr_queue'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
status_path=queue/'aggregation_after_publish_status.json'
def status(value,**kw):
    status_path.write_text(json.dumps(dict(status=value,time=time.time(),**kw),indent=2),encoding='utf-8')
try:
    status('WAITING_FOR_VERIFIED_PUBLICATION')
    while True:
        try:
            state=json.loads((queue/'finalization_status.json').read_text(encoding='utf-8'))
            if state['status']=='FAILED':raise RuntimeError('MCR finalization failed')
            if state['status']=='COMPLETE':break
        except (OSError,ValueError):pass
        time.sleep(10)
    scripts=[]
    for name in ['aggregate_mcr.py','join_indicator_records.py']:
        path=here/name;before=sha(path);status('RUNNING_ROOT_SCRIPT',script=name)
        with (queue/(name+'.log')).open('w',encoding='utf-8') as log:
            cp=subprocess.run([sys.executable,'-u',str(path)],stdout=log,stderr=subprocess.STDOUT)
        assert cp.returncode==0,name+' failed; see log'
        assert sha(path)==before,'Root script changed during execution'
        scripts.append({'script':str(path),'sha256':before,'exit_code':cp.returncode})
    aggregation=json.loads((work/'aggregation'/'mcr_aggregation_receipt.json').read_text(encoding='utf-8'))
    join=json.loads((work/'aggregation'/'indicator_join_receipt.json').read_text(encoding='utf-8'))
    assert aggregation['status']=='COMPLETE' and len(aggregation['completed'])==15 and not aggregation['pending']
    assert join['status']=='JOIN_COMPLETE_SCORES_NOT_RUN' and join['no_imputation']
    publication=json.loads(Path(state['published_manifest']).read_text(encoding='utf-8'))
    assert publication['status']=='COMPLETE_VERIFIED_PUBLISHED_COPY' and len(publication['scenarios'])==15
    status('COMPLETE',scripts=scripts,mcr_aggregation=aggregation,indicator_join=join,
           publication_manifest=state['published_manifest'],scores_not_run=True,root_scripts_unchanged=True)
    print('MCR_AGGREGATION_AND_JOIN_COMPLETE_NO_SCORES',flush=True)
except BaseException:
    status('FAILED',traceback=traceback.format_exc());raise
