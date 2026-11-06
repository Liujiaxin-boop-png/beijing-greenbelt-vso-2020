"""Area-weighted reporting and fixed-class scenario comparisons."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'03_结果文件/evaluation';IND=ROOT/'03_结果文件/indicators'

def wstats(g,col):
    good=g[col].notna()&(g.intersect_m2>0);x=g.loc[good,col].to_numpy();w=g.loc[good,'intersect_m2'].to_numpy()
    if not len(x):return [np.nan,np.nan,0.]
    mean=float(np.average(x,weights=w));std=float(np.sqrt(np.average((x-mean)**2,weights=w)))
    return [mean,std,float(w.sum())]

def main():
    raw=pd.read_csv(IND/'six_indicator_records.csv')
    scored=pd.read_csv(OUT/'scores_all_scenarios.csv')
    cls=json.loads((OUT/'classification.json').read_text(encoding='utf8'))['habitats']
    scored['ER_class']=pd.Series(pd.NA,index=scored.index,dtype='Int64')
    for habitat,info in cls.items():
        m=scored.habitat==habitat
        uppers=np.array([x['upper'] for x in info['classes']])
        values=scored.loc[m,'ER'].to_numpy()
        scored.loc[m,'ER_class']=np.minimum(4,np.searchsorted(uppers,values,side='left'))+1
    scored.to_csv(OUT/'scores_classified.csv',index=False,encoding='utf-8-sig')
    baseline=scored[scored.scenario=='baseline'].copy()
    weights=pd.read_csv(IND/'town_grid_weights_1000.csv').rename(columns={'Grid_ID':'grid_id','Name':'town'})
    town_area=weights.groupby('town').intersect_m2.sum()
    merged=weights.merge(baseline,on='grid_id',how='inner',validate='many_to_many')
    townrows=[]
    for (town,habitat),g in merged.groupby(['town','habitat']):
        mean,std,valid=wstats(g,'ER')
        r={'town':town,'habitat':habitat,'grid_n':g.grid_id.nunique(),'covered_town_area_m2':town_area[town],'six_valid_area_m2':valid,'six_valid_fraction':valid/town_area[town],'ER_mean':mean,'ER_within_town_sd':std,'lowest_class_area_m2':float(g.loc[g.ER_class==1,'intersect_m2'].sum())}
        for c in ['V','S','O']:r[c+'_mean']=wstats(g,c+'_score')[0]
        townrows.append(r)
    town=pd.DataFrame(townrows)
    # Ensure zero-valid town-habitat combinations are represented, not dropped.
    allpairs=pd.MultiIndex.from_product([sorted(town_area.index),sorted(cls)],names=['town','habitat']).to_frame(index=False)
    town=allpairs.merge(town,on=['town','habitat'],how='left')
    town['covered_town_area_m2']=town.town.map(town_area)
    for c in ['grid_n','six_valid_area_m2','six_valid_fraction','lowest_class_area_m2']:town[c]=town[c].fillna(0)
    town.to_csv(OUT/'township_results.csv',index=False,encoding='utf-8-sig')
    region=[]
    for habitat,g in baseline.groupby('habitat'):
        w=g.scope_area_m2.to_numpy();mean=float(np.average(g.ER,weights=w));area=float(w.sum())
        region.append({'habitat':habitat,'valid_grid_n':len(g),'valid_scope_area_m2':area,'ER_area_weighted_mean':mean,'ER_area_weighted_sd':float(np.sqrt(np.average((g.ER-mean)**2,weights=w))),'ER_min':g.ER.min(),'ER_max':g.ER.max(),'lowest_class_area_m2':float(g.loc[g.ER_class==1,'scope_area_m2'].sum())})
    pd.DataFrame(region).to_csv(OUT/'regional_results.csv',index=False,encoding='utf-8-sig')
    changes=[];stability=[]
    primary=['worldcover','core35_land_road','core100_land_road','core10_land_only','crop_in_ecological_space','scale500_to1000_full_coverage']
    for habitat,b in baseline.groupby('habitat'):
        b=b.set_index('grid_id');seen={gid:[] for gid in b.index}
        for scenario,a in scored[(scored.habitat==habitat)&(scored.scale_m==1000)].groupby('scenario'):
            if scenario in ['baseline','scale500_to1000_partial_coverage']:continue
            if scenario.startswith('baseline_paired_'):continue
            reference=b;reference_name='baseline'
            if scenario.endswith('_reweighted'):
                underlying=scenario[:-len('_reweighted')]
                reference_name='baseline_paired_'+underlying+'_reweighted'
                reference=scored[(scored.habitat==habitat)&(scored.scenario==reference_name)].set_index('grid_id')
                assert len(reference)>0,'Reweighted class comparison needs its paired baseline'
            a=a.set_index('grid_id');common=reference.index.intersection(a.index)
            if not len(common):continue
            wb=reference.loc[common,'scope_area_m2'];cb=reference.loc[common,'ER_class'].astype(int);ca=a.loc[common,'ER_class'].astype(int)
            bothlow=(cb==1)&(ca==1);eitherlow=(cb==1)|(ca==1)
            changes.append({'habitat':habitat,'scenario':scenario,'reference_scenario':reference_name,'paired_n':len(common),'paired_area_m2':wb.sum(),'same_class_fraction_area':float(wb[cb==ca].sum()/wb.sum()),'lowest_class_Jaccard_area':float(wb[bothlow].sum()/wb[eitherlow].sum()) if wb[eitherlow].sum()>0 else np.nan,'limitation':'classification agreement on common valid area; no statement for excluded cells'})
            if scenario in primary:
                for gid in common:seen[gid].append((scenario,int(a.loc[gid,'ER_class'])))
        for gid,comparisons in seen.items():
            vals=[v for _,v in comparisons];classes=[int(b.loc[gid,'ER_class'])]+vals
            stability.append({'grid_id':gid,'habitat':habitat,'baseline_class':classes[0],'comparison_count':len(vals),'planned_comparison_count':len(primary),'complete_comparison_set':len(vals)==len(primary),'low_in_all_available_schemes':all(v==1 for v in classes) and len(vals)>0,'consistent_low_complete_set':len(vals)==len(primary) and all(v==1 for v in classes),'class_span':max(classes)-min(classes),'available_scenarios':';'.join(k for k,_ in comparisons)})
    pd.DataFrame(changes).to_csv(OUT/'class_agreement.csv',index=False,encoding='utf-8-sig')
    stable=pd.DataFrame(stability);stable.to_csv(OUT/'spatial_stability.csv',index=False,encoding='utf-8-sig')
    geom=gpd.read_file(IND/'grid_geometry.gpkg',layer='grid_1000')
    scope=gpd.read_file(ROOT/'02_过程文件/spatial/scope.gpkg',layer='study_scope').geometry.iloc[0]
    geom['geometry']=geom.geometry.intersection(scope)
    for habitat in cls:
        rr=raw[(raw.habitat==habitat)&(raw['product']=='clcd')&(raw.scale_m==1000)].copy()
        bs=baseline[baseline.habitat==habitat][['grid_id','ER','ER_class','V_score','S_score','O_score','limiting_dimension']]
        rr=rr.merge(bs,on='grid_id',how='left',validate='one_to_one').merge(stable[stable.habitat==habitat].drop(columns='habitat'),on='grid_id',how='left',validate='one_to_one')
        layer=geom.merge(rr,left_on='Grid_ID',right_on='grid_id',how='left',validate='one_to_one')
        # GeoPackage field names are case-insensitive. Preserve one canonical
        # field only after proving both merged copies contain identical data.
        assert layer['Grid_ID'].eq(layer['grid_id']).all(), 'Geometry and result grid IDs differ'
        assert layer['Scale_m'].eq(layer['scale_m']).all(), 'Geometry and result grid scales differ'
        layer=layer.drop(columns=['Grid_ID','Scale_m'])
        assert len({str(c).casefold() for c in layer.columns})==len(layer.columns), 'Case-insensitive duplicate GPKG fields remain'
        layer['map_class']=layer.ER_class.fillna(0).astype(int)
        # Explicit integer flags avoid driver-specific serialization of
        # nullable Python booleans as the strings "True"/"False" in QGIS.
        for flag in ['complete_comparison_set','consistent_low_complete_set','low_in_all_available_schemes']:
            layer[flag]=layer[flag].eq(True).astype('int16')
        layer.to_file(OUT/'evaluation_maps.gpkg',layer=habitat,driver='GPKG')
    (ROOT/'02_过程文件/evaluation/reporting_receipt.json').write_text(json.dumps({'status':'TABLES_AND_MAP_LAYERS_COMPLETE','town_rows':len(town),'town_area_policy':'original township intersections; overlaps not summed into regional total','regional_policy':'scope union with exact grid intersection weights','class_policy':'baselineJenks five classes frozen for all scenarios','stable_low_policy':'all six planned primary comparisons must be valid and low; incomplete comparisons flagged separately'},ensure_ascii=False,indent=2),encoding='utf8')
    print('REPORTING_COMPLETE')

if __name__=='__main__':main()
