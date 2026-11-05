"""Independent verification of joins, supports and rank correlations.
Rebuild pairs from frozen source tables; do not trust the combined join table.
"""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd,geopandas as gpd
ROOT=Path(__file__).resolve().parents[2]
PRO=ROOT/"02_过程文件/thermal_association";OUT=ROOT/"03_结果文件/thermal_association"
rec=json.loads((PRO/"association_receipt.json").read_text(encoding="utf8"))
src=pd.read_csv(PRO/"input_snapshot/hq_graygreen_by_grid.csv")
raw=src[(src["product"]=="clcd")&(src.scale_m==1000)]
matrix=raw.pivot(index="grid_id",columns="habitat",values=["SSI","E_fraction","construction_m2","ecological_m2"])
for variable in ["SSI","E_fraction","construction_m2","ecological_m2"]:
 block=matrix[variable].to_numpy(dtype=float)
 assert np.all((block==block[:,[0]]) | (np.isnan(block)&np.isnan(block[:,[0]])))
single=matrix.xs("forest_shrub",axis=1,level=1)
candidate=single[(single.construction_m2>0)&(single.ecological_m2>0)&single.SSI.notna()&single.E_fraction.notna()]
assert len(candidate)==1268
grid=gpd.read_file(ROOT/"02_过程文件/spatial/analysis.gdb",layer="grid_1000").set_index("Grid_ID")
scope=gpd.read_file(ROOT/"02_过程文件/spatial/scope.gpkg",layer="study_scope")
b=scope.total_bounds;cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
quad={}
for gid,g in grid.geometry.items():
 xmin,ymin,xmax,ymax=g.bounds
 quad[gid]=("N" if (ymin+ymax)/2>=cy else "S")+("E" if (xmin+xmax)/2>=cx else "W")
declared=json.loads((PRO/"quadrant_definition.json").read_text(encoding="utf8"))
assert declared["midpoint_x_m"]==cx and declared["midpoint_y_m"]==cy
for q,ids in declared["grid_ids"].items():assert set(ids)=={k for k,v in quad.items() if v==q}
reported=pd.read_csv(OUT/"graygreen_LST_spearman_descriptive.csv")
cov=pd.read_csv(OUT/"graygreen_LST_coverage_by_date_domain.csv")
verification=[]
for scene in [rec["primary_scene"]]+rec["comparison_scenes"]:
 t=pd.read_csv(ROOT/"03_结果文件/thermal"/(scene+"_1000m_full_grid.csv")).set_index("Grid_ID")
 assert t.index.is_unique and set(t.index)==set(grid.index) and t.support.eq("full_grid").all()
 scatter=pd.read_csv(OUT/(scene+"_scatter_real_grid_values.csv")).set_index("Grid_ID")
 expected_ids=[k for k in candidate.index if np.isfinite(t.loc[k,"LST_mean_C"]) and t.loc[k,"valid_area_m2"]>0]
 assert set(scatter.index)==set(expected_ids) and scatter.index.is_unique
 for k in expected_ids:
  assert abs(scatter.loc[k,"SSI"]-candidate.loc[k,"SSI"])<1e-9
  assert abs(scatter.loc[k,"E_fraction"]-candidate.loc[k,"E_fraction"])<1e-12
  assert abs(scatter.loc[k,"LST_mean_C"]-t.loc[k,"LST_mean_C"])<1e-9
  assert scatter.loc[k,"quadrant"]==quad[k]
 for domain in ["ALL","NW","NE","SW","SE"]:
  baseids=[k for k in candidate.index if domain=="ALL" or quad[k]==domain]
  ids=[k for k in expected_ids if domain=="ALL" or quad[k]==domain]
  c=cov[(cov.scene_id==scene)&(cov.domain==domain)].iloc[0]
  assert int(c.n_eligible_graygreen_grids)==len(baseids) and int(c.n_paired_grids)==len(ids)
  direct_area=sum(t.loc[k,"valid_area_m2"] for k in baseids)
  direct_denom=sum(t.loc[k,"zone_area_m2"] for k in baseids)
  assert abs(direct_area/direct_denom-c.valid_area_fraction_of_eligible_full_grids)<1e-12
  for variable in ["SSI","E_fraction"]:
   row=reported[(reported.scene_id==scene)&(reported.domain==domain)&(reported.predictor==variable)].iloc[0]
   assert int(row.n_grid_pairs)==len(ids)
   if len(ids)<2:
    assert pd.isna(row.spearman_rho)
    verification.append({"scene":scene,"domain":domain,"variable":variable,"n":len(ids),"status":"undefined_as_expected"})
    continue
   # Independent method: Pearson coefficient of pandas average ranks, not scipy.spearmanr.
   rx=candidate.loc[ids,variable].rank(method="average").to_numpy()
   ry=t.loc[ids,"LST_mean_C"].rank(method="average").to_numpy()
   dx=rx-rx.mean();dy=ry-ry.mean()
   rho=float(np.sum(dx*dy)/np.sqrt(np.sum(dx*dx)*np.sum(dy*dy)))
   error=abs(rho-row.spearman_rho);assert error<1e-12
   verification.append({"scene":scene,"domain":domain,"variable":variable,"n":len(ids),"absolute_rho_error":error,"status":"passed"})
for item in rec["inputs"]:
 assert hashlib.sha256((ROOT/item["path"]).read_bytes()).hexdigest()==item["sha256"]
report={"status":"PASSED","deduplication_independent_pivot":"passed","one_to_one_joins_and_real_scatter_readback":"passed",
"full_square_support_and_quadrant_reconstruction":"passed","input_hashes":"passed","pair_selection":"C>0,E>0,finite SSI/E,valid LST; no arbitrary coverage cutoff",
"correlation_checks":verification,"n_semantics":"Grid count per date/domain, not habitat-row count or native-pixel count.",
"independence_note":"Spatial independence is not asserted; no ordinary iid P-value inference is made."}
(PRO/"association_independent_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps({"status":"PASSED","correlation_rows":len(verification),"defined_correlations":sum(x["status"]=="passed" for x in verification)}))
