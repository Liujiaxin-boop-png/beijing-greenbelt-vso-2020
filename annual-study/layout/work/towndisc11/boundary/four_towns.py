from pathlib import Path
import geopandas as gp,shapely as sh,pandas as pd,numpy as np
w=Path(__file__).resolve().parent
src=Path('D:/ER219_project')
gk=w/'二道绿隔边界精确叠置.gpkg'
U=gp.read_file(gk,layer='user_boundary')
R=gp.read_file(gk,layer='reconstructed').geometry[0]
crs=U.crs;U=U.geometry[0]
O=U.union(R)
g=pd.read_csv(w/'边界对照逐格面积与已有年度得分.csv')
shapes=sh.box(g.ix*500,g.iy*500,(g.ix+1)*500,(g.iy+1)*500)
c2015=g['2015'].to_numpy();c2025=g['2025'].to_numpy()
delta=c2025-c2015
v=np.isfinite(delta)
source=gp.read_file(src/'GIS数据/GIS数据/0219/北京全域.shp',encoding='GB18030').to_crs(crs)
source['town']=source.Name.str.replace('地区办事处','地区',regex=False)
source.geometry=source.geometry.make_valid()
info=pd.read_csv(w/'同基准镇界内的叠置面积.csv').set_index('town')
rows=[]
for nm in ('东小口地区','阳坊镇','长辛店镇','李桥镇'):
    i=source.index[source.town==nm][0]
    town=source.geometry[i].intersection(O)
    neigh=source[source.index!=i]
    ov=sh.union_all(neigh.geometry[neigh.intersects(town)].intersection(town).to_numpy())
    town=town.difference(ov)
    for label,geom,col in [('重建',R,'recon_km2'),('自有',U,'user_km2')]:
        cut=town.intersection(geom)
        ix=np.array([j for j in np.where(sh.intersects(shapes,cut))[0] if shapes[j].intersection(cut).area>1e-6],int)
        ar=sh.area(sh.intersection(shapes[ix],cut))/1e6
        assert abs(ar.sum()-info.loc[nm,col])<1e-6
        valid=v[ix]; a=ar[valid];d=delta[ix][valid]
        pdn=a[d<0].sum()/a.sum()*100;md=np.average(d,weights=a)
        t=('A 普遍下降' if md<0 else 'C 局部上升主导') if pdn>50 else ('D 局部下降主导' if md<0 else 'B 普遍上升')
        lo=a[d<0].sum()/ar.sum()*100;hi=(a[d<0].sum()+ar[~valid].sum())/ar.sum()*100
        rows.append({'town':nm,'boundary':label,'area_km2':ar.sum(),'missing_km2':ar[~valid].sum(),'missing_n':(~valid).sum(),'covered_pct':100*a.sum()/ar.sum(),'dy':md,'down_pct':pdn,'type_on_available':t,'lower_pct':lo,'upper_pct':hi,'flip_req_unscored_mean':-a.sum()*md/ar[~valid].sum() if (~valid).any() else None})
r=pd.DataFrame(rows)
r.to_csv(w/'四个案例两种边界已覆盖部分的类型.csv',index=False,encoding='utf-8-sig')
print(r.round(7).to_string(index=False))
