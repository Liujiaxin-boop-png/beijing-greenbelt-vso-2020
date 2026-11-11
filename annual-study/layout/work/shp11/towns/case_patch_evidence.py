"""Locate and measure connected ups/downs within each town's planning-area intersection."""
from collections import defaultdict, deque
import json
from pathlib import Path
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shapely
from shapely.geometry import Point, box

HERE = Path(__file__).resolve().parent
BASE = Path('D:/ER219_work/annual_actual')
SOURCE=HERE.parent/'core'
case_selection=pd.read_csv(HERE/'四类入选镇街指标与增减地段强度.csv')
TOWNS={r.town_seq:(r.base_type,{'长辛店镇':'原长辛店镇'}.get(r.display_name,r.display_name)) for r in case_selection.itertuples()}
CLASSES = ['未分类','耕地','林地','灌丛','草地','水体','冰雪','裸地','不透水面','湿地']
VARS = ['delta','delta_HQI','delta_MCR','delta_LRI','delta_LDI','delta_LBI','delta_ALLDIST']
sys.path.insert(0,str(BASE/'analysis/geo'))
from exactextract import exact_extract

def polygons(geom):
    if geom.is_empty:
        return
    if geom.geom_type == 'Polygon':
        if geom.area > 0.0001:
            yield geom
    elif hasattr(geom, 'geoms'):
        for g in geom.geoms:
            yield from polygons(g)

def partition(frame):
    """Rook graph within the actual cuts; coordinate-tangency never joins patches."""
    geoms=frame.geometry.values
    a,b=shapely.STRtree(geoms).query(geoms,predicate='intersects')
    ok=(a<b)&(frame['up'].to_numpy()[a]==frame['up'].to_numpy()[b])
    a=a[ok];b=b[ok]
    shared=shapely.length(shapely.intersection(geoms[a],geoms[b]))
    edges={i:[] for i in range(len(frame))}
    for i,j in zip(a[shared>1e-6],b[shared>1e-6]):
        edges[i].append(j)
        edges[j].append(i)
    ids=np.full(len(frame),-1,dtype=int)
    cluster=0
    for start in range(len(frame)):
        if ids[start]>=0:continue
        waiting=deque([start]);ids[start]=cluster
        while waiting:
            for nei in edges[waiting.popleft()]:
                if ids[nei]<0:
                    ids[nei]=cluster;waiting.append(nei)
        cluster+=1
    return ids

def record_values(rows, area):
    return {k:float(np.average(rows[k],weights=area)) for k in VARS}

def quadrants(geom):
    xmin,ymin,xmax,ymax=geom.bounds
    xm=(xmin+xmax)/2;ym=(ymin+ymax)/2
    return {lb:box(x0,y0,x1,y1) for lb,(x0,y0,x1,y1) in
            {'西北':(xmin,ym,xm,ymax),'东北':(xm,ym,xmax,ymax),
             '西南':(xmin,ymin,xm,ym),'东南':(xm,ymin,xmax,ym)}.items()}

