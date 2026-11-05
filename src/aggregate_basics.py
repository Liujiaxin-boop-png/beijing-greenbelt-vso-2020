"""Exact fractional-cell aggregation of native HQ and gray-green measures.

Each metric uses the full square landscape context. Actual study/town
intersection areas are separate reporting weights, never fabricated land.
"""
from pathlib import Path
import json,math,time
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio

ROOT=Path(__file__).resolve().parents[2]
SP=ROOT/'02_过程文件/spatial';WORK=ROOT/'02_过程文件/aggregation';WORK.mkdir(exist_ok=True)
OUT=ROOT/'03_结果文件/indicators';OUT.mkdir(exist_ok=True)
GROUPS={'forest_shrub':[2,3],'grassland':[4],'water_wetland':[5,9]}

def window_area(array,aff,bounds):
    left,bottom,right,top=bounds
    c0=max(0,int(math.floor((left-aff.c)/aff.a)));c1=min(array.shape[1],int(math.ceil((right-aff.c)/aff.a)))
    r0=max(0,int(math.floor((aff.f-top)/(-aff.e))));r1=min(array.shape[0],int(math.ceil((aff.f-bottom)/(-aff.e))))
    xs=aff.c+np.arange(c0,c1)*aff.a;ys=aff.f+np.arange(r0,r1)*aff.e
    wx=np.maximum(0,np.minimum(xs+aff.a,right)-np.maximum(xs,left))
    wy=np.maximum(0,np.minimum(ys,top)-np.maximum(ys+aff.e,bottom))
    weights=wy[:,None]*wx[None,:]
    return array[r0:r1,c0:c1],weights,(slice(r0,r1),slice(c0,c1))

def main():
    scope=gpd.read_file(SP/'scope.gpkg',layer='study_scope').geometry.iloc[0]
    grids={};records=[];checks=[];masters=[]
    for scale in [1000,500]:
        grid=gpd.read_file(SP/'analysis.gdb',layer='grid_'+str(scale))
        grid['scope_area_m2']=grid.geometry.intersection(scope).area
        grid=grid[grid.scope_area_m2>0].copy().sort_values('Grid_ID')
        assert np.allclose(grid.geometry.area,scale**2,atol=.01)
        assert abs(float(grid.scope_area_m2.sum())-scope.area)<1.0
        grid['grid_area_m2']=float(scale**2)
        grids[scale]=grid
        for row in grid.itertuples():
            b=list(row.geometry.bounds)
            masters.append({'grid_id':row.Grid_ID,'scale_m':scale,'bounds':b,'grid_area_m2':float(scale**2),'scope_area_m2':float(row.scope_area_m2)})
        grid[['Grid_ID','Scale_m','scope_area_m2','grid_area_m2','geometry']].to_file(OUT/'grid_geometry.gpkg',layer='grid_'+str(scale),driver='GPKG')
        pieces=gpd.read_file(SP/'analysis.gdb',layer='town_grid_'+str(scale))
        pieces['intersect_m2']=pieces.geometry.area
        pieces[['Grid_ID','Name','intersect_m2']].to_csv(OUT/('town_grid_weights_'+str(scale)+'.csv'),index=False,encoding='utf-8-sig')
    (SP/'grid_identity.json').write_text(json.dumps({'grids':masters,'source':'native ArcGIS CreateFishnet','support':'full square; actual intersections are reporting weights'},ensure_ascii=False,indent=2),encoding='utf8')
    for product,filename in [('clcd','clcd2020.tif'),('wc','worldcover2020_common30m.tif')]:
        with rasterio.open(SP/filename) as s:land=s.read(1);aff=s.transform;crs=s.crs
        with rasterio.open(ROOT/'03_结果文件/hq'/(product+'_HQ2020.tif')) as s:
            hq=s.read(1);assert s.shape==land.shape and s.transform==aff and s.crs==crs
        distances={}
        for ecology in ['base','crop_included']:
            with rasterio.open(ROOT/'02_过程文件/distance'/(product+'_'+ecology+'_euclidean_m.tif')) as s:
                assert s.shape==land.shape and s.transform==aff and s.crs==crs
                distances[ecology]=s.read(1)
        for scale,grid in grids.items():
            for row in grid.itertuples():
                local,weights,slices=window_area(land,aff,row.geometry.bounds)
                assert abs(float(weights.sum())-scale**2)<.01
                assert np.all(local>0)
                C=float(weights[local==8].sum())
                E=float(weights[np.isin(local,[2,3,4,5,9])].sum())
                crop=float(weights[local==1].sum())
                qq=hq[slices]
                SSI=float(np.sum(distances['base'][slices][local==8]*weights[local==8])/C) if C>0 else np.nan
                SSI_crop=float(np.sum(distances['crop_included'][slices][local==8]*weights[local==8])/C) if C>0 else np.nan
                if C>0:assert SSI_crop<=SSI+1e-5
                for group,codes in GROUPS.items():
                    focal=np.isin(local,codes);area=float(weights[focal].sum())
                    HQ=float(np.sum(qq[focal]*weights[focal])/area) if area>0 else np.nan
                    rec={'grid_id':row.Grid_ID,'scale_m':scale,'product':product,'habitat':group,
                         'grid_area_m2':scale**2,'scope_area_m2':float(row.scope_area_m2),
                         'habitat_m2':area,'construction_m2':C,'ecological_m2':E,'cropland_m2':crop,
                         'HQ_H':HQ,'SSI':SSI,'E_fraction':E/(E+C) if C>0 else np.nan,
                         'SSI_crop_included':SSI_crop,'E_fraction_crop_included':(E+crop)/(E+crop+C) if C>0 else np.nan,
                         'has_habitat':area>0,'has_construction':C>0}
                    records.append(rec)
            print('AGGREGATED '+product+' '+str(scale),flush=True)
    df=pd.DataFrame(records)
    df.to_csv(OUT/'hq_graygreen_by_grid.csv',index=False,encoding='utf-8-sig')
    summary=df.groupby(['product','scale_m','habitat']).agg(records=('grid_id','count'),habitat_present=('has_habitat','sum'),construction_present=('has_construction','sum')).reset_index()
    summary.to_csv(OUT/'base_support_counts.csv',index=False,encoding='utf-8-sig')
    (WORK/'basic_aggregation_receipt.json').write_text(json.dumps({'status':'HQ_SSI_AREA_AGGREGATED','records':len(df),
        'grids_by_scale':{str(k):len(v) for k,v in grids.items()},'regional_area_km2':scope.area/1e6,
        'area_partition_verified':True,'crop_inclusion_distance_monotonic_verified':True,
        'missing_policy':'No focal habitat or no construction remains not applicable; no imputation',
        'support':'Full native square; exact fractional30m pixel-square intersections; town/study reporting weights stored separately',
        'remaining_metrics':['NTL','CLUMPY join','MCR']},ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':main()
