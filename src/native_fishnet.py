# -*- coding: utf-8 -*-
"""ArcGIS Desktop 10.8 native projected fishnet; no analysis values fabricated."""
from __future__ import print_function
import os,sys,json,datetime,traceback
CONFIG=sys.argv[1] if len(sys.argv)>1 else r'D:\ER219_work\spatial\native_config.json'
cfg=json.loads(open(CONFIG,'rb').read().decode('utf-8'))
P=cfg['native_work']
def dump(name,value):
    with open(os.path.join(P,name),'wb') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2).encode('utf8'))
def log(stage):
    print(stage);sys.stdout.flush();dump('native_stage.json',{'stage':stage,'pid':os.getpid(),'utc':datetime.datetime.utcnow().isoformat()+'Z'})
log('import_arcpy')
import arcpy
arcpy.env.overwriteOutput=False
gdb=cfg['native_gdb'];sr=arcpy.Describe(cfg['raster_native']).spatialReference
log('create_gdb')
if not arcpy.Exists(gdb):arcpy.CreateFileGDB_management(P,'analysis.gdb')
arcpy.env.workspace=gdb;arcpy.env.scratchWorkspace=gdb;arcpy.env.outputCoordinateSystem=sr
scope=os.path.join(gdb,'scope_parts')
if not arcpy.Exists(scope):arcpy.Project_management(cfg['scope_source'],scope,sr)
towns=os.path.join(gdb,'towns')
if not arcpy.Exists(towns):arcpy.Dissolve_management(scope,towns,'Name')
union=os.path.join(gdb,'study_scope')
if not arcpy.Exists(union):arcpy.Dissolve_management(towns,union)
x0,y0=cfg['origin_xy'];x1,y1=cfg['corner_xy'];reports=[]
for scale in cfg['scales_m']:
    log('fishnet_'+str(scale))
    fish=os.path.join(gdb,'square_all_'+str(scale))
    if not arcpy.Exists(fish):
        arcpy.CreateFishnet_management(fish,'%s %s'%(x0,y0),'%s %s'%(x0,y0+scale),scale,scale,0,0,'%s %s'%(x1,y1),'NO_LABELS','#','POLYGON')
        arcpy.AddField_management(fish,'Grid_ID','TEXT',field_length=40)
        arcpy.AddField_management(fish,'Scale_m','LONG')
        with arcpy.da.UpdateCursor(fish,['SHAPE@XY','Grid_ID','Scale_m']) as cursor:
            for row in cursor:
                xx,yy=row[0];ix=int(round((xx-x0)/scale-.5));iy=int(round((yy-y0)/scale-.5))
                row[1]='G%s_%s_%s'%(scale,ix,iy);row[2]=scale;cursor.updateRow(row)
    layer='fl_%s'%scale;arcpy.MakeFeatureLayer_management(fish,layer)
    arcpy.SelectLayerByLocation_management(layer,'INTERSECT',union)
    selected=os.path.join(gdb,'grid_'+str(scale))
    if not arcpy.Exists(selected):arcpy.CopyFeatures_management(layer,selected)
    pieces=os.path.join(gdb,'town_grid_'+str(scale))
    if not arcpy.Exists(pieces):arcpy.Intersect_analysis([selected,towns],pieces,'ALL','#','INPUT')
    reports.append({'scale_m':scale,'grid_count':int(arcpy.GetCount_management(selected).getOutput(0)),
        'town_pieces':int(arcpy.GetCount_management(pieces).getOutput(0)),
        'geometry_area_m2':sum(x[0] for x in arcpy.da.SearchCursor(selected,['SHAPE@AREA']))})
    arcpy.Delete_management(layer)
dump('native_fishnet_receipt.json',{'status':'NATIVE_FISHNET_CREATED','engine':arcpy.GetInstallInfo(),'grids':reports,'spatial_reference':sr.exportToString()})
log('completed')
