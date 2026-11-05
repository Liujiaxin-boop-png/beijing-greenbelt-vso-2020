from pathlib import Path
import json,hashlib,datetime,csv
import rasterio,numpy as np,geopandas as gpd
from shapely.geometry import box
from shapely.ops import unary_union
from rasterio.warp import transform_bounds
ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/'01_原始数据';AUDIT=ROOT/'02_过程文件/数据审计'
records=[]
for group in ['CLCD2020','WorldCover2020官方整幅','NASADEM完整瓦片','Landsat8_2020已有原生窗口','Landsat8_2020补充质量层']:
    for p in sorted((RAW/group).rglob('*.tif')):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
        with rasterio.open(p) as ds:
            records.append({'group':group,'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':h.hexdigest(),'crs':ds.crs.to_wkt(),'bounds':list(ds.bounds),'bounds_wgs84':list(transform_bounds(ds.crs,'EPSG:4326',*ds.bounds)),'shape':list(ds.shape),'resolution':list(ds.res),'dtype':ds.dtypes[0],'nodata':ds.nodata})

clcd=RAW/'CLCD2020/CLCD_2020_v102_native_background17km.tif'
with rasterio.open(clcd) as ds:
    b=transform_bounds(ds.crs,'EPSG:4326',*ds.bounds,densify_pts=101)
    targetbox=box(*b)
coverage={}
for group in ['WorldCover2020官方整幅','NASADEM完整瓦片']:
    polys=[box(*x['bounds_wgs84']) for x in records if x['group']==group]
    coverage[group]={'full_clcd_background_envelope_covered':unary_union(polys).covers(targetbox),'tile_count':len(polys),'target_envelope_wgs84':b}

software={'ArcGIS_Desktop':{'version':'10.8','build':'12790','path':'D:/Apps/Desktop10.8','python':'C:/Python27/ArcGIS10.8/python.exe','native_import_test':'PASS','product':'ArcInfo','Spatial_extension':'Available','warning':'936 codepage table unavailable warning during import; prefer ASCII runtime paths and verify Chinese field handling'},'ArcGIS_Pro':{'registry_version':'3.1.41833','patch':'3.1.6','path':'F:/Program Files/ArcGIS/Pro','native_import_test':'not_run'},'QGIS':{'registry_version':'3.28.2 Firenze','path':'F:/Program Files/QGIS 3.28.2','GDAL_binary_version':'3.6.1','native_desktop_test':'not_run'},'Excel':{'path':'C:/Program Files/Microsoft Office/root/Office16/EXCEL.EXE','file_version':'16.0.17932.21056','native_open_test':'not_run'},'Python312':{'path':'C:/Users/LJX/AppData/Local/Programs/Python/Python312/python.exe','rasterio':'1.5.0','geopandas':'1.1.4','shapely':'2.1.2','natcap_invest_import':False,'osgeo_import':False,'pygeoprocessing_import':False},'FRAGSTATS':{'registry_before_current_setup':'not_found','note':'Another project agent is preparing official FRAGSTATS4.2; refer to calculation audit for tested executable status'},'InVEST':{'registry_before_current_setup':'not_found','archived_official_whl':'natcap_invest-3.20.2-cp312-cp312-win_amd64.whl','note':'Archive existence is not successful installation; parent handles dedicated environment'}}

receipt={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'DATA_STAGE_AVAILABLE_EXCEPT_EOG_VIIRS','rasters':records,'coverage':coverage,'software':software,'remaining_required_input':'EOG VIIRS 2020 annual radiance plus valid observation counts cf_cvg; official download requires free account. No substitute, interpolation or zero filling applied.','method_unchanged':True}
(AUDIT/'219_data_audit_final.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
with (AUDIT/'219_raster_inventory.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['group','file','bytes','sha256','crs','bounds','bounds_wgs84','shape','resolution','dtype','nodata']);writer.writeheader();writer.writerows(records)
(AUDIT/'219_数据与软件审计说明.txt').write_text('''数据与软件审计（开题报告218执行）

1. 现有可计算数据均已另存，旧文件未改。研究范围为38个面、35个乡镇名称；无无效几何。研究范围不是官方二道绿隔规划范围的替代件。
2. CLCD：使用Zenodo记录8176941（版本1.0.2）的2020年文件。原始文件名CLCD_v01_2020_albert.tif中的v01不表示引用了版本1.0.1。已有原生30m等积背景窗口可立即计算；下载完整全国COG后再核对窗口像元一致性。参照文献应指向8176941，并保留Yang和Huang的数据论文。
3. WorldCover：已取得ESA官方2020 v100的N39E114、N39E117两幅完整原始GeoTIFF；两幅完整覆盖CLCD背景。比较时应重分类并一次性汇总至同一CLCD30m网格；不能拿WorldCover作独立真值。
4. 道路：已复制Geofabrik china-200101-free.shp.zip解出的全部原始道路成员（含校验记录），为2020年1月1日快照，不是年末道路，不代表每条路的实际建成年份。ODbL署名保留。原始成员没有做研究区裁剪或主路筛选。
5. NASADEM：补齐六幅完整原生COG，39/40N×115/116/117E，覆盖CLCD整个背景。数据主要对应2000年SRTM观测，经NASADEM重新处理，不能标成2020年实测高程。
6. Landsat：严格沿用已有2020年6月16日、8月3日、8月10日三景，不增加日期。原生ST_B10、QA_PIXEL、QA_RADSAT、MTL已归档；补下同景ST_QA温度不确定性层。8月3日主景在研究区内基本全覆盖；其余两景有云或仅覆盖部分研究区。温度DN换算为K=DN×0.00341802+149，摄氏度再减273.15；值来自原始元数据，不是估计值。质量统计仅为数据覆盖盘点，不是生态韧性结论。
7. VIIRS：本地未找到2020年EOG年度原始辐亮度和cf_cvg。EOG当前官方下载跳转免费账户认证。已保存官方产品介绍及注册说明，未绕过登录；已发现的公开衍生库均缺有效观测覆盖或经过外推、重采样，未纳入。该缺口必须补齐，不能以建设面积或其他夜光产品静默替代。
8. ArcGIS Desktop10.8导入和Spatial扩展可用性实测通过；QGIS3.28.2、ArcGIS Pro3.1.6、Excel2024可查。FRAGSTATS与InVEST先前未检出安装，其他代理正在准备官方软件，具体能否计算以其运行回执为准。

所有原始来源、路径、SHA256、坐标系和分辨率见本目录JSON/CSV。原始窗口明确标为原生无损下载子集；没有把重投影层、历史计算结果当作原始输入。
''',encoding='utf-8')
print(json.dumps({'status':receipt['status'],'rasters':len(records),'coverage':coverage},ensure_ascii=False))
