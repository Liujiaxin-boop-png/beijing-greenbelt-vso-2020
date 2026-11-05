"""Native FRAGSTATS CLUMPY for existing 1 km / 500 m complete square grids.

Inputs are common 30 m projected CLCD/WorldCover rasters and original native
fishnet bounds exported read-only from the project geodatabase. Whole-square
context is preserved. No town clipping, no resampling, no filling of N/A.
"""
from pathlib import Path
import csv
import json
import math
import sys
import time
from collections import Counter
import numpy as np
import rasterio
from agent_fragstats_clumpy import run_ascii_grids, sha256

def window_by_centres(bounds, transform, shape):
    xmin,ymin,xmax,ymax=bounds
    assert transform.a==30 and transform.e==-30 and transform.b==0 and transform.d==0
    c0=math.ceil((xmin-transform.c)/30-.5)
    c1=math.ceil((xmax-transform.c)/30-.5)
    r0=math.ceil((transform.f-ymax)/30-.5)
    r1=math.ceil((transform.f-ymin)/30-.5)
    assert 0<=r0<r1<=shape[0] and 0<=c0<c1<=shape[1], 'Fishnet exceeds full raster background'
    return r0,r1,c0,c1

def main(config_path,process_root,result_root):
    cfg=json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    work=Path(process_root);result=Path(result_root)
    result.mkdir(parents=True,exist_ok=True)
    spatial=Path(cfg['native_work'])
    products={'CLCD':spatial/'clcd2020.tif','WorldCover':spatial/'worldcover2020_common30m.tif'}
    focal={2:'forest_shrub',4:'grass',5:'water_wetland'}
    overall=[]
    for product,raster in products.items():
        with rasterio.open(raster) as src:
            land=src.read(1)
            affine=src.transform
            crs=src.crs.to_wkt()
            nodata=src.nodata
        known=np.isin(land,[1,2,3,4,5,6,7,8,9])
        # Combining types changes their class label only; every other valid
        # land-cover class remains a landscape class, not background/NoData.
        land=land.astype(np.int16)
        land[land==3]=2;land[land==9]=5
        land[~known]=9999
        for scale in cfg['scales_m']:
            t=time.time()
            unit_dir=work/(product.lower()+'_'+str(scale))
            unit_dir.mkdir(parents=True,exist_ok=True)
            bounds_path=work/('grid_bounds_'+str(scale)+'.csv')
            with bounds_path.open(encoding='utf-8-sig',newline='') as f:
                units=list(csv.DictReader(f))
            output=[];batch_receipts=[]
            for offset in range(0,len(units),256):
                group=units[offset:offset+256]
                grids={};meta={}
                for row in group:
                    gid=row['Grid_ID']
                    bb=tuple(float(row[k]) for k in ('xmin','ymin','xmax','ymax'))
                    r0,r1,c0,c1=window_by_centres(bb,affine,land.shape)
                    arr=land[r0:r1,c0:c1]
                    counts=Counter(arr.ravel().tolist())
                    grids[gid]=arr
                    meta[gid]={'Grid_ID':gid,'OBJECTID':int(row['OBJECTID']),'scale_m':scale,
                               'product':product,'row_start':r0,'row_stop':r1,
                               'col_start':c0,'col_stop':c1,'window_rows':r1-r0,
                               'window_cols':c1-c0,'total_window_pixels':arr.size,
                               'valid_support_pixels':int(arr.size-counts[9999]),
                               'nodata_pixels':counts[9999],
                               'square_area_m2':float(row['area_m2']),
                               'pixel_support_area_m2':int(arr.size-counts[9999])*900,
                               '_counts':counts}
                batch_path=unit_dir/('batch_'+str(offset//256).zfill(3))
                native=run_ascii_grids(grids,batch_path,cell_size=30.0,neighborhood=8,timeout=180)
                lookup={(row['LID'].removesuffix('.asc'),int(row['TYPE'].removeprefix('cls_'))):row for row in native['rows']}
                for gid,m in meta.items():
                    counts=m.pop('_counts')
                    for code,typ in focal.items():
                        native_row=lookup.get((gid,code))
                        value=None
                        if not counts[code]:reason='ABSENT_FOCAL_HABITAT'
                        elif native_row is None:raise RuntimeError('Positive focal class missing from native output '+gid)
                        elif native_row['CLUMPY']=='N/A':
                            if counts[code]==m['valid_support_pixels']:reason='ONLY_FOCAL_CLASS_FRAGSTATS_NA'
                            elif counts[code]==1:reason='SINGLE_FOCAL_PIXEL_FRAGSTATS_NA'
                            else:reason='FRAGSTATS_UNDEFINED'
                        else:
                            value=float(native_row['CLUMPY']);reason='VALID'
                            assert -1.00001<=value<=1.00001
                        output.append(dict(m,habitat_type=typ,habitat_class=code,
                            habitat_pixels=counts[code],habitat_area_m2=counts[code]*900,
                            habitat_fraction=counts[code]/m['valid_support_pixels'] if m['valid_support_pixels'] else None,
                            CLUMPY=value,status=reason,
                            native_CA_ha=float(native_row['CA']) if native_row else None,
                            native_PLAND_pct=float(native_row['PLAND']) if native_row else None,
                            native_NP=int(float(native_row['NP'])) if native_row else None))
                        if native_row:
                            assert abs(float(native_row['CA'])-counts[code]*.09)<.000051
                batch_receipts.append(str(batch_path/'run_receipt.json'))
                print(product,scale,'completed',min(offset+256,len(units)),'/',len(units),flush=True)
            dest=result/('clumpy_'+product.lower()+'_'+str(scale)+'.csv')
            with dest.open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(output[0]));writer.writeheader();writer.writerows(output)
            receipt={'status':'COMPLETE_NATIVE_FRAGSTATS','product':product,'scale_m':scale,
                     'engine':'FRAGSTATS v4.2.1.612','grid_count':len(units),'record_count':len(output),
                     'raster':str(raster),'raster_sha256':sha256(raster),
                     'native_bounds':str(bounds_path),'native_bounds_sha256':sha256(bounds_path),
                     'result':str(dest),'result_sha256':sha256(dest),
                     'crs_wkt':crs,'source_nodata':nodata,'batch_receipts':batch_receipts,
                     'window_shapes':dict(Counter(str((r['window_rows'],r['window_cols'])) for r in output[::3])),
                     'status_counts':dict(Counter(r['status'] for r in output)),
                     'nodata_window_count':sum(r['nodata_pixels']>0 for r in output[::3]),
                     'support':'complete native square; raster cells selected by centres; no reprojection or resampling',
                     'aggregation':'none; class-specific unweighted CLUMPY retained',
                     'output_precision':'native FRAGSTATS text output four decimal places',
                     'elapsed_seconds':time.time()-t}
            (result/('clumpy_'+product.lower()+'_'+str(scale)+'_receipt.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
            overall.append(receipt)
    (result/'clumpy_batch_manifest.json').write_text(json.dumps(overall,indent=2),encoding='utf-8')
    print('ALL_FOUR_GROUPS_COMPLETE',flush=True)

if __name__=='__main__':
    main(*sys.argv[1:4])
