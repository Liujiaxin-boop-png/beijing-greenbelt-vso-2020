"""Prepare clipped map geometry from approved, already-calculated raw indicators.
No indicator is recalculated; no MCR, NTL, or ER is manufactured here.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/"02_过程文件/map_inputs_s1";WORK.mkdir(exist_ok=True)
HQ=ROOT/"03_结果文件/indicators/hq_graygreen_by_grid.csv"
CL=ROOT/"03_结果文件/clumpy/clumpy_clcd_1000.csv"
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
before={str(p.relative_to(ROOT)):digest(p) for p in [HQ,CL]}
base=pd.read_csv(HQ);base=base[(base["product"]=="clcd")&(base.scale_m==1000)].copy()
assert len(base)==7434 and not base.duplicated(["grid_id","habitat"]).any()
assert set(base.habitat)=={"forest_shrub","grassland","water_wetland"}
cl=pd.read_csv(CL).rename(columns={"Grid_ID":"grid_id","habitat_type":"habitat"})
cl["habitat"]=cl.habitat.replace({"grass":"grassland"})
assert not cl.duplicated(["grid_id","habitat"]).any()
assert len(cl)==7434 and set(cl.habitat)==set(base.habitat)
assert cl.scale_m.eq(1000).all() and cl["product"].str.lower().eq("clcd").all()
codes={"forest_shrub":"FS","grassland":"G","water_wetland":"W"}
h=base.pivot(index="grid_id",columns="habitat",values="HQ_H").rename(columns={x:"HQ_"+y for x,y in codes.items()})
c=cl.pivot(index="grid_id",columns="habitat",values="CLUMPY").rename(columns={x:"CLUMPY_"+y for x,y in codes.items()})
data=h.join(c,validate="one_to_one")
for name in ["SSI","E_fraction"]:
    p=base.pivot(index="grid_id",columns="habitat",values=name)
    assert all(np.array_equal(p.iloc[:,0].to_numpy(),p.iloc[:,j].to_numpy(),equal_nan=True) for j in range(1,3))
    data[name]=p.iloc[:,0]
assert data.index.is_unique and len(data)==2478
for name in ["HQ_FS","HQ_G","HQ_W","E_fraction"]:
    v=data[name].dropna();assert v.between(0,1).all()
for name in ["CLUMPY_FS","CLUMPY_G","CLUMPY_W"]:
    v=data[name].dropna();assert v.between(-1,1).all()
assert data.SSI.dropna().ge(0).all()
grid=gpd.read_file(ROOT/"02_过程文件/spatial/analysis.gdb",layer="grid_1000").rename(columns={"Grid_ID":"grid_id"})
assert set(grid.grid_id)==set(data.index)
scope=gpd.read_file(ROOT/"02_过程文件/spatial/scope.gpkg",layer="study_scope")
assert scope.crs==grid.crs
union=scope.geometry.union_all()
geo=grid[["grid_id","geometry"]].merge(data.reset_index(),on="grid_id",validate="one_to_one")
geo["full_grid_area_m2"]=geo.area
geo.geometry=shapely.intersection(geo.geometry.values,union)
assert geo.geometry.is_valid.all() and geo.area.gt(0).all()
geo["display_area_m2"]=geo.area
assert abs(geo.area.sum()-union.area)<.01
gpkg=WORK/"S1_raw_indicator_cells.gpkg"
geo.to_file(gpkg,layer="cells",driver="GPKG",engine="pyogrio")
data.reset_index().to_csv(WORK/"S1_raw_indicator_values.csv",index=False,encoding="utf-8-sig")
panel_fields=["HQ_FS","HQ_G","HQ_W","SSI","CLUMPY_FS","CLUMPY_G","CLUMPY_W","E_fraction"]
summary=[]
for name in panel_fields:
    v=data[name].dropna()
    summary.append({"field":name,"valid_n":len(v),"NA_n":int(data[name].isna().sum()),"observed_min":float(v.min()),"observed_max":float(v.max()),
                    "legend_min":float(v.min()) if name=="SSI" else (-1 if name.startswith("CLUMPY") else 0),
                    "legend_max":float(v.max()) if name=="SSI" else 1})
pd.DataFrame(summary).to_csv(WORK/"S1_panel_statistics.csv",index=False,encoding="utf-8-sig")
after={str(p.relative_to(ROOT)):digest(p) for p in [HQ,CL]};assert before==after
record={"status":"RAW_VALUES_AND_DISPLAY_GEOMETRY_PREPARED","inputs_sha256":before,"grid_n":len(geo),
        "full_grid_support":"1000 m squares; calculated values unchanged; geometry clipped to study union only for display",
        "projection":grid.crs.to_wkt(),"display_area_km2":float(geo.area.sum()/1e6),"H_invariant_metrics_verified":["SSI","E_fraction"],
        "NA_policy":"Retain source NA; no zero substitution. Missing focal habitat or unsatisfied input support can cause NA.",
        "no_new_metrics":["MCR","NTL","ER"],"panels":summary,"display_gpkg_sha256":digest(gpkg)}
(WORK/"S1_data_receipt.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf8")
print("S1_DATA_PREPARED",flush=True)
