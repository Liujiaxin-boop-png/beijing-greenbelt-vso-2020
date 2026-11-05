# -*- coding: utf-8 -*-
"""Exact Esri Spatial Analyst leave-parent-out MCR.

Run in a licensed ArcGIS Python environment with a UTF-8 JSON configuration.
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


def _patch_minima(p, best, alloc, nodata=-9999.0):
    """Group all complete parents in one raster pass, with row-major tie break.

    Packing sparse input IDs avoids an allocation proportional to the largest
    ID. This computes the same minima as repeatedly masking each parent.
    """
    import numpy as np
    parents=np.unique(p[p>0])
    packed=(np.searchsorted(parents,p).astype(np.int32)+1)
    packed[p<=0]=0
    count=np.bincount(packed.ravel(),minlength=len(parents)+1)
    minimum=np.full(len(parents)+1,np.inf,dtype=np.float32)
    valid=(p>0)&(best!=nodata)&(alloc>0)
    np.minimum.at(minimum,packed[valid],best[valid])
    candidate=np.flatnonzero(valid&(best==minimum[packed]))
    chosen=np.full(len(parents)+1,np.iinfo(np.int64).max,dtype=np.int64)
    np.minimum.at(chosen,packed.ravel()[candidate],candidate)
    dest=np.zeros(len(parents)+1,dtype=np.int32)
    exists=np.isfinite(minimum)
    dest[exists]=alloc.ravel()[chosen[exists]]
    minimum[~exists]=nodata
    records=[]
    for idx,pid in enumerate(parents,1):
        if not exists[idx]:
            records.append({'parent_id':int(pid),'status':'NO_OTHER_REACHABLE_SAME_TYPE_SOURCE'})
            continue
        row,col=np.unravel_index(int(chosen[idx]),p.shape)
        records.append({'parent_id':int(pid),'status':'VALID','cost':float(minimum[idx]),
                        'destination_parent_id':int(dest[idx]),'origin_row':int(row),
                        'origin_col':int(col),'habitat_cells':int(count[idx])})
    return records,minimum[packed],dest[packed],packed


def _selected_destination_euclidean(src, records, cell_height, cell_width):
    """Exact planar nearest core-centre distance, not a least-cost path endpoint.

    Uses one sorted grouping of positive source cells. The KD tree only answers
    a geometric diagnostic; all cumulative costs remain native Esri outputs.
    Equal Euclidean destinations use the first row-major source cell.
    """
    import numpy as np
    from scipy.spatial import cKDTree
    source_flat=np.flatnonzero(src>0)
    order=np.argsort(src.ravel()[source_flat],kind='mergesort')
    source_flat=source_flat[order]
    source_values=src.ravel()[source_flat]
    ids,begins=np.unique(source_values,return_index=True)
    ends=np.r_[begins[1:],len(source_flat)]
    slices=dict((int(sid),(int(lo),int(hi))) for sid,lo,hi in zip(ids,begins,ends))
    grouped={}
    for r in records:
        if r['status']=='VALID':grouped.setdefault(r['destination_parent_id'],[]).append(r)
    for sid,rows in sorted(grouped.items()):
        lo,hi=slices[sid]
        flat=source_flat[lo:hi]
        rr,cc=np.unravel_index(flat,src.shape)
        coords=np.column_stack((rr*cell_height,cc*cell_width))
        query=np.array([[r['origin_row']*cell_height,r['origin_col']*cell_width] for r in rows],dtype=float)
        tree=cKDTree(coords)
        dd,ii=tree.query(query,k=2)
        for n,r in enumerate(rows):
            index=int(ii[n,0])
            if np.isfinite(dd[n,1]) and abs(dd[n,1]-dd[n,0])<=1e-9:
                candidates=np.asarray(tree.query_ball_point(query[n],float(dd[n,0])+1e-7),dtype=np.int64)
                delta=coords[candidates]-query[n]
                square=np.sum(delta*delta,axis=1)
                tied=candidates[square==square.min()]
                index=int(tied[np.argmin(flat[tied])])
            r['euclidean_m']=float(dd[n,0])
            r['nearest_euclidean_source_row']=int(rr[index])
            r['nearest_euclidean_source_col']=int(cc[index])
    return records


def run(config):
    import numpy as np
    arcpy = _arcpy()
    from arcpy.sa import CostDistance, CostAllocation, EucDistance, SetNull
    print('RUN_ARCPY_IMPORTED');sys.stdout.flush()
    outdir=os.path.abspath(_upath(config['out_dir']))
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    if os.path.exists(os.path.join(outdir,'mcr_run_receipt.json')):
        raise RuntimeError('Existing run receipt: use a fresh scenario output directory; no overwrite')
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
    assert not np.any((c!=-9999)&((c<=0)|~np.isfinite(c))),'Cost must be strictly positive and finite'
    assert np.all(p[src>0]==src[src>0]),'Source IDs must equal full ParentPatchID'
    del c
    parents=np.unique(p[p>0])
    source_ids=np.unique(src[src>0])
    strategy=config.get('source_strategy','leave_one_parent_out')
    assert strategy in ('leave_one_parent_out','binary_parent_partition')
    install=arcpy.GetInstallInfo()
    report={'status':'RUNNING','engine':install.get('ProductName','ArcGIS')+' '+install.get('Version','unknown')+' Spatial Analyst CostDistance/CostAllocation',
            'install':arcpy.GetInstallInfo(),'started':time.time(),'synthetic_only':config.get('synthetic_only',False),
            'grid_shape':list(p.shape),'source_parent_ids':source_ids.tolist(),'target_parent_count':len(parents),
            'config':config,'runs':[],'destination_same_parent_count':None,
            'patch_aggregation':'minimum cost over all cells of complete original ParentPatchID',
            'euclidean_comparison':'shortest planar distance from chosen patch-minimum origin cell to any core-cell centre in the selected destination parent; not necessarily the endpoint of the least-cost path',
            'license_lifecycle':'CheckOutExtension; normal interpreter exit returns licences automatically per Esri documentation',
            'license_lifecycle_source':'https://pro.arcgis.com/en/pro-app/3.6/arcpy/functions/checkoutextension.htm'}
    report['source_strategy']=strategy
    report['partition_equivalence']='Other-parent sources are the union of opposite-bit subsets of distinct dense parent codes; min over subset minima equals the minimum over the union.'
    report['destination_tie_rule']='Within each native source subset retain CostAllocation output; for exactly equal stored costs across subsets choose the smallest returned ParentPatchID. For patch-origin ties choose first row-major cell. This is deterministic, not a claim of unique ecological destination.'
    report['intergroup_equal_cost_candidate_count']=0
    euclidean_engine=config.get('euclidean_engine','native_euclidean')
    assert euclidean_engine in ('native_euclidean','ckdtree_exact')
    report['euclidean_engine']=euclidean_engine
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
    def native_run(label, source_input, target_mask, combine_min=False):
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
        if combine_min:
            available=target_mask&(da!=nodata)&(aa>0)
            ties=available&(best!=nodata)&(da==best)&(aa!=alloc)
            report['intergroup_equal_cost_candidate_count']+=int(np.sum(ties))
            update=available&((best==nodata)|(da<best)|((da==best)&(aa<alloc)))
        else:
            update=target_mask
        best[update]=da[update]
        alloc[update]=aa[update]
        report['runs'].append({'label':label,'seconds':time.time()-t,'target_cells':int(np.sum(target_mask)),
                               'distance_path':cd_path,'allocation_path':ca_path})
        _dump(os.path.join(outdir,'mcr_run_receipt.json'),report)
    if len(source_ids):
        native_run('all',source,p>0)
    if strategy=='leave_one_parent_out':
        for sid in source_ids:
            target=p==sid
            if len(source_ids)<2:
                best[target]=nodata
                alloc[target]=0
                continue
            exclude=os.path.join(outdir,'source_exclude_'+str(int(sid))+'.tif')
            SetNull(arcpy.Raster(source)==int(sid),arcpy.Raster(source)).save(exclude)
            native_run('exclude_'+str(int(sid)),exclude,target)
    else:
        # Each target accepts only opposite-bit source groups. All other source
        # parents differ in at least one bit, and its own parent differs in none.
        # Native Esri tools still compute every distance/allocation surface.
        has_source_parent=np.in1d(p.ravel(),source_ids).reshape(p.shape)&(p>0)
        target_codes=np.full(p.shape,-1,dtype=np.int32)
        target_codes[has_source_parent]=np.searchsorted(source_ids,p[has_source_parent])
        best[has_source_parent]=nodata;alloc[has_source_parent]=0
        nbits=(int(len(source_ids))-1).bit_length() if len(source_ids)>1 else 0
        report['source_codebook']=[{'parent_id':int(sid),'dense_code':i} for i,sid in enumerate(source_ids)]
        report['partition_bits']=nbits
        for bit in range(nbits):
            for value in (0,1):
                group_ids=source_ids[((np.arange(len(source_ids))>>bit)&1)==value]
                if not len(group_ids):continue
                source_mask=np.in1d(src.ravel(),group_ids).reshape(src.shape)&(src>0)
                group_array=np.where(source_mask,src,0).astype(np.int32)
                label='bit_'+str(bit)+'_value_'+str(value)
                grouped=save_arr(group_array,'source_'+label+'.tif',0)
                target=has_source_parent&(((target_codes>>bit)&1)!=value)
                if np.any(target):native_run(label,grouped,target,combine_min=True)
        del target_codes,has_source_parent
    valid=(p>0)&(best!=nodata)&(alloc>0)
    bad=valid&(alloc==p)
    report['destination_same_parent_count']=int(np.sum(bad))
    assert not np.any(bad),'Same-parent destinations remain'
    save_arr(best,'mcr_pixel_cost.tif',nodata)
    save_arr(alloc,'mcr_pixel_destination_parent.tif',0)
    records,pmin,pdest,packed=_patch_minima(p,best,alloc,nodata)
    geom_lookup=np.full(len(parents)+1,nodata,dtype=np.float32)
    record_groups={}
    for idx,r in enumerate(records,1):
        if r['status']=='VALID':
            record_groups.setdefault(r['destination_parent_id'],[]).append((idx,r))
    # Geometry is for the selected MCR destination, not a potentially different
    # globally nearest Euclidean destination.
    if euclidean_engine=='ckdtree_exact':
        _selected_destination_euclidean(src,records,gm[2],gm[3])
        for idx,r in enumerate(records,1):
            if r['status']=='VALID':geom_lookup[idx]=r['euclidean_m']
    else:
        for sid in sorted(record_groups):
            only=os.path.join(outdir,'source_only_'+str(sid)+'.tif')
            SetNull(arcpy.Raster(source)!=sid,arcpy.Raster(source)).save(only)
            ed_path=os.path.join(outdir,'euc_to_'+str(sid)+'.tif')
            EucDistance(only).save(ed_path)
            ed=arcpy.RasterToNumPyArray(ed_path,nodata_to_value=nodata)
            for idx,r in record_groups[sid]:
                r['euclidean_m']=float(ed[r['origin_row'],r['origin_col']])
                geom_lookup[idx]=r['euclidean_m']
    pgeom=geom_lookup[packed]
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
    # Standalone interpreter termination returns checked-out licences according
    # to Esri's documented lifecycle. This local Pro install fails on explicit
    # CheckInExtension, after calculations, so let the interpreter close normally.
    # No licence files, settings, system clock, or security controls are modified.
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
