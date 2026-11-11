from pathlib import Path
import json
import sys
import math

import geopandas as gp
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from pyproj import Transformer, Geod

work = Path(__file__).resolve().parent
figs = Path('D:/ER219_figures/四个典型镇街_镇内十年变化_ArcMap10.8').resolve()
annual = Path('D:/ER219_work/annual_actual')
src = Path('D:/ER219_work/six_final11/annual/ALLDIST/六项格网十年变化.csv')
townfile = annual / 'boundary/planning_towns.gpkg'
towns = gp.read_file(townfile,layer='towns')
grid = pd.read_csv(src)
pieces = pd.read_csv(annual / 'towns/pieces_full.csv')
full = pd.read_csv('D:/ER219_work/litlogic11/types/78镇街首末年分型与敏感性.csv')
cases = [(7,'东小口地区','东小口地区','普遍下降型'),(8,'阳坊镇','阳坊镇','普遍上升型'),
         (9,'长辛店镇','原长辛店镇','局部上升主导型'),(10,'李桥镇','李桥镇','局部下降主导型')]
palette = ['#985B45','#C68C6D','#EDD4BD','#D9DBD7','#CAE1D6','#7FB69D','#397963']
labels = ['≤ −0.010','(−0.010, −0.001]','(−0.001, 0)','= 0','(0, +0.001]','(+0.001, +0.010]','> +0.010']
display = [('ERclass','综合指数变化'),('HQclass','生境质量分项变化'),('MCclass','斑块联系分项变化')]
metrics = ['delta','delta_HQI','delta_MCR']
ink,muted = '#26322D','#46564E'
rev = Transformer.from_crs(towns.crs,'EPSG:4326',always_xy=True)
fwd = Transformer.from_crs('EPSG:4326',towns.crs,always_xy=True)
earth = Geod(ellps='WGS84')

def polygonal(g):
    if isinstance(g,(Polygon,MultiPolygon)): return g
    return shapely.union_all([p for p in g.geoms if p.geom_type in ('Polygon','MultiPolygon')])

def classification(v):
    return np.select([v<=-.01,v<=-.001,v<0,v==0,v<=.001,v<=.01],[1,2,3,4,5,6],7).astype('int16')

def fc(g, db, name):
    g.to_file(db, layer=name, driver='OpenFileGDB', engine='pyogrio',index=False,
              geometry_type='MultiPolygon' if g.geometry.geom_type.isin(['Polygon','MultiPolygon']).all() else 'Point',
              promote_to_multi=g.geometry.geom_type.isin(['Polygon','MultiPolygon']).all(),
              layer_options={'TARGET_ARCGIS_VERSION':'ALL'})

