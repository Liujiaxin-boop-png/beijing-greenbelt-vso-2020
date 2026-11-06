"""Snapshot the requested five-folder delivery without touching source files.

Raw data, result files and figures receive content hashes. Active intermediate
files receive metadata only; this inventory is never a claim of completion.
"""
from pathlib import Path
import csv,datetime,hashlib,json

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/project_audit'
FOLDERS=['01_原始数据','02_过程文件','03_结果文件','04_图件','05_代码']

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    WORK.mkdir(exist_ok=True)
    previous=WORK/'file_inventory.json'
    cache={r['path']:r for r in json.loads(previous.read_text(encoding='utf8')).get('files',[])} if previous.exists() else {}
    rows=[];errors=[];summary=[]
    for folder in FOLDERS:
        n=0;total=0
        for path in sorted((ROOT/folder).rglob('*')):
            if not path.is_file() or '.git' in path.parts or '__pycache__' in path.parts or WORK in path.parents:continue
            # Do not inspect credentials or machine-specific environment overrides.
            if path.name in ['.env','local_runtime.json'] or 'private' in path.parts:continue
            try:
                stat=path.stat();rel=path.relative_to(ROOT).as_posix();old=cache.get(rel,{})
                hashed=folder!='02_过程文件' and path.suffix.lower() not in ['.lock','.tmp','.sr.lock','.rd.lock']
                digest=old.get('sha256') if old.get('bytes')==stat.st_size and old.get('mtime_ns')==stat.st_mtime_ns else None
                if hashed and not digest:digest=sha(path)
                after=path.stat()
                changed=(stat.st_size,stat.st_mtime_ns)!=(after.st_size,after.st_mtime_ns)
                if changed:digest=None
                row={'folder':folder,'path':rel,'bytes':after.st_size,'mtime_ns':after.st_mtime_ns,'sha256':digest if hashed else None,'hash_policy':'FILE_CHANGED_DURING_READ' if changed else 'CONTENT_HASH' if hashed else 'ACTIVE_INTERMEDIATE_METADATA_ONLY'}
                rows.append(row);n+=1;total+=after.st_size
            except OSError as exc:errors.append({'path':str(path.relative_to(ROOT)),'error_type':type(exc).__name__})
        summary.append({'folder':folder,'files':n,'bytes':total})
    proposal=ROOT/'01_原始数据/研究依据/北京二道绿隔生态韧性评价_开题报告_组会汇报清稿_20261106.docx'
    assert sha(proposal)=='e31da3054ae9c7e95d705a9e92718704c9ca5b92ce13ba5059d03f8143519db7'
    report={'status':'INVENTORY_SNAPSHOT_ONLY','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':rows,'summary':summary,'read_errors':errors,'approved_proposal_unchanged':True,'completion_note':'Current per-stage receipts and final delivery QA determine completion. This inventory verifies retained files, not ecological validity or manuscript acceptance.'}
    previous.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    with (WORK/'file_inventory.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({'summary':summary,'read_errors':errors,'proposal_unchanged':True},ensure_ascii=False))

if __name__=='__main__':main()
