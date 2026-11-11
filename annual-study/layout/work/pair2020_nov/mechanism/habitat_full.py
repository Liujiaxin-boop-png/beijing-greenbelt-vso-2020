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

def main(project):
    link=project/'02_过程文件/annual_actual';r=project/'03_结果文件/年度评价_2015_2025'
    out=Path(__file__).resolve().parent; annual=out.parent/'annual';g=pd.read_csv(annual/'格网五项十年变化.csv')
    src=r/'格网与尺度/格网指标与综合分_500m_2015至2025.csv.gz'; orig=pd.read_csv(src,usecols=['year','grid_id','HQI'])
    target=np.column_stack([g[['grid_id']].merge(orig[orig.year==y],on='grid_id',validate='one_to_one').HQI for y in YEARS])
    cfile=annual/'核查摘要.json'; pars=json.loads(cfile.read_text(encoding='utf-8-sig'))
    scale=pars['weights']['HQI']/(pars['upper']['HQI']-pars['lower']['HQI'])
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
    catalogue_path=link/'towns/town_catalogue.csv'; pieces_path=link/'towns/pieces_full.csv'
    towns=pd.read_csv(catalogue_path,dtype={'town_id':str}).set_index('town_seq')
    full=pd.read_csv(pieces_path).merge(g.reset_index()[['index','ix','iy']],on=['ix','iy'],validate='many_to_one')
    for seq,piece in full.groupby('town_seq'):
        note(towns.loc[seq,'town_id'],towns.loc[seq,'display_name'],piece['index'].to_numpy(),piece.poly_area.to_numpy()/1e6)
    pd.DataFrame(rows).to_csv(out/'HQI_input_attribution.csv',encoding='utf-8-sig',index=False,float_format='%.12g')
    moves=pd.DataFrame(change_rows,columns=['index','from','to','phi_land'])
    totals=moves.groupby('index').phi_land.sum().reindex(range(len(g)),fill_value=0).to_numpy()
    trans_err=float(np.max(abs(totals-phi[:,0])));assert trans_err<2e-12
    parts=np.load(link/'towns/weights_full.npz')
    cover=np.load(link/'towns/pixel_codes_full.npz')
    # Precise 30 m transition area inside intersection of town and planning
    # boundary, unlike the modeled full-square contributions above.
    row_lookup=pd.Series(np.arange(len(g)),index=pd.MultiIndex.from_arrays([g.ix,g.iy]))
    fid=parts['fid'];area_px=parts['area_m2'];eligible=pd.MultiIndex.from_arrays([parts['ix'],parts['iy']]).isin(row_lookup.index)
    keep=eligible[fid];state0=cover['2015'].astype(int);state1=cover['2025'].astype(int)
    move_codes=(state0*10+state1)[keep];tse=parts['town'][fid[keep]].astype(int)
    actual=np.bincount(tse*100+move_codes,weights=area_px[keep]/1e6,minlength=100*len(towns)).reshape(len(towns),100)
    assert abs(actual.sum()-sum(g.area_km2))<0.0001
    transition_report=[]
    names={1:'耕地',2:'林地',3:'灌丛',4:'草地',5:'水体',7:'裸地',8:'不透水面',9:'湿地'}
    def describe(tid,name,subset,den,areas):
        part=moves.merge(subset,on='index',validate='many_to_one')
        part['weighted']=part.phi_land*part.area/den
        val=part.groupby(['from','to']).weighted.sum()
        for fr in names:
            for to in names:
                if fr==to:continue
                phi_v=val.get((fr,to),0.)
                a=areas[fr*10+to]
                if abs(phi_v)<1e-12 and a<1e-8:continue
                transition_report.append(dict(id=tid,name=name,from_code=fr,to_code=to,from_class=names[fr],to_class=names[to],
                     intersection_transition_area_km2=a,land_input_delta_HQI=phi_v,land_input_delta_ER=phi_v*scale))
    describe('all','全区固定样本',pd.DataFrame({'index':g.index,'area':g.area_km2}),g.area_km2.sum(),actual.sum(axis=0))
    for seq,v in full.groupby('town_seq'):
        a=v.poly_area/1e6
        describe(towns.loc[seq,'town_id'],towns.loc[seq,'display_name'],pd.DataFrame({'index':v['index'],'area':a}),a.sum(),actual[seq])
    tdf=pd.DataFrame(transition_report)
    tdf.to_csv(out/'HQI_land_transitions.csv',encoding='utf-8-sig',index=False,float_format='%.12g')
    reg=tdf[tdf.id=='all']
    assert abs(reg.land_input_delta_HQI.sum()-rows[0]['delta_HQI_land_class'])<1e-11
    measured=pars['contribution']['C_HQI']
    assert abs(measured-rows[0]['HQI_contribution_to_ER'])<1e-8
    provenance={'fixed_grid_count':len(g),'input_factor_order':FACTORS,'subsets':16,'orders':24,
        'diagnostic':'Within-model input attribution. Land class changes habitat suitability and class-specific sensitivities as a block. Built, crop and road are distance-decayed pressures, using endpoint inputs independently. Paired land class / threat counterfactuals are algebraic model tests.',
        'aggregations':'Whole 500 m squares integrate exact fractional 30 m pixels; regional and township summaries weighted by 500 m squares intersected with planning boundary / township boundary within planning area. Same eleven-year cohort used for all attribution.',
        'max_abs_error_native_pixel_vs_rebuilt':max_pixel_error,'max_abs_error_rebuilt_500m_HQI_vs_published':ident_error,
        'max_abs_grid_land_transition_partition_error':trans_err,'max_abs_grid_Shapley_closure_error':closure,'regional_abs_HQI_ER_contribution_error':abs(measured-rows[0]['HQI_contribution_to_ER']),
        'entropy_weight_over_HQI_range':scale,'threat_weights_built_crop_road':w.tolist(),'k':k,
        'source_files':{str(p):sha(p) for p in [*(p for v in files for p in v.values()),tfile,kfile,cfile,catalogue_path,pieces_path]}}
    (out/'HQI_input_audit.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    print(rows[0],flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--project',type=Path,required=True)
    main(parser.parse_args().project.resolve())
