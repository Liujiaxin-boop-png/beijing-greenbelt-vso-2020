"""Attribute the 2015–2025 change in the InVEST habitat quality input to the ER score.

All 16 endpoint input combinations are evaluated at 30 m. Per-input marginal
changes use exact four-player Shapley weights; no regression or causal claim.
Requires grid.csv produced by decompose_change.py for its fixed 11-year cohort.
"""
from pathlib import Path
import argparse
from contextlib import ExitStack
from collections import defaultdict
import math
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
import json
import hashlib

YEARS=(2015,2025)
FACTORS=['land_class','built_field','crop_field','road_field']
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def average_grids(raster, tr, x, y):
    # The exact integral on a rectangle is a bilinear interpolation of cumulative
    # area at pixel vertices, evaluated at the four corners of the full square.
    r=np.pad(raster.cumsum(0,dtype='float64').cumsum(1,dtype='float64'),((1,0),(1,0)))
    def integral(col,row):
        i=np.floor(col).astype(int);j=np.floor(row).astype(int)
        w=col-i;v=row-j
        return (1-v)*((1-w)*r[j,i]+w*r[j,i+1])+v*((1-w)*r[j+1,i]+w*r[j+1,i+1])
    x0=(x*500-tr.c)/30;x1=x0+500/30
    y0=(tr.f-(y+1)*500)/30;y1=y0+500/30
    return (integral(x1,y1)-integral(x0,y1)-integral(x1,y0)+integral(x0,y0))*(30/500)**2

