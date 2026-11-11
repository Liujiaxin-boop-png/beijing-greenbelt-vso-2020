"""Six-term controlled comparisons. All external outcomes are independent 2020 MODIS observations."""
from pathlib import Path
import json,sys,warnings
import numpy as np,pandas as pd,rasterio
from scipy.special import xlogy
from scipy.stats import spearmanr,rankdata
from build_candidates import OUT,ROOT,PUB,grid,WINDOWS,integral,integrate,xy
from concurrent.futures import ThreadPoolExecutor

BASE=['LDI','HQI','LBI','MCR','LRI']
CANDS=['SSI','RATIO_C','RATIO','PLAND','CPLAND','ALLDIST']+['SSI_W'+str(i) for i in WINDOWS]
DIR={k:(-1 if (k in ['LBI','MCR','ALLDIST'] or k.startswith('SSI')) else 1) for k in BASE+CANDS}
HABS=['forest_shrub','grassland']
unit=['ix','iy']; OLD=['HQ_H','NTL','CLUMPY','MCR','SSI','E_fraction']
def save(df,name):
    df.to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.11g')
def rho(a,b):
    ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()<4 or np.ptp(np.array(a)[ok])==0 or np.ptp(np.array(b)[ok])==0:return np.nan
    return spearmanr(np.array(a)[ok],np.array(b)[ok]).statistic
def avg(a,w):
    return np.average(a,weights=w)
def fit(sample,fields,sign=None):
    direction=np.array([DIR[k] for k in fields]) if sign is None else np.array(sign)
    low=sample[fields].min().values;high=sample[fields].max().values;d=high-low
    def transform(s):
        z=(s[fields].values-low)/np.where(d>0,d,1);z=np.where(direction==-1,1-z,z)
        return z
    z=transform(sample);p=z/np.where(z.sum(0)>0,z.sum(0),1)
    info=1+xlogy(p,p).sum(0)/np.log(len(p))
    info=np.where(d>0,info,0)
    w=info/info.sum()
    return lambda source:transform(source)@w, w
def alt():
    B=ROOT/'alternative_model';df=pd.read_csv(OUT/'WorldCover2020候选指标_500m.csv')
    u=df.ix.to_numpy();v=df.iy.to_numpy()
    f=B/'fields_500_0.bin'
    with f.open('rb') as fh:
        x0,y0,x1,y1=np.fromfile(fh,'<i4',4)
        raw=np.memmap(f,dtype='<f8',mode='r',offset=16,shape=(y1-y0,x1-x0,10))[v-y0,u-x0]
    df['LDI'],df['SSI'],df['LRI']=raw[:,0],raw[:,4],raw[:,5]
    par=json.loads((OUT/'parameters.json').read_text())
    lo=np.array(par['LBI_component_lo']);hi=np.array(par['LBI_component_hi'])
    df['LBI']=((raw[:,1:4]-lo)/(hi-lo))@np.array([.5,.3,.2])
    for k,src in [('HQI',B/'invest/quality_c.tif'),('MCR',B/'mcr/2020/MCR_2020.tif')]:
        with rasterio.open(src) as f: df[k]=integrate(integral(f.read(1)),f.transform,(u+.5)*500,(v+.5)*500,500)
    return df
def paired_boot(rows,values,ref=0,rep=1499):
    """Spearman with tied ranks, resampling spatial blocks together."""
    blockid=rows.ix.to_numpy()//10*100000+rows.iy.to_numpy()//10
    blocks,bix=np.unique(blockid,return_inverse=True)
    vals=np.column_stack([rows.ndvi]+[values[k] for k in values]);inv=[np.unique(col,return_inverse=True)[1] for col in vals.T]
    def corrs(w):
        center=.5*w.sum()
        dr=[]
        for group in inv:
            mass=np.bincount(group,weights=w,minlength=int(group.max())+1)
            dr.append((mass.cumsum()-.5*mass)[group]-center)
        vec=np.array(dr);scale=np.sqrt((vec**2)@w)
        with np.errstate(invalid='ignore',divide='ignore'):return ((vec[1:]*vec[0])@w)/(scale[1:]*scale[0])
    estimates=corrs(np.ones(len(rows)))
    assert np.allclose(estimates,[rho(rows.ndvi,values[k]) for k in values],atol=1e-9,equal_nan=True)
    rng=np.random.default_rng(20261110);boot=np.stack([corrs(m[bix]) for m in rng.multinomial(len(blocks),np.full(len(blocks),1/len(blocks)),rep)])
    out=[]
    for i,key in enumerate(values):
        record=dict(candidate=key,n=len(rows),blocks=len(blocks),rho=estimates[i],delta_vs_reference=estimates[i]-estimates[ref])
        if len(blocks)>=6 and len(rows)>=10:
            a,b=np.nanquantile(boot[:,i]-boot[:,ref],[.025,.975]);record.update(delta_lo=a,delta_hi=b)
        out.append(record)
    return out
