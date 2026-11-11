from pathlib import Path
import gzip, json
import geopandas as gp
import shapely
import pandas as pd

work=Path(__file__).resolve().parent
directory=Path('D:/ER219_work/townmaps11/evidence')
src=next(Path('D:/ER219_raw/年度分析_2015_2025/OSM年末主要道路').glob('ohsome_2025*.geojson.gz'))
features=json.load(gzip.open(src,'rt',encoding='utf8'))['features']
roads=gp.GeoDataFrame.from_features(features,crs='EPSG:4326')
patch=gp.read_file(directory/'case_hotspots.gpkg',layer='patches').set_index('code')
roads=roads.to_crs(patch.crs)
check=pd.read_csv(directory/'patch_road_landmarks.csv')
picks=[('北清路','文华路'),('六环路','沙阳路'),('长兴路','丰台梨园桥'),('通顺路','六环路')]
r=[]
for entry,names,letter in zip(json.loads((work/'case_maps.json').read_text('utf8')),picks,'ABCD'):
    rows=[]
    for ind,name in enumerate(names,1):
        code=letter+str(ind)
        cr=check[(check.code==code)&(check.road==name)].iloc[0]
        ids=cr.osm_ids.split('|')
        for _,osm in roads.loc[roads['@osmId'].isin(ids)&roads.name.eq(name)].iterrows():
            geom=osm.geometry.intersection(patch.loc[code].geometry)
            parts=[g for g in shapely.get_parts(geom) if g.geom_type in ('MultiLineString','LineString') and g.length>0]
            if parts:
                line=shapely.union_all(parts)
                rows.append(dict(case_code=code,marker_no=ind,road_name=name,osm_id=osm['@osmId'],mapped_m=line.length,geometry=line))
        recomputed=shapely.union_all([g['geometry'] for g in rows if g['case_code']==code]).length/1000
        assert abs(recomputed-cr.mapped_line_km)<1e-8,(code,recomputed,cr.mapped_line_km)
        r.append(dict(case=code,road=name,km=recomputed))
    g=gp.GeoDataFrame(rows,crs=patch.crs);g['marker_no']=g.marker_no.astype('int16')
    g.to_file(Path(entry['destination'])/'data/镇内变化.gdb',layer='roads_2025',engine='pyogrio',driver='OpenFileGDB',geometry_type='MultiLineString',promote_to_multi=True,
              layer_options={'TARGET_ARCGIS_VERSION':'ALL'},index=False)
(work/'road_layer_provenance.json').write_text(json.dumps(dict(source=str(src),patch=str(directory/'case_hotspots.gpkg'),landmarks=r),ensure_ascii=False,indent=2),'utf8')
