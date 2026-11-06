"""Finalize the implementation repair audit after full independent QA."""
from pathlib import Path
import csv,json,hashlib,datetime,collections,math,statistics,bisect
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'02_过程文件/evaluation/jenks_implementation_fix'
OUT=ROOT/'03_结果文件/evaluation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
path=WORK/'implementation_fix_receipt.json';record=json.loads(path.read_text(encoding='utf8'))
for rel,expected in record['protected_continuous_sha256'].items():assert sha(ROOT/rel)==expected,rel
qa=json.loads((ROOT/'02_过程文件/evaluation/final_scientific_QA.json').read_text(encoding='utf8'));assert qa['status']=='PASS'
old={(r['habitat'],r['scenario'],r['grid_id']):r for r in rows(WORK/'before_fix/scores_classified.csv')}
now=rows(OUT/'scores_classified.csv');diff=[]
for r in now:
    k=(r['habitat'],r['scenario'],r['grid_id'])
    assert r['ER']==old[k]['ER'],'Continuous exported ER changed'
    if r['ER_class']!=old[k]['ER_class']:diff.append({'habitat':k[0],'scenario':k[1],'grid_id':k[2],'before':old[k]['ER_class'],'after':r['ER_class']})
record.update(status='PASS',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 protected_continuous_hashes_unchanged=True,independent_scientific_QA_sha256=sha(ROOT/'02_过程文件/evaluation/final_scientific_QA.json'),
 changed_class_records=len(diff),class_changes_by_habitat=dict(collections.Counter(r['habitat'] for r in diff)),class_changes=diff,
 exact_Jenks_validation=next(x for x in qa['checks'] if x['section']=='independent_Jenks_and_fixed_scenario_classes'),
 geometry_validation=next(x for x in qa['checks'] if x['section']=='all_35_townships_and_region'),
 original_township_csv_byte_identical=sha(OUT/'township_results.csv')==sha(WORK/'before_fix/township_results.csv'),
 classification_input_policy='All frozen original score doubles after independent scalar scoring passed; no tolerance moves a class boundary',
 pipeline_classifier='05_代码/src/classify_scores.py',native_map_engine='QGIS3.28.2',
 diagnosis_paths=['02_过程文件/evaluation/native_jenks_diagnostic/native_breaks.json','02_过程文件/evaluation/jenks_boundary_diagnosis.json','02_过程文件/evaluation/town_geometry_diagnosis.json'])
record['final_output_sha256']={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}
path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':record['status'],'changed_class_records':len(diff),'unchanged_continuous':True,'township_csv_byte_identical':record['original_township_csv_byte_identical']},ensure_ascii=False))