def main():
    base=pd.read_csv(OUT/'基准及SSI.csv.gz')
    more=pd.read_csv(OUT/'候选指标_500m.csv.gz')
    full=base.merge(more.drop(columns=['area_km2','ix','iy','product']),on=['year','grid_id'],validate='one_to_one')
    z=full[full.year==2020].sort_values(unit).reset_index(drop=True)
    q=alt().sort_values(unit).reset_index(drop=True)
    assert q.grid_id.equals(z.grid_id)
    d=full[full.year==2025].set_index('grid_id')[BASE+CANDS]-full[full.year==2015].set_index('grid_id')[BASE+CANDS]
    cv=[];common=z[CANDS+BASE].notna().all(axis=1)&q[CANDS+BASE].notna().all(axis=1)
    annual=set(full.year)
    for k in CANDS:
        orig=z[k].notna()
        both=orig&q[k].notna()
        balance=full.groupby('grid_id')[k].count().eq(len(annual))
        area=z.loc[z.grid_id.map(balance),'area_km2'].sum()
        obs=z.loc[orig,k].values
        disp=lambda vec:np.quantile(vec,.75)-np.quantile(vec,.25)
        rel=z[k].where(common)
        r=dict(candidate=k,n_2020=int(orig.sum()),km2_2020=z.loc[orig,'area_km2'].sum(),n_complete_11=int(balance.sum()),km2_complete_11=area,n_product_common=int(both.sum()),product_common_km2=z.loc[both,'area_km2'].sum(),rho_product=rho(z[k],q[k]),rho_product_strict=rho(rel,q[k]),wmad=avg(abs(z.loc[both,k]-q.loc[both,k]),z.loc[both,'area_km2']),wmad_strict=avg(abs(z.loc[common,k]-q.loc[common,k]),z.loc[common,'area_km2']),iqr_2020=disp(obs),strict_common_n=int(common.sum()),mean_2020=avg(z.loc[orig,k],z.loc[orig,'area_km2']),double_zero_2020_frac=float(np.mean(abs(obs)<1e-9)))
        for b in BASE:
            r['rho_level_'+b]=rho(z[k],z[b]);r['rho_change_'+b]=rho(d[k],d[b])
        if k.startswith('SSI_W'):
            r['rho_vs_native_SSI']=rho(z[k],z.SSI)
        cv.append(r)
    C=pd.DataFrame(cv);save(C,'指标替换_覆盖冗余与底图.csv')
    ndvi=pd.read_csv(OUT/'ndvi500.csv',usecols=['ix','iy','ndvi','valid_fraction'])
    z=z.merge(ndvi,on=unit,validate='one_to_one')
    olds=pd.read_csv(OUT/'old_scores.csv',usecols=['ix','iy','habitat',*OLD])
    results=[];score_rows=[]
    for name in ['all_common']+HABS:
        g=z.copy()
        if name!='all_common':
            old=olds[olds.habitat==name].rename(columns={k:'old_'+k for k in OLD})
            g=g.merge(old.drop(columns='habitat'),on=unit,validate='one_to_one')
            g=g.dropna(subset=['old_'+k for k in OLD])
        g=g.dropna(subset=BASE+CANDS)
        score={}; fits={}
        if name!='all_common':
            f,w=fit(g,['old_'+n for n in OLD],[1,-1,1,-1,-1,1]);score['legacy_six']=f(g)
        for k in CANDS:
            f,w=fit(g,BASE+[k]);fits[k]=f;sc=f(g);score[k]=sc
            if name=='all_common':
                cl,wd=z.loc[common],q.loc[common]
                score_rows.append(dict(candidate=k,paired_n=len(cl),rho_score_product=rho(f(cl),f(wd)),wmad_score_product=avg(abs(f(cl)-f(wd)),cl.area_km2),focal_entropy_weight=w[-1]))
        for threshold in [.8]:
            keep=g.valid_fraction.ge(threshold)&g.ndvi.notna()
            sample=g.loc[keep]
            for r in paired_boot(sample,{k:a[keep.to_numpy()] for k,a in score.items()}):
                results.append(dict(sample=name,training_n=len(g),reliability=threshold,**r))
    save(pd.DataFrame(score_rows),'六项综合分换底图.csv')
    save(pd.DataFrame(results),'六项方案与2020独立植被绿度.csv')
    print(C[['candidate','n_complete_11','rho_product','rho_product_strict','rho_level_LRI','rho_change_LRI','rho_level_HQI','iqr_2020']].round(3).to_string(index=False))
    print(pd.DataFrame(results).query('reliability==.8')[['sample','candidate','n','blocks','rho','delta_vs_reference','delta_lo','delta_hi']].round(3).to_string(index=False))
if __name__=='__main__':main()
