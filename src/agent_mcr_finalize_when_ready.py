"""Wait for the native queue, then run cross-scenario QA and publish copies."""
from pathlib import Path
import json
import subprocess
import sys
import time
import traceback

manifest=Path(sys.argv[1]);destination=Path(sys.argv[2])
queue=manifest.parent.parent/'mcr_queue';here=Path(__file__).parent
log_path=queue/'finalization.log';state_path=queue/'finalization_status.json'
def status(value,**kw):
    state_path.write_text(json.dumps(dict(status=value,time=time.time(),**kw),indent=2),encoding='utf-8')
try:
    status('WAITING_FOR_QUEUE')
    while True:
        if (queue/'queue_failure.json').exists():raise RuntimeError('Native queue failure requires review')
        try:
            current=json.loads((queue/'queue_checkpoint.json').read_text(encoding='utf-8'))
            if current['status']=='COMPLETE':break
        except (OSError,ValueError):pass
        time.sleep(10)
    with log_path.open('w',encoding='utf-8') as log:
        status('CROSS_SCENARIO_QA')
        subprocess.run([sys.executable,str(here/'agent_mcr_cross_scenario_qa.py'),str(manifest)],stdout=log,stderr=subprocess.STDOUT,check=True)
        status('PUBLISHING_VERIFIED_RESULTS')
        subprocess.run([sys.executable,str(here/'agent_publish_mcr.py'),str(manifest),str(destination)],stdout=log,stderr=subprocess.STDOUT,check=True)
    status('COMPLETE',published_manifest=str(destination/'published_mcr_manifest.json'))
    print('MCR_FINALIZATION_COMPLETE',flush=True)
except BaseException:
    status('FAILED',traceback=traceback.format_exc());raise
