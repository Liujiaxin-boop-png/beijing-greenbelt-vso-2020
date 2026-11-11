from pathlib import Path
import sys,json,itertools,math
import numpy as np,pandas as pd,rasterio as rio
OUT=Path(__file__).resolve().parent
A=Path('D:/ER219_work/annual_actual')
sys.path.insert(0,'D:/ER219_work/feng_round2/pilot')
from five_indices import get_window
pieces=pd.read_csv(OUT/'pieces_full.csv')
pieces['grid_id']='500_'+pieces.ix.astype(str)+'_'+pieces.iy.astype(str)
mix=pd.read_csv(OUT/'patch_grid_contributions.csv')
hs=pd.read_csv(A/'hq/sensitivity_3threat.csv').set_index('lucode')
lookup=np.zeros((11,4));lookup[hs.index]=hs[['habitat','built','crop','road']].values
k=json.loads((OUT.parent/'core/domain.json').read_text('utf8'))['new_hq_k'];weights=np.array([1,.7,1])/2.7
labels=['geometry_habitat','built_threat','crop_threat','road_threat']
result=[]; crossings=[]
case_towns=pd.read_csv(OUT/'四类入选镇街指标与增减地段强度.csv')
for code,t in zip(case_towns.base_type,case_towns.town_seq):
    g=pieces.loc[pieces.town_seq==t,['ix','iy','grid_id','poly_area']].copy()
    xy=g[['ix','iy']].to_numpy();x0,y0=xy.min(axis=0)*500;x1,y1=(xy.max(axis=0)+1)*500
    hh=[];sens=[];th=[];obs=[];classes=[]
    for y in [2015,2025]:
        with rio.open(A/'years/model'/f'CLCD_{y}.tif') as ds:
            win=rio.windows.from_bounds(x0-60,y0-60,x1+60,y1+60,transform=ds.transform).round_offsets().round_lengths()
            lc=ds.read(1,window=win);aff=ds.window_transform(win)
        classes.append(lc);hh.append(lookup[lc,0]);sens.append(lookup[lc,1:])
        fields=[]
        for key in ['built','crop','road']:
            with rio.open(A/'hq/native'/str(y)/'intermediate'/f'filtered_linear_{key}_c.tif') as ds:fields.append(ds.read(1,window=win))
        th.append(np.stack(fields,axis=-1))
        with rio.open(A/'hq/results'/f'HQI_{y}.tif') as ds:obs.append(ds.read(1,window=win))
    vals=[]
    for mask in range(16):
        yrs=[(mask>>j)&1 for j in range(4)]
        D=sum(weights[j]*sens[yrs[0]][:,:,j]*th[yrs[j+1]][:,:,j] for j in range(3))
        vals.append(hh[yrs[0]]*k**2.5/(D**2.5+k**2.5))
    att=[]
    for j in range(4):
        v=np.zeros_like(hh[0])
        for s in range(16):
            if s&(1<<j):continue
            m=s.bit_count()
            v+=(vals[s+(1<<j)]-vals[s])*math.factorial(m)*math.factorial(3-m)/24
        att.append(v)
    for rec in g.itertuples():
        x,y=rec.ix*500,rec.iy*500
        sl,ar,_=get_window([x,y,x+500,y+500],aff)
        vv=[(v[sl]*ar).sum()/ar.sum() for v in att + [vals[0],vals[15],*obs]]
        assert abs(sum(vv[:4])-(vv[5]-vv[4]))<1e-7 and max(abs(vv[4]-vv[6]),abs(vv[5]-vv[7]))<1e-6
        pairs=10*classes[0][sl]+classes[1][sl]
        for pair in np.unique(pairs):
            mask=pairs==pair
            contrib=np.sum(att[0][sl]*ar*mask)/ar.sum()
            area=np.sum(ar*mask)/ar.sum()
            crossings.append(dict(code=code,grid_id=rec.grid_id,pair=int(pair),model_class_term=contrib,area_share=area))
        result.append(dict(code=code,grid_id=rec.grid_id,**dict(zip(labels,vv[:4])),HQ_change=vv[5]-vv[4]))
trans=pd.DataFrame(crossings)
expanded=mix.merge(trans,on='grid_id',suffixes=('_patch','_town'))
expanded=expanded[expanded.code_patch.str[:1]==expanded.code_town]
expanded['contrib']=expanded.area_km2*expanded.model_class_term
expanded['area']=expanded.area_km2*expanded.area_share
v=expanded.groupby(['code_patch','pair'])[['contrib','area']].sum().reset_index()
v=v.merge(mix.groupby('code').area_km2.sum().rename('whole').to_frame(),left_on='code_patch',right_index=True)
v['mean_term']=v.contrib/v.whole
v.to_csv(OUT/'HQ_model_attribution_transition.csv',index=False)
for patch in ['B2','C1','C2','D1']:
    z=v[(v.code_patch==patch)&(v.pair//10!=v.pair%10)]
    print(patch,z.nsmallest(3,'mean_term')[['pair','mean_term']].values.tolist(),z.nlargest(3,'mean_term')[['pair','mean_term']].values.tolist())
grid=pd.DataFrame(result);grid.to_csv(OUT/'HQ_model_attribution_grid.csv',index=False)
tab=[]
for pid, sub in mix.groupby('code'):
    joined=sub.merge(grid[grid.code==pid[:1]].drop(columns='code'),on='grid_id',how='left',validate='many_to_one')
    assert joined['HQ_change'].notna().all()
    a=joined.area_km2
    v=np.average(joined[labels+['HQ_change']],weights=a,axis=0)
    tab.append(dict(patch=pid,**dict(zip(labels+['HQ_change'],v))))
patch=pd.DataFrame(tab);patch.to_csv(OUT/'HQ_model_attribution_patch.csv',index=False)
print(patch.to_string(index=False))
