"""Context-only source comparison on the common30m reporting pixel mask.
These areas are pixel-centre accounting, not exact polygon area estimates.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import rasterio
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'03_结果文件/context';OUT.mkdir(exist_ok=True)
with rasterio.open(ROOT/'02_过程文件/spatial/reporting_mask.tif') as ds:mask=ds.read(1)>0
values={};rows=[];labels={1:'耕地',2:'林地',3:'灌丛',4:'草地',5:'水体',7:'裸地',8:'不透水面',9:'湿地'}
for name,file in [('CLCD','clcd2020.tif'),('WorldCover','worldcover2020_common30m.tif')]:
    with rasterio.open(ROOT/'02_过程文件/spatial'/file) as ds:a=ds.read(1);assert ds.read_masks(1)[mask].all()
    v=a[mask];values[name]=v
    for code,label in labels.items():
        count=int((v==code).sum());rows.append({'product':name,'class_code':code,'landcover':label,'pixels':count,'pixel_center_area_km2':count*.0009,'fraction':count/len(v),'support':'common30m pixel centres inside scope union'})
pd.DataFrame(rows).to_csv(OUT/'landcover_composition.csv',index=False,encoding='utf-8-sig')
ct=pd.crosstab(pd.Series(values['CLCD'],name='CLCD_code'),pd.Series(values['WorldCover'],name='WorldCover_code'))
ct.to_csv(OUT/'landcover_cross_tab_pixels.csv',encoding='utf-8-sig')
info={'status':'COMPLETE','scope_pixels':int(mask.sum()),'pixel_centre_area_km2':float(mask.sum()*.0009),'label_disagreement_fraction':float(np.mean(values['CLCD']!=values['WorldCover'])),'accuracy_claim':False,'mapping':'WorldCover10m mode projected to common30m, class mapping frozen in prepare_spatial.py','role':'context and product agreement; not an additional resilience indicator'}
(OUT/'landcover_comparison.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf8');print(info)
