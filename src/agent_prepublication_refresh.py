"""Read-only refresh of the retained raw-data/code pre-publication audit.

Only this audit report is written. Large original rasters are not rehashed:
their existing source receipts, sizes and snapshot mtimes are checked instead.
"""
from pathlib import Path
import datetime, hashlib, json, re, subprocess
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT/'05_代码'
WORK = ROOT/'02_过程文件'
OUT = WORK/'delivery/prepublication_refresh.json'

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def git(*args):
    r = subprocess.run(['git','-C',str(CODE),*args],capture_output=True,text=True,encoding='utf-8')
    if r.returncode: raise RuntimeError('git command failed: '+str(args))
    return r.stdout

def main():
    oldpath = WORK/'delivery/pre_delivery_data_audit.json'
    old = read(oldpath)
    fails=[]; raw_checks=[]
    for item in old['raw_archive']['inventory']:
        p=ROOT/item['path']
        same=p.is_file() and p.stat().st_size==item['bytes'] and p.stat().st_mtime_ns==item['mtime_ns']
        raw_checks.append({'path':item['path'],'unchanged_size_mtime':same})
        if not same: fails.append('raw_snapshot_changed: '+item['path'])
    current_files={str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'01_原始数据').rglob('*') if p.is_file()}
    prior_files={x['path'].replace('\\','/') for x in old['raw_archive']['inventory']}
    new_files=sorted(current_files-prior_files)
    indexed=[]
    for r in old['reused_receipt_file_checks']['records']:
        p=ROOT/r['file']; sizes=r['receipt_bytes']
        okay=p.is_file() and (not sizes or p.stat().st_size in sizes) and len(r['receipt_sha256'])==1
        indexed.append({'path':r['file'],'pass':okay,'retained_sha256':r['receipt_sha256']})
        if not okay:fails.append('raw_receipt_inconsistent: '+r['file'])
    protocol=read(WORK/'执行方法锁定.json')
    copy=ROOT/protocol['proposal_file']
    original=ROOT.parent/'2020年论文成果/05_投稿文件/汇报清稿218_20261106'/copy.name
    proposal_hashes={str(p):sha(p) for p in (copy,original)}
    proposal_ok=set(proposal_hashes.values())=={protocol['proposal_sha256']} and read(CODE/'config/approved_protocol.json')==protocol
    if not proposal_ok:fails.append('frozen_proposal_or_protocol_changed')
    provenance=[]
    for dataset in old['source_ledger']:
        row={'data':dataset['data'],'source':dataset['source'],'version':dataset['version'],'form':dataset['form'],
             'provenance':dataset['provenance'],'all_provenance_present':all((ROOT/f).is_file() for f in dataset['provenance'])}
        provenance.append(row)
        if not row['all_provenance_present']:fails.append('missing_source_provenance: '+dataset['data'])
    ntl=read(WORK/'aggregation/ntl_aggregation_receipt.json')
    nqa=read(WORK/'aggregation/ntl_independent_QA.json')
    eog=read(ROOT/'01_原始数据/EOG2020官方原件/来源与完整性核验.json')
    ntl_inputs=[]
    for name,record in nqa['inputs'].items():
        p=Path(name)
        if p.suffix.lower()!='.tif':continue
        okay=p.is_file() and p.stat().st_size==record['bytes'] and p.stat().st_mtime_ns==record['mtime_ns']
        ntl_inputs.append({'file':name,'unchanged_since_raw_hash_QA':okay,'retained_sha256':record['sha256']})
        if not okay:fails.append('NTL_input_changed: '+name)
    if ntl['status']!='PASS' or nqa['status']!='PASS':fails.append('NTL_QA_not_PASS')
    content=read(WORK/'manuscript/manuscript_content.json')
    result_paths=[
        '03_结果文件/indicators/ntl_by_grid.csv','03_结果文件/indicators/six_indicator_records.csv',
        '03_结果文件/indicators/mcr_by_grid.csv','03_结果文件/evaluation/scores_classified.csv',
        '03_结果文件/evaluation/entropy_weights.csv','03_结果文件/evaluation/paired_sensitivity.csv',
        '03_结果文件/evaluation/township_results.csv','03_结果文件/evaluation/regional_results.csv',
        '03_结果文件/evaluation/spatial_stability.csv']
    result_paths += [b['path'] for b in content['blocks'] if b.get('type')=='figure']
    result_paths += ['03_结果文件/论文/'+content['filename']]
    artifacts=[{'path':r,'exists':(ROOT/r).is_file(),'bytes':(ROOT/r).stat().st_size if (ROOT/r).is_file() else None} for r in result_paths]
    candidates=sorted(set(filter(None,git('ls-files','--cached','--others','--exclude-standard','-z').split('\0'))))
    patterns={
        'github_token':re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
        'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        'aws_key':re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
        'literal_bearer':re.compile(r'\bBearer\s+[A-Za-z0-9._~+/=-]{24,}'),
        'credential_url':re.compile(r'https?://[^/\s:@]+:[^/\s@]+@')}
    data_suffix={'.tif','.tiff','.gz','.zip','.7z','.shp','.shx','.dbf','.gpkg','.sqlite','.pbf','.parquet','.pdf','.docx','.pptx'}
    findings=[];data_candidates=[];scanned=0
    for name in candidates:
        p=CODE/name
        if p.suffix.lower() in data_suffix:data_candidates.append(name)
        if not p.is_file() or p.stat().st_size>3_000_000:continue
        try:text=p.read_text(encoding='utf-8-sig')
        except (UnicodeError,OSError):continue
        scanned+=1
        for i,line in enumerate(text.splitlines(),1):
            for kind,pattern in patterns.items():
                if pattern.search(line):findings.append({'file':name,'line':i,'kind':kind,'value':'REDACTED'})
            for url in re.findall(r'https?://[^\s\"\'<>]+',line):
                try: query=parse_qs(urlsplit(url).query)
                except ValueError:continue
                if any(k.lower() in {'sig','access_token','api_key','apikey','token'} and any(len(v)>16 and 'REPLACE' not in v for v in vals) for k,vals in query.items()):
                    findings.append({'file':name,'line':i,'kind':'signed_or_secret_url','value':'REDACTED'})
    probes=['example.tif.gz','example.gpkg','example.shp','.env.local','cookies.json','credentials.json','example.tif','example.docx']
    ir=subprocess.run(['git','-C',str(CODE),'check-ignore',*probes],capture_output=True,text=True)
    if ir.returncode not in (0,1):raise RuntimeError('ignore probe error')
    unprotected=sorted(set(probes)-set(ir.stdout.splitlines()))
    if findings or data_candidates or unprotected:fails.append('code_publication_candidates_require_review')
    readme=(CODE/'README.md').read_text(encoding='utf-8-sig')
    readme_boundary='不能仅凭计算验收推定全文交付完成' in readme and '原生 Office 渲染与逐页审阅仍须另行完成' in readme
    if not readme_boundary:fails.append('README_final_document_gate_unclear')
    manifest=read(ROOT/'project.yaml')
    cont=read(WORK/'继续执行说明.json')
    stale=[]
    if 'BLOCKED' in manifest.get('sources',{}).get('ntl',{}).get('access',{}).get('status',''):
        stale.append({'file':'project.yaml','current_fact':'Official NTL pair archived, aggregation and independent QA PASS; refresh source artifacts and execution snapshot'})
    if 'BLOCKED' in str(cont.get('goal_status','')) or 'absent' in str(cont.get('main_blocker','')):
        stale.append({'file':'02_过程文件/继续执行说明.json','current_fact':'Inputs and six-indicator analysis complete; document/layout/push gates must reflect actual final receipts'})
    pending=[]
    for rel in ['02_过程文件/aggregation/NTL汇总运行说明.txt','02_过程文件/数据审计/219_data_audit_final.json',
                '02_过程文件/数据审计/219_raster_inventory.csv','02_过程文件/数据审计/219_数据与软件审计说明.txt',
                '02_过程文件/aggregation/ntl_script_delivery_manifest.json']:
        p=ROOT/rel
        pending.append({'file':rel,'exists':p.is_file(),'policy':'Earlier acquisition snapshot; preserve historical text and explicitly supersede/link current complete audit in final index'})
    scientific=read(WORK/'evaluation/final_scientific_QA.json')
    textqa=read(WORK/'manuscript/final_numeric_text_QA.json')
    report={'status':('PASS_INPUTS_AND_CODE_SCREEN_WITH_STATUS_REFRESH_PENDING' if stale else 'PASS_PREPUBLICATION_INPUTS_AND_CODE_SCREEN') if not fails else 'FAIL',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'failures':fails,
        'scope':'Read-only raw/provenance and current code candidate check. Does not certify native final Word/PDF layout or remote publication.',
        'large_raw_hashes_recomputed':False,'receipt_reuse_basis':{'prior_audit':str(oldpath),'prior_sha256':sha(oldpath),'unchanged_size_mtime_checks':raw_checks},
        'raw_files_n':len(current_files),'new_raw_files_since_previous_audit':new_files,'indexed_source_checks':indexed,
        'approved_proposal':{'hashes':proposal_hashes,'unchanged_and_protocol_identical':proposal_ok},
        'data_source_ledger':provenance,'EOG':{'release':eog['release_prefix'],'archive_status':eog['status'],'aggregation':ntl['status'],'independent_QA':nqa['status'],'retained_input_checks':ntl_inputs},
        'artifact_presence':artifacts,'missing_artifacts':[a['path'] for a in artifacts if not a['exists']],
        'scientific_QA_status':scientific['status'],'numeric_text_QA_status':textqa['status'],
        'numeric_text_content_hash_matches':textqa.get('content_sha256')==sha(WORK/'manuscript/manuscript_content.json'),
        'README_keeps_final_Word_gate':readme_boundary,'current_status_files_to_update':stale,'historical_records_to_supersede':pending,
        'code_screen':{'candidate_files':len(candidates),'text_files_scanned':scanned,'data_candidates':data_candidates,'credential_findings':findings,'unprotected_ignore_probes':unprotected,
            'scope':'Current tracked and nonignored untracked files; no browser credential access and no all-history secret scan',
            'head_commit':git('rev-parse','HEAD').strip(),'worktree_status':git('status','--short').splitlines(),'remote':git('remote','get-url','origin').strip(),'commit_or_push_performed':False},
        'auditor_script_sha256':sha(Path(__file__))}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','failures','raw_files_n','missing_artifacts','README_keeps_final_Word_gate','current_status_files_to_update']},ensure_ascii=False))

if __name__=='__main__':main()
