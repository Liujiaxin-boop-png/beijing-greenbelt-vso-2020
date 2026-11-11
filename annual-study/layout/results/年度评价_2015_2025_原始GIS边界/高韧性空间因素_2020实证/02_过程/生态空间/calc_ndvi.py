"""MOD13Q1 native footprints weighted over 500m full and clipped cells; conservative cloud/snow/water masks, common seasonal timing and sensitivity."""
from pathlib import Path
import sys,json,warnings,hashlib,time
import numpy as np,pandas as pd, geopandas as gp,shapely,rasterio
from rasterio.windows import Window,from_bounds
from scipy.sparse import coo_matrix
from pyproj import Transformer
here=Path(__file__).resolve().parent
mode=sys.argv[1] if len(sys.argv)>1 else 'season'
year=int(sys.argv[2]) if len(sys.argv)>2 else 2020
if mode=='summer':assert year==2020
raw=here.parents[1]/'01_原始数据'/f'MOD13Q1_{year}_生长季' if mode=='season' else Path('D:/ER219_raw/年度分析_2015_2025/MOD13Q1_2020_夏季独立观测')
outprefix=mode if year==2020 else f'{mode}_{year}'
g=gp.read_file(next(Path('D:/ER219_results/年度评价_2015_2025_原始GIS边界/计算结果与核验').rglob('annual_grid_500.gpkg')))
square=shapely.box(g.ix*500,g.iy*500,(g.ix+1)*500,(g.iy+1)*500)
def clipped_native(t):
    with rasterio.open(t) as f:return f.bounds[:],f.transform,f.crs
out=g.drop(columns='geometry').copy(); n=len(out)
qcs={}; accum={};areas={}; method={}
for tile in (['mosaic'] if (raw/'ORNL完整原生窗.txt').exists() else ['h26v04','h26v05']):
    items=sorted(p.name[:-len('_NDVI.tif')] for p in raw.glob('*'+tile+'*_NDVI.tif'))
    assert len(items)==(13 if mode=='season' else 5),(tile,len(items))
    metas=[clipped_native(raw/(it+'_NDVI.tif')) for it in items]; native=metas[0][2]
    bb=(min(z[0][0] for z in metas),min(z[0][1] for z in metas),max(z[0][2] for z in metas),max(z[0][3] for z in metas));w=from_bounds(*bb,metas[0][1]); aff=metas[0][1]*rasterio.Affine.translation(round(w.col_off),round(w.row_off));nr,nc=round(w.height),round(w.width)
    def read(k):
        with rasterio.open(raw/(it+'_'+k+'.tif')) as f:
            assert f.crs==native and abs(f.transform.a-aff.a)<1e-7
            wp=from_bounds(*bb,f.transform)
            win=Window(round(wp.col_off),round(wp.row_off),nc,nr)
            return f.read(1,window=win,boundless=True,fill_value=(65535 if k=='VIQ' else (255 if k=='QA' else -3000)))
    allv=[];goodm=[];strictm=[]
    days=np.array([int(it.split('.')[1][-3:]) for it in items])
    for it in items:
        v=read('NDVI').astype(float)*.0001;qa=read('QA');rng=(v>=-.2)&(v<=1.)
        if mode=='season':
            q=read('VIQ').astype(np.uint16);mod=q&3;use=(q>>2)&15;aero=(q>>6)&3
            env=(q!=65535)&(((q>>8)&1)==0)&(((q>>10)&1)==0)&(((q>>14)&1)==0)&(((q>>15)&1)==0)&(aero!=3)&(((q>>11)&7)==1)
            valid=env&rng&((qa==0)|((qa==1)&(mod<=1)&(use<=10)))
            strict=env&rng&(qa==0)
        else:valid=rng&(qa==0);strict=valid
        allv.append(v);goodm.append(valid);strictm.append(strict)
    v=np.stack(allv);good=np.stack(goodm);strict=np.stack(strictm)
    if mode=='season':
        sub=(days<=145,(days>=161)&(days<=241),days>=257)
        def summary(mask):
            en=mask.sum(0)>=6
            mean=np.zeros((nr,nc))
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',RuntimeWarning)
                for a in sub:
                    keep=mask[a];en &= keep.any(0)
                    m=np.nanmedian(np.where(keep,v[a],np.nan),axis=0)
                    mean+=a.sum()/len(days)*np.nan_to_num(m)
            return en,mean
        channels={'ndvi':summary(good),'strict_ndvi':summary(strict)}
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning);md=np.nanmedian(np.where(good,v,np.nan),axis=0)
        channels={'ndvi':(good.sum(0)>=3,md)}
    rr,cc=np.indices((nr,nc));X=aff.c+aff.a*cc.ravel();Y=aff.f+aff.e*rr.ravel();boxes=shapely.box(X,Y+aff.e,X+aff.a,Y)
    tr=Transformer.from_crs(native,g.crs,always_xy=True)
    poly=shapely.transform(shapely.segmentize(boxes,55),tr.transform,interleaved=False)
    tree=shapely.STRtree(poly)
    for tag,geo in [('full',square),('clip',g.geometry.to_numpy())]:
        i,j=tree.query(geo,predicate='intersects');ar=shapely.area(shapely.intersection(geo[i],poly[j]));mat=coo_matrix((ar,(i,j)),shape=(len(g),len(poly))).tocsr()
        areas[tag]=areas.get(tag,np.zeros(n))+np.asarray(mat.sum(axis=1)).ravel()
        for key,(valid,med) in channels.items():
            name=key+'_'+tag; wc=mat@valid.ravel().astype('f8');prod=mat@np.where(valid,med,0).ravel()
            if name not in accum: accum[name]=np.zeros((2,n))
            accum[name][0]+=wc;accum[name][1]+=prod
