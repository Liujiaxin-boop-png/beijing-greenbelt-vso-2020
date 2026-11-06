"""Archive pre-fix classification outputs, code and upstream provenance."""
from pathlib import Path
import json,hashlib,shutil,urllib.request,datetime
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'02_过程文件/evaluation/jenks_implementation_fix'
ARCH=WORK/'before_fix';ARCH.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
record={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'ARCHIVED_BEFORE_CLASSIFICATION_FIX',
 'scientific_method':'Five-class Fisher-Jenks natural breaks, baseline fitted separately by habitat; frozen thresholds across scenarios',
 'implementation_reason':'QGIS3.28.2 backtracking defect in official source; alternate Pro3.1.6 NaturalBreaks did not always attain independent global minimum within-class SSE',
 'preserved_scope':'Indicators, baseline populations, normalization, entropy weights and all continuous ER values unchanged',
 'files':[],'references':[]}
for p in (ROOT/'03_结果文件/evaluation').iterdir():
    if p.is_file():
        t=ARCH/p.name;assert not t.exists();shutil.copy2(p,t);assert sha(p)==sha(t)
        record['files'].append({'source':str(p.relative_to(ROOT)),'archived_to':str(t.relative_to(ROOT)),'sha256':sha(p)})
for name in ('qgis_classify_scores.py','summarize_evaluation.py','verify_final_analysis.py','pipeline.py'):
    p=ROOT/'05_代码'/('src/'+name if name!='pipeline.py' else name)
    t=ARCH/name;assert not t.exists();shutil.copy2(p,t)
    record['files'].append({'source':str(p.relative_to(ROOT)),'archived_to':str(t.relative_to(ROOT)),'sha256':sha(p)})
for name in ('final_scientific_QA.json','jenks_boundary_diagnosis.json','class_boundary_diagnosis.json'):
    p=ROOT/'02_过程文件/evaluation'/name;t=ARCH/name;assert not t.exists();shutil.copy2(p,t)
links={
 'qgis3282_jenks.cpp':'https://raw.githubusercontent.com/qgis/QGIS/final-3_28_2/src/core/classification/qgsclassificationjenks.cpp',
 'qgis_issue67546.html':'https://github.com/qgis/QGIS/issues/67546',
 'jenkspy_pypi_0.4.1.json':'https://pypi.org/pypi/jenkspy/0.4.1/json',
 'jenkspy_readme.md':'https://raw.githubusercontent.com/mthh/jenkspy/master/README.md'}
for name,url in links.items():
    target=WORK/name;target.write_bytes(urllib.request.urlopen(url,timeout=45).read())
    record['references'].append({'url':url,'saved_file':str(target.relative_to(ROOT)),'sha256':sha(target)})
meta=json.loads((WORK/'jenkspy_pypi_0.4.1.json').read_text())
wheel=WORK/'software/jenkspy-0.4.1-cp312-cp312-win_amd64.whl'
entry=next(x for x in meta['urls'] if x['filename']==wheel.name)
assert sha(wheel)==entry['digests']['sha256']
record['library']={'package':'jenkspy','version':'0.4.1','wheel':wheel.name,'sha256':sha(wheel),'official_pypi_hash_match':True,'source_url':entry['url'],'upload_time':entry['upload_time_iso_8601'],'author':meta['info']['author'],'license':meta['info']['license']}
protected=[ROOT/'03_结果文件/indicators/six_indicator_records.csv']+[ROOT/'03_结果文件/evaluation'/n for n in ('scores_all_scenarios.csv','normalization.csv','entropy_weights.csv','paired_sensitivity.csv','scenario_coverage.csv','reestimated_weights.csv','indicator_correlations.csv','indicator_descriptives.csv')]
record['protected_continuous_sha256']={str(p.relative_to(ROOT)):sha(p) for p in protected}
(WORK/'implementation_fix_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':record['status'],'archived_files':len(record['files']),'library':record['library']},ensure_ascii=False))
