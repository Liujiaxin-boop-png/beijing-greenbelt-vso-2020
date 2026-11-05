from pathlib import Path
import json, hashlib, shutil, datetime
import rasterio
import geopandas as gpd
from rasterio.warp import transform_bounds

OUT = Path(__file__).resolve().parents[3]
ROOT = OUT.parent
RAW = OUT / '01_原始数据'
AUDIT = OUT / '02_过程文件' / '数据审计'
OLD = ROOT / '生态韧性新研究' / '数据下载_20261020'

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

rows=[]
def stage(src, rel, role, source_url=None, year=None):
    dst=RAW/rel;dst.parent.mkdir(parents=True,exist_ok=True)
    hs=digest(src)
    if dst.exists():
        if digest(dst)!=hs:raise RuntimeError('Existing destination differs: '+str(dst))
    else:shutil.copy2(src,dst)
    assert digest(dst)==hs
    d={'source_local':str(src),'staged_relative':str(dst.relative_to(OUT)), 'bytes':dst.stat().st_size,'sha256':hs,'role':role,'source_url':source_url,'year':year}
    if dst.suffix.lower() in ('.tif','.tiff'):
        with rasterio.open(dst) as ds:
            d.update(crs_wkt=ds.crs.to_wkt(),bounds=list(ds.bounds),bounds_wgs84=list(transform_bounds(ds.crs,'EPSG:4326',*ds.bounds)),resolution=list(ds.res),shape=list(ds.shape),count=ds.count,dtypes=ds.dtypes,nodata=ds.nodata)
    rows.append(d)
    return dst

def stage_dir(src, rel, role, source_url=None, year=None):
    for p in sorted(src.rglob('*')):
        if p.is_file() and not p.name.endswith('.lock'):stage(p,Path(rel)/p.relative_to(src),role,source_url,year)

clcd=OLD/'11_InVEST扩大背景/CLCD土地覆盖/2020/CLCD_2020_v102_background17km.tif'
stage(clcd,'CLCD2020/CLCD_2020_v102_native_background17km.tif','Native-grid lossless download window; not resampled or reclassified','https://zenodo.org/records/8176941/files/CLCD_v01_2020_albert.tif?download=1',2020)
stage(OLD/'download_manifest_expanded_background.json','来源记录/CLCD_expanded_original_manifest.json','Original download and source metadata')

study=ROOT/'GIS数据/GIS数据/研究范围0328.shp'
for p in study.parent.glob(study.stem+'.*'):
    if p.suffix.lower() in ('.shp','.shx','.dbf','.prj','.cpg','.sbn','.sbx','.xml'):stage(p,'研究范围/'+p.name,'User-provided case boundary, not official greenbelt boundary')
g=gpd.read_file(study)
boundary={'path':str(study),'records':len(g),'towns':int(g['Name'].nunique()),'names':sorted(g.Name.unique().tolist()),'crs':str(g.crs),'bounds':g.total_bounds.tolist(),'invalid_count':int((~g.is_valid).sum())}
(AUDIT/'219_boundary_readback.json').write_text(json.dumps(boundary,ensure_ascii=False,indent=2),encoding='utf-8')

stage_dir(OLD/'05_OSM道路/03_Geofabrik_20200101_原始道路成员','OSM2020原始道路成员','Original members extracted losslessly from Geofabrik 2020-01-01 national archive','https://download.geofabrik.de/asia/china-200101-free.shp.zip',2020)
stage(OLD/'download_manifest_osm.json','来源记录/OSM_original_manifest.json','Original download and source metadata')

stage_dir(OLD/'04_地形高程/NASADEM_SRTM重处理','NASADEM已有原生窗口','Native-grid NASADEM windows; source elevations primarily February 2000',year=2000)
stage(OLD/'download_manifest_landsat_dem.json','来源记录/Landsat_NASADEM_original_manifest.json','Original per-file source URL, acquisition date, checksum and scaling metadata')

stage_dir(ROOT/'2020年论文成果/01_原始数据/2020热状态候选_84','Landsat8_2020已有原生窗口','Native-grid Landsat 8 C2 L2 ST_B10 DN, QA and original scene MTL; three dates only',year=2020)

receipt={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'EXISTING_INPUTS_STAGED_WITH_SHA256','files':rows,'boundary':boundary,'missing_or_coverage_issues':['2020 EOG VIIRS annual radiance and cf_cvg not present in workspace; official site requires account authentication','WorldCover existing window insufficient for full CLCD background; two official original tiles being obtained','NASADEM existing windows cover study area but not full CLCD background; expanded retrieval being evaluated'], 'notes':['No upstream file modified','Lossless native-grid windows are retrieval subsets, not complete original national/tile files; all subset methods and source URLs retained','2020 road snapshot is 2020-01-01; OSM feature existence is not proof of construction date','Three Landsat dates are clear-sky snapshots and must not be described as annual mean or independent whole-resilience validation']}
(AUDIT/'219_existing_inputs_inventory.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':receipt['status'],'files':len(rows),'bytes':sum(x['bytes'] for x in rows),'boundary':boundary},ensure_ascii=False))
