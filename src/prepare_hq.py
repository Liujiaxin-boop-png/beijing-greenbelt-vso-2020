"""Freeze 2020 native InVEST inputs, using the published Beijing parameters."""
from pathlib import Path
import json,csv,hashlib,datetime
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_bounds
from shapely.geometry import box

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'01_原始数据';SP=ROOT/'02_过程文件/spatial';P=ROOT/'02_过程文件/hq'
P.mkdir(exist_ok=True)
ALIAS=Path('D:/ER219_work')

def dump(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for x in iter(lambda:f.read(1048576),b''):h.update(x)
    return h.hexdigest()
def main():
    with rasterio.open(SP/'clcd2020.tif') as src:
        profile=src.profile;aff=src.transform;crs=src.crs;shape=src.shape;bounds=src.bounds
    national=RAW/'OSM2020原始道路成员/gis_osm_roads_free_1.shp'
    whitelist=['motorway','trunk','primary','motorway_link','trunk_link','primary_link']
    roadpath=P/'major_roads.gpkg'
    if roadpath.exists():roads=gpd.read_file(roadpath)
    else:
        bb=transform_bounds(crs,4326,*bounds,densify_pts=21)
        clause='fclass IN ('+','.join("'"+x+"'" for x in whitelist)+')'
        roads=gpd.read_file(national,bbox=bb,where=clause).to_crs(crs)
        roads=roads[roads.geometry.intersects(box(*bounds))].copy()
        assert roads.is_valid.all()
        roads.to_file(roadpath,driver='GPKG')
    assert set(roads['fclass']).issubset(whitelist)
    rr=rasterize([(g,1) for g in roads.geometry],out_shape=shape,transform=aff,fill=0,dtype='uint8',all_touched=False)
    pp=profile.copy();pp.update(dtype='uint8',count=1,nodata=255,compress='deflate')
    with rasterio.open(P/'road.tif','w',**pp) as dst:
        dst.write(rr,1);dst.update_tags(source='OSM Geofabrik 2020-01-01',scope='major mapped roads only',rasterization='30m Bresenham line; not surveyed road width')
    source_params=Path(__file__).resolve().parents[1]/'config/hq_sensitivity.csv'
    with source_params.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    fields=['lucode','name','habitat','built','road']
    with (P/'sensitivity.csv').open('w',newline='',encoding='ascii') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    codes_known={int(r['lucode']) for r in rows}
    info=[]
    for product,filename in [('clcd','clcd2020.tif'),('wc','worldcover2020_common30m.tif')]:
        with rasterio.open(SP/filename) as src:a=src.read(1)
        codes=set(int(x) for x in np.unique(a));assert codes.issubset(codes_known),str(codes-codes_known)
        built=(a==8).astype(np.uint8)
        with rasterio.open(P/(product+'_built.tif'),'w',**pp) as dst:dst.write(built,1)
        threats=P/(product+'_threats.csv')
        with threats.open('w',newline='',encoding='ascii') as f:
            w=csv.writer(f);w.writerow(['threat','max_dist','weight','decay','cur_path'])
            w.writerows([['built',10000,1,'linear',str(ALIAS/'hq'/(product+'_built.tif'))],['road',3000,1,'linear',str(ALIAS/'hq/road.tif')]])
        args={'workspace_dir':str(ALIAS/'hq'/('pilot_'+product)),
              'lulc_cur_path':str(ALIAS/'spatial'/filename),
              'threats_table_path':str(ALIAS/'hq'/threats.name),
              'sensitivity_table_path':str(ALIAS/'hq/sensitivity.csv'),
              'half_saturation_constant':0.05,'n_workers':-1,'results_suffix':''}
        stack={'invest_version':'3.20.2','model_name':'natcap.invest.habitat_quality.habitat_quality','model_id':'habitat_quality','args':args}
        dump(P/(product+'_pilot.json'),stack)
        info.append({'product':product,'landcover_sha256':sha(SP/filename),'class_codes':sorted(codes),'built_pixels':int(built.sum()),'datastack':str(P/(product+'_pilot.json'))})
    dump(P/'input_freeze.json',{'status':'INPUTS_FROZEN_BEFORE_NATIVE_EXECUTION','source_doi':'10.13209/j.0479-8023.2016.057',
        'roads_whitelist':whitelist,'road_feature_count':len(roads),'road_pixels':int(rr.sum()),'date':'2020-01-01',
        'road_source_sha256':sha(national),'roads_classes':{str(k):int(v) for k,v in roads.fclass.value_counts().items()},
        'source_parameter_sha256':sha(source_params),'model_version':'3.20.2','native_executable':'D:/Apps/InVEST-3.20.2/invest.exe',
        'max_dist_unit':'metres','max_dist_values':[10000,3000],'relative_weights':[1,1],'decay':'linear',
        'pilot_k':0.05,'final_k_rule':'0.5*max(baseline native D over valid study-scope pixel centres), identical for all final product runs',
        'products':info,'NTL_used_as_threat':False,'created':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(json.dumps({'status':'HQ_INPUTS_READY','roads':len(roads),'road_pixels':int(rr.sum())}),flush=True)

if __name__=='__main__':main()
