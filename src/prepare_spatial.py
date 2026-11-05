"""Prepare immutable geographic context, aligned inputs and fishnet definition."""
from pathlib import Path
import hashlib, json, math, shutil, datetime, subprocess
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.features import rasterize
from shapely.geometry import box, mapping
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'01_原始数据';WORK=ROOT/'02_过程文件/spatial'
WORK.mkdir(parents=True,exist_ok=True)

def dump(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def main():
    landfile=RAW/'CLCD2020/CLCD_2020_v102_native_background17km.tif'
    scopefile=RAW/'研究范围/研究范围0328.shp'
    with rasterio.open(landfile) as src:
        profile=src.profile;crs=src.crs;aff=src.transform;shape=src.shape;land=src.read(1)
    scopes=gpd.read_file(scopefile,encoding='gbk').to_crs(crs)
    assert len(scopes)==38
    assert scopes.is_valid.all(), 'Supplied geometry invalid; do not silently repair'
    towns=scopes[['Name','geometry']].dissolve(by='Name',as_index=False)
    assert len(towns)==35
    scope=unary_union(towns.geometry)
    overlap_excess=float(sum(towns.area)-scope.area)
    # Preserve the provided boundaries. They are not a perfectly disjoint
    # administrative partition. Regional totals use union; per-town statistics
    # use each supplied area and must never be summed as a regional total.
    gpkg=WORK/'scope.gpkg'
    if not gpkg.exists():
        scopes.to_file(gpkg,layer='source_parts',driver='GPKG')
        towns.to_file(gpkg,layer='towns',driver='GPKG')
        gpd.GeoDataFrame({'name':['study_scope']},geometry=[scope],crs=crs).to_file(gpkg,layer='study_scope',driver='GPKG')
    target=WORK/'clcd2020.tif'
    if not target.exists():shutil.copy2(landfile,target)
    assert sha(target)==sha(landfile)
    mask=rasterize([(scope,1)],out_shape=shape,transform=aff,fill=0,dtype='uint8')
    pp=profile.copy();pp.update(dtype='uint8',count=1,nodata=0,compress='deflate')
    with rasterio.open(WORK/'reporting_mask.tif','w',**pp) as dst:dst.write(mask,1)
    x0=math.floor(scope.bounds[0]/1000)*1000;y0=math.floor(scope.bounds[1]/1000)*1000
    xmax=math.ceil(scope.bounds[2]/1000)*1000;ymax=math.ceil(scope.bounds[3]/1000)*1000
    config={'native_work':r'D:\ER219_work\spatial','raster_native':r'D:\ER219_work\spatial\clcd2020.tif',
            'scope_source':str(scopefile),'scope_projected_geojson':str(WORK/'scope_projected.geojson'),
            'origin_xy':[x0,y0],'corner_xy':[xmax,ymax],'scales_m':[1000,500],
            'crs_wkt':crs.to_wkt(),'shape':list(shape),'transform':list(aff),
            'support_rule':'Full square landscape context; scope/town intersections determine reporting-area weights only; no replacement with full administrative areas',
            'native_gdb':r'D:\ER219_work\spatial\analysis.gdb'}
    dump(WORK/'native_config.json',config)
    # GeoJSON is explicitly projected, for internal interchange only.
    dump(WORK/'scope_projected.geojson',{'type':'FeatureCollection','crs':{'type':'name','properties':{'name':crs.to_wkt()}},
        'features':[{'type':'Feature','properties':{'town':str(row.Name)},'geometry':mapping(row.geometry)} for row in towns.itertuples()]})
    with rasterio.open(WORK/'worldcover2020_common30m.tif','w',**pp) as dst:
        wc=np.zeros(shape,np.uint8)
        sources=sorted((RAW/'WorldCover2020官方整幅').glob('*Map.tif'))
        assert len(sources)==2
        # Mosaic native tiles BEFORE mode resampling. Independent tile warps
        # compute different partial modes along the common seam.
        vrt=WORK/'worldcover2020_native.vrt'
        subprocess.run([r'F:\Program Files\QGIS 3.28.2\bin\gdalbuildvrt.exe','-overwrite',str(vrt),*[str(p) for p in sources]],check=True)
        with rasterio.open(vrt) as s:
            reproject(rasterio.band(s,1),wc,src_transform=s.transform,src_crs=s.crs,src_nodata=0,
                dst_transform=aff,dst_crs=crs,dst_nodata=0,resampling=Resampling.mode,num_threads=2)
        mapped=np.zeros(shape,np.uint8)
        for old,new in {10:2,20:3,30:4,40:1,50:8,60:7,70:6,80:5,90:9}.items():mapped[wc==old]=new
        assert np.all(mapped[mask==1]>0), 'Unknown WorldCover classes in reporting domain'
        dst.write(mapped,1)
        dst.update_tags(source='ESA WorldCover 2020 v100',resampling='mode',mapping='10:2,20:3,30:4,40:1,50:8,60:7,70:6,80:5,90:9')
    dump(WORK/'spatial_preparation_receipt.json',{'status':'SPATIAL_INPUTS_PREPARED_NATIVE_FISHNET_PENDING',
        'source_count':38,'towns':35,'scope_area_km2':scope.area/1e6,'pixel_count_inside_centres':int(mask.sum()),
        'town_overlap_excess_m2':overlap_excess,'town_stats_not_additive':True,'source_geometry_repaired':False,
        'crs_wkt':crs.to_wkt(),'origin_xy':[x0,y0],'scope_bounds':list(scope.bounds),
        'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [landfile,scopefile,*sources]},
        'WC_known_inside_fraction':float((mapped[mask==1]>0).mean()),'clcd_codes':dict(zip(*[x.tolist() for x in np.unique(land,return_counts=True)])),
        'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(json.dumps({'status':'SPATIAL_INPUTS_PREPARED','area_km2':scope.area/1e6,'origin_xy':[x0,y0]},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
