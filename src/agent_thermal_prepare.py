"""Frozen-scene Landsat C2 L2 thermal preparation and exact polygon-area aggregation.
Run with Python 3.12 + rasterio, numpy, scipy, shapely, geopandas, pyproj.
No image interpolation, no cross-date composite, no empirical thermal cutoff.
"""
from pathlib import Path
import json, hashlib, datetime, time, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from scipy import sparse
import shapely
from pyproj import Transformer

warnings.filterwarnings("ignore",category=DeprecationWarning)
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"01_原始数据"
PRO=ROOT/"02_过程文件/thermal"
OUT=ROOT/"03_结果文件/thermal"
PRO.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
SP=ROOT/"02_过程文件/spatial"
RAWBASE=RAW/"Landsat8_2020已有原生窗口"
QABASE=RAW/"Landsat8_2020补充质量层"
SCENES=["LC08_L2SP_123032_20200803_02_T1","LC08_L2SP_123032_20200616_02_T1","LC08_L2SP_124032_20200810_02_T1"]
SCALE=0.00341802; OFFSET=149.0; CELSIUS=273.15
NODATA=-9999.0
def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf8")
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(path): return str(Path(path).relative_to(ROOT))
def safe_div(a,b):
    return np.divide(a,b,out=np.full_like(np.asarray(a,dtype=float),np.nan),where=np.asarray(b)>0)
def wf_quantile(v,w,q):
    order=np.argsort(v); v=v[order]; w=w[order]
    c=np.cumsum(w)
    return v[np.searchsorted(c,q*c[-1],side="left")]

ref_path=next((RAWBASE/SCENES[0]).glob("*_ST_B10_DN_window.tif"))
with rasterio.open(ref_path) as ref:
    H,W=ref.shape; TRANS=ref.transform; CRS=ref.crs
zones={}; mats={}; map_receipts=[]
scope=gpd.read_file(SP/"scope.gpkg",layer="study_scope").geometry.union_all()
for scale in [1000,500]:
    g=gpd.read_file(SP/"analysis.gdb",layer="grid_"+str(scale)).sort_values("Grid_ID").reset_index(drop=True)
    assert g.Grid_ID.is_unique and g.crs.is_projected
    clipped=shapely.intersection(g.geometry.values,scope)
    zones[scale]=(g,clipped)
TO=Transformer.from_crs(CRS,zones[1000][0].crs,always_xy=True)

def pixel_polys(rr,cc,segments=1):
    # Source product pixels retain their UTM footprint. Densified projected edges
    # are used to check the corner-footprint numerical approximation.
    offsets=[]
    for j in range(segments): offsets.append((j/segments,0))
    for j in range(segments): offsets.append((1,j/segments))
    for j in range(segments): offsets.append((1-j/segments,1))
    for j in range(segments): offsets.append((0,1-j/segments))
    offsets.append(offsets[0])
    off=np.asarray(offsets)
    x=TRANS.c+(cc[:,None]+off[None,:,0])*TRANS.a
    y=TRANS.f+(rr[:,None]+off[None,:,1])*TRANS.e
    xx,yy=TO.transform(x,y)
    return shapely.polygons(np.stack([xx,yy],axis=2))

