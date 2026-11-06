"""Historical QGIS diagnostic, excluded from the canonical pipeline.

QGIS3.28.2 Jenks failed minimum-SSE verification (upstream issue67546).
Use classify_scores.py with fixed jenkspy0.4.1; QGIS remains the map engine.
The original diagnostic implementation below is preserved for audit only.
"""
raise RuntimeError('Use Python3.12 src/classify_scores.py; native QGIS3.28.2 Jenks is excluded after a verified upstream implementation defect.')
import os,csv,json,gc
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import QgsApplication,QgsClassificationJenks,Qgis
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'03_结果文件/evaluation/scores_all_scenarios.csv'
if not path.exists():raise RuntimeError('Empirical six-indicator scores are not available')
app=QgsApplication([],False);app.initQgis()
def classify():
    with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    groups={}
    for row in rows:
        if row['scenario']=='baseline':groups.setdefault(row['habitat'],[]).append(float(row['ER']))
    classes={}
    for habitat,vals in groups.items():
        method=QgsClassificationJenks();ranges=method.classes(vals,5)
        assert len(ranges)==5
        bounds=[{'lower':r.lowerBound(),'upper':r.upperBound(),'label':r.label()} for r in ranges]
        assert all(bounds[i]['upper']<=bounds[i+1]['upper'] for i in range(4))
        classes[habitat]={'n':len(vals),'classes':bounds,'fit':'baseline only','comparison':'same fixed bounds in every comparison; underflow firstclass and overflow lastclass','meaning':'relative within-habitat descriptive levels; no universal ecological thresholds'}
    out=ROOT/'03_结果文件/evaluation/classification.json'
    out.write_text(json.dumps({'engine':'QGIS '+Qgis.QGIS_VERSION,'method':'natural_breaks_Jenks','reference':'Shi etal2022 Land11:921 section2.3 andFig2','habitats':classes},ensure_ascii=False,indent=2),encoding='utf8')
    print('BASELINE_JENKS_CLASSIFICATION_COMPLETE')

classify()
gc.collect();app.exitQgis()
