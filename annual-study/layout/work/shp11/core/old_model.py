"""Rebuild the November 6 six-indicator protocol on the current 2020 reporting domain.

Reuses original native model rasters (not cropped to old reporting extent);
terrain/landcover canvas and all full square locations are checked.  Habitats
remain separate throughout. No ecological observations enter these functions.
"""
from pathlib import Path
import argparse
import json
import os
import sys
import hashlib
import numpy as np
import pandas as pd
import rasterio
import shapely
from pyproj import Transformer
from scipy.sparse import coo_matrix
from concurrent.futures import ThreadPoolExecutor

DIR=Path(__file__).resolve().parent
W=Path('D:/ER219_work')
R=Path('D:/ER219_results')
OLD=W/'spatial/clcd2020.tif'
CUR=W/'annual_actual/years/model/CLCD_2020.tif'
sys.path.insert(0,str(Path('D:/ER219_code/src')))
os.environ['ER219_FRAGSTATS_HOME']=str(W/'计算审计/FRAGSTATS4.2')
from agent_batch_clumpy import window_by_centres
from agent_fragstats_clumpy import run_ascii_grids
from agent_ntl_aggregate import source_polygons,valid_pair,aggregate_arrays
from evaluate_resilience import entropy

HAB={'forest_shrub':[2,3], 'grassland':[4], 'water_wetland':[5,9]}
METRICS=['HQ_H','NTL','CLUMPY','MCR','SSI','E_fraction']
DIRS=pd.Series([1,-1,1,-1,-1,1],index=METRICS)

def cells():
    c=pd.read_csv(DIR/'cells_500_0.csv')
    origin=json.loads((W/'spatial/native_config.json').read_text('utf8'))['origin_xy']
    assert np.allclose(np.asarray(origin)/500,np.rint(np.asarray(origin)/500),rtol=0,atol=1e-6)
    c['grid_id']='500_'+c.ix.astype(str)+'_'+c.iy.astype(str)
    geom=json.loads((W/'spatial/grid_identity.json').read_text('utf8'))['grids']
    lookup={}
    for row in geom:
        if row['scale_m']!=500:continue
        x,y,x1,y1=row['bounds']; ix,iy=round(x/500),round(y/500)
        assert max(abs(x-ix*500),abs(y-iy*500),abs(x1-(ix+1)*500),abs(y1-(iy+1)*500))<1e-5
        assert (ix,iy) not in lookup
        lookup[ix,iy]=row['grid_id']
    c['legacy_id']=[lookup.get((x,y)) for x,y in zip(c.ix,c.iy)]
    assert len(c)==4478 and c.grid_id.is_unique
    return c

def bounds(row):
    return (row.ix*500.,row.iy*500.,(row.ix+1)*500.,(row.iy+1)*500.)

