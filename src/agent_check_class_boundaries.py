"""Read-only diagnosis of round-trip floating point at fixed class boundaries."""
import csv,json,bisect
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'03_结果文件/evaluation'
def rows(name):return list(csv.DictReader((OUT/name).open(encoding='utf-8-sig',newline='')))
score={(r['habitat'],r['scenario'],r['grid_id']):r for r in rows('scores_all_scenarios.csv')}
breaks=json.loads((OUT/'classification.json').read_text(encoding='utf8'))['habitats']
ans=[]
for r in rows('scores_classified.csv'):
    k=(r['habitat'],r['scenario'],r['grid_id']);original=float(score[k]['ER']);exported=float(r['ER'])
    upper=[c['upper'] for c in breaks[r['habitat']]['classes']]
    expected=min(4,bisect.bisect_left(upper,original))+1
    if expected!=int(r['ER_class']):
        ans.append({'key':k,'original_ER':original,'summarized_ER':exported,'numeric_change':exported-original,'class_using_original_score':expected,'reported_class':int(r['ER_class'])})
record={'class_mismatches_using_original_frozen_scores':len(ans),'details':ans}
(ROOT/'02_过程文件/evaluation/class_boundary_diagnosis.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps(record))