def main():
    link=Path('D:/ER219_work/annual_actual')
    out=Path(__file__).resolve().parent
    g=pd.read_csv(out/'六项格网十年变化.csv')
    orig=pd.read_csv(out/'六项逐格逐年原值与得分.csv.gz',usecols=['year','grid_id','HQI'])
    target=np.column_stack([g[['grid_id']].merge(orig[orig.year==y],on='grid_id',validate='one_to_one').HQI for y in YEARS])
    cfile=out/'parameters.json';pars=json.loads(cfile.read_text('utf8'))
    scale=pars['weights']['HQI']/(pars['max']['HQI']-pars['min']['HQI'])
    tfile=link/'hq/sensitivity_3threat.csv'; table=pd.read_csv(tfile).set_index('lucode');lut=np.zeros((256,4))
    for code,rec in table.iterrows():lut[code]=rec[['habitat','built','crop','road']].values
    kfile=link/'hq/full_scope_frozen_k.json'; k=json.loads(kfile.read_text())['k'];kpot=k**2.5
    w=np.array([1,.7,1])/2.7
    files=[{'land_class':link/'years/model'/f'CLCD_{yr}.tif',
          **{f'{n}_field':link/'hq/native'/str(yr)/'intermediate'/f'filtered_linear_{n}_c.tif' for n in ['built','crop','road']},
          'native_HQI':link/'hq/results'/f'HQI_{yr}.tif'} for yr in YEARS]
    q=np.zeros((len(g),16));max_pixel_error=0.;ixt=g.ix.to_numpy();iyt=g.iy.to_numpy()
    change_rows=[]
    with ExitStack() as stack:
        inputs=[{k:stack.enter_context(rasterio.open(p)) for k,p in yrs.items()} for yrs in files]
        plan=inputs[0]['land_class'];tr=plan.transform
        assert all(ds.crs==plan.crs and ds.transform.almost_equals(tr) and ds.shape==plan.shape for yr in inputs for ds in yr.values())
        for _, subset in g.groupby([g.ix//9,g.iy//9]):
            ids=subset.index.to_numpy();x=ixt[ids];y=iyt[ids]
            cl=math.floor((x.min()*500-tr.c)/30)-1;cr=math.ceil(((x.max()+1)*500-tr.c)/30)+1
            rt=math.floor((tr.f-(y.max()+1)*500)/30)-1;rb=math.ceil((tr.f-y.min()*500)/30)+1
            win=Window(cl,rt,cr-cl,rb-rt);wt=plan.window_transform(win)
            h=[];fields=[];quality=[];lc=[]
            for yrs in inputs:
                land=yrs['land_class'].read(1,window=win)
                assert np.isin(np.unique(land),table.index).all()
                lc.append(land);h.append(lut[land]);fields.append([yrs[f].read(1,window=win).astype(float) for f in FACTORS[1:]])
                quality.append(yrs['native_HQI'].read(1,window=win))
            land_phi=np.zeros_like(quality[0],dtype=float)
            for bits in range(16):
                i=bits&1
                D=sum(w[j]*h[i][:,:,j+1]*fields[(bits>>(j+1))&1][j] for j in range(3))
                raster=h[i][:,:,0]*kpot/(D**2.5+kpot)
                other_count=(bits>>1).bit_count()
                marginal_weight=math.factorial(other_count)*math.factorial(3-other_count)/24
                land_phi+=(1 if i else -1)*marginal_weight*raster
                if bits in (0,15):
                    max_pixel_error=max(max_pixel_error,float(np.max(abs(raster-quality[int(bits==15)]))))
                q[ids,bits]=average_grids(raster,wt,x,y)
            # The qualifying full square may extend beyond the planning boundary.
            # Each transition contribution therefore inherits the clipped area's weight after grid averaging.
            codes=lc[0].astype('int16')*10+lc[1]
            for code in np.unique(codes):
                frm,to=divmod(int(code),10)
                if frm==to:continue
                mask=codes==code
                quality_term=average_grids(land_phi*mask,wt,x,y)
                for idx,value in zip(ids,quality_term):
                    if abs(value)>1e-13:change_rows.append((int(idx),frm,to,value))
    ident_error=float(np.max(np.abs(q[:,[0,15]]-target)));assert max_pixel_error<1e-6 and ident_error<1e-7,(max_pixel_error,ident_error)
    phi=np.zeros((len(g),4))
    for j in range(4):
        for bits in range(16):
            if bits&(1<<j):continue
            m=bits.bit_count()
            phi[:,j]+=(q[:,bits|(1<<j)]-q[:,bits])*math.factorial(m)*math.factorial(3-m)/24
    closure=float(max(abs(phi.sum(axis=1)-(q[:,15]-q[:,0]))));assert closure<1e-13
    cell=g[['ix','iy','grid_id','area_km2']].copy();cell['HQI_2015']=q[:,0];cell['HQI_2025']=q[:,15]
    for j,n in enumerate(FACTORS):cell['delta_HQI_'+n]=phi[:,j];cell['delta_ER_'+n]=phi[:,j]*scale
    cell.to_csv(out/'HQI_inputs_grid.csv',encoding='utf-8-sig',index=False,float_format='%.12g')
    rows=[]
    def note(id_,name,ii,area):
        c=np.average(phi[ii],axis=0,weights=area)
        rows.append(dict(id=id_,name=name,n_grid=len(ii),area_km2=sum(area),
            delta_HQI=c.sum(),HQI_contribution_to_ER=c.sum()*scale,
            **{'delta_HQI_'+n:c[j] for j,n in enumerate(FACTORS)},**{'delta_ER_'+n:c[j]*scale for j,n in enumerate(FACTORS)}))
    note('all','全区固定样本',np.arange(len(g)),g.area_km2.to_numpy())
    pd.DataFrame(rows).to_csv(out/'HQI_input_attribution.csv',encoding='utf-8-sig',index=False,float_format='%.14g')
    moves=pd.DataFrame(change_rows,columns=['index','from','to','phi_land'])
    sums=moves.groupby('index').phi_land.sum().reindex(range(len(g)),fill_value=0).to_numpy()
    err=float(np.max(abs(sums-phi[:,0])));assert err<2e-12
    moves=moves.merge(g[['ix','iy','grid_id','area_km2']].reset_index(),on='index',validate='m:1')
    moves.to_csv(out/'HQI_transition_grids.csv.gz',index=False,encoding='utf-8-sig',float_format='%.14g')
    measured=np.average(g.delta_HQI,weights=g.area_km2)
    assert abs(measured-rows[0]['HQI_contribution_to_ER'])<1e-8
    audit={'n':len(g),'area_km2':g.area_km2.sum(),'fixed_k':k,'n_combinations':16,'n_permutations':24,'source_original_model_script':'D:/ER219_work/pair2020_nov/mechanism/habitat_full.py','sources':[str(p) for pack in files for p in pack.values()],'maximum_HQI_pixel_error':max_pixel_error,'maximum_grid_HQI_error':ident_error,'maximum_Shapley_closure_error':closure,'maximum_land_cover_type_partition_error':err,'HQI_total_ER_closure_error':abs(measured-rows[0]['HQI_contribution_to_ER'])}
    (out/'HQI_input_audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),'utf8')
    print(rows[0],flush=True)
if __name__=='__main__':main()
