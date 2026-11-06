"""Generate the local project manifest from retained evidence, without inventing status.

JSON syntax is also valid YAML. Data remain in the four user-requested folders;
this generator and the manifest schema are separate from numerical execution.
"""
from pathlib import Path
import datetime,hashlib,json

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件'

def read(p):
    q=ROOT/p
    return json.loads(q.read_text(encoding='utf8')) if q.exists() else None

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')

def main():
    now=datetime.datetime.now(datetime.timezone.utc)
    stamp=now.strftime('%Y%m%dT%H%M%SZ')
    audit=read('02_过程文件/数据审计/219_data_audit_final.json')
    rasters=audit['rasters']
    source_defs=[
      ('clcd','CLCD2020','authoritative_input','Yang and Huang','CLCD 2020, Zenodo 8176941 v1.0.2','https://zenodo.org/records/8176941','CLCD_2020_v1.0.2','Primary land-cover labels; full distributed file and verified lossless native window.'),
      ('worldcover','WorldCover2020官方整幅','authoritative_input','ESA WorldCover','WorldCover 2020 v100','https://esa-worldcover.org/en/data-access','2020_v100_N39E114_N39E117','Predeclared classification-product sensitivity; not a ground-truth accuracy reference.'),
      ('nasadem','NASADEM完整瓦片','context','NASA/USGS','NASADEM HGT 1 arc-second','https://lpdaac.usgs.gov/products/nasadem_hgtv001/','NASADEM_HGT.001','Archived terrain context only; not one of the six scored indicators.'),
      ('landsat','Landsat8','context','USGS','Landsat 8 Collection 2 Level-2','https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature','LC08_C02_L2_20200616_20200803_20200810','Native ST, QA and metadata for grey-green/thermal association only.')]
    sources={}
    for sid,group,role,provider,dataset,url,version,why in source_defs:
        files=[{k:r[k] for k in ('file','bytes','sha256','crs','shape','resolution','nodata')} for r in rasters if group in r['group']]
        sources[sid]={'role':role,'provider':provider,'dataset':dataset,'source_url':url,
          'version':{'identifier':version},'access':{'method':'http(s) and verified retained local inputs','audit_record':'02_过程文件/数据审计/219_data_audit_final.json','files':files},
          'rationale':why,'license':{'status':'See original provider metadata retained in 01_原始数据/来源记录; no raw raster redistribution in Git.'}}
    sources['scope']={'role':'authoritative_input','provider':'User-supplied previous study','dataset':'研究范围0328.shp and companion files','version':{'identifier':'frozen_supplied_0328_geometry'},'access':{'method':'local','path':'01_原始数据/研究范围','audit_record':'02_过程文件/数据审计/219_boundary_readback.json'},'rationale':'Approved research footprint: 38 polygons, portions of 35 townships, not the official whole greenbelt boundary.'}
    sources['roads']={'role':'authoritative_input','provider':'OpenStreetMap contributors','dataset':'2020-01-01 China snapshot road members','source_url':'https://www.openstreetmap.org/copyright','version':{'identifier':'2020-01-01'},'access':{'method':'local retained snapshot','path':'01_原始数据/OSM2020原始道路成员','audit_record':'02_过程文件/数据审计/219_existing_inputs_inventory.json'},'selection':{'filter':'motorway,trunk,primary,motorway_link,trunk_link,primary_link'},'license':{'name':'Open Database License','url':'https://www.openstreetmap.org/copyright'},'rationale':'Dated major-road pressure input; not present-day OSM.'}
    ntl=read('02_过程文件/aggregation/ntl_aggregation_receipt.json')
    sources['ntl']={'role':'authoritative_input','provider':'Earth Observation Group','dataset':'VIIRS annual VNL v2.1 2020 average_masked and original cf_cvg','source_url':'https://eogdata.mines.edu/nighttime_light/annual/v21/2020/','version':{'identifier':'VNL_v21_npp_2020_global_vcmslcfg_c202205302300'},'access':{'method':'official authenticated website download','status':(ntl or {}).get('status','MISSING'),'audit_record':'02_过程文件/aggregation/ntl_aggregation_receipt.json'},'rationale':'Approved independent night-activity pressure; missing brightness is never replaced with zeros, proxies or a different release.'}
    original_ntl=read('01_原始数据/EOG2020官方原件/来源与完整性核验.json')
    if original_ntl:
        originals=[]
        for record in original_ntl['files']:
            stem=Path(record['download_file']).name[:-3]
            for kind,suffix in [('gzip','.gz'),('tif','')]:
                originals.append({'file':'01_原始数据/EOG2020官方原件/'+stem+suffix,'bytes':record[kind+'_bytes'],'sha256':record[kind+'_sha256'],'source_url':record['source_url']})
        sources['ntl']['access']['files']=originals
        sources['ntl']['access']['independent_qa']='02_过程文件/aggregation/ntl_independent_QA.json'
        sources['ntl']['access']['original_manifest']='01_原始数据/EOG2020官方原件/来源与完整性核验.json'
    queue=read('02_过程文件/mcr_queue/queue_checkpoint.json') or {}
    status_files={
      'hq':'02_过程文件/hq/native_hq_execution.json',
      'mcr_queue':'02_过程文件/mcr_queue/queue_checkpoint.json',
      'mcr_finalization':'02_过程文件/mcr_queue/finalization_status.json',
      'ntl':'02_过程文件/aggregation/ntl_aggregation_receipt.json',
      'arithmetic':'02_过程文件/evaluation/arithmetic_validation.json',
      'context_projects':'02_过程文件/map_inputs/context_project_native_QA.json',
      'scientific':'02_过程文件/evaluation/final_scientific_QA.json',
      'result_maps':'02_过程文件/map_results/visual_QA.json',
      'word':'02_过程文件/manuscript/final_delivery_QA.json',
      'delivery':'02_过程文件/delivery/final_delivery_receipt.json'}
    evidence={key:{'path':p,'exists':(ROOT/p).exists(),'sha256':digest(ROOT/p) if (ROOT/p).exists() else None} for key,p in status_files.items()}
    inputs_hash=hashlib.sha256(json.dumps({k:v['access'] for k,v in sources.items()},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    outputs_hash=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest()
    report={'run_id':'manifest-'+stamp,'status':'warning','type':'partial_execution_inventory_not_scientific_completion','mcr_completed':queue.get('completed_count',0),'mcr_expected':15,'ntl_status':(ntl or {}).get('status','MISSING'),'evidence':evidence,'inputs_hash':inputs_hash,'outputs_hash':outputs_hash,'note':'Hashes describe the retained source inventory and checkpoint evidence at this instant. Ongoing outputs can change. Composite results and manuscript are not certified by this manifest.'}
    report_path='02_过程文件/project_audit/manifest-'+stamp+'.json'
    dump(ROOT/report_path,report)
    manifest={'schema':'openmapstack-project/v1',
      'project':{'id':'beijing-greenbelt-vso-2020','title':'北京二道绿隔及周边地区2020年生态韧性评价','question':'Apply the approved six-indicator VSO proposal to ecological resilience assessment and township maintenance diagnosis.','created_at':datetime.datetime.fromtimestamp(1793912390,datetime.timezone.utc).isoformat(),'updated_at':now.isoformat(),'status':'in_progress'},
      'interpretation':{'objective':'Produce traceable data, native editable GIS figures, code and a Chinese manuscript without changing the approved framework.','assumptions':[{'id':'support','statement':'Full 1000 m squares supply metric context; reporting uses exact scope/town intersections.','rationale':'The frozen proposal uses square landscape units and separate township interpretation.'},{'id':'missing','statement':'All six indicators must be defined within each habitat before aggregation.','rationale':'No imputation or five-indicator substitution is authorized.'},{'id':'software','statement':'ArcGIS Pro 3.1.6 executes the same native Euclidean Distance, Cost Distance and Cost Allocation algorithms because local ArcMap 10.8 could not initialize.','rationale':'Actual native engine is recorded; no claim of successful ArcMap execution.'}]},
      'sources':sources,'overrides':[{'policy':'No changes to supplied scope geometry; approved class mapping and published parameter adaptations are explicit config inputs.','files':['05_代码/config/approved_protocol.json','05_代码/config/hq_sensitivity.csv','05_代码/config/mcr_parameters.json']}],
      'processing':{'analysis_crs':'WGS84 Albers Equal Area, lon0=105, lat0=0, lat1=25, lat2=47, metres','storage_crs':'Native archived inputs; aligned 30 m analysis rasters; original NTL/Landsat pixel footprints for aggregation','steps':[{'id':s,'entrypoint':'05_代码/pipeline.py --stage '+s} for s in ['spatial','hq','euclidean','clumpy','mspa','mcr','ntl','aggregate','arithmetic_qa','evaluate','context_maps']]},
      'outputs':{'raw':'01_原始数据','intermediate':'02_过程文件','results':'03_结果文件','figures':'04_图件','code':'05_代码','status':'Partial computation; inspect per-stage receipts before using any output.'},
      'validation':{'required':['original source hashes','native software readback','per-indicator numerical QA','paired support accounting','all six actual indicators','final visual and numeric manuscript QA'],'domain_checks':['No target habitat is not zero resilience.','No other same-parent-excluded source is undefined MCR.','Cloud/no-observation values are not zero.','Township areas overlap slightly and must not be summed for regional totals.','Product disagreement is not accuracy.','Thermal association is not independent whole-index validation.']},
      'presentation':{'native_projects':['04_图件/生态韧性2020_可编辑地图.qgz','04_图件/技术路线_可编辑布局.qgz'],'palette':'05_代码/config/palette.json','reporting':'Chinese manuscript and editable local GIS layouts; no additional web dashboard requested.'},
      'runtime':{'implementation':{'pipeline':'05_代码/pipeline.py'},'software':['ArcGIS Pro 3.1.6 Spatial Analyst','InVEST 3.20.2','FRAGSTATS 4.2.1.612','JRC MSPA 2.4','QGIS 3.28.2','Python 3.12']},
      'runs':{'latest':{'id':report['run_id'],'started_at':now.isoformat(),'completed_at':now.isoformat(),'status':'warning','inputs_hash':inputs_hash,'outputs_hash':outputs_hash,'validation_report':report_path}}}
    final=read(status_files['delivery']) or {}
    finished=final.get('status')=='PASS_FINAL_DELIVERY'
    manifest['project']['status']='complete' if finished else 'in_progress'
    manifest['outputs']['status']='Verified local manuscript, scientific outputs, editable figures and published code.' if finished else 'Inspect current stage receipts; final delivery is not yet certified.'
    manifest['processing']['steps']=[{'id':s,'entrypoint':'05_代码/pipeline.py --stage '+s} for s in ['spatial','hq','euclidean','clumpy','mspa','mcr','ntl','aggregate','arithmetic_qa','evaluate','final_qa','context_maps','result_maps','thermal','thermal_figure']]
    manifest['presentation']['native_projects']=[str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'04_图件').glob('*.qgz')]
    manifest['runtime']['software'].append('jenkspy 0.4.1 exact Fisher-Jenks classification')
    manifest['sources']['roads']['source_url']='https://download.geofabrik.de/asia/china-200101-free.shp.zip'
    manifest['sources']['roads']['version']['precision']='Archive filename date; exact snapshot UTC cutoff unavailable.'
    manifest['runs']['latest']['status']='success' if finished else 'warning'
    report['status']='success' if finished else 'warning'
    report['type']='verified_final_delivery_inventory' if finished else 'current_execution_inventory'
    report['note']='Completion requires the independently retained final delivery receipt; this source manifest does not assert ecological process validation or publication acceptance.'
    dump(ROOT/report_path,report)
    dump(ROOT/'project.yaml',manifest)
    print(json.dumps({'manifest':str(ROOT/'project.yaml'),'status':'COMPLETE' if finished else 'IN_PROGRESS','mcr_completed':report['mcr_completed'],'ntl':report['ntl_status']},ensure_ascii=False))

if __name__=='__main__':main()
