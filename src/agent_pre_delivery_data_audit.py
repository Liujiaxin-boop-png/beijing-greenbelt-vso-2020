"""Read-only delivery snapshot; reuse provenance receipts, never rehash all raw data."""
from pathlib import Path
import collections, datetime, hashlib, json, re, subprocess
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT/'05_代码'
OUT = ROOT/'02_过程文件/delivery/pre_delivery_data_audit.json'

def read(rel):
    return json.loads((ROOT/rel).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(CODE), *args], encoding='utf8', errors='replace')

def relative(path):
    return str(Path(path).relative_to(ROOT))

def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw = ROOT/'01_原始数据'
    files = [p for p in raw.rglob('*') if p.is_file()]
    folders = []
    for folder in sorted(p for p in raw.iterdir() if p.is_dir()):
        items = [p for p in files if folder in p.parents]
        folders.append({'folder': relative(folder), 'files': len(items), 'bytes': sum(p.stat().st_size for p in items)})
    expected = {}

    def add(path, record, evidence):
        p = Path(path)
        p = p if p.is_absolute() else ROOT/p
        try:
            rel = relative(p.resolve())
        except ValueError:
            return
        if not rel.startswith('01_原始数据'):
            return
        digest = record.get('sha256')
        if digest:
            expected.setdefault(rel, []).append({'sha256': digest, 'bytes': record.get('bytes'), 'receipt': evidence})

    evidence_paths = [
        '02_过程文件/数据审计/219_existing_inputs_inventory.json',
        '02_过程文件/数据审计/219_data_audit_final.json',
        '02_过程文件/数据审计/219_worldcover_original_download.json',
        '02_过程文件/数据审计/219_support_downloads.json',
        '02_过程文件/数据审计/219_stqa_downloads.json',
        '02_过程文件/thermal/aux_download_manifest.json',
    ]
    def index(obj, evidence):
        if isinstance(obj, dict):
            if obj.get('sha256'):
                for key in ['staged_relative', 'local_relative', 'raw_file', 'file', 'output', 'path']:
                    if isinstance(obj.get(key), str):
                        add(obj[key], obj, evidence)
            for val in obj.values(): index(val, evidence)
        elif isinstance(obj, list):
            for val in obj: index(val, evidence)
    for rel in evidence_paths:
        index(read(rel), rel)
    eog_rel = '01_原始数据/EOG2020官方原件/来源与完整性核验.json'
    eog = read(eog_rel)
    eog_checks = []
    for row in eog['files']:
        name = eog['release_prefix']+'.'+row['product']+'.dat.tif'
        for ext, sizekey, hashkey in [('', 'tif_bytes', 'tif_sha256'), ('.gz', 'gzip_bytes', 'gzip_sha256')]:
            p = raw/'EOG2020官方原件'/(name+ext)
            rec = {'bytes': row[sizekey], 'sha256': row[hashkey]}
            add(p, rec, eog_rel)
            eog_checks.append({'file': relative(p), 'exists': p.exists(), 'actual_bytes': p.stat().st_size if p.exists() else None,
                               'expected_bytes': row[sizekey], 'size_match': p.exists() and p.stat().st_size == row[sizekey],
                               'retained_verified_sha256': row[hashkey], 'gzip_crc_verified': row['gzip_crc_verified'],
                               'official_url': row['source_url'], 'large_hash_repeated_in_this_audit': False})
    indexed_checks, inconsistent = [], []
    for rel, records in sorted(expected.items()):
        p = ROOT/rel
        digests = sorted(set(x['sha256'] for x in records))
        sizes = sorted(set(x['bytes'] for x in records if x['bytes'] is not None))
        okay = p.exists() and (not sizes or p.stat().st_size in sizes) and len(digests) == 1 and len(sizes) <= 1
        indexed_checks.append({'file': rel, 'exists': p.exists(), 'actual_bytes': p.stat().st_size if p.exists() else None,
                               'receipt_bytes': sizes, 'receipt_sha256': digests, 'pass_size_and_receipt_consistency': okay,
                               'evidence_receipts': sorted(set(x['receipt'] for x in records))})
        if not okay: inconsistent.append(rel)
    locked = read('02_过程文件/执行方法锁定.json')
    proposal = ROOT/locked['proposal_file']
    original = ROOT.parent/'2020年论文成果/05_投稿文件/汇报清稿218_20261106'/proposal.name
    proposal_hashes = {relative(proposal): sha(proposal), str(original): sha(original)}
    proposal_ok = set(proposal_hashes.values()) == {locked['proposal_sha256']}
    protocol_same = read('05_代码/config/approved_protocol.json') == locked
    ntl = read('02_过程文件/aggregation/ntl_aggregation_receipt.json')
    ntl_qa = read('02_过程文件/aggregation/ntl_independent_QA.json')
    for item in eog_checks:
        if item['file'].endswith('.tif'):
            p = (ROOT/item['file']).resolve()
            prior = ntl_qa['inputs'].get(str(p))
            item['fresh_independent_hash_receipt_matches'] = bool(prior and prior['sha256'] == item['retained_verified_sha256'])
            item['unchanged_since_independent_QA'] = bool(prior and p.stat().st_size == prior['bytes'] and p.stat().st_mtime_ns == prior['mtime_ns'])
    source_ledger = [
        {'data': 'CLCD2020', 'source': 'https://zenodo.org/records/8176941', 'version': 'record v1.0.2; source filename CLCD_v01_2020_albert.tif retained',
         'archive': '01_原始数据/CLCD2020', 'provenance': ['01_原始数据/CLCD2020/CLCD_v01_2020_albert.metadata.json','02_过程文件/数据审计/219_CLCD_full_original_window_equality.json'],
         'form': 'Complete national distributed file plus independently verified native-grid subset; subset is not a separate full original product'},
        {'data': 'WorldCover2020', 'source': 'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/map/', 'version': '2020 v100 N39E114 and N39E117',
         'archive': '01_原始数据/WorldCover2020官方整幅', 'provenance': ['02_过程文件/数据审计/219_worldcover_original_download.json'], 'form': 'Two complete official original tiles'},
        {'data': 'OSM roads', 'source': 'https://download.geofabrik.de/asia/china-200101-free.shp.zip', 'version': 'Archive filename date 2020-01-01; exact UTC cutoff unavailable',
         'archive': '01_原始数据/OSM2020原始道路成员', 'provenance': ['01_原始数据/来源记录/OSM_original_manifest.json','02_过程文件/数据审计/219_existing_inputs_inventory.json'],
         'form': 'Six original road-layer/README ZIP members with retained CRC and SHA; complete national ZIP not downloaded'},
        {'data': 'EOG VIIRS', 'source': 'https://eogdata.mines.edu/nighttime_light/annual/v21/2020/', 'version': eog['release_prefix'],
         'archive': '01_原始数据/EOG2020官方原件', 'provenance': [eog_rel,'02_过程文件/aggregation/ntl_independent_QA.json'], 'form': 'Both original gzip and both decompressed TIFF; no replacement product'},
        {'data': 'Landsat 8 C2 L2', 'source': 'https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2',
         'version': '2020-08-03 primary, 2020-06-16 and 2020-08-10 separate supplementary snapshots',
         'archive': '01_原始数据/Landsat8_2020已有原生窗口 + Landsat8_2020补充质量层',
         'provenance': ['01_原始数据/Landsat8_2020已有原生窗口/download_extent_provenance.json','02_过程文件/数据审计/219_stqa_downloads.json','02_过程文件/thermal/aux_download_manifest.json'],
         'form': 'Unaltered native-pixel DN/QA/EMIS extraction windows and scene MTL/STAC; not complete scene products; not an annual-temperature composite'},
        {'data': 'NASADEM', 'source': 'https://lpdaac.usgs.gov/products/nasadem_hgtv001/', 'version': 'HGT v001, SRTM-era terrain rather than a 2020 observation',
         'archive': '01_原始数据/NASADEM完整瓦片', 'provenance': ['02_过程文件/数据审计/219_support_downloads.json'],
         'form': 'Six complete distributed tiles plus earlier retained native subsets; ancillary archive, not an extra seventh indicator'},
        {'data': '研究范围0328', 'source': 'User-supplied previous-study spatial database', 'version': '38 features, portions of 35 townships',
         'archive': '01_原始数据/研究范围', 'provenance': ['02_过程文件/数据审计/219_boundary_readback.json','02_过程文件/数据审计/219_boundary_overlap_audit.json'],
         'form': 'Original shapefile with companions; do not replace with official greenbelt planning boundary'},
    ]
    source_missing = []
    for row in source_ledger:
        row['provenance_files_present'] = all((ROOT/p).exists() for p in row['provenance'])
        if not row['provenance_files_present']: source_missing.append(row['data'])
    stale = [
        {'file':'project.yaml', 'issue':'sources.ntl.access.status remains BLOCKED_MISSING_INPUT and raw file list absent; current run snapshot predates actual NTL/evaluation', 'update':'Refresh from actual receipts; add four EOG original artifacts, release, hashes, independent QA and current evaluation/map state'},
        {'file':'02_过程文件/继续执行说明.json', 'issue':'goal_status/main_blocker/manuscript_status/remaining_required still say original EOG inputs absent and ER not calculated', 'update':'Replace with current nonblocked input state and genuinely pending delivery tasks; update pushed commit only after actual push'},
        {'file':'05_代码/README.md', 'issue':'Current status paragraphs claim NTL missing and no new six-indicator score', 'update':'Record real 11479-row NTL and actual six-indicator evaluation, distinguishing pending scientific/figure/manuscript QA'},
        {'file':'02_过程文件/aggregation/NTL汇总运行说明.txt', 'issue':'Opening paragraph says real originals absent, no CSV and BLOCKED', 'update':'Add actual archived release/config/output/QA status; retain reproducible procedure and complete-support rule'},
        {'file':'02_过程文件/数据审计/219_data_audit_final.json', 'issue':'DATA_STAGE_AVAILABLE_EXCEPT_EOG_VIIRS and remaining_required_input are historical, software tests are also pre-install snapshots', 'update':'Preserve historical evidence; create or link a current consolidated data/engine audit rather than silently presenting old status as current'},
        {'file':'02_过程文件/数据审计/219_raster_inventory.csv', 'issue':'Consolidated raster table predates EOG originals', 'update':'Add both original EOG TIFFs with nominal15arcsec/actual0.0041666667degree affine, raw NoData=None, provenance/hash; distinguish originals from native subsets'},
        {'file':'02_过程文件/数据审计/219_数据与软件审计说明.txt', 'issue':'Summary belongs to the pre-EOG acquisition snapshot', 'update':'Point readers to current complete source ledger and actual native software receipts'},
        {'file':'02_过程文件/aggregation/ntl_script_delivery_manifest.json', 'issue':'IMPLEMENTATION_READY_REAL_INPUTS_ABSENT plus old hashes no longer describe edited input-recognition code and new independent audit', 'update':'Preserve as historical or regenerate current source artifact manifest and include independent QA script'},
        {'file':'05_代码/src/inventory_project.py', 'issue':'Generated completion_note hardcodes active MCR stages and absent EOG inputs', 'update':'Use neutral/current receipt-based wording before regenerating inventory'},
        {'file':'05_代码/src/build_project_manifest.py', 'issue':'NTL status reads live receipt but its source entry omits actual files/hashes; outputs/type/steps remain partial-era defaults', 'update':'Include actual receipt inputs and all downstream stages; leave completion conditional on final scientific and document QA'},
    ]
    historical = [
        {'file':'02_过程文件/goal_blocked_audit_20261106.json', 'policy':'Keep historical blocked-turn evidence; current continue file should supersede it, never rewrite history'},
        {'file':'02_过程文件/aggregation/ntl_implementation_checks.json', 'policy':'Keep pre-input implementation test provenance; NOT_RUN was true then and is not current observational status'},
        {'file':'02_过程文件/数据审计/219_NTL_access_audit.json', 'policy':'Keep historical access investigation; current official acquisition supersedes missing-input inference'},
        {'file':'02_过程文件/执行方法锁定.json and 05_代码/config/approved_protocol.json', 'policy':'Preserve frozen approved methodological payload; report actual execution status separately'},
    ]
    receipt_paths = [
        '02_过程文件/aggregation/indicator_join_receipt.json','02_过程文件/evaluation/evaluation_receipt.json',
        '02_过程文件/evaluation/reporting_receipt.json','02_过程文件/evaluation/final_scientific_QA.json',
        '02_过程文件/mcr_aggregation_independent_QA.json','02_过程文件/aggregation/ntl_independent_QA.json',
    ]
    current_receipts = {p:{k:v for k,v in read(p).items() if k in ['status','records','six_valid','town_rows','failure','missing_entire_metrics','sample_n','grid_samples_n']} for p in receipt_paths}
    expected_artifacts = [
        '03_结果文件/indicators/ntl_by_grid.csv','03_结果文件/indicators/six_indicator_records.csv',
        '03_结果文件/evaluation/scores_classified.csv','03_结果文件/evaluation/entropy_weights.csv',
        '03_结果文件/evaluation/paired_sensitivity.csv','03_结果文件/evaluation/township_results.csv',
        '03_结果文件/evaluation/regional_results.csv','03_结果文件/evaluation/spatial_stability.csv',
        '04_图件/图3_生态韧性空间分布.png','04_图件/图4_三维相对短板.png','04_图件/图5_空间分级稳定性.png',
        '03_结果文件/论文/北京二道绿隔生态韧性评价_论文_20261106.docx',
    ]
    artifacts = [{'path':p, 'exists':(ROOT/p).is_file(), 'bytes':(ROOT/p).stat().st_size if (ROOT/p).is_file() else None} for p in expected_artifacts]
    tracked = set(filter(None, git('ls-files','-z').split('\0')))
    candidates = sorted(set(filter(None, git('ls-files','--cached','--others','--exclude-standard','-z').split('\0'))))
    credential_patterns = {
        'github_token': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
        'aws_access_key': re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
        'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        'literal_bearer': re.compile(r'\bBearer\s+[A-Za-z0-9._~+/=-]{24,}'),
        'credential_url': re.compile(r'https?://[^/\s:@]+:[^/\s@]+@'),
    }
    findings, raw_candidates = [], []
    data_extensions = {'.tif','.tiff','.gz','.zip','.7z','.shp','.shx','.dbf','.gpkg','.sqlite','.pbf','.parquet','.pdf','.docx','.pptx'}
    text_n = 0
    for name in candidates:
        p = CODE/name
        if p.suffix.lower() in data_extensions or any(x in p.parts for x in ['01_原始数据','02_过程文件','03_结果文件','04_图件']):
            raw_candidates.append(name)
        if not p.is_file() or p.stat().st_size > 3_000_000:
            continue
        try:
            content = p.read_text(encoding='utf-8-sig')
        except (UnicodeError, OSError):
            continue
        text_n += 1
        for number, line in enumerate(content.splitlines(), 1):
            for kind, pattern in credential_patterns.items():
                if pattern.search(line): findings.append({'file':name,'line':number,'kind':kind,'value':'REDACTED'})
            for url in re.findall(r'https?://[^\s\"\'<>]+', line):
                try: query = parse_qs(urlsplit(url).query)
                except ValueError: continue
                if any(k.lower() in {'sig','access_token','api_key','apikey','token'} and any(len(v)>16 and 'REPLACE' not in v for v in values) for k,values in query.items()):
                    findings.append({'file':name,'line':number,'kind':'signed_or_secret_url_literal','value':'REDACTED'})
    probes = ['example.tif.gz','example.gpkg','example.shp','.env.local','cookies.json','credentials.json','example.tif','example.docx']
    # Pass literal arguments: Windows text-mode stdin can add CR characters
    # which make check-ignore probe a different pathname.
    ignore_probe = subprocess.run(['git','-C',str(CODE),'check-ignore',*probes],capture_output=True,text=True)
    assert ignore_probe.returncode in (0, 1), 'git check-ignore probe failed'
    ignored = set(ignore_probe.stdout.splitlines())
    public = {'tracked_files':len(tracked),'candidate_files':len(candidates),'text_files_scanned':text_n,
              'tracked_or_candidate_raw_data_artifacts':raw_candidates,'high_confidence_credential_findings':findings,
              'scan_scope':'Current tracked and nonignored untracked source/config text; no browser configuration or credentials store accessed; not a retrospective scan of all remote commits',
              'ignore_probe_unprotected':[p for p in probes if p not in ignored],
              'recommendation':'No current raw/credential file finding is not a future guarantee. Strengthen .gitignore for *.gz, geodata companions, .env.*, local cookies/credentials before broad git add; continue uploading only source/config/README.',
              'worktree_status':git('status','--short').splitlines(),'head_commit':git('rev-parse','HEAD').strip()}
    raw_inventory = [{'path':relative(p),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,
                      'has_reused_file_hash_receipt':relative(p) in expected} for p in sorted(files)]
    report = {
        'status':'PRE_DELIVERY_REVIEW_ACTIONS_REQUIRED','snapshot_utc':now,
        'scope':'Read-only pre-delivery data/provenance/status/code-upload audit; no manuscript edits or production reruns',
        'large_raw_hashing':'Not repeated. Reused original ingestion and fresh independent NTL SHA/CRC receipts; checked file existence/sizes and NTL stability. Only original/frozen proposal hashed anew.',
        'approved_proposal':{'expected_sha256':locked['proposal_sha256'],'actual_hashes':proposal_hashes,'unchanged':proposal_ok,'frozen_protocol_copies_identical':protocol_same},
        'raw_archive':{'file_n':len(files),'bytes':sum(p.stat().st_size for p in files),'groups':folders,'inventory':raw_inventory},
        'reused_receipt_file_checks':{'indexed_file_n':len(indexed_checks),'inconsistencies':inconsistent,'records':indexed_checks},
        'EOG_original_pair':{'archive_status':eog['status'],'release':eog['release_prefix'],'files':eog_checks,'production_status':ntl['status'],'independent_QA_status':ntl_qa['status'],'grid_rows':ntl['rows'],
                             'provider_checksum_available':eog['provider_checksum_available'],'hash_interpretation':'Local SHA confirms retained/copy identity, gzip CRC integrity and current original readback; no provider-published SHA was available'},
        'source_ledger':source_ledger,'missing_provenance_files':source_missing,
        'source_inventory_recommendation':'Evidence exists per dataset, but update the consolidated download/raster ledger to include EOG and direct Geofabrik URL. Keep extraction windows distinct from whole original products; do not relabel NASADEM as a 2020 measurement.',
        'current_stale_files_to_update':stale,'historical_records_to_preserve':historical,
        'current_stage_receipts':current_receipts,'core_artifact_presence':artifacts,
        'not_yet_delivery_ready':{'missing_artifacts_at_snapshot':[a['path'] for a in artifacts if not a['exists']],
                                 'final_scientific_QA_status':current_receipts['02_过程文件/evaluation/final_scientific_QA.json'].get('status'),
                                 'note':'Results may exist while independent QA is unresolved. Final native/visual figure checks, manuscript per-page numeric/visual QA and Git push verification remain separate gates; this audit does not certify them.'},
        'public_code_upload':public,
        'no_data_gap_found_for_frozen_six_indicator_inputs':not inconsistent and not source_missing and ntl_qa['status']=='PASS',
        'changes_made':['Only this audit script and its requested delivery audit JSON; no source archive, frozen proposal, manuscript or analytical output changed'],
    }
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'status':report['status'],'proposal_unchanged':proposal_ok,'raw_files':len(files),'receipt_checks':len(indexed_checks),
                      'receipt_inconsistencies':len(inconsistent),'credential_findings':len(findings),'raw_upload_candidates':len(raw_candidates),
                      'missing_artifacts':report['not_yet_delivery_ready']['missing_artifacts_at_snapshot']},ensure_ascii=False))

if __name__=='__main__': main()