def calculate(which, base, title, typename):
    out = figs/f'图{which}'
    out.mkdir(parents=True,exist_ok=True)
    db = out/'data'/'镇内变化.gdb'
    db.parent.mkdir(exist_ok=True)
    t = towns[towns.display_name==base].iloc[0]
    row=full[full.display_name.eq(base)].iloc[0]
    ds = pieces.loc[pieces.town_seq.eq(row.town_seq)].merge(grid,on=['ix','iy'],validate='1:1')
    cut = shapely.intersection(shapely.box(ds.ix*500, ds.iy*500,(ds.ix+1)*500,(ds.iy+1)*500),t.geometry)
    clipped = gp.GeoDataFrame(ds,geometry=[polygonal(g) for g in cut],crs=towns.crs)
    np.testing.assert_allclose(clipped.area,clipped.poly_area,rtol=1e-10,atol=0.0001)
    assert abs(clipped.area.sum()/1e6-row.km2)<1e-8
    for (field,_),metric in zip(display,metrics): clipped[field]=classification(clipped[metric])
    keep = ['grid_id','ix','iy','poly_area','ER2015','ER2025','delta','delta_LDI','delta_HQI','delta_LBI','delta_MCR','delta_ALLDIST','delta_LRI','ERclass','HQclass','MCclass','geometry']
    for f in ('ix','iy'):clipped[f]=clipped[f].astype('int32')
    clipped['town_name'] = title
    clipped['area_km2'] = clipped.area/1e6
    fc(clipped[keep+['town_name','area_km2']],db,'cells')
    outline = gp.GeoDataFrame({'town_name':[title]},geometry=[t.geometry],crs=towns.crs)
    fc(outline, db,'scope')
    left,bottom,right,top = t.geometry.bounds
    fw,fh,fy = 5.65,5.23,2.14
    xs = [.28,6.26,12.24]
    unit=max((right-left)/fw,(top-bottom)/fh)*1.13
    cx,cy=(right+left)/2,(top+bottom)/2
    ext=[cx-fw*unit/2,cy-fh*unit/2,cx+fw*unit/2,cy+fh*unit/2]
    file_stem=f'{title}镇内生态韧性变化' if title=='东小口地区' else f'{title}生态韧性镇内变化'
    file_stem=title+'规划区内生态韧性变化'
    vals=[dict(value=str(i+1),label=s,color=col) for i,(s,col) in enumerate(zip(labels,palette))]
    maps=[]
    for j,(field,mname) in enumerate(display):
        layers=[dict(name=mname,kind='polygon',gdb=str(db),fc='cells',renderer='unique',field=field,values=vals),
                dict(name='镇内规划区轮廓',kind='polygon',gdb=str(db),fc='scope',fill='none',stroke='#68736D',width=.27)]
        maps.append(dict(name=mname,x=xs[j],y=fy,w=fw,h=fh,extent=ext,
                         border_width=.4,border_color='#AEB7B0',layers=layers))
    el=[]
    def txt(name,s,x,y,size=8,bold=False,align='left',color=ink):
        el.append(dict(kind='text',name=name,text=s,x=float(x),y=float(y),size=size,bold=bold,
                       align=align,valign='center',font='SimHei',color=color))
    def line(name,points,color,width):
        el.append(dict(kind='line',name=name,points=points,color=color,width=width))
    def rectangle(name,x,y,w,h,fill):
        el.append(dict(kind='rect',name=name,x=x,y=y,w=w,h=h,fill=fill,stroke='none',width=0))
    txt('镇街与类型',title+'  /  '+typename,.29,8.75,11.4,True)
    txt('年份与单元','2015—2025年   ·   500 m格网',16.95,8.72,8.9,False,'right',muted)
    line('标题下划线',[[.28,8.34],[17.91,8.34]],'#95A49B',.48)
    for j,(_,mname) in enumerate(display):
        txt('分面'+str(j),'('+chr(ord('a')+j)+')  '+mname,xs[j],7.99,9.3,True)
    txt('指数释义','2025年减2015年',xs[0],7.62,7.75,False,'left',muted)
    txt('生境释义','正值表示模型生境质量提高',xs[1],7.62,7.75,False,'left',muted)
    txt('联系释义','正值表示源地间潜在通行成本降低',xs[2],7.62,7.75,False,'left',muted)
    # Projection orientation at the centre of each actual mapped town.
    lon,lat=rev.transform(cx,cy)
    lon2,lat2,_=earth.fwd(lon,lat,0,1000)
    ex,ey=fwd.transform(lon2,lat2)
    vx,vy=ex-cx,ey-cy
    length=math.hypot(vx,vy);ux,uy=vx/length,vy/length
    nr,ny=17.67,8.68
    el.append(dict(kind='polygon',name='正北箭头',points=[[nr-.103*uy,ny+.103*ux],[nr+.103*uy,ny-.103*ux],
                   [nr+.40*ux,ny+.40*uy],[nr-.103*uy,ny+.103*ux]],fill=ink,stroke=ink,width=.28))
    txt('北','N',nr,ny-.16,7.7,True,'center')
    # Colour breaks are identical on every map. Zero is a distinct, neutral swatch.
    txt('图例','指数分值差',.29,1.57,8.8,True)
    start,bw,ht=2.36,1.61,.22
    for j,i in enumerate([0,1,2,4,5,6]):
        rectangle('色带'+str(i),start+bw*j,1.46,bw,ht,palette[i])
    for j,lab in enumerate(['−0.010','−0.001','0','+0.001','+0.010']):
        xx=start+bw*(j+1)
        line('刻度'+str(j),[[xx,1.46],[xx,1.38]],muted,.4)
        txt('断点'+str(j),lab,xx,1.15,7.9,False,'center')
    txt('负值','下降',start,1.17,7.5,False,'left',muted)
    txt('正值','上升',start+6*bw,1.17,7.5,False,'right',muted)
    rectangle('零',12.55,1.46,.37,ht,palette[3])
    txt('零图例','= 0',13.03,1.55,7.9)
    txt('定位图例','(a)  1  最大连片下降区     2  最大连片上升区',.31,.47,8.1)
    txt('有效范围','着色为镇界与绿隔规划范围的交集',17.9,.48,7.8,False,'right',muted)
    # Optional anchors: real points within the largest co-edged patches.
    coordfile=Path('D:/ER219_work/townmaps11/evidence/case_hotspots.csv')
    if coordfile.is_file():
        anchors=pd.read_csv(coordfile)
        anchors=anchors[anchors['seq'].eq(row.town_seq)].rename(columns={'marker':'num'}).reset_index(drop=True)
        assert set(anchors.num)=={1,2}
        for a in anchors.itertuples(index=False):
            pxy=shapely.Point(a.x,a.y)
            assert t.geometry.covers(pxy),(base,a)
            pix=xs[0]+(a.x-ext[0])/unit
            piy=fy+(a.y-ext[1])/unit
            el.append(dict(kind='marker',name='片区定位'+str(a.num),x=pix,y=piy,size=8.9,fill='#FFFFFF',stroke='#26352F',width=.55))
            txt('片区编号'+str(a.num),str(a.num),pix,piy,6.7,True,'center')
        points=gp.GeoDataFrame({'case_no':anchors.num,'feature':['最大连片下降区' if v==1 else '最大连片上升区' for v in anchors.num]},
                              geometry=gp.points_from_xy(anchors.x,anchors.y),crs=towns.crs)
        fc(points,db,'locators')
        shapes=gp.read_file(coordfile.with_suffix('.gpkg'),layer='patches')
        foci=shapes.loc[shapes['seq'].eq(row.town_seq),['marker','geometry']].copy()
        assert len(foci)==2 and foci.crs.equals(towns.crs,ignore_axis_order=True)
        fc(foci,db,'focus_areas')
        maps[0]['layers'].append(dict(name='最大连续升降片区边界',kind='polygon',gdb=str(db),fc='focus_areas',
                                      fill='none',stroke='#4C514B',width=.62))
        maps[0]['layers'].append(dict(name='最大连片下降及上升区定位',kind='point',gdb=str(db),fc='locators',
                                      fill='#FFFFFF',stroke='#26352F',size=8.9,width=.55))
    cfg=dict(page=dict(width_cm=18.2,height_cm=9.18,font='SimHei'),maps=maps,elements=el,
             scales=[dict(name='三图共同的比例尺',map=display[0][1],x=14.4,y=1.08,w=2.78,h=.12,
                          division_km=.5 if unit<1600 else 1,divisions=2,font_size=7.5,color='#445049')],
             north_arrows=[],dpi=500,expected_maps=3,export_stem=str(work/f'case{which}'),
             output_mxd=str(out/(file_stem+'.mxd')))
    (work/f'case{which}.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),'utf8')
    return dict(figure=which,name=title,field_codes=dict(zip(('综合指数差','生境质量对综合分贡献变化','通行条件对综合分贡献变化'),metrics)),
                area_km2=clipped.area.sum()/1e6,units=len(clipped),dec_area_pct=(clipped.loc[clipped.delta<0].area.sum()/clipped.area.sum()*100),
                grid_min=float(clipped.delta.min()),grid_max=float(clipped.delta.max()),
                extent=ext,unit_per_cm=unit,destination=str(out),mxd=cfg['output_mxd'])

if __name__=='__main__':
    audits=[calculate(*case) for case in cases]
    (work/'case_maps.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2),'utf8')
    print([(r['name'],r['units'],round(r['area_km2'],2)) for r in audits])