# Verify the 30 m pixel polygon approximation against 3 m segmented edges.
rr=np.array([0,0,H//2,H-1,H-1]); cc=np.array([0,W-1,W//2,0,W-1])
a4=shapely.area(pixel_polys(rr,cc,1)); a40=shapely.area(pixel_polys(rr,cc,10))
projection_check={"corner_vs_3m_segment_area_max_abs_m2":float(np.max(np.abs(a4-a40))),
                  "corner_vs_3m_segment_area_max_relative":float(np.max(np.abs(a4-a40)/a40)),
                  "sample_pixels":5}
assert projection_check["corner_vs_3m_segment_area_max_relative"]<1e-7

for scale,(g,clip) in zones.items():
    fcache=PRO/("weights_full_grid_"+str(scale)+".npz")
    scache=PRO/("weights_scope_intersection_"+str(scale)+".npz")
    metadata=PRO/("weights_"+str(scale)+"_manifest.json")
    geomhash=hashlib.sha256(b"".join(shapely.to_wkb(g.geometry.values))+scope.wkb).hexdigest()
    if fcache.exists() and scache.exists() and metadata.exists():
        m=json.loads(metadata.read_text(encoding="utf8"))
        assert m["geometry_hash"]==geomhash and m["shape"]==[H,W]
        assert m["source_transform"]==list(TRANS) and m["source_crs"]==str(CRS)
        mats[scale]=(sparse.load_npz(fcache),sparse.load_npz(scache))
        map_receipts.append(m); print("Loaded weights",scale,flush=True); continue
    tree=shapely.STRtree(g.geometry.values)
    inside=shapely.covers(scope,g.geometry.values)
    rparts=[]; cparts=[]; fparts=[]; sparts=[]
    for r0 in range(0,H,32):
        rr,cc=np.meshgrid(np.arange(r0,min(r0+32,H)),np.arange(W),indexing="ij")
        rr=rr.ravel(); cc=cc.ravel()
        polys=pixel_polys(rr,cc)
        pairs=tree.query(polys,predicate="intersects")
        if not pairs.shape[1]: continue
        pi,gi=pairs
        ints=shapely.intersection(polys[pi],g.geometry.values[gi])
        fa=shapely.area(ints)
        sa=fa.copy()
        boundary=~inside[gi]
        sa[boundary]=shapely.area(shapely.intersection(ints[boundary],clip[gi[boundary]]))
        sel=fa>1e-7  # numerical area cutoff: < 1e-10 of one source pixel, not ecological threshold
        rparts.append(gi[sel].astype(np.int32)); cparts.append((rr[pi[sel]]*W+cc[pi[sel]]).astype(np.int32))
        fparts.append(fa[sel]); sparts.append(sa[sel])
        if r0%256==0: print("Area intersections",scale,r0,"/",H,flush=True)
    ri=np.concatenate(rparts); ci=np.concatenate(cparts); fv=np.concatenate(fparts); sv=np.concatenate(sparts)
    fm=sparse.coo_matrix((fv,(ri,ci)),shape=(len(g),H*W)).tocsr()
    sm=sparse.coo_matrix((sv,(ri,ci)),shape=(len(g),H*W)).tocsr(); sm.eliminate_zeros()
    full_expected=g.area.to_numpy(); scope_expected=shapely.area(clip)
    full_got=np.asarray(fm.sum(axis=1)).ravel(); scope_got=np.asarray(sm.sum(axis=1)).ravel()
    full_err=float(np.max(np.abs(full_expected-full_got)))
    scope_err=float(np.max(np.abs(scope_expected-scope_got)))
    assert full_err<0.1 and scope_err<0.1,(scale,full_err,scope_err)
    sparse.save_npz(fcache,fm); sparse.save_npz(scache,sm)
    m={"scale_m":scale,"geometry_hash":geomhash,"shape":[H,W],"source_transform":list(TRANS),
       "source_crs":str(CRS),"analysis_crs":g.crs.to_wkt(),"method":"native-pixel projected footprint intersected with fixed grid polygon; area in Albers equal-area metres",
       "full_weights":rel(fcache),"scope_weights":rel(scache),"full_nnz":int(fm.nnz),"scope_nnz":int(sm.nnz),
       "grid_full_area_max_error_m2":full_err,"grid_scope_area_max_error_m2":scope_err,
       "projection_polygon_check":projection_check}
    dump(metadata,m); map_receipts.append(m); mats[scale]=(fm,sm)
    del rparts,cparts,fparts,sparts,ri,ci,fv,sv
    print("Weights ready",scale,flush=True)

def aligned(path,shape,transform,crs):
    with rasterio.open(path) as ds:
        assert ds.crs==crs and ds.res==(30,30)
        w=from_bounds(*rasterio.transform.array_bounds(*shape,transform),ds.transform)
        vals=[w.col_off,w.row_off,w.width,w.height]
        assert max(abs(x-round(x)) for x in vals)<1e-6
        w=w.round_offsets().round_lengths()
        assert ds.window_transform(w)==transform
        a=ds.read(1,window=w)
        assert a.shape==shape
        return a,ds.nodata

def summarize(mat,zone_area,arrays,grid_ids,scene,scale,support):
    valid=arrays["valid"]; area=mat.dot(valid.astype(float))
    temp=arrays["temperature"]; qa=arrays["stqa"]
    ts=mat.dot(np.where(valid,temp,0)); ts2=mat.dot(np.where(valid,temp*temp,0))
    mean=safe_div(ts,area); variance=np.maximum(0,safe_div(ts2,area)-mean*mean)
    df=pd.DataFrame({"Grid_ID":grid_ids,"scale_m":scale,"scene_id":scene,"date":scene.split("_")[3],
                     "support":support,"zone_area_m2":zone_area,"window_area_m2":mat.dot(arrays["window"].astype(float)),
                     "valid_area_m2":area,"valid_coverage":safe_div(area,zone_area),
                     "LST_mean_C":mean,"LST_sd_C":np.sqrt(variance),
                     "STQA_mean_K":safe_div(mat.dot(np.where(valid,qa,0)),area)})
    for label in ["qapixel_fill","st_fill","cloud_dilated","cirrus","cloud","shadow","snow","radsat_nonzero","stqa_fill","emis_fill","st_missing_nonfill","medium_cloud_retained"]:
        df[label+"_area_m2"]=mat.dot(arrays[label].astype(float))
    extra=np.full((len(df),9),np.nan)
    counts=np.zeros(len(df),dtype=np.int32)
    for i in range(mat.shape[0]):
        lo,hi=mat.indptr[i:i+2]; idx=mat.indices[lo:hi]; wei=mat.data[lo:hi]
        good=valid[idx] & (wei>1e-7); idx=idx[good]; wei=wei[good]
        counts[i]=len(idx)
        if not len(idx): continue
        tv=temp[idx]; qv=qa[idx]
        extra[i,:]=[tv.min(),tv.max(),wf_quantile(tv,wei,.1),wf_quantile(tv,wei,.5),
                    wf_quantile(tv,wei,.9),qv.min(),qv.max(),wf_quantile(qv,wei,.5),wf_quantile(qv,wei,.9)]
    for j,name in enumerate(["LST_min_C","LST_max_C","LST_p10_C","LST_p50_C","LST_p90_C","STQA_min_K","STQA_max_K","STQA_p50_K","STQA_p90_K"]): df[name]=extra[:,j]
    df["valid_product_pixel_count"]=counts
    df["window_coverage"]=safe_div(df.window_area_m2.to_numpy(),zone_area)
    df["valid_coverage_within_window"]=safe_div(area,df.window_area_m2.to_numpy())
    assert (df.valid_coverage.dropna()<=1.0000001).all()
    assert (df.valid_area_m2<=df.window_area_m2+0.1).all()
    return df

scene_records=[]; outputs=[]
for scene in SCENES:
    srcdir=RAWBASE/scene; qadir=QABASE/scene; outdir=PRO/scene; outdir.mkdir(exist_ok=True)
    stp=next(srcdir.glob("*_ST_B10_DN_window.tif")); qpp=next(srcdir.glob("*_QA_PIXEL_window.tif"))
    rsp=next(srcdir.glob("*_QA_RADSAT_window.tif")); qap=next(qadir.glob("*_ST_QA_native_window.tif"))
    emp=next(qadir.glob("*_ST_EMIS_native_window.tif")); mtp=next(srcdir.glob("*_MTL.json"))
    with rasterio.open(stp) as ds: st=ds.read(1); profile=ds.profile.copy(); transform=ds.transform; crs=ds.crs
    qp,_=aligned(qpp,st.shape,transform,crs); rs,_=aligned(rsp,st.shape,transform,crs)
    qa,qa_no=aligned(qap,st.shape,transform,crs); em,em_no=aligned(emp,st.shape,transform,crs)
    mtl=json.loads(mtp.read_text(encoding="utf8"))["LANDSAT_METADATA_FILE"]
    rawmeta=mtl["LEVEL2_SURFACE_TEMPERATURE_PARAMETERS"]
    assert float(rawmeta["TEMPERATURE_MULT_BAND_ST_B10"])==SCALE
    assert float(rawmeta["TEMPERATURE_ADD_BAND_ST_B10"])==OFFSET
    flags={"qapixel_fill":(qp&1)>0,"st_fill":st==0,"cloud_dilated":(qp&2)>0,"cirrus":(qp&4)>0,
           "cloud":(qp&8)>0,"shadow":(qp&16)>0,"snow":(qp&32)>0,"radsat_nonzero":rs!=0,
           "stqa_fill":qa==qa_no,"emis_fill":em==em_no}
    valid=(st>0)&((qp&63)==0)&(rs==0)&(qa!=qa_no)&(qa>=0)&(em!=em_no)
    flags["st_missing_nonfill"]=(st==0)&((qp&1)==0)
    flags["medium_cloud_retained"]=valid&(((qp>>8)&3)==2)
    temperature=st.astype(np.float64)*SCALE+OFFSET-CELSIUS
    quality=qa.astype(np.float64)*.01
    reasons=np.zeros(st.shape,dtype=np.uint16)
    for bit,label in enumerate(list(flags)[:10]): reasons |= flags[label].astype(np.uint16)<<bit
    prof=profile.copy(); prof.update(dtype="float32",nodata=NODATA,compress="DEFLATE",tiled=True,blockxsize=256,blockysize=256)
    for name,a in [("LST_C_QA",temperature),("ST_QA_K_valid",quality)]:
        dest=outdir/(scene+"_"+name+".tif")
        with rasterio.open(dest,"w",**prof) as dst:
            dst.write(np.where(valid,a,NODATA).astype(np.float32),1)
            dst.update_tags(scene_id=scene,measurement="instantaneous overpass; not annual mean",
                            native_thermal_sampling_m="100",product_pixel_m="30",quality_policy="ST>0; QA_PIXEL bits0-5=0; QA_RADSAT=0; ST_QA and ST_EMIS not fill")
    prof.update(dtype="uint16",nodata=None)
    with rasterio.open(outdir/(scene+"_exclusion_reason_bits.tif"),"w",**prof) as dst:
        dst.write(reasons,1); dst.update_tags(bit_definitions=json.dumps(dict(enumerate(list(flags)[:10]))))
    prof.update(dtype="uint8",nodata=None)
    with rasterio.open(outdir/(scene+"_valid_mask.tif"),"w",**prof) as dst: dst.write(valid.astype(np.uint8),1)
    assert transform==TRANS and st.shape[0]==H and st.shape[1]<=W
    def pad(a,fill=0):
        b=np.full((H,W),fill,dtype=a.dtype); b[:,:st.shape[1]]=a; return b.ravel()
    arrays={k:pad(v,False) for k,v in flags.items()}
    arrays.update(valid=pad(valid,False),temperature=pad(temperature,0),stqa=pad(quality,0),window=pad(np.ones(st.shape,dtype=bool),False))
    summaries={}
    for scale,(g,clip) in zones.items():
        for support,mat,area in [("full_grid",mats[scale][0],g.area.to_numpy()),
                                 ("scope_intersection",mats[scale][1],shapely.area(clip))]:
            df=summarize(mat,area,arrays,g.Grid_ID.to_numpy(),scene,scale,support)
            target=OUT/(scene+"_"+str(scale)+"m_"+support+".csv")
            df.to_csv(target,index=False,encoding="utf-8-sig",float_format="%.10f")
            outputs.append({"path":rel(target),"sha256":sha(target),"rows":len(df)})
            summary={"zone_area_km2":float(df.zone_area_m2.sum()/1e6),
                     "window_area_km2":float(df.window_area_m2.sum()/1e6),
                     "valid_area_km2":float(df.valid_area_m2.sum()/1e6),
                     "valid_coverage_pct":float(100*df.valid_area_m2.sum()/df.zone_area_m2.sum()),
                     "valid_grids":int((df.valid_area_m2>0).sum()),"total_grids":len(df),
                     "LST_area_weighted_mean_C":float((df.LST_mean_C.fillna(0)*df.valid_area_m2).sum()/df.valid_area_m2.sum()),
                     "STQA_area_weighted_mean_K":float((df.STQA_mean_K.fillna(0)*df.valid_area_m2).sum()/df.valid_area_m2.sum())}
            summaries[str(scale)+"_"+support]=summary
    rec={"scene_id":scene,"landsat_product_id":mtl["PRODUCT_CONTENTS"]["LANDSAT_PRODUCT_ID"],
         "date":mtl["IMAGE_ATTRIBUTES"]["DATE_ACQUIRED"],"scene_center_time_utc":mtl["IMAGE_ATTRIBUTES"]["SCENE_CENTER_TIME"],
         "role":"primary" if scene==SCENES[0] else "separate_date_comparison",
         "inputs":[{"path":rel(p),"sha256":sha(p)} for p in [stp,qpp,rsp,qap,emp,mtp]],
         "grid_shape":list(st.shape),"valid_product_pixels_entire_window":int(valid.sum()),
         "ST_QA_raw_valid_range":[int(qa[valid].min()),int(qa[valid].max())],
         "quality_flag_counts_entire_window":{k:int(v.sum()) for k,v in flags.items()},
         "summaries":summaries}
    scene_records.append(rec)
    dump(outdir/"processing_receipt.json",rec)
    print("Prepared and aggregated",scene,flush=True)
receipt={"status":"THERMAL_PREPARATION_AND_AREA_WEIGHTED_AGGREGATION_COMPLETE",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "primary_scene":SCENES[0],"temperature_formula_C":"DN * 0.00341802 + 149 - 273.15",
 "STQA_formula_K":"DN * 0.01","temperature_cutoff":None,"STQA_uncertainty_cutoff":None,
 "QA_policy":"ST>0, QA_PIXEL bits 0-5 unset, QA_RADSAT=0, valid ST_QA and ST_EMIS; no masking of water bit7",
 "QA_RADSAT_note":"Landsat 8 QA_RADSAT includes reflective-band saturation and terrain occlusion; it is not a direct TIRS band10 saturation flag.",
 "emissivity_gap_note":"ST_EMIS fill and ST missing/nonfill are recorded separately. ASTER GED gaps can cause missing ST; no missing-pixel value is imputed and no claim that every missing pixel is uniquely caused by ASTER.",
 "uncertainty_note":"STQA is per-product-pixel model uncertainty; area-weighted STQA is descriptive, not the standard error of a grid mean.",
 "resolution_note":"Native TIRS acquisition 100 m; distributed Collection2 ST product 30 m. Product-pixel count is not independent sample size.",
 "aggregation":"Native 30m product-pixel projected footprint intersections in frozen CLCD Albers equal-area CRS. No raster resampling or date compositing.",
 "support_note":"Main full-square support matches landscape indicators; supplementary scope_intersection support covers actual research-area parts. Do not mix supports.",
 "maps":map_receipts,"scenes":scene_records,"outputs":outputs,
 "versions":{"numpy":np.__version__,"rasterio":rasterio.__version__,"geopandas":gpd.__version__,"shapely":shapely.__version__},
 "official_sources":["https://doi.org/10.5066/P9OGBGM6",
 "https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands",
 "https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature-data-gaps-due-missing",
 "https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1619_Landsat-8-9-C2-L2-ScienceProductGuide-v4.pdf"]}
dump(PRO/"thermal_preparation_receipt.json",receipt)
dump(OUT/"thermal_scene_summary.json",{"scenes":[{"scene_id":r["scene_id"],"role":r["role"],"summaries":r["summaries"]} for r in scene_records]})
print("THERMAL COMPLETE",flush=True)
