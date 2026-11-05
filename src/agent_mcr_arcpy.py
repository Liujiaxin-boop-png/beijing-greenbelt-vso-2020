# -*- coding: utf-8 -*-
"""Exact Esri Spatial Analyst leave-parent-out MCR.

Run using C:\Python27\ArcGIS10.8\python.exe with a UTF-8 JSON configuration.
Required config keys: parent_raster, source_parent_raster, cost_raster, out_dir.
The three rasters must share projected grid geometry. Parent IDs are positive;
non-habitat and non-source cells MUST be NoData, never a valid zero source.
Every core source cell stores its complete original habitat ParentPatchID.
No source thresholds/resistance values are selected by this module.

Outputs retain cellwise cost and patch-minimum cost separately. The minimum
over a complete parent patch is calculated on the full modeling background,
not on each clipped evaluation grid. Identical-parent source cores are excluded
as destinations, but their cells remain traversable on the resistance surface.
"""
from __future__ import print_function
import os
import sys
import json
import time
import traceback
import math
import heapq

try:
    unicode
except NameError:
    unicode = str


def _arcpy():
    # ArcMap's legacy standalone licence initialization precedes import arcpy.
    # ArcGIS Pro has no arcinfo module; its licensed environment initializes it.
    if sys.version_info[0] == 2:
        import arcinfo
    import arcpy
    return arcpy


def _upath(v):
    if isinstance(v,unicode):
        return v
    return v.decode(sys.getfilesystemencoding())


def _dump(path, obj):
    with open(path,'wb') as out:
        out.write(json.dumps(obj,ensure_ascii=False,indent=2).encode('utf-8'))


