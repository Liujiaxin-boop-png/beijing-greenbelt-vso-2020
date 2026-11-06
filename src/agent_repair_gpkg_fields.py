"""One-time output-schema repair receipt; does not recompute scores or classes."""
from pathlib import Path
import hashlib,json,datetime,subprocess,sys,shutil
import geopandas as gpd
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'03_结果文件/evaluation'
WORK=ROOT/'02_过程文件/evaluation/gpkg_field_compatibility_fix'
WORK.mkdir(parents=True,exist_ok=True)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
record={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'purpose':'GeoPackage case-insensitive field compatibility only; no method, indicator, score or class change',
 'original_error':"pyogrio.errors.FieldError: Error adding field 'grid_id' to layer",
 'removed_redundant_fields':['Grid_ID','Scale_m'],'retained_fields':['grid_id','scale_m'],
 'software':{'python':sys.version,'executable':sys.executable},'status':'STARTED'}
before={p.name:sha(p) for p in OUT.iterdir() if p.suffix in ('.csv','.json')}
record['numerical_and_classification_before_sha256']=before
geom=gpd.read_file(ROOT/'03_结果文件/indicators/grid_geometry.gpkg',layer='grid_1000')
raw=pd.read_csv(ROOT/'03_结果文件/indicators/six_indicator_records.csv')
record['duplicate_field_checks']=[]
for h in ('forest_shrub','grassland','water_wetland'):
    rr=raw[(raw.habitat==h)&(raw['product']=='clcd')&(raw.scale_m==1000)]
    m=geom.merge(rr,left_on='Grid_ID',right_on='grid_id',validate='one_to_one')
    assert len(m)==2478
    assert m.Grid_ID.eq(m.grid_id).all() and m.Scale_m.eq(m.scale_m).all()
    record['duplicate_field_checks'].append({'habitat':h,'rows':len(m),'grid_keys_equal':True,'scales_equal':True})
failed=OUT/'evaluation_maps.gpkg';backup=WORK/'evaluation_maps_failed_before_field_fix.gpkg'
assert failed.exists() and not backup.exists(), 'One-time repair requires original failed GPKG and unused backup path'
assert failed.resolve().is_relative_to(ROOT.resolve()) and backup.resolve().is_relative_to(ROOT.resolve())
record['failed_gpkg_sha256']=sha(failed)
shutil.move(str(failed),str(backup))
assert sha(backup)==record['failed_gpkg_sha256']
record['failed_gpkg_archived_to']=str(backup)
script=ROOT/'05_代码/src/summarize_evaluation.py'
record['repaired_script_sha256']=sha(script)
(WORK/'repair_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
with (WORK/'summarize_stdout.log').open('w',encoding='utf8') as log:
    run=subprocess.run([sys.executable,str(script)],stdout=log,stderr=subprocess.STDOUT)
record['summarize_returncode']=run.returncode
after={name:sha(OUT/name) for name in before}
record['numerical_and_classification_after_sha256']=after
record['all_preexisting_csv_and_classification_byte_identical']=before==after
record['changed_files']=[name for name in before if before[name]!=after[name]]
record['output_layers']=[]
if run.returncode==0:
    for h in ('forest_shrub','grassland','water_wetland'):
        layer=gpd.read_file(OUT/'evaluation_maps.gpkg',layer=h)
        assert len(layer)==2478 and layer.grid_id.nunique()==2478
        assert len({str(c).casefold() for c in layer.columns})==len(layer.columns)
        record['output_layers'].append({'habitat':h,'rows':len(layer),'unique_grid_ids':layer.grid_id.nunique(),'field_names_unique_case_insensitive':True})
record['status']='PASS' if run.returncode==0 and before==after else 'FAIL'
record['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(WORK/'repair_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(record,ensure_ascii=False))
sys.exit(0 if record['status']=='PASS' else 1)
