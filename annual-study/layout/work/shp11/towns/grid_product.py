from pathlib import Path
import pandas as pd,numpy as np,geopandas as gp,shapely as sh,rasterio as rio,sys,json
w=Path(__file__).parent
src=Path('D:/ER219_work/annual_actual')
sys.path.insert(0,str(src/'analysis/geo'))
from exactextract import exact_extract
towns=gp.read_file(w/'planning_towns.gpkg',layer='towns')
un=gp.read_file(w/'planning_towns.gpkg',layer='unassigned')
t=pd.concat([towns,un],ignore_index=True)
assert np.array_equal(t.town_seq,np.arange(len(t)))
pieces=pd.read_csv(w/'pieces_full.csv').merge(t[['town_seq','town_id','display_name']],validate='m:1')
boxes=sh.box(500*pieces.ix,500*pieces.iy,500*(pieces.ix+1),500*(pieces.iy+1))
cuts=gp.GeoDataFrame(pieces,geometry=sh.intersection(boxes,t.geometry.values[pieces.town_seq]),crs=t.crs)
def polygonal(g):
    if g.geom_type in ('Polygon','MultiPolygon'):return g
    return sh.union_all([p for p in sh.get_parts(g) if p.geom_type in ('Polygon','MultiPolygon')])
cuts.geometry=cuts.geometry.map(polygonal)
layers={}
for y in (2015,2017,2025):
    for p in ('CLCD','Esri'):
        if p=='Esri' and y==2015: continue
        name=(src/f'years/model/CLCD_{y}.tif') if p=='CLCD' else (src/f'product_check/Esri_native_code_on30_{y}.tif')
        with rio.open(name) as ds:
            if not layers:
                cs=exact_extract(ds,cuts,['cell_id','coverage'],output='pandas')
                shape=ds.shape;tr=ds.transform
            assert ds.shape==shape and ds.transform==tr
            layers[p,y]=ds.read(1).ravel()
records=[];trans=[]
for i,rr in enumerate(cs.itertuples()):
    ww=np.asarray(rr.coverage,float)*.09;idx=np.asarray(rr.cell_id,int)
    row=pieces.iloc[i]
    assert abs(row.poly_area/1e4-ww.sum())<.001
    common=np.ones(len(idx),bool)
    for key,layer in layers.items():
        if key[1]!=2015:common&=np.isin(layer[idx], range(1,10) if key[0]=='CLCD' else [1,2,4,5,7,8,9,11])
    v={'town_seq':row.town_seq,'town_id':row.town_id,'display_name':row.display_name,'grid_id':row.grid_id,'area_ha':ww.sum(),'valid_ha':ww[common].sum()}
    for p in ('CLCD','Esri'):
        sel=8 if p=='CLCD' else 7
        a=layers[p,2017][idx][common]==sel;b=layers[p,2025][idx][common]==sel
        for key,arr in [('2017',a),('2025',b),('gain',~a & b),('loss',a&~b)]:
            v[f'{p}_{key}_ha']=ww[common][arr].sum()
    records.append(v)
    a=layers['CLCD',2015][idx].astype(int);b=layers['CLCD',2025][idx].astype(int)
    assert np.isin(a,range(1,10)).all() and np.isin(b,range(1,10)).all()
    mat=np.bincount(a*10+b,weights=ww,minlength=100)
    for k in np.flatnonzero(mat):
        trans.append((row.town_seq,row.grid_id,k//10,k%10,mat[k]))
r=pd.DataFrame(records)
summary_fields=[f for f in r.columns if f.endswith('_ha')]
def stats(df):
    f=df.copy()
    for p in ('CLCD','Esri'):
        f[p+'_delta_pp']=100*(f[p+'_gain_ha']-f[p+'_loss_ha'])/f.valid_ha
        f[p+'_delta_ha']=f[p+'_gain_ha']-f[p+'_loss_ha']
    f['valid_pct']=100*f.valid_ha/f.area_ha
    return f
def save(df,n):df.to_csv(w/n,index=False,encoding='utf-8-sig',float_format='%.12g')
save(stats(r),'镇街格网两产品共有效建设变化.csv.gz')
g=stats(r.groupby('grid_id',as_index=False)[summary_fields].sum())
save(g,'全区4478格两产品共有效建设变化.csv.gz')
f=stats(r[summary_fields].sum().to_frame().T);save(f,'全区两产品共有效建设变化.csv')
z=stats(r.groupby(['town_seq','town_id','display_name'],as_index=False)[summary_fields].sum())
d=pd.read_csv(w/'全镇街两套产品2017至2025建成林木水湿变化.csv')
for p in ('CLCD','Esri'):
    q=z.merge(d,on='town_seq',validate='1:1');q=q[q.valid_ha_x>.001]
    assert np.max(abs(q[p+'_delta_pp']-q[p+'_built_delta_pp']))<.0002
trn=pd.DataFrame(trans,columns=['town_seq','grid_id','from','to','ha'])
save(trn,'镇街格网CLCD2015至2025地类转移_公顷.csv.gz')
assert len(g)==4478 and np.allclose(trn.ha.sum(),r.area_ha.sum())
print(f.round(4).to_string(index=False))
print('opposite product directions',((g.CLCD_delta_pp*g.Esri_delta_pp)<-1e-10).sum())

