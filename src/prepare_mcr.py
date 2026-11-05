"""Freeze literature resistance and native MSPA source-parent inputs.

Core component area (not summed parent area) selects sources; every selected
core pixel retains its complete, 8-connected original habitat ParentPatchID.
NoData is not traversable. Source and parent zero values are stored as NoData.
"""
from pathlib import Path
import json,time
import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/mcr_inputs'
SP=ROOT/'02_过程文件/spatial'
GROUPS={'forest_shrub':[2,3],'grassland':[4],'water_wetland':[5,9]}

def dump(p,o):
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf8')

def alias(p):
    return str(p).replace(str(ROOT/'02_过程文件'),'D:\\ER219_work')

def save(p,a,profile,nodata):
    pr=profile.copy();pr.update(driver='GTiff',dtype=a.dtype,count=1,nodata=nodata,compress='LZW',BIGTIFF='IF_SAFER')
    with rasterio.open(p,'w',**pr) as dst:dst.write(a,1)

def main():
    WORK.mkdir(exist_ok=True)
    spec=json.loads((Path(__file__).resolve().parents[1]/'config/mcr_parameters.json').read_text(encoding='utf8'))
    costs={r['clcd_code']:r['cost'] for r in spec['land_cost']['rows']}
    with rasterio.open(ROOT/'02_过程文件/distance/road_euclidean_m.tif') as ds:
        rd=ds.read(1);road_profile=ds.profile;aff=ds.transform
    roadcost=np.choose(np.digitize(rd,[200,400,800,1000]),[9,7,5,3,1]).astype('float32')
    tasks=[];audit=[]
    for product,landpath,mspa_product in [('clcd','clcd2020.tif','clcd2020'),('wc','worldcover2020_common30m.tif','worldcover2020')]:
        with rasterio.open(SP/landpath) as ds:
            land=ds.read(1);profile=ds.profile;valid=ds.read_masks(1)>0
            assert ds.transform==aff and ds.shape==rd.shape and ds.crs==road_profile['crs']
        observed=set(map(int,np.unique(land[valid])))
        assert observed.issubset(costs),('Unmapped land class',observed-set(costs))
        lc=np.full(land.shape,-9999,dtype='float32')
        for code,cost in costs.items():lc[(land==code)&valid]=cost
        blended=np.where(valid,(.3445*lc+.0281*roadcost)/.3726,-9999).astype('float32')
        assert np.all((blended[valid]>=1-1e-6)&(blended[valid]<=9+1e-6))
        cost_path=WORK/(product+'_land_road_cost.tif');save(cost_path,blended,profile,-9999)
        land_cost_path=WORK/(product+'_land_only_cost.tif');save(land_cost_path,lc,profile,-9999)
        for habitat,codes in GROUPS.items():
            out=WORK/(product+'_'+habitat);out.mkdir(exist_ok=True)
            fg=np.isin(land,codes)&valid
            parent,nparent=ndimage.label(fg,np.ones((3,3),dtype='uint8'))
            parent=parent.astype('int32');parent_path=out/'parent_id.tif';save(parent_path,parent,profile,0)
            with rasterio.open(ROOT/'02_过程文件/mspa'/(mspa_product+'_'+habitat)/'core_mask_georef.tif') as ds:
                core=ds.read(1)==1
                assert ds.transform==aff and ds.shape==land.shape and ds.crs==profile['crs']
            assert np.all(fg[core])
            cc,ncore=ndimage.label(core,np.ones((3,3),dtype='uint8'))
            area=np.bincount(cc.ravel())*abs(aff.a*aff.e)/10000.
            touched=np.unique(np.concatenate([parent[0,:],parent[-1,:],parent[:,0],parent[:,-1]]));touched=touched[touched>0]
            counts=np.bincount(parent.ravel())
            par=pd.DataFrame({'parent_id':np.arange(1,nparent+1),'area_ha':counts[1:]*abs(aff.a*aff.e)/10000.,'background_truncated':np.isin(np.arange(1,nparent+1),touched)})
            par.to_csv(out/'parent_catalog.csv',index=False,encoding='utf-8-sig')
            # Each connected core must be contained in exactly one full parent.
            core_parent=np.zeros(ncore+1,dtype='int32')
            np.maximum.at(core_parent,cc[core],parent[core])
            assert np.all(core_parent[cc[core]]==parent[core])
            pd.DataFrame({'core_id':np.arange(1,ncore+1),'area_ha':area[1:],'parent_id':core_parent[1:]}).to_csv(out/'core_catalog.csv',index=False,encoding='utf-8-sig')
            for label,threshold,strict in [('core10',10,False),('core35',35,False),('core100',100,True)]:
                if product=='wc' and label!='core10':continue
                eligible=area>threshold if strict else area>=threshold
                eligible[0]=False
                sm=eligible[cc]
                sources=np.where(sm,parent,0).astype('int32')
                sourcepath=out/(label+'_source_parent.tif');save(sourcepath,sources,profile,0)
                sourceids=np.unique(sources[sources>0])
                info={'product':product,'habitat':habitat,'source_rule':label,'threshold_ha':threshold,'operator':'>' if strict else '>=','parent_count':int(nparent),'core_component_count':int(ncore),'selected_core_components':int(eligible.sum()),'source_parent_count':len(sourceids),'source_core_area_ha':float(sm.sum()*abs(aff.a*aff.e)/10000.),'truncated_source_parent_count':int(np.isin(sourceids,touched).sum()),'truncated_parent_ids':list(map(int,touched))}
                audit.append(info)
                variants=[('land_road',cost_path)]
                if product=='clcd' and label=='core10':variants.append(('land_only',land_cost_path))
                for variant,cpath in variants:
                    scenario=product+'_'+habitat+'_'+label+'_'+variant
                    cfg={'parent_raster':alias(parent_path),'source_parent_raster':alias(sourcepath),'cost_raster':alias(cpath),'out_dir':'D:\\ER219_work\\mcr_native\\'+scenario,'source_strategy':'binary_parent_partition','synthetic_only':False,'scenario':scenario,'product':product,'habitat':habitat,'threshold':info,'resistance_source_doi':'10.1038/s41598-024-79433-9','resistance_variant':variant}
                    cp=out/(scenario+'.json');dump(cp,cfg)
                    tasks.append({'scenario':scenario,'config':alias(cp),'source_parents':len(sourceids)})
                print(json.dumps(info,ensure_ascii=False),flush=True)
    pd.DataFrame(audit).drop(columns=['truncated_parent_ids']).to_csv(WORK/'source_summary.csv',index=False,encoding='utf-8-sig')
    dump(WORK/'source_details.json',audit)
    dump(WORK/'regional_queue.json',{'status':'INPUTS_READY','tasks':tasks,'source_selection':'native MSPA connected core component area; full original parent exclusion','resistance_specification':str(spec['specification']),'scope':'full background, per-cell geometric projection; not clipped at study boundary','created':time.time()})
    print('MCR_INPUTS_READY',len(tasks))

if __name__=='__main__':main()