def run(config):
    import numpy as np
    arcpy = _arcpy()
    from arcpy.sa import CostDistance, CostAllocation, EucDistance, SetNull
    print('RUN_ARCPY_IMPORTED');sys.stdout.flush()
    outdir=os.path.abspath(_upath(config['out_dir']))
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    print('RUN_CHECKOUT_SPATIAL');sys.stdout.flush()
    checkout=arcpy.CheckOutExtension('Spatial')
    print('RUN_CHECKOUT_RESULT',checkout);sys.stdout.flush()
    if checkout not in ('CheckedOut', 'AlreadyInitialized'):
        raise RuntimeError('Spatial Analyst checkout failed: ' + str(checkout))
    print('RUN_SET_ENVIRONMENT');sys.stdout.flush()
    arcpy.env.overwriteOutput=False
    arcpy.env.parallelProcessingFactor='0'
    arcpy.env.workspace=outdir
    arcpy.env.scratchWorkspace=outdir
    cost=os.path.abspath(_upath(config['cost_raster']))
    source=os.path.abspath(_upath(config['source_parent_raster']))
    parent=os.path.abspath(_upath(config['parent_raster']))
    print('RUN_DESCRIBE_COST');sys.stdout.flush()
    meta=arcpy.Describe(cost)
    arcpy.env.snapRaster=cost
    arcpy.env.cellSize=cost
    arcpy.env.extent=meta.extent
    arcpy.env.outputCoordinateSystem=meta.spatialReference
    assert meta.spatialReference.type=='Projected'
    def geometry(path):
        d=arcpy.Describe(path)
        r=arcpy.Raster(path)
        return (r.height,r.width,r.meanCellHeight,r.meanCellWidth,d.extent.XMin,d.extent.YMin,
                d.extent.XMax,d.extent.YMax,d.spatialReference.exportToString())
    print('RUN_VERIFY_GRID_GEOMETRY');sys.stdout.flush()
    gm=geometry(cost)
    assert geometry(source)==gm and geometry(parent)==gm,'Input grid geometry differs'
    print('RUN_READ_INPUT_ARRAYS');sys.stdout.flush()
    p=arcpy.RasterToNumPyArray(parent,nodata_to_value=0).astype(np.int32)
    src=arcpy.RasterToNumPyArray(source,nodata_to_value=0).astype(np.int32)
    c=arcpy.RasterToNumPyArray(cost,nodata_to_value=-9999)
    assert not np.any((c!=-9999)&(c<=0)),'Cost must be strictly positive'
    assert np.all(p[src>0]==src[src>0]),'Source IDs must equal full ParentPatchID'
    parents=np.unique(p[p>0])
    source_ids=np.unique(src[src>0])
    install=arcpy.GetInstallInfo()
    report={'status':'RUNNING','engine':install.get('ProductName','ArcGIS')+' '+install.get('Version','unknown')+' Spatial Analyst CostDistance/CostAllocation',
            'install':arcpy.GetInstallInfo(),'started':time.time(),'synthetic_only':config.get('synthetic_only',False),
            'grid_shape':list(p.shape),'source_parent_ids':source_ids.tolist(),'target_parent_count':len(parents),
            'config':config,'runs':[],'destination_same_parent_count':None,
            'patch_aggregation':'minimum cost over all cells of complete original ParentPatchID',
            'euclidean_comparison':'shortest planar distance from chosen patch-minimum origin cell to its chosen destination core'}
    _dump(os.path.join(outdir,'mcr_run_receipt.json'),report)
    nodata=-9999.0
    best=np.full(p.shape,nodata,dtype=np.float32)
    alloc=np.full(p.shape,0,dtype=np.int32)
    arcpy.env.compression='LZW'
    def save_arr(arr,name,nodata_value):
        path=os.path.join(outdir,name)
        arcpy.NumPyArrayToRaster(arr,arcpy.Point(meta.extent.XMin,meta.extent.YMin),gm[3],gm[2],nodata_value).save(path)
        arcpy.DefineProjection_management(path,meta.spatialReference)
        return path
    def native_run(label, source_input, target_mask):
        t=time.time()
        cd_path=os.path.join(outdir,'cd_'+label+'.tif')
        ca_path=os.path.join(outdir,'ca_'+label+'.tif')
        # Use CostDistance itself as specified in the approved proposal.
        print('RUN_COST_DISTANCE',label);sys.stdout.flush()
        cd=CostDistance(source_input,cost)
        print('RUN_SAVE_COST_DISTANCE',label);sys.stdout.flush()
        cd.save(cd_path)
        print('RUN_COST_ALLOCATION',label);sys.stdout.flush()
        ca=CostAllocation(source_input,cost)
        ca.save(ca_path)
        da=arcpy.RasterToNumPyArray(cd_path,nodata_to_value=nodata)
        aa=arcpy.RasterToNumPyArray(ca_path,nodata_to_value=0)
        assert da.shape==p.shape and aa.shape==p.shape
        best[target_mask]=da[target_mask]
        alloc[target_mask]=aa[target_mask]
        report['runs'].append({'label':label,'seconds':time.time()-t,'target_cells':int(np.sum(target_mask)),
                               'distance_path':cd_path,'allocation_path':ca_path})
        _dump(os.path.join(outdir,'mcr_run_receipt.json'),report)
    if len(source_ids):
        native_run('all',source,p>0)
    for sid in source_ids:
        target=p==sid
        if len(source_ids)<2:
            best[target]=nodata
            alloc[target]=0
            continue
        exclude=os.path.join(outdir,'source_exclude_'+str(int(sid))+'.tif')
        SetNull(arcpy.Raster(source)==int(sid),arcpy.Raster(source)).save(exclude)
        native_run('exclude_'+str(int(sid)),exclude,target)
    valid=(p>0)&(best!=nodata)&(alloc>0)
    bad=valid&(alloc==p)
    report['destination_same_parent_count']=int(np.sum(bad))
    assert not np.any(bad),'Same-parent destinations remain'
    save_arr(best,'mcr_pixel_cost.tif',nodata)
    save_arr(alloc,'mcr_pixel_destination_parent.tif',0)
    pmin=np.full(p.shape,nodata,dtype=np.float32)
    pdest=np.zeros(p.shape,dtype=np.int32)
    pgeom=np.full(p.shape,nodata,dtype=np.float32)
    records=[]
    for pid in parents:
        ii=np.flatnonzero((p==pid)&valid)
        if not len(ii):
            records.append({'parent_id':int(pid),'status':'NO_OTHER_REACHABLE_SAME_TYPE_SOURCE'})
            continue
        # A deterministic row-major tie break keeps audits/reruns consistent.
        k=int(ii[np.argmin(best.ravel()[ii])])
        row,col=np.unravel_index(k,p.shape)
        val=float(best[row,col]); sid=int(alloc[row,col])
        mask=p==pid
        pmin[mask]=val; pdest[mask]=sid
        records.append({'parent_id':int(pid),'status':'VALID','cost':val,'destination_parent_id':sid,
                        'origin_row':int(row),'origin_col':int(col),'habitat_cells':int(np.sum(mask))})
    # Geometry is for the selected MCR destination, not a potentially different
    # globally nearest Euclidean destination.
    for sid in sorted(set(r['destination_parent_id'] for r in records if r['status']=='VALID')):
        only=os.path.join(outdir,'source_only_'+str(sid)+'.tif')
        SetNull(arcpy.Raster(source)!=sid,arcpy.Raster(source)).save(only)
        ed_path=os.path.join(outdir,'euc_to_'+str(sid)+'.tif')
        EucDistance(only).save(ed_path)
        ed=arcpy.RasterToNumPyArray(ed_path,nodata_to_value=nodata)
        for r in records:
            if r.get('destination_parent_id')==sid:
                r['euclidean_m']=float(ed[r['origin_row'],r['origin_col']])
                pgeom[p==r['parent_id']]=r['euclidean_m']
    paths={'pixel_cost':os.path.join(outdir,'mcr_pixel_cost.tif'),
           'pixel_destination':os.path.join(outdir,'mcr_pixel_destination_parent.tif'),
           'patch_minimum_cost':save_arr(pmin,'mcr_patch_min_cost.tif',nodata),
           'patch_destination':save_arr(pdest,'mcr_patch_destination_parent.tif',0),
           'patch_euclidean_m':save_arr(pgeom,'mcr_patch_euclidean_m.tif',nodata)}
    _dump(os.path.join(outdir,'mcr_patch_records.json'),records)
    report.update(status='COMPLETE',elapsed_seconds=time.time()-report['started'],outputs=paths,
                  valid_parent_count=sum(r['status']=='VALID' for r in records),
                  nodata_parent_count=sum(r['status']!='VALID' for r in records))
    _dump(os.path.join(outdir,'mcr_run_receipt.json'),report)
    arcpy.CheckInExtension('Spatial')
    return report