def calc_clumpy():
    c=cells()
    legacy=pd.read_csv(R/'clumpy/clumpy_clcd_500.csv')
    shared=c[c.legacy_id.notna()].merge(legacy,left_on='legacy_id',right_on='Grid_ID',validate='one_to_many')
    shared=shared.rename(columns={'habitat_type':'habitat','status':'CLUMPY_status'})
    shared['habitat']=shared.habitat.replace({'grass':'grassland'})
    verify=c[c.legacy_id.notna()].iloc[::60].grid_id
    todo=c[c.legacy_id.isna() | c.grid_id.isin(verify)]
    with rasterio.open(OLD) as src:
        land=src.read(1); aff=src.transform
    land[land==3]=2;land[land==9]=5
    codes={2:'forest_shrub',4:'grassland',5:'water_wetland'}
    def batch(ib):
        sub=todo.iloc[ib:ib+128]
        grids={}
        for row in sub.itertuples():
            s,t,u,v=window_by_centres(bounds(row),aff,land.shape)
            grid=land[s:t,u:v]; assert np.all(np.isin(grid,[1,2,4,5,6,7,8]))
            grids[row.grid_id]=grid
        dest=DIR/'native_fragstats'/f'b{ib:04d}';receipt=dest/'run_receipt.json'
        if receipt.exists():
            results=json.loads(receipt.read_text('utf8'));assert not results['exit_code'] and len(results['inputs'])==len(grids)
        else:results=run_ascii_grids(grids,dest,cell_size=30,neighborhood=8,timeout=300)
        rows={(r['LID'].removesuffix('.asc'),int(r['TYPE'][4:])):r for r in results['rows']}
        out=[]
        for gid,grid in grids.items():
            for code,hab in codes.items():
                r=rows.get((gid,code));n=(grid==code).sum()
                v=np.nan
                if n==0:reason='ABSENT_FOCAL_HABITAT'
                else:
                    assert r and abs(float(r['CA'])-n*.09)<.000051
                    if r['CLUMPY']=='N/A':reason='ONLY_FOCAL_CLASS_FRAGSTATS_NA' if n==grid.size else 'SINGLE_FOCAL_PIXEL_FRAGSTATS_NA' if n==1 else 'FRAGSTATS_UNDEFINED'
                    else:v=float(r['CLUMPY']);reason='VALID'
                out.append((gid,hab,v,reason))
        return out
    with ThreadPoolExecutor(max_workers=3) as ex:
        batches=list(ex.map(batch,range(0,len(todo),128)))
    new=pd.DataFrame(sum(batches,[]),columns=['grid_id','habitat','CLUMPY','CLUMPY_status'])
    chk=shared[shared.grid_id.isin(verify)].merge(new,on=['grid_id','habitat'],validate='one_to_one')
    assert len(chk)==len(verify)*3
    assert np.allclose(chk.CLUMPY_x,chk.CLUMPY_y,atol=1e-9,equal_nan=True)
    assert (chk.CLUMPY_status_x==chk.CLUMPY_status_y).all()
    result=pd.concat([shared[new.columns],new[~new.grid_id.isin(verify)]],ignore_index=True)
    assert len(result)==len(c)*3
    result.to_csv(DIR/'full_clumpy.csv',index=False)
    print('FRAGSTATS complete, archived',len(shared)//3,'new',c.legacy_id.isna().sum(),'check',len(verify),flush=True)

def calc_ntl():
    c=cells()
    with rasterio.open(OLD) as f:crs=f.crs
    dir_=W/'aggregation/ntl_native'
    with rasterio.open(next(dir_.glob('*masked_native_window.tif'))) as a,rasterio.open(next(dir_.glob('*cvg_native_window.tif'))) as b:
        raw=a.read(1);cvg=b.read(1);valid=valid_pair(raw,cvg,a.read_masks(1)>0,b.read_masks(1)>0)
        rr,cc=np.indices(a.shape)
        pix=source_polygons(a.transform,Transformer.from_crs(4326,crs,always_xy=True),rr.ravel(),cc.ravel())
    box=shapely.box(c.ix*500,c.iy*500,(c.ix+1)*500,(c.iy+1)*500).values
    si,gi=shapely.STRtree(box).query(pix,predicate='intersects')
    areas=shapely.area(shapely.intersection(pix[si],box[gi]));sel=areas>0
    mat=coo_matrix((areas[sel],(gi[sel],si[sel])),shape=(len(c),len(pix))).tocsr()
    tbl=aggregate_arrays(mat,np.full(len(c),250000.),raw.astype(float).ravel(),cvg.ravel(),valid.ravel(),c.grid_id,500)
    tbl[['grid_id','NTL','ntl_valid_fraction']].to_csv(DIR/'full_ntl.csv',index=False)
    print('NTL valid',tbl.NTL.notna().sum(),flush=True)

def calc_raw():
    c=cells()
    with rasterio.open(OLD) as f,rasterio.open(CUR) as same:
        land=f.read(1);aff=f.transform;crs=f.crs
        assert f.transform==same.transform and f.crs==same.crs and np.array_equal(land,same.read(1))
    def load(path):
        with rasterio.open(path) as f:
            assert f.transform==aff and f.crs==crs and f.shape==land.shape
            return f.read(1),f.nodata
    hq,_=load(R/'hq/clcd_HQ2020.tif')
    distance,_=load(W/'distance/clcd_base_euclidean_m.tif')
    windows=[]
    for r in c.itertuples():
        x,y,xx,yy=bounds(r)
        u,v=np.floor([(x-aff.c)/30,(aff.f-yy)/30]).astype(int)
        u1,v1=np.ceil([(xx-aff.c)/30,(aff.f-y)/30]).astype(int)
        xs=aff.c+np.arange(u,u1)*30; ys=aff.f-np.arange(v,v1)*30
        wx=np.minimum(xs+30,xx)-np.maximum(xs,x);wy=np.minimum(ys,yy)-np.maximum(ys-30,y)
        w=np.maximum(0,wy[:,None])*np.maximum(0,wx)
        assert abs(w.sum()-250000)<.01
        windows.append(((slice(v,v1),slice(u,u1)),w))
    out=[]
    for hab,codes in HAB.items():
        source=W/'mcr_native'/f'clcd_{hab}_core10_land_road'
        costs,nd=load(source/'mcr_patch_min_cost.tif')
        dst,_=load(source/'mcr_patch_destination_parent.tif')
        parent,_=load(W/'mcr_inputs'/('clcd_'+hab)/'parent_id.tif')
        assert np.all((parent>0)==np.isin(land,codes))
        for r,(sl,w) in zip(c.itertuples(),windows):
            l=land[sl];focal=parent[sl]>0; ar=w[focal].sum();C=w[l==8].sum();E=w[np.isin(l,[2,3,4,5,9])].sum()
            h=(hq[sl][focal]*w[focal]).sum()/ar if ar>0 else np.nan
            ok=focal&np.isfinite(costs[sl])&(costs[sl]!=nd)&(dst[sl]>0)
            valid=w[ok].sum(); m=(w[ok]*costs[sl][ok]).sum()/ar if ar>0 and np.isclose(valid,ar,atol=1e-5,rtol=1e-10) else np.nan
            s=(distance[sl][l==8]*w[l==8]).sum()/C if C>0 else np.nan
            e=E/(E+C) if C>0 else np.nan
            out.append((r.grid_id,hab,h,m,s,e,C,E,ar,valid))
        del costs,dst,parent
    pd.DataFrame(out,columns=['grid_id','habitat','HQ_H','MCR','SSI','E_fraction','construction_m2','ecological_m2','habitat_m2','MCR_valid_m2']).to_csv(DIR/'full_other_raw.csv',index=False)

def assemble():
    c=cells()
    f=c.merge(pd.read_csv(DIR/'full_other_raw.csv'),on='grid_id',validate='one_to_many')
    f=f.merge(pd.read_csv(DIR/'full_ntl.csv'),on='grid_id',validate='many_to_one').merge(pd.read_csv(DIR/'full_clumpy.csv'),on=['grid_id','habitat'],validate='one_to_one')
    assert len(f)==4478*3 and not f.duplicated(['grid_id','habitat']).any()
    hist=pd.read_csv(W/'pair2020_nov/old/old_scores.csv');common=f.merge(hist,on=['grid_id','habitat'])
    for key in METRICS:assert np.allclose(common[key+'_x'],common[key+'_y'],rtol=1e-8,atol=1e-6,equal_nan=True),key
    f.to_csv(DIR/'old_scores.csv',index=False,encoding='utf-8-sig')
if __name__=='__main__':
    op=sys.argv[1]; {'clumpy':calc_clumpy,'ntl':calc_ntl,'raw':calc_raw,'assemble':assemble}[op]()
