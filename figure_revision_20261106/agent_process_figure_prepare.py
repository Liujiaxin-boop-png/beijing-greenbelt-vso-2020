"""Join frozen real scores to existing clipped geometry for process figures only."""
from pathlib import Path
import datetime, hashlib, json
import numpy as np
import pandas as pd
import geopandas as gpd

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/figure_revision_20261106'
OUT=ROOT/'04_图件/统一图式与过程图_20261106'
SOURCE=ROOT/'03_结果文件/evaluation/scores_classified.csv'
GEOM=ROOT/'03_结果文件/evaluation/evaluation_maps.gpkg'
FIELDS=['HQ_H','NTL','CLUMPY','MCR','SSI','E_fraction','V_score','S_score','O_score']
HAB={'forest_shrub':840,'grassland':153,'water_wetland':532}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    WORK.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    frozen={str(p):sha(p) for p in [SOURCE,GEOM,ROOT/'05_代码/figure_revision_20261106/figure_style.json']}
    scores=pd.read_csv(SOURCE,low_memory=False)
    b=scores[(scores.scenario=='baseline')&(scores.scale_m==1000)&(scores['product']=='clcd')].copy()
    assert not b.duplicated(['habitat','grid_id']).any()
    geom=gpd.read_file(GEOM,layer='forest_shrub')[['grid_id','geometry']]
    assert len(geom)==2478 and geom.grid_id.is_unique and geom.geometry.is_valid.all()
    gpkg=WORK/'process_figure_sources.gpkg'
    if gpkg.exists():gpkg.unlink()
    rows=[];raw_specs=[]
    forest=b[b.habitat=='forest_shrub']
    specs=[('HQ_H','生境质量 HQ','指数','linear',float(forest.HQ_H.min()),float(forest.HQ_H.max())),
           ('NTL','夜间灯光 NTL','nW / (cm² · sr)','log10_1p',float(forest.NTL.min()),float(forest.NTL.max())),
           ('CLUMPY','聚集度 CLUMPY','指数','linear',-1.,1.),
           ('MCR','最小累积阻力 MCR','相对阻力 · m','log10_1p',float(forest.MCR.min()),float(forest.MCR.max())),
           ('SSI','源汇平均距离 SSI','m','linear',float(forest.SSI.min()),float(forest.SSI.max())),
           ('E_fraction','生态空间比例 E/(E+C)','比例','linear',0.,1.)]
    for field,title,unit,mode,lo,hi in specs:
        raw_specs.append({'field':field,'title':title,'unit':unit,'display_transform':mode,'display_min_raw':lo,'display_max_raw':hi,
                          'observed_min':float(forest[field].min()),'observed_max':float(forest[field].max()),
                          'observed_median':float(forest[field].median()),'color_field':'display_'+field,'direction':-1 if field in ['NTL','MCR','SSI'] else 1})
    for h,expected in HAB.items():
        sub=b[b.habitat==h][['grid_id']+FIELDS].copy();assert len(sub)==expected
        assert np.isfinite(sub[FIELDS].to_numpy()).all()
        g=geom.merge(sub,on='grid_id',how='left',validate='one_to_one')
        g['habitat']=h;g['baseline_valid']=g.HQ_H.notna().astype(int)
        for field in ['V_score','S_score','O_score']:
            assert sub[field].between(0,1).all();g['display_'+field]=g[field]
        if h=='forest_shrub':
            for sp in raw_specs:
                v=g[sp['field']];lo,hi=sp['display_min_raw'],sp['display_max_raw']
                if sp['display_transform']=='log10_1p':v=np.log10(1+v);lo,hi=np.log10(1+lo),np.log10(1+hi)
                g[sp['color_field']]=(v-lo)/(hi-lo)
                assert g.loc[g.baseline_valid==1,sp['color_field']].between(-1e-12,1+1e-12).all()
        g.to_file(gpkg,layer=h,driver='GPKG')
        reread=gpd.read_file(gpkg,layer=h)
        actual=reread[reread.baseline_valid==1].set_index('grid_id')
        ref=sub.set_index('grid_id')
        exact={f:bool(np.array_equal(actual.loc[ref.index,f].to_numpy(),ref[f].to_numpy())) for f in FIELDS}
        assert all(exact.values()) and len(actual)==expected
        rows.append({'habitat':h,'all_clipped_grid_n':len(g),'valid_grid_n':expected,'all_original_fields_exact':exact,
                     'display_field_definition':'Color-only fields, not added indicators or recalculated scores'})
    assert all(sha(Path(p))==d for p,d in frozen.items())
    report={'status':'PASS_PREPARED_FROM_FROZEN_RESULTS','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'input_sha256':frozen,'output_gpkg':str(gpkg),'output_sha256':sha(gpkg),'raw_specs':raw_specs,'layers':rows,
            'support':'Figure3: same840 forest/shrub baseline six-valid1km grids for all6 fields. Figure4: habitat-specific baseline domains840/153/532; full1km values rendered on existing study-clipped geometry.',
            'geometry_source':'Existing evaluation_maps.gpkg grid_id and geometry only; no clipping, resampling or model rerun',
            'CRS':geom.crs.to_wkt(),'scale_m':1000,'scenario':'baseline','product':'clcd',
            'missing_semantics':'Lightgray grids outside each baseline complete-six domain; not numerical zero and not low resilience.',
            'model_recomputed':False,'new_ecological_classes':False,'between_habitat_rank_claim':False}
    (WORK/'process_figures_data_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'valid_n':HAB,'sha256':report['output_sha256']},ensure_ascii=False))

if __name__=='__main__':main()