def main():
    towns=gpd.read_file(HERE/'planning_towns.gpkg',layer='towns')
    grid=pd.read_csv(SOURCE/'六项格网十年变化.csv')
    assert not (grid.delta==0).any()
    published=pd.read_csv(HERE/'pieces_full.csv').drop(columns='grid_id').merge(grid,on=['ix','iy'],validate='m:1')
    summaries=[];qrows=[];loc=[];outlines=[];cell_records=[]
    for seq,(typ,name) in TOWNS.items():
        town=towns.geometry.iloc[seq]
        zones=quadrants(town)
        view=published[published.town_seq==seq]
        components=[]
        for r in view.to_dict('records'):
            g=box(500*r['ix'],500*r['iy'],500*(r['ix']+1),500*(r['iy']+1)).intersection(town)
            assert abs(g.area-r['poly_area'])<0.001,(r['grid_id'],g.area,r['poly_area'])
            for poly in polygons(g):
                components.append({'seq':seq,'town':name,'grid_id':r['grid_id'],'geometry':poly,
                                   'up':int(r['delta']>0),**{k:r[k] for k in VARS}})
        cuts=gpd.GeoDataFrame(components,crs=towns.crs)
        cuts['sqm']=cuts.area
        cuts['patch']=partition(cuts)
        assert abs(cuts.area.sum()-town.area)<.01
        cuts.to_file(HERE/'case_cells.gpkg',layer=f'case_{typ}',driver='GPKG')
        for qn,q in zones.items():
            inter=shapely.area(shapely.intersection(cuts.geometry.values,q))
            for up,g in cuts.groupby('up'):
                ar=inter[g.index]
                if ar.sum()>0:
                    qrows.append({'seq':seq,'town':name,'quad':qn,'up':int(up),'km2':ar.sum()/1e6,**record_values(g,ar)})
        xmin,ymin,xmax,ymax=town.bounds
        for up,sub in cuts.groupby('up'):
            ranked=sub.groupby('patch').sqm.sum().sort_values(ascending=False)
            g=sub[sub.patch==ranked.index[0]]
            poly=shapely.union_all(g.geometry.values)
            # A point with a large internal clearance tends to be legible on the map.
            marker=Point(shapely.maximum_inscribed_circle(poly,tolerance=1).coords[0])
            assert poly.contains(marker)
            tquad=next(n for n,z in zones.items() if z.covers(marker))
            mark=2 if up else 1
            pcode=f'{typ}{mark}'
            qarea={n:poly.intersection(z).area/1e6 for n,z in zones.items()}
            med={k:np.round(v,5) for k,v in record_values(g,g.sqm).items()}
            share=poly.area/sub.area.sum()
            rec={'code':pcode,'seq':seq,'town':name,'marker':mark,'up':int(up),'x':marker.x,'y':marker.y,
                 'point_quad':tquad,'x_frac':(marker.x-xmin)/(xmax-xmin),'y_frac':(marker.y-ymin)/(ymax-ymin),
                 'area_km2':poly.area/1e6,'fraction_of_same_sign':share,'n_grids':g.grid_id.nunique(),
                 **record_values(g,g.sqm),**{f'{name}_km2':v for name,v in qarea.items()}}
            summaries.append(rec)
            loc.append({**{c:rec[c] for c in ['code','seq','town','marker','x','y']},'geometry':marker})
            outlines.append({'code':pcode,'seq':seq,'town':name,'marker':mark,'km2':poly.area/1e6,'geometry':poly})
            for _,r in g.iterrows():
                cell_records.append({'code':pcode,'grid_id':r.grid_id,'area_km2':r.sqm/1e6,**{k:r[k] for k in VARS}})
    patches=gpd.GeoDataFrame(outlines,crs=towns.crs)
    points=gpd.GeoDataFrame(loc,crs=towns.crs)
    output=HERE/'case_hotspots.gpkg'
    patches.to_file(output,layer='patches',driver='GPKG')
    points.to_file(output,layer='markers',driver='GPKG')
    pd.DataFrame(summaries).to_csv(HERE/'case_hotspots.csv',encoding='utf-8-sig',index=False)
    pd.DataFrame(qrows).to_csv(HERE/'quadrants.csv',encoding='utf-8-sig',index=False)
    pd.DataFrame(cell_records).to_csv(HERE/'patch_grid_contributions.csv',encoding='utf-8-sig',index=False)
    with rasterio.open(BASE/'years/model/CLCD_2015.tif') as before, rasterio.open(BASE/'years/model/CLCD_2025.tif') as after:
        assert before.shape==after.shape and before.transform==after.transform and before.crs==after.crs
        p=exact_extract(before,patches,['cell_id','coverage'],include_cols=['code'],output='pandas')
        first=before.read(1).ravel();last=after.read(1).ravel()
        transitions=[]
        for row in p.itertuples():
            cells=np.array(row.cell_id,dtype=int)
            area=np.array(row.coverage,dtype=float)*900/1e4
            a=first[cells];b=last[cells]
            assert a.min()>=1 and b.min()>=1 and a.max()<=9 and b.max()<=9
            M=np.bincount((a.astype(int)*10+b.astype(int)),weights=area,minlength=100).reshape(10,10)
            expected=patches.set_index('code').loc[row.code].geometry.area/1e4
            assert abs(M.sum()-expected)<0.001
            for i,j in zip(*np.nonzero(M)):
                transitions.append({'code':row.code,'from':CLASSES[i],'to':CLASSES[j],'ha':M[i,j],'pct':M[i,j]/expected*100})
    pd.DataFrame(transitions).to_csv(HERE/'patch_land_transitions.csv',encoding='utf-8-sig',index=False)
if __name__=='__main__':
    main()
