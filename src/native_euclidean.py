"""Native licensed Esri Euclidean Distance; normal process exit returns license."""
from pathlib import Path
import json,sys,time
import arcpy
from arcpy.sa import EucDistance

cfg=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
checkout=arcpy.CheckOutExtension('Spatial')
assert checkout in ['CheckedOut','AlreadyInitialized'],checkout
arcpy.env.overwriteOutput=False
arcpy.env.parallelProcessingFactor='0'
arcpy.env.workspace=cfg['work'];arcpy.env.scratchWorkspace=cfg['work']
arcpy.env.snapRaster=cfg['template'];arcpy.env.cellSize=cfg['template']
arcpy.env.extent=arcpy.Describe(cfg['template']).extent
arcpy.env.outputCoordinateSystem=arcpy.Describe(cfg['template']).spatialReference
arcpy.env.compression='LZW'
report={'status':'RUNNING','install':arcpy.GetInstallInfo(),'tasks':[],'license_lifecycle':'official automatic return on standalone interpreter exit'}
for task in cfg['tasks']:
    print('EUCLIDEAN '+task['name'],flush=True)
    t=time.monotonic()
    if not arcpy.Exists(task['output']):EucDistance(task['source']).save(task['output'])
    report['tasks'].append(dict(task,seconds=time.monotonic()-t))
    Path(cfg['work'],'native_euclidean_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
report['status']='NATIVE_EUCLIDEAN_COMPLETED'
Path(cfg['work'],'native_euclidean_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('COMPLETED',flush=True)
