from pathlib import Path
import sys,json,math
import rasterio as rio, pandas as pd, numpy as np, geopandas as gp
base=Path('D:/ER219_work/annual_actual')
out=Path(__file__).resolve().parent
sys.path.insert(0,str(base/'analysis/geo'))
from exactextract import exact_extract
p=gp.read_file(out/'case_hotspots.gpkg',layer='patches')
with rio.open(base/'years/model/CLCD_2015.tif') as ds:
    shape,tr,crs=ds.shape,ds.transform,ds.crs
    tab=exact_extract(ds,p,['cell_id','coverage'],include_cols=['code'],output='pandas')
samples={}
for rr in tab.itertuples():
    samples[rr.code]={'ids':np.array(rr.cell_id,int),'ha':np.array(rr.coverage,float)*0.09}
def read(code,file):
    with rio.open(file) as ds:
        assert (ds.shape,ds.transform,ds.crs)==(shape,tr,crs)
        arr=ds.read(1).ravel()
        for site,row in samples.items():
            row[code]=arr[row['ids']]
for y in [0,1]:
    year=(2015,2025)[y]
    read(('cl',y),base/f'years/model/CLCD_{year}.tif')
    read(('hq',y),base/f'hq/results/HQI_{year}.tif')
    read(('mcr',y),base/f'mcr/{year}/MCR_{year}.tif')
    for th in ['built','crop','road']:read((th,y),base/f'hq/native/{year}/intermediate/filtered_linear_{th}_c.tif')
kt=json.loads((out.parent/'core/domain.json').read_text('utf8'))['new_hq_k']
lookup=np.zeros((11,4))
for _,r in pd.read_csv(base/'hq/sensitivity_3threat.csv').iterrows():
    lookup[int(r.lucode)]=r[['habitat','built','crop','road']].values
fac=['local_classes','built','crop','road']
recs=[]
for sc,a in samples.items():
    ha=a['ha']
    vv={}
    for bits in range(16):
        cover=a['cl',bits&1]
        threat=sum(lookup[cover,j+1]*a[key,(bits>>(j+1))&1]*weight for j,(key,weight) in enumerate([('built',1/2.7),('crop',.7/2.7),('road',1/2.7)]))
        vv[bits]=lookup[cover,0]*kt**2.5/(threat**2.5+kt**2.5)
    assert max(np.max(np.abs(a['hq',0]-vv[0])),np.max(np.abs(a['hq',1]-vv[15])))<1e-6
    vals={}
    for j,lab in enumerate(fac):
        weight=0
        for bits in range(16):
            if ((bits>>j)&1): continue
            m=bits.bit_count()
            weight+=math.factorial(m)*math.factorial(3-m)/24*(vv[bits|1<<j]-vv[bits])
        vals[lab]=weight
    assert np.max(np.abs(sum(vals.values())-vv[15]+vv[0]))<1e-8
    veg0=np.isin(a['cl',0],[2,3,4]); veg1=np.isin(a['cl',1],[2,3,4])
    for group,domain in [('片区全部',np.full(len(ha),True)),('保留林灌草',veg0 & veg1),('转入林灌草',(~veg0)&veg1),('转出林灌草',veg0&(~veg1)),('余下地类',~(veg0|veg1))]:
        weight=ha[domain]
        if weight.sum()==0:continue
        r={'code':sc,'group':group,'ha':weight.sum()}
        for lab,v in vals.items():r[lab]=np.average(v[domain],weights=weight)
        for key in ['hq','mcr']:
            for y in [0,1]:r[key+str(y)]=np.average(a[key,y][domain],weights=weight)
            r[key+'_change']=r[key+'1']-r[key+'0']
        recs.append(r)
df=pd.DataFrame(recs)
df.to_csv(out/'八片区像元质量四因素与用地组分解.csv',encoding='utf-8-sig',index=False)
print(df[df.group.isin(['片区全部','转入林灌草','保留林灌草'])][['code','group','ha','local_classes','built','crop','road','hq_change','mcr_change']].round(5).to_string(index=False))
