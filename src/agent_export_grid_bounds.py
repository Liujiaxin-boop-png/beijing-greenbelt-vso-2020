"""Read original native fishnet geometry; do not rebuild or modify it."""
import arcpy
import csv
import json
import sys
from pathlib import Path

conf=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
for scale in conf['scales_m']:
    src=str(Path(conf['native_gdb'])/('grid_'+str(scale)))
    rows=[]
    with arcpy.da.SearchCursor(src,['OID@','Grid_ID','Scale_m','SHAPE@']) as cur:
        for oid,gid,scale_m,geom in cur:
            bb=geom.extent
            rows.append({'OBJECTID':oid,'Grid_ID':gid,'Scale_m':scale_m,
                         'xmin':bb.XMin,'ymin':bb.YMin,'xmax':bb.XMax,'ymax':bb.YMax,
                         'area_m2':geom.area})
    with (out/('grid_bounds_'+str(scale)+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (out/('grid_bounds_'+str(scale)+'_receipt.json')).write_text(json.dumps({
        'source':src,'engine':arcpy.GetInstallInfo(),'record_count':len(rows),
        'original_native_geometry_read_only':True,'no_grid_regeneration':True},indent=2),encoding='utf-8')
    print('EXPORTED',scale,len(rows),flush=True)