def _dijkstra(cost, source_mask):
    """Independent small-array 8-neighbour graph reference for synthetic QA."""
    import numpy as np
    rows,cols=cost.shape
    out=np.full(cost.shape,np.inf)
    todo=[]
    for row,col in zip(*np.where(source_mask)):
        out[row,col]=0.0;heapq.heappush(todo,(0.0,int(row),int(col)))
    while todo:
        dist,row,col=heapq.heappop(todo)
        if dist!=out[row,col]:continue
        for dr,dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            rr,cc=row+dr,col+dc
            if not (0<=rr<rows and 0<=cc<cols) or cost[rr,cc]<=0:continue
            new=dist+30.0*math.sqrt(dr*dr+dc*dc)*0.5*(cost[row,col]+cost[rr,cc])
            if new<out[rr,cc]:out[rr,cc]=new;heapq.heappush(todo,(new,rr,cc))
    return out


def synthetic_check(root):
    import numpy as np
    print('SYNTHETIC_IMPORT_ARCPY');sys.stdout.flush()
    arcpy = _arcpy()
    print('SYNTHETIC_ARCPY_IMPORTED');sys.stdout.flush()
    out=os.path.join(os.path.abspath(root),'synthetic_mcr')
    if not os.path.isdir(out):os.makedirs(out)
    p=np.zeros((9,11),dtype=np.int32)
    p[1:4,1:4]=10;p[5:8,8:10]=20;p[6:8,1:3]=30
    s=np.zeros_like(p);s[2,2]=10;s[6,9]=20
    c=np.ones_like(p,dtype=np.float32);c[1:8,5]=10
    sr=arcpy.SpatialReference(32650)
    print('SYNTHETIC_SPATIAL_REF_CREATED');sys.stdout.flush()
    conf={'out_dir':os.path.join(out,'run'),'synthetic_only':True}
    for arr,key,filename,nd in [(p,'parent_raster','parent.tif',0),(s,'source_parent_raster','source.tif',0),(c,'cost_raster','cost.tif',-9999)]:
        path=os.path.join(out,filename)
        print('SYNTHETIC_CREATE_ARRAY_RASTER',filename);sys.stdout.flush()
        rr=arcpy.NumPyArrayToRaster(arr,arcpy.Point(500000,4400000),30,30,nd)
        print('SYNTHETIC_SAVE_ARRAY_RASTER',filename);sys.stdout.flush()
        rr.save(path)
        print('SYNTHETIC_PROJECT_ARRAY_RASTER',filename);sys.stdout.flush()
        arcpy.DefineProjection_management(path,sr);conf[key]=path
    _dump(os.path.join(out,'synthetic_config.json'),conf)
    actual=run(conf)
    costs=arcpy.RasterToNumPyArray(actual['outputs']['pixel_cost'],nodata_to_value=-9999)
    per_parent=[]
    for pid in [10,20,30]:
        expected=_dijkstra(c,(s>0)&(s!=pid))
        diff=np.abs(costs[p==pid]-expected[p==pid])
        error=float(np.max(diff))
        assert error<0.001,'Native cost disagrees with independent eight-neighbour graph'
        per_parent.append({'parent':pid,'cells':int(np.sum(p==pid)),'maximum_absolute_error':error})
    qa={'status':'PASS_SYNTHETIC_NATIVE_ESRI_VS_DIJKSTRA','engine':actual['engine'],'per_parent':per_parent,
        'cost_surface':'all=1 except interior barrier column=10','cell_size_m':30,
        'source_parents':[10,20],'nonsource_target_parent':30,'not_research_observations':True}
    _dump(os.path.join(out,'synthetic_validation.json'),qa)
    print(json.dumps(qa))


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--synthetic':
        synthetic_check(_upath(sys.argv[2]))
    else:
        with open(_upath(sys.argv[1]),'rb') as f:
            conf=json.loads(f.read().decode('utf-8-sig'))
        try:
            result=run(conf)
            print(json.dumps({'status':result['status'],'elapsed_seconds':result['elapsed_seconds']}))
        except BaseException:
            _dump(os.path.join(conf['out_dir'],'mcr_failure.json'),{'traceback':traceback.format_exc()})
            raise
