from pathlib import Path
import geopandas as gp,pandas as pd,numpy as np,shapely as sh
w=Path(__file__).resolve().parent
src=Path('D:/ER219_work/towndisc11/boundary/二道绿隔边界精确叠置.gpkg')
p=gp.read_file(src,layer='parts')
print(p.drop(columns='geometry').to_string(index=False))
common=p.loc[p.zone=='common'].geometry.union_all()
t=gp.read_file(w/'planning_towns.gpkg',layer='towns')
u=gp.read_file(w/'planning_towns.gpkg',layer='unassigned')
s=pd.concat([t[['town_seq','geometry']],u[['town_seq','geometry']]]).sort_values('town_seq')
r=pd.read_csv(w/'pieces_full.csv')
cells=sh.box(500*r.ix,500*r.iy,500*(r.ix+1),500*(r.iy+1))
assert p.crs==t.crs
c=sh.intersection(cells,s.geometry.values[r.town_seq])
r['poly_area']=sh.area(sh.intersection(c,common))
r=r[r.poly_area>1e-7]
assert abs(r.poly_area.sum()-common.area)<.05
r.to_csv(w/'pieces_common.csv',index=False)
print('Common area verified',common.area/1e6)
