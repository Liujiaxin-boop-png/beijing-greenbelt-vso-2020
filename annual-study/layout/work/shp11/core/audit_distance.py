from pathlib import Path
import json
import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr
from build_candidates import OUT,ROOT,PUB,grid,xy
from compare_six import BASE,DIR,fit,paired_boot

def independent_edt_audit():
    rows=[]
    for which, year in [(k,y) for k in ['CLCD'] for y in range(2015,2026)]+[('WorldCover',2020)]:
        alt=which=='WorldCover';folder=ROOT/'alternative_model' if alt else ROOT
        with rasterio.open(folder/'years'/'model'/f'CLCD_{year}.tif') as ds:
            whole=ds.read(1);tr=ds.transform
        d=distance_transform_edt(~np.isin(whole,[2,3,4,5,9]),sampling=30)
        native=(folder/'distance.raw' if alt else ROOT/f'landscape/{year}/distance.raw')
        candidate=np.memmap(native,mode='r',dtype='<f4',shape=whole.shape)
        x,y=xy[500]
        c0=int((x.min()-250-tr.c)/30);c1=int(np.ceil((x.max()+250-tr.c)/30))
        r0=int((tr.f-y.max()-250)/30);r1=int(np.ceil((tr.f-y.min()+250)/30))
        margin=min(c0,r0,whole.shape[0]-r1,whole.shape[1]-c1)*30
        view=np.s_[r0:r1,c0:c1]
        err=float(np.max(np.abs(d[view]-candidate[view])))
        max_d=float(d[view].max())
        assert max_d<margin and err<.002
        rows.append(dict(dataset=which,year=year,region_rectangle_max_distance_m=max_d,min_margin_to_raster_edge_m=margin,max_difference_independent_edt_m=err))
    pd.DataFrame(rows).to_csv(OUT/'距蓝绿空间距离场_全期独立复算与边界核查.csv',index=False,encoding='utf-8-sig')

if __name__=='__main__':independent_edt_audit()
