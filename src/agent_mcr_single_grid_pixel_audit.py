"""Independent native-cell geometry audit; no production aggregation imports."""
from pathlib import Path
import json,csv,math
import rasterio
from rasterio.windows import Window
from shapely.geometry import box
ROOT=Path(__file__).resolve().parents[2]
scenario='clcd_forest_shrub_core10_land_road';gid='G1000_10_16'
queue=json.loads((ROOT/'02_过程文件/mcr_inputs/regional_queue.json').read_text(encoding='utf8'))
task=next(t for t in queue['tasks'] if t['scenario']==scenario)
cfg=json.loads(Path(task['config']).read_text(encoding='utf8'))
grid=next(g for g in json.loads((ROOT/'02_过程文件/spatial/grid_identity.json').read_text(encoding='utf8'))['grids'] if g['grid_id']==gid and g['scale_m']==1000)
extent=box(*grid['bounds']);native=ROOT/'02_过程文件/mcr_native'/scenario
with rasterio.open(cfg['parent_raster']) as source:
    aff=source.transform;inverse=~aff
    c0,r1=inverse*(grid['bounds'][0],grid['bounds'][1]);c1,r0=inverse*(grid['bounds'][2],grid['bounds'][3])
    r0,c0,r1,c1=math.floor(r0),math.floor(c0),math.ceil(r1),math.ceil(c1)
    window=Window(c0,r0,c1-c0,r1-r0);parents=source.read(1,window=window)
with rasterio.open(native/'mcr_patch_min_cost.tif') as source:cost=source.read(1,window=window);nd=source.nodata
with rasterio.open(native/'mcr_patch_destination_parent.tif') as source:dest=source.read(1,window=window)
cells=[]
for row in range(parents.shape[0]):
    for col in range(parents.shape[1]):
        if parents[row,col]<=0:continue
        x0,y0=aff*(c0+col,r0+row);x1,y1=aff*(c0+col+1,r0+row+1)
        area=box(min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1)).intersection(extent).area
        if area<=0:continue
        v=float(cost[row,col]);valid=math.isfinite(v) and v!=nd and dest[row,col]>0
        assert not valid or dest[row,col]!=parents[row,col]
        cells.append({'global_row':r0+row,'global_col':c0+col,'area_m2':area,'parent_id':int(parents[row,col]),'destination_parent_id':int(dest[row,col]),'native_patch_cost':v,'valid':bool(valid)})
ha=math.fsum(c['area_m2'] for c in cells);va=math.fsum(c['area_m2'] for c in cells if c['valid'])
mean=math.fsum(c['area_m2']*c['native_patch_cost'] for c in cells if c['valid'])/va
table=next(r for r in csv.DictReader((ROOT/'03_结果文件/indicators/mcr_by_grid.csv').open(encoding='utf-8-sig',newline='')) if r['grid_id']==gid and r['scenario']==scenario)
assert abs(float(table['habitat_m2'])-ha)<1e-6 and abs(float(table['MCR_valid_m2'])-va)<1e-6
assert abs(float(table['MCR'])-mean)<1e-8
record={'status':'PASS','grid_id':gid,'scenario':scenario,'method':'Shapely exact native-cell polygon intersection, no production window_area import','native_habitat_area_m2':ha,'native_valid_area_m2':va,'native_area_weighted_cost':mean,'cost_unit':'resistance-weighted map distance; not square metres','cells':cells,'table':table}
(ROOT/'02_过程文件/evaluation/mcr_G1000_10_16_native_pixel_QA.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(record,ensure_ascii=False))
