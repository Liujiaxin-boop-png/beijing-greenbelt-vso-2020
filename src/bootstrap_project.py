"""Freeze the approved protocol without modifying any historical document."""
from pathlib import Path
import json, hashlib, shutil, datetime

PROJECT = Path(__file__).resolve().parents[2]
WORKSPACE = PROJECT.parent

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def main():
    for name in ['01_原始数据','02_过程文件','03_结果文件','04_图件','05_代码']:
        (PROJECT/name).mkdir(exist_ok=True)
    source = WORKSPACE/'2020年论文成果/05_投稿文件/汇报清稿218_20261106/北京二道绿隔生态韧性评价_开题报告_组会汇报清稿_20261106.docx'
    expected = 'e31da3054ae9c7e95d705a9e92718704c9ca5b92ce13ba5059d03f8143519db7'
    assert sha(source)==expected, 'Approved proposal changed; review before proceeding'
    protocol_dir = PROJECT/'01_原始数据/研究依据'
    protocol_dir.mkdir(exist_ok=True)
    dest=protocol_dir/source.name
    if not dest.exists(): shutil.copy2(source,dest)
    assert sha(dest)==expected
    text_source=WORKSPACE/'2020年论文成果/02_过程数据/汇报清稿218_20261106/218_clean_fulltext.txt'
    shutil.copy2(text_source,protocol_dir/'已确认开题报告全文.txt')
    lock = {
        'status':'PROTOCOL_FROZEN_ANALYSIS_NOT_YET_COMPLETE',
        'approved_on':'2026-11-06','proposal_sha256':expected,
        'proposal_file':str(dest.relative_to(PROJECT)),
        'year':2020,'framework':'Vulnerability-Sensitivity-Self-organization',
        'scope':'Research-scope polygon: covered portions of 35 townships; no automatic substitution with the official planning boundary',
        'main_grid_m':1000,'scale_sensitivity_m':500,'grid_shape':'square',
        'habitat_groups':{'forest_shrub':[2,3],'grassland':[4],'water_wetland':[5,9]},
        'ecological_classes_CLCD':[2,3,4,5,9],'construction_proxy_CLCD':[8],
        'criteria':{'V':['HQ_H','NTL'],'S':['CLUMPY','MCR'],'O':['SSI','E_fraction']},
        'directions':{'HQ_H':1,'NTL':-1,'CLUMPY':1,'MCR':-1,'SSI':-1,'E_fraction':1},
        'software_contract':{'HQ':'native InVEST Habitat Quality','CLUMPY':'native FRAGSTATS class-level','grid':'ArcMap 10.8 Create Fishnet','MCR':'ArcMap 10.8 Cost Distance, excluding same complete ParentPatchID','SSI':'ArcMap 10.8 Euclidean Distance','mapping':'installed GIS software with editable project'},
        'normalization':'positive/negative min-max, fixed references for planned comparisons',
        'weighting':'entropy weights; linear aggregation; within habitat and common valid domain',
        'town_statistics':'intersection-area-weighted inside research scope, report valid coverage',
        'comparisons':['single-indicator omission with remaining weights rescaled','CLCD versus WorldCover','source-selection parameters','resistance parameters','500m aggregated to 1km','reestimated weights separately'],
        'thermal_check':'2020 Landsat8 surface temperature; grey-green configuration, repeated across spatial sectors',
        'data_excluded':['NPP','questionnaires','social resilience'],
        'safeguards':['No fabricated missing values','No upstream/component regression against ER as causal evidence','No changes to the six-indicator framework','No transplant of prior R-Re-A empirical results'],
        'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    (PROJECT/'02_过程文件/执行方法锁定.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'protocol_sha256':expected,'project':str(PROJECT),'status':lock['status']},ensure_ascii=False))

if __name__=='__main__':main()
