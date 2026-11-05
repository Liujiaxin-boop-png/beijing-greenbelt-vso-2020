"""Join measured components without pretending a missing NTL is a score."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'03_结果文件/indicators'
KEY=['grid_id','scale_m','product','habitat']

def main():
    base=pd.read_csv(OUT/'hq_graygreen_by_grid.csv');assert not base.duplicated(KEY).any()
    cl=[]
    for product in ['clcd','wc']:
        for scale in [1000,500]:
            disk_product='worldcover' if product=='wc' else product
            f=pd.read_csv(ROOT/'03_结果文件/clumpy'/('clumpy_'+disk_product+'_'+str(scale)+'.csv'))
            f=f.rename(columns={'Grid_ID':'grid_id','habitat_type':'habitat','status':'CLUMPY_status'})
            f['habitat']=f['habitat'].replace({'grass':'grassland'})
            f['product']=product
            cl.append(f[KEY+['CLUMPY','CLUMPY_status','habitat_pixels','total_window_pixels']])
    clf=pd.concat(cl,ignore_index=True);assert not clf.duplicated(KEY).any()
    base=base.merge(clf,on=KEY,how='left',validate='one_to_one')
    assert base.CLUMPY_status.notna().all()
    mpath=OUT/'mcr_by_grid.csv'
    if mpath.exists():
        m=pd.read_csv(mpath)
        mainm=m[m.scenario.str.endswith('_core10_land_road')].copy()
        base=base.merge(mainm.drop(columns=['habitat_m2','scenario']),on=KEY,how='left',validate='one_to_one')
    ntlpath=OUT/'ntl_by_grid.csv'
    if ntlpath.exists():
        ntl=pd.read_csv(ntlpath);assert not ntl.duplicated(['grid_id','scale_m']).any()
        base=base.merge(ntl,on=['grid_id','scale_m'],how='left',validate='many_to_one')
    required=['HQ_H','NTL','CLUMPY','MCR','SSI','E_fraction']
    missing=[x for x in required if x not in base]
    for x in missing:base[x]=float('nan')
    finite=np.isfinite(base[required].to_numpy(dtype=float))
    base['six_valid']=finite.all(axis=1)
    base['invalid_or_missing_metrics']=[';'.join(np.array(required)[~row]) for row in finite]
    base.to_csv(OUT/'six_indicator_records.csv',index=False,encoding='utf-8-sig')
    counts=base.groupby(['product','scale_m','habitat']).agg(grid_count=('grid_id','size'),six_valid=('six_valid','sum')).reset_index()
    counts.to_csv(OUT/'six_indicator_coverage.csv',index=False,encoding='utf-8-sig')
    receipt={'status':'JOIN_COMPLETE_SCORES_NOT_RUN','records':len(base),'missing_entire_metrics':missing,'six_valid':int(base.six_valid.sum()),'no_imputation':True}
    (ROOT/'02_过程文件/aggregation/indicator_join_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8');print(receipt)

if __name__=='__main__':main()
