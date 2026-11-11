from pathlib import Path
import hashlib,json
import geopandas as gp,shapely as sh,pandas as pd,numpy as np
base=Path(__file__).resolve().parent
root=Path(r'D:/ER219_project/GIS数据/GIS数据')
scopefile=root/'二道绿隔范围.shp';townfile=root/'0219/北京全域.shp'
crs=gp.read_file('D:/ER219_work/annual_actual/boundary/beijing_greenbelt_full.gpkg',rows=1).crs
def poly(g):
    if g.geom_type in ('Polygon','MultiPolygon'):return g
    return sh.union_all([c for c in sh.get_parts(g) if c.geom_type in ('Polygon','MultiPolygon')])
def validate(g):return poly(sh.make_valid(g))
U=gp.read_file(scopefile).to_crs(crs);scope=sh.union_all([validate(g) for g in U.geometry])
inner=scope.buffer(-250);assert inner.area>0
z=gp.read_file(townfile,encoding='GB18030').to_crs(crs)
z['town_id']=z.Code.str[3:12];z['district_id']=z.Code.str[3:9]
z['district']=z.district_id.map({'110101':'东城区','110102':'西城区','110105':'朝阳区','110106':'丰台区','110107':'石景山区','110108':'海淀区','110109':'门头沟区','110111':'房山区','110112':'通州区','110113':'顺义区','110114':'昌平区','110115':'大兴区','110116':'怀柔区','110117':'平谷区','110118':'密云区','110119':'延庆区'})
z['town_name']=z.Name;z['display_name']=z.Name.str.replace('地区办事处','地区',regex=False);z['source_code']=z.Code
z.geometry=z.geometry.map(validate).intersection(scope).map(poly);z=z[z.area>.01].copy()
matched=sh.STRtree(z.geometry.values).query(z.geometry.values,predicate='intersects')
area_dups=[]
for i,j in zip(*matched):
    if i>=j:continue
    ov=poly(z.geometry.iloc[i].intersection(z.geometry.iloc[j]))
    if ov.area>1e-5:area_dups.append(ov)
raw_union=z.geometry.union_all()
gap=scope.difference(raw_union);over=sh.union_all(area_dups)
z.geometry=z.geometry.difference(over).map(poly)
z=z[z.area>0.01].copy().sort_values(['district','town_id']).reset_index(drop=True)
z['town_seq']=np.arange(len(z));z['area_km2']=z.area/1e6; z['interior_km2']=z.geometry.intersection(inner).area/1e6
z=z[['town_seq','town_id','district_id','district','town_name','display_name','source_code','area_km2','interior_km2','geometry']]
assert len(z)==82 and abs(z.area.sum()+over.area+gap.area-scope.area)<.01
boundary=base/'planning_towns.gpkg'
z.to_file(boundary,layer='towns')
extra=gp.GeoDataFrame({'town_seq':range(len(z),len(z)+2),'town_id':['UN_M','UN_G'],'district':['未归属','未归属'],'display_name':['多重归属','底图空隙']},geometry=[over,gap],crs=crs)
extra['area_km2']=extra.area/1e6;extra['interior_km2']=extra.geometry.intersection(inner).area/1e6
extra.to_file(boundary,layer='unassigned')
gp.GeoDataFrame({'type':['user_scope','inner250']},geometry=[scope,inner],crs=crs).to_file(boundary,layer='scope')
types=['town_seq','town_id','district','display_name','area_km2','interior_km2','geometry']
territories=pd.concat([z[types],extra[types]],ignore_index=True)
territories.drop(columns='geometry').to_csv(base/'town_catalogue.csv',index=False,encoding='utf-8-sig')
def grid(geometry,d=500):
    xmin,ymin,xmax,ymax=geometry.bounds
    xx,yy=np.meshgrid(np.arange(int(np.floor(xmin/d)),int(np.ceil(xmax/d))),np.arange(int(np.floor(ymin/d)),int(np.ceil(ymax/d))))
    xx=xx.ravel(); yy=yy.ravel(); g=sh.box(xx*d,yy*d,(xx+1)*d,(yy+1)*d)
    return xx,yy,g
xx,yy,g=grid(scope);rows=[]
gi,ti=sh.STRtree(territories.geometry.values).query(g,predicate='intersects')
parts=sh.intersection(g[gi],territories.geometry.values[ti])
good=sh.area(parts)>1e-7
rows=pd.DataFrame({'town_seq':ti[good],'ix':xx[gi[good]],'iy':yy[gi[good]],'poly_area':sh.area(parts[good])})
rows['grid_id']='500_'+rows.ix.astype(str)+'_'+rows.iy.astype(str)
out_cols=['town_seq','ix','iy','grid_id','poly_area']
rows[out_cols].to_csv(base/'pieces_full.csv',index=False)
assert np.isclose(rows.poly_area.sum(),scope.area,atol=.01,rtol=0)
rows['poly_area']=sh.area(sh.intersection(parts[good],inner))
rows[rows.poly_area>1e-7][out_cols].to_csv(base/'pieces_interior.csv',index=False)
nfiles={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in [scopefile,townfile]}
data={'files':nfiles,'n':len(z),'districts':z.groupby('district').size().to_dict(),'scope_km2':scope.area/1e6,'named_km2':z.area.sum()/1e6,'overlap_km2':over.area/1e6,'uncovered_km2':gap.area/1e6,'interior250_km2':inner.area/1e6,'n_inner250':int((z.interior_km2>1e-8).sum())}
(base/'boundary_QA.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf8')
print(data)
