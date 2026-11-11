from pathlib import Path
import hashlib,json,itertools
import sys
import geopandas as gp, shapely as sh,numpy as np,pandas as pd
from shapely.geometry import Polygon
src=Path('D:/ER219_project')
out=Path(__file__).resolve().parent
base=Path('D:/ER219_work/annual_actual/boundary')
G=gp.read_file(base/'beijing_greenbelt_full.gpkg',layer='planning_scope');crs=G.crs;R=G.geometry.union_all()
file=src/'GIS数据/GIS数据/二道绿隔范围.shp'
S=gp.read_file(file); sf=S.to_crs(crs)
def polys(g):
    if g.geom_type in ('MultiPolygon','Polygon'):return g
    return sh.union_all([p for p in sh.get_parts(g) if p.geom_type in ('MultiPolygon','Polygon')])
def validated(geom):
    return polys(sh.make_valid(geom))
def union(geom):
    return sh.union_all([validated(o) for o in geom])
U=union(sf.geometry)
I=U.intersection(R);RU=R.difference(U);UR=U.difference(R);O=R.union(U)
raw= {'user':U,'recon':R,'common':I,'user_only':UR,'recon_only':RU,'both_union':O}
assert abs((I.area+UR.area)-U.area)<.01
assert abs((I.area+RU.area)-R.area)<.01
km=lambda x:x.area/1e6
start={'native_crs':crs.to_proj4(),'user_crs':S.crs.to_string(),'features_user':len(S),'valid_per_feature':sf.is_valid.tolist(),'orig_attribute_area':S['面积'].tolist(),'source_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),**{k+'_km2':km(v) for k,v in raw.items()},'user_inside_recon_pct':100*I.area/U.area,'recon_inside_user_pct':100*I.area/R.area,'iou_pct':100*I.area/O.area,'user_minus_recon_net_km2':(U.area-R.area)/1e6,'symmetric_difference_km2':(UR.area+RU.area)/1e6}
cands=[]
for f in (src/'GIS数据').rglob('*.shp'):
    if f.stem in ('二道绿隔范围','绿隔范围'):
        fr=gp.read_file(f)
        pp=union(fr.to_crs(crs).geometry)
        cands.append({'path':str(f.relative_to(src)),'n':len(fr),'km2':km(pp),'symdiff_user_km2':pp.symmetric_difference(U).area/1e6,'shapefile_hash':hashlib.sha256(f.read_bytes()).hexdigest()})
pd.DataFrame(cands).to_csv(out/'自有边界副本比对.csv',encoding='utf-8-sig',index=False)
zones=gp.GeoDataFrame({'zone':['common','user_only','recon_only']},geometry=[I,UR,RU],crs=crs)
for layer,obj in [('parts',zones),('user_boundary',gp.GeoDataFrame({'name':['用户原始边界']},geometry=[U],crs=crs)),('reconstructed',G)]:obj.to_file(out/'二道绿隔边界精确叠置.gpkg',layer=layer,driver='GPKG')
meta=json.loads((base/'scope_reconstruction.json').read_text())
band=R.boundary.buffer(meta['uncertainty_margin_m'])
start['diff_in246_771m_boundary_band_pct']=100*((UR.area+RU.area)-(UR.difference(band).area+RU.difference(band).area))/(UR.area+RU.area)
start['beyond_band_user_only_km2']=km(UR.difference(band));start['beyond_band_recon_only_km2']=km(RU.difference(band))
(out/'统计.json').write_text(json.dumps(start,indent=2,ensure_ascii=False),'utf8')
srcad=src/'GIS数据/GIS数据/0219/北京全域.shp'
a=gp.read_file(srcad,encoding='GB18030').to_crs(crs)
a['town_id']=a.Code.str[3:12];a['district_id']=a.Code.str[3:9]
oldtown=gp.read_file(base/'planning_towns.gpkg',layer='towns')
db=oldtown.drop(columns='geometry').set_index('town_id')
a['geometry']=a.geometry.map(validated).intersection(O).map(polys)
a=a[a.area>.01].copy()
s=a.geometry.values;pair=sh.STRtree(s).query(s,predicate='intersects')
ij=[(i,j) for i,j in zip(*pair) if i<j]
ov=sh.union_all([polys(s[i].intersection(s[j])) for i,j in ij]);vac=O.difference(a.geometry.union_all());a.geometry=a.geometry.difference(ov).map(polys)
a['town']=a.Name.str.replace('地区办事处','地区',regex=False)
a['district']=a.district_id.map(oldtown.groupby('district_id').district.first())
zout=[]
for i,x in a.iterrows():
    g=x.geometry
    d={'town_id':x.town_id,'town':x.town,'district':x.district}
    for k,v in raw.items():d[k+'_km2']=g.intersection(v).area/1e6
    if x.town_id in db.index:assert abs(d['recon_km2']-db.loc[x.town_id,'area_km2'])<1e-6,(x.Name,d['recon_km2'],db.loc[x.town_id,'area_km2'])
    d['different_km2']=d['user_only_km2']+d['recon_only_km2'];d['net_km2']=d['user_km2']-d['recon_km2']
    zout.append(d)
ta=pd.DataFrame(zout).sort_values('different_km2',ascending=False)
ta.to_csv(out/'同基准镇界内的叠置面积.csv',index=False,encoding='utf-8-sig')
for name,g in [('多重归属',ov),('镇街底图空隙',vac)]:
    d={'town_id':'','town':name}
    for k,v in raw.items():d[k+'_km2']=g.intersection(v).area/1e6
    zout.append(d)
tot=pd.DataFrame(zout)
assert np.allclose([tot[k+'_km2'].sum() for k in raw],[km(x) for x in raw.values()],atol=1e-5)
tot.tail(2).to_csv(out/'镇界重叠与空隙.csv',index=False,encoding='utf-8-sig')
start['valid_towns_recon']=int((ta.recon_km2>1e-8).sum());start['valid_towns_user']=int((ta.user_km2>1e-8).sum())
start['different_towns_gt1km2']=int((ta.different_km2>1).sum());start['added_user_towns']=ta.loc[(ta.user_km2>1e-8)&(ta.recon_km2<=1e-8),'town'].tolist();start['removed_names']=ta.loc[(ta.recon_km2>1e-8)&(ta.user_km2<=1e-8),'town'].tolist()
(out/'统计.json').write_text(json.dumps(start,indent=2,ensure_ascii=False),'utf8')
print(json.dumps(start,ensure_ascii=False,indent=1))
print(ta.head(8)[['town','user_km2','recon_km2','common_km2','different_km2','net_km2']].round(3).to_string(index=False))
print(ta[ta.town.isin(['东小口地区','阳坊镇','李桥镇','长辛店镇'])][['town','user_km2','recon_km2','common_km2','different_km2','net_km2']].round(4).to_string(index=False))
