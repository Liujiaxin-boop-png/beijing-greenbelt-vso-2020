"""Derive candidate organisation metrics on the same Beijing grid and 30m lattice."""
from pathlib import Path
import sys
import json
import warnings
import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import binary_erosion

ROOT=Path(r'D:/ER219_work/annual_actual')
OUT=Path(__file__).resolve().parent
PUB=Path(r'D:/ER219_results/年度评价_2015_2025')
SCALES=[500]
WINDOWS=[500,1000,2000,3000,5000]
grid={s:pd.read_csv(OUT/f'cells_{s}_0.csv') for s in SCALES}
for s,g in grid.items():
    g['grid_id']=['%d_%d_%d'%(s,x,y) for x,y in zip(g.ix,g.iy)]
    g['area_km2']=g['area']/1e6
xy={s:((g.ix.to_numpy()+.5)*s,(g.iy.to_numpy()+.5)*s) for s,g in grid.items()}
def integral(mask):
    pref=np.zeros((mask.shape[0]+1,mask.shape[1]+1),'float64')
    np.cumsum(mask,axis=0,dtype=np.float64,out=pref[1:,1:])
    np.cumsum(pref[1:,1:],axis=1,out=pref[1:,1:])
    return pref
def integrate(p,tr,x,y,w):
    def where(xx,yy):
        c=(xx-tr.c)/tr.a; r=(yy-tr.f)/tr.e
        i=c.astype('int64');j=r.astype('int64')
        assert (i>=0).all() and (j>=0).all() and i.max()+1<p.shape[1] and j.max()+1<p.shape[0]
        cx=c-i; cy=r-j
        return (1-cy)*((1-cx)*p[j,i]+cx*p[j,i+1])+cy*((1-cx)*p[j+1,i]+cx*p[j+1,i+1])
    return (where(x+w/2,y-w/2)-where(x-w/2,y-w/2)-where(x+w/2,y+w/2)+where(x-w/2,y+w/2))*(30/w)**2
def records(y,product):
    al=product=='WorldCover'
    ras=ROOT/('alternative_model/years/model/CLCD_2020.tif' if al else f'years/model/CLCD_{y}.tif')
    distpath=ROOT/('alternative_model/distance.raw' if al else f'landscape/{y}/distance.raw')
    with rasterio.open(ras) as ds:
        xx=np.concatenate([pair[0] for pair in xy.values()]); yy=np.concatenate([pair[1] for pair in xy.values()])
        ext=ds.window(xx.min()-2700,yy.min()-2700,xx.max()+2700,yy.max()+2700)
        w=rasterio.windows.Window(np.floor(ext.col_off),np.floor(ext.row_off),np.ceil(ext.width)+1,np.ceil(ext.height)+1)
        tr=ds.window_transform(w);land=ds.read(1,window=w)
        r0,c0=int(w.row_off),int(w.col_off);r1,c1=r0+land.shape[0],c0+land.shape[1]
        distance=np.memmap(distpath,mode='r',dtype='<f4',shape=ds.shape)[r0:r1,c0:c1]
        assert tr.a==30 and tr.e==-30
    green=np.isin(land,[2,3,4,5,9]);built=(land==8)
    assert np.all(distance[green]==0) and np.all(distance[~green]>0)
    core=binary_erosion(green,np.ones((3,3),bool),border_value=0)
    rec={s:grid[s][['ix','iy','grid_id','area_km2']].assign(year=y,product=product).copy() for s in SCALES}
    area={}
    for name,img in [('PLAND',green),('built',built),('CPLAND',core),('ALLDIST',distance),('built_dist',distance*built)]:
        pref=integral(img)
        for s,df in rec.items():
            x,y=xy[s]
            if name not in ['built_dist']:
                val=integrate(pref,tr,x,y,s)
                if name=='ALLDIST':
                    assert np.isfinite(val).all() and np.min(val)>=-1e-7
                    # Prefix-integral cancellation may leave sub-micrometre residuals in all-green cells.
                    df[name]=np.where(np.abs(val)<1e-7,0.,val)
                else:
                    df[name]=np.clip(val,0,1)
            if name=='built' or name=='built_dist':
                for width in WINDOWS:
                    val=integrate(pref,tr,x,y,width)
                    if name=='built':
                        area[s,width]=val
                    else:
                        a=area[s,width]
                        df[f'SSI_W{width}']=np.divide(val,a,out=np.full(a.shape,np.nan),where=a>1e-9)
        del pref
    for s,df in rec.items():
        total=df.PLAND+df.built
        df['RATIO']=np.divide(df.PLAND,total,out=np.full(len(df),np.nan),where=total>1e-9)
        df['RATIO_C']=df.RATIO.where(df.built>1e-9)
        assert df.CPLAND.le(df.PLAND+1e-8).all()
    return rec
if __name__=='__main__':
    allrec={s:[] for s in SCALES}
    for y in range(2015,2026):
        rec=records(y,'CLCD')
        for s in SCALES:allrec[s].append(rec[s])
        print('done',y,flush=True)
    for s,arr in allrec.items():
        v=pd.concat(arr);assert not v.duplicated(['grid_id','year']).any()
        v.to_csv(OUT/f'候选指标_{s}m.csv.gz',index=False,encoding='utf-8-sig',float_format='%.12g')
    alt=records(2020,'WorldCover')
    alt[500].to_csv(OUT/'WorldCover2020候选指标_500m.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
