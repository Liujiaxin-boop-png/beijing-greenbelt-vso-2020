"""Independent bounded readback and direct polygon recomputation for thermal outputs."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd,geopandas as gpd,rasterio,shapely
from pyproj import Transformer
from rasterio.windows import from_bounds
ROOT=Path(__file__).resolve().parents[2]
PRO=ROOT/"02_过程文件/thermal"; OUT=ROOT/"03_结果文件/thermal"
receipt=json.loads((PRO/"thermal_preparation_receipt.json").read_text(encoding="utf8"))
checks=[]; direct=[]
scope=gpd.read_file(ROOT/"02_过程文件/spatial/scope.gpkg",layer="study_scope").geometry.union_all()
grids={k:gpd.read_file(ROOT/"02_过程文件/spatial/analysis.gdb",layer="grid_"+str(k)).set_index("Grid_ID") for k in [1000,500]}
for r in receipt["scenes"]:
 scene=r["scene_id"]; paths=[ROOT/i["path"] for i in r["inputs"]]
 for p,meta in zip(paths,r["inputs"]):
  assert hashlib.sha256(p.read_bytes()).hexdigest()==meta["sha256"]
 stp,qpp,rsp,qap,emp,mtp=paths
 with rasterio.open(stp) as ds:
  st=ds.read(1); tr=ds.transform; crs=ds.crs; bounds=ds.bounds
 def rd(p):
  with rasterio.open(p) as d:
   w=from_bounds(*bounds,d.transform).round_offsets().round_lengths()
   a=d.read(1,window=w)
   assert a.shape==st.shape
   return a,d.nodata
 qp,_=rd(qpp); rs,_=rd(rsp); qa,qn=rd(qap); em,en=rd(emp)
 expected=(st!=0)&np.equal(qp&63,0)&np.equal(rs,0)&np.not_equal(qa,qn)&(qa>=0)&np.not_equal(em,en)
 with rasterio.open(PRO/scene/(scene+"_valid_mask.tif")) as ds:
  valid=ds.read(1).astype(bool); assert np.array_equal(valid,expected)
 with rasterio.open(PRO/scene/(scene+"_LST_C_QA.tif")) as ds:
  out=ds.read(1); assert np.array_equal(out==ds.nodata,~expected)
  maxdiff=float(np.max(np.abs(out[expected]-(st[expected].astype(float)*.00341802+149-273.15))))
  assert maxdiff<1e-4
 checks.append({"scene":scene,"source_hashes":"passed","quality_mask_exact_match":"passed","temperature_scale_max_readback_error_C":maxdiff})
 if r["role"]!="primary": continue
 for scale in [1000,500]:
  for support in ["full_grid","scope_intersection"]:
   df=pd.read_csv(OUT/(scene+"_"+str(scale)+"m_"+support+".csv"))
   # Deterministic central and smallest support examples.
   sample=pd.concat([df.iloc[[len(df)//2]],df.nsmallest(2,"zone_area_m2")]).drop_duplicates("Grid_ID")
   for row in sample.itertuples():
    geom=grids[scale].loc[row.Grid_ID,"geometry"]
    if support=="scope_intersection": geom=geom.intersection(scope)
    to_native=Transformer.from_crs(grids[scale].crs,crs,always_xy=True)
    native_geom=shapely.transform(geom,to_native.transform,interleaved=False)
    xmin,ymin,xmax,ymax=native_geom.bounds
    win=from_bounds(xmin,ymin,xmax,ymax,tr)
    c0=max(0,int(np.floor(win.col_off))-1); c1=min(st.shape[1],int(np.ceil(win.col_off+win.width))+1)
    r0=max(0,int(np.floor(win.row_off))-1); r1=min(st.shape[0],int(np.ceil(win.row_off+win.height))+1)
    rr,cc=np.meshgrid(np.arange(r0,r1),np.arange(c0,c1),indexing="ij"); rr=rr.ravel(); cc=cc.ravel()
    # Eight-vertex footprints (edge midpoints) provide a distinct geometric check.
    off=np.array([[0,0],[.5,0],[1,0],[1,.5],[1,1],[.5,1],[0,1],[0,.5],[0,0]])
    x=tr.c+(cc[:,None]+off[None,:,0])*tr.a; y=tr.f+(rr[:,None]+off[None,:,1])*tr.e
    tf=Transformer.from_crs(crs,grids[scale].crs,always_xy=True); xx,yy=tf.transform(x,y)
    pp=shapely.polygons(np.stack([xx,yy],axis=2))
    wei=shapely.area(shapely.intersection(pp,geom)); ok=expected[rr,cc]&(wei>1e-7)
    area=float(wei[ok].sum())
    temp=st[rr[ok],cc[ok]].astype(float)*.00341802+149-273.15
    mean=float(np.sum(temp*wei[ok])/area) if area>0 else None
    area_diff=abs(area-row.valid_area_m2); mean_diff=abs(mean-row.LST_mean_C) if mean is not None else 0
    assert area_diff<.1 and mean_diff<1e-6,(row.Grid_ID,area_diff,mean_diff)
    direct.append({"grid_id":row.Grid_ID,"scale":scale,"support":support,"valid_area_abs_difference_m2":area_diff,"mean_abs_difference_C":mean_diff})
# Scope support should agree across grid scales because it partitions the same union.
for r in receipt["scenes"]:
 a=r["summaries"]["1000_scope_intersection"]; b=r["summaries"]["500_scope_intersection"]
 assert abs(a["valid_area_km2"]-b["valid_area_km2"])<1e-6
 assert abs(a["LST_area_weighted_mean_C"]-b["LST_area_weighted_mean_C"])<1e-7
for out in receipt["outputs"]:
 p=ROOT/out["path"]; assert hashlib.sha256(p.read_bytes()).hexdigest()==out["sha256"]
 table=pd.read_csv(p); assert len(table)==out["rows"] and table.Grid_ID.is_unique
report={"status":"PASSED","source_and_raster_checks":checks,"independent_direct_pixel_polygon_checks":direct,
"scope_partition_consistency":"passed","all_12_csv_hashes_rows_unique_ids":"passed",
"interpretation":"Validation is computational QA, not ecological model validation or ground-temperature accuracy validation.",
"openmapstack_cli_validation":"not_testable: bounded module uses parent research project; no separate CLI artifact configured"}
(PRO/"thermal_validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps({"status":"PASSED","scene_checks":len(checks),"direct_checks":len(direct),"csv_count":len(receipt["outputs"])}))
