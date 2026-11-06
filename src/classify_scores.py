"""Exact Fisher-Jenks natural breaks fitted once to each real habitat baseline.

Only the classification implementation changed after native QGIS3.28.2 failed
independent minimum-SSE verification (upstream QGIS issue67546). Indicators,
scores, five classes, habitat domains and fixed-threshold comparisons remain
unchanged. Run with the recorded Python3.12 environment and jenkspy0.4.1.
"""
import csv,json,math,hashlib
from pathlib import Path
import jenkspy
ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT/'03_结果文件/evaluation/scores_all_scenarios.csv'

def main():
    assert jenkspy.__version__=='0.4.1','Reproduction requires fixed jenkspy0.4.1'
    before=hashlib.sha256(PATH.read_bytes()).hexdigest()
    with PATH.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    groups={}
    for row in rows:
        if row['scenario']=='baseline':groups.setdefault(row['habitat'],[]).append(float(row['ER']))
    assert set(groups)=={'forest_shrub','grassland','water_wetland'}
    classes={}
    for habitat,values in groups.items():
        assert all(math.isfinite(v) for v in values) and len(set(values))>=5
        breaks=[float(v) for v in jenkspy.jenks_breaks(values,n_classes=5)]
        assert len(breaks)==6 and breaks[0]==min(values) and breaks[-1]==max(values)
        assert all(breaks[i]<breaks[i+1] for i in range(5))
        bounds=[{'lower':breaks[i],'upper':breaks[i+1],'label':f'{breaks[i]:.4f} - {breaks[i+1]:.4f}'} for i in range(5)]
        classes[habitat]={'n':len(values),'classes':bounds,'fit':'baseline only; all valid baseline scores, no sampling','comparison':'same fixed bounds in every comparison; underflow firstclass and overflow lastclass','meaning':'relative within-habitat descriptive levels; no universal ecological thresholds'}
    output={'engine':'jenkspy '+jenkspy.__version__,'algorithm':'exact Fisher-Jenks optimization',
      'method':'natural_breaks_Jenks','reference':'Shi etal2022 Land11:921 section2.3 andFig2',
      'software_reference':'https://github.com/mthh/jenkspy','implementation_fix_reference':'https://github.com/qgis/QGIS/issues/67546',
      'source_scores_sha256':before,'habitats':classes}
    assert hashlib.sha256(PATH.read_bytes()).hexdigest()==before
    (PATH.parent/'classification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf8')
    print('BASELINE_EXACT_FISHER_JENKS_CLASSIFICATION_COMPLETE')

if __name__=='__main__':main()