for tag in ['full','clip']:
    catalog_area=areas[tag];ref=np.full(n,250000.) if tag=='full' else g.area.to_numpy()
    out['catalog_coverage_'+tag]=np.minimum(1,catalog_area/ref)
    for key in (['ndvi','strict_ndvi'] if mode=='season' else ['ndvi']):
        name=key+'_'+tag; ar,sm=accum[name];out[name]=np.divide(sm,ar,out=np.full(n,np.nan),where=ar>1e-5);out[name+'_coverage']=np.clip(ar/ref,0,1)
    assert np.min(catalog_area/ref)>.998,(tag,np.min(catalog_area/ref)) if mode=='season' else True
out.to_csv(here/(outprefix+'_ndvi500.csv'),index=False,encoding='utf-8-sig',float_format='%.10g')
small=out[['grid_id','ndvi_full','ndvi_full_coverage']].rename(columns={'ndvi_full':'ndvi','ndvi_full_coverage':'coverage'}).copy()
small.loc[small.coverage<.8,'ndvi']=np.nan
small.to_csv(here/(('ndvi_main' if mode=='season' else 'ndvi_summer')+('' if year==2020 else f'_{year}')+'.csv'),index=False,encoding='utf-8-sig',float_format='%.10g')
meta={'product':'Terra MOD13Q1 v061, nominal 250 m, 16-day composites','doi':'https://doi.org/10.5067/MODIS/MOD13Q1.061','guide':'https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf','mode':mode,'days_2020':days.tolist(),'QA':('only native land pixels (land/water==1), no cloud-adjacency/mixed cloud/shadow/snow/high aerosols; summary QA good or marginal where MODLAND<=1 and VI usefulness<=10, raw NDVI in [-2000,10000]. Strict comparator also requires QA==0.' if mode=='season' else 'pixel reliability=0; valid 3 of 5 summer composites, median of available observations.'),'season_rule':('13 complete periods Apr06–Oct30; >=6 valid measurements, >=1 each in early/mid/late growing season (4/6/3 composites). Average of three sub-season medians weighted 4/13,6/13,3/13.' if mode=='season' else 'Jun09–Aug27 only'), 'geometry':'Densified native sinusoidal pixel footprint intersection with full 500m or clipped polygon; NDVI values divided by observed valid area, record full/clip valid coverage independently. NDVI interpret on land, not water.','fields':{}}
for col in out.filter(like='_coverage').columns:meta['fields'][col]={'min':float(out[col].min()),'mean':float(out[col].mean()),'n_ge80':int((out[col]>=.8).sum()),'n_ge50':int((out[col]>=.5).sum())}
meta['year']=year;meta['doy']=meta.pop('days_2020')
if mode=='season':meta['season_rule']='13 complete 16-day periods with start DOY 97..289 (April–October); >=6 valid measurements and >=1 each early/mid/late season; respective medians weighted by 4/13,6/13,3/13. For main CSV only, full-square area coverage must be >=80%.'
(here/(outprefix+'_ndvi_method.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
print(meta)
