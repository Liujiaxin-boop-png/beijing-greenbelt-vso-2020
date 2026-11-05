"""Proposal218: descriptive grid-unit Spearman association, gray-green and LST.
Primary scene 2020-08-03; other frozen dates separately. No ER or NTL input.
"""
from pathlib import Path
from io import BytesIO
import hashlib,json,datetime,shutil
import numpy as np,pandas as pd,geopandas as gpd,scipy
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parents[2]
PROC=ROOT/"02_过程文件/thermal_association"
OUT=ROOT/"03_结果文件/thermal_association"
PROC.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
EXTERNAL_SOURCE=Path(r"D:\ER219_results\indicators\hq_graygreen_by_grid.csv")
FROZEN_SOURCE=PROC/"input_snapshot/hq_graygreen_by_grid.csv"
SOURCE=FROZEN_SOURCE if FROZEN_SOURCE.exists() else EXTERNAL_SOURCE
THERMAL=ROOT/"03_结果文件/thermal"
SCENES=["LC08_L2SP_123032_20200803_02_T1","LC08_L2SP_123032_20200616_02_T1","LC08_L2SP_124032_20200810_02_T1"]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf8")
def csv(p,df):df.to_csv(p,index=False,encoding="utf-8-sig",float_format="%.17g")
content=SOURCE.read_bytes(); input_hash=hashlib.sha256(content).hexdigest()
df=pd.read_csv(BytesIO(content))
assert sha(SOURCE)==input_hash,"Source changed during read"
snapshot=PROC/"input_snapshot";snapshot.mkdir(exist_ok=True)
snap=snapshot/SOURCE.name
if snap.exists():assert sha(snap)==input_hash,"Existing frozen snapshot differs; explicit new run needed."
else:snap.write_bytes(content)
base=df.loc[(df["product"]=="clcd")&(df.scale_m==1000)].copy()
invariant=["scale_m","product","grid_area_m2","scope_area_m2","construction_m2","ecological_m2",
"cropland_m2","SSI","E_fraction","SSI_crop_included","E_fraction_crop_included","has_construction"]
counts=base.groupby("grid_id").size()
assert counts.eq(3).all()
assert base.groupby("grid_id")["habitat"].agg(lambda x:set(x)=={"forest_shrub","grassland","water_wetland"}).all()
variation=base.groupby("grid_id")[invariant].nunique(dropna=False)
assert variation.le(1).all().all(),"Habitat-specific gray-green values differ"
unique=base.sort_values(["grid_id","habitat"]).drop_duplicates("grid_id")[["grid_id"]+invariant].copy()
unique=unique.rename(columns={"grid_id":"Grid_ID"})
assert unique.Grid_ID.is_unique
calc=unique.ecological_m2/(unique.ecological_m2+unique.construction_m2)
ratio_diff=float(np.nanmax(np.abs(calc-unique.E_fraction)))
assert ratio_diff<1e-8
unique["eligible_graygreen"]=(unique.construction_m2>0)&(unique.ecological_m2>0)&np.isfinite(unique.SSI)&np.isfinite(unique.E_fraction)
unique["selection_reason"]=np.select(
 [unique.construction_m2<=0,unique.ecological_m2<=0,~np.isfinite(unique.SSI),~np.isfinite(unique.E_fraction)],
 ["no_construction","no_ecological_space","SSI_missing","E_fraction_missing"],default="eligible")
grids=gpd.read_file(ROOT/"02_过程文件/spatial/analysis.gdb",layer="grid_1000")
scope=gpd.read_file(ROOT/"02_过程文件/spatial/scope.gpkg",layer="study_scope")
assert grids.Grid_ID.is_unique and grids.crs==scope.crs
bounds=scope.total_bounds
xmid=float((bounds[0]+bounds[2])/2);ymid=float((bounds[1]+bounds[3])/2)
cent=grids.geometry.centroid
geo=pd.DataFrame({"Grid_ID":grids.Grid_ID,"centroid_x_m":cent.x,"centroid_y_m":cent.y,"geometry_area_m2":grids.area})
geo["quadrant"]=np.where(geo.centroid_y_m>=ymid,
 np.where(geo.centroid_x_m>=xmid,"NE","NW"),np.where(geo.centroid_x_m>=xmid,"SE","SW"))
geo["quadrant_cn"]=geo.quadrant.map({"NE":"东北","NW":"西北","SE":"东南","SW":"西南"})
assert set(unique.Grid_ID)==set(geo.Grid_ID)
unique=unique.merge(geo,on="Grid_ID",validate="one_to_one")
assert np.max(np.abs(unique.grid_area_m2-unique.geometry_area_m2))<.001
unique=unique.sort_values("Grid_ID").reset_index(drop=True)
csv(PROC/"graygreen_clcd_1000m_deduplicated.csv",unique)
quaddef={"definition":"Classify each FULL 1000m square by its centroid relative to the midpoint of study-scope bounds in frozen Albers equal-area CRS.",
"bounds":[float(x) for x in bounds],"midpoint_x_m":xmid,"midpoint_y_m":ymid,"crs_wkt":grids.crs.to_wkt(),
"axis_tie_rule":"x==midpoint assigned East; y==midpoint assigned North",
"domains":{"NW":"x < midpoint_x and y >= midpoint_y","NE":"x >= midpoint_x and y >= midpoint_y",
"SW":"x < midpoint_x and y < midpoint_y","SE":"x >= midpoint_x and y < midpoint_y"},
"interpretation":"Descriptive spatial partitions; not official planning or administrative zones.",
"assignment":"Whole grid assigned by centroid. Grids crossing a partition axis are not split.",
"grid_ids":{q:unique.loc[unique.quadrant==q,"Grid_ID"].tolist() for q in ["NW","NE","SW","SE"]}}
dump(PROC/"quadrant_definition.json",quaddef)
dedup={"input_source":str(SOURCE),"original_external_source":str(EXTERNAL_SOURCE),"snapshot":str(snap.relative_to(ROOT)),"sha256":input_hash,
"input_rows_all_products_scales":len(df),"selected_rows_clcd_1000m":len(base),"unique_grids":len(unique),
"rows_per_grid":3,"invariant_columns":invariant,"maximum_distinct_values_in_any_invariant_group":int(variation.to_numpy().max()),
"E_fraction_formula":"E / (E + C), not E / whole square area","maximum_formula_rounding_difference":ratio_diff,
"eligible_rule":"C>0 and E>0 and finite SSI and E_fraction; no minimum LST coverage fraction added",
"n_eligible_graygreen":int(unique.eligible_graygreen.sum()),"selection_counts":{str(k):int(v) for k,v in unique.selection_reason.value_counts().items()},
"habitat_rows_not_replicates":True}
dump(PROC/"deduplication_audit.json",dedup)

allrows=[];stats=[];coverage=[];missing=[];inputs=[{"path":str(snap.relative_to(ROOT)),"sha256":input_hash}]
domains=["ALL","NW","NE","SW","SE"]
for scene in SCENES:
 path=THERMAL/(scene+"_1000m_full_grid.csv")
 t=pd.read_csv(path)
 assert t.Grid_ID.is_unique and len(t)==len(unique)
 assert t.support.eq("full_grid").all() and t.scale_m.eq(1000).all() and t.scene_id.eq(scene).all()
 assert set(t.Grid_ID)==set(unique.Grid_ID)
 inputs.append({"path":str(path.relative_to(ROOT)),"sha256":sha(path)})
 joined=unique.merge(t.drop(columns=["scale_m"]),on="Grid_ID",validate="one_to_one")
 assert np.max(np.abs(joined.grid_area_m2-joined.zone_area_m2))<.001
 assert np.max(np.abs(joined.LST_mean_C.to_numpy()[np.isfinite(joined.LST_mean_C)]))<1e4
 joined["has_valid_LST"]=np.isfinite(joined.LST_mean_C)&(joined.valid_area_m2>0)
 joined["paired"]=joined.eligible_graygreen&joined.has_valid_LST
 joined["date_role"]="primary" if scene==SCENES[0] else "separate_date_comparison"
 allrows.append(joined)
 scatter=joined[joined.paired].copy()
 scattercols=["Grid_ID","date","scene_id","date_role","quadrant","quadrant_cn","centroid_x_m","centroid_y_m",
 "SSI","E_fraction","construction_m2","ecological_m2","grid_area_m2","scope_area_m2",
 "LST_mean_C","LST_sd_C","STQA_mean_K","valid_coverage","valid_area_m2","window_coverage","valid_product_pixel_count"]
 csv(OUT/(scene+"_scatter_real_grid_values.csv"),scatter[scattercols].sort_values("Grid_ID"))
 for domain in domains:
  d=joined if domain=="ALL" else joined[joined.quadrant==domain]
  eligible=d[d.eligible_graygreen]; paired=eligible[eligible.has_valid_LST]; lost=eligible[~eligible.has_valid_LST]
  denom=eligible.zone_area_m2.sum()
  cov={"scene_id":scene,"date":scene.split("_")[3],"date_role":joined.date_role.iloc[0],"domain":domain,
  "n_all_domain_grids":len(d),"n_eligible_graygreen_grids":len(eligible),"n_paired_grids":len(paired),
  "n_eligible_no_LST":len(lost),"paired_fraction_of_eligible":len(paired)/len(eligible) if len(eligible) else np.nan,
  "eligible_full_grid_area_km2":denom/1e6,"eligible_scope_reporting_area_km2":eligible.scope_area_m2.sum()/1e6,
  "window_area_fraction_of_eligible_full_grids":eligible.window_area_m2.sum()/denom if denom else np.nan,
  "valid_area_fraction_of_eligible_full_grids":eligible.valid_area_m2.sum()/denom if denom else np.nan,
  "paired_valid_coverage_min":paired.valid_coverage.min(),"paired_valid_coverage_q25":paired.valid_coverage.quantile(.25),
  "paired_valid_coverage_median":paired.valid_coverage.median(),"paired_valid_coverage_q75":paired.valid_coverage.quantile(.75),
  "paired_valid_coverage_max":paired.valid_coverage.max(),
  "LST_valid_area_weighted_mean_C":np.average(paired.LST_mean_C,weights=paired.valid_area_m2) if len(paired) else np.nan,
  "STQA_valid_area_weighted_mean_K":np.average(paired.STQA_mean_K,weights=paired.valid_area_m2) if len(paired) else np.nan}
  coverage.append(cov)
  for variable in ["SSI","E_fraction"]:
   valid_pairs=paired[[variable,"LST_mean_C"]].dropna()
   rho=float(spearmanr(valid_pairs[variable],valid_pairs.LST_mean_C).statistic) if len(valid_pairs)>1 and valid_pairs[variable].nunique()>1 and valid_pairs.LST_mean_C.nunique()>1 else np.nan
   stats.append({"scene_id":scene,"date":scene.split("_")[3],"date_role":cov["date_role"],"domain":domain,
   "predictor":variable,"response":"LST_mean_C","n_grid_pairs":len(valid_pairs),"spearman_rho":rho,
   "rho_weighting":"unweighted grid-unit ranks","support":"full_1000m_square","inference":"descriptive_only_no_iid_P_or_causal_claim"})
   for subset,dd in [("all_eligible",eligible),("LST_available",paired),("LST_missing",lost)]:
    missing.append({"scene_id":scene,"date":scene.split("_")[3],"domain":domain,"subset":subset,"variable":variable,
    "n_grids":len(dd),"mean":dd[variable].mean(),"q25":dd[variable].quantile(.25),"median":dd[variable].median(),"q75":dd[variable].quantile(.75),
    "min":dd[variable].min(),"max":dd[variable].max()})
joined_all=pd.concat(allrows,ignore_index=True)
csv(PROC/"graygreen_LST_joined_all_dates.csv",joined_all)
csv(OUT/"graygreen_LST_spearman_descriptive.csv",pd.DataFrame(stats))
csv(OUT/"graygreen_LST_coverage_by_date_domain.csv",pd.DataFrame(coverage))
csv(OUT/"graygreen_LST_missingness_descriptive.csv",pd.DataFrame(missing))
receipt={"status":"DESCRIPTIVE_ASSOCIATIONS_COMPLETE","created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"proposal_basis":"218 section 3.6; contemporaneous thermal context for gray-green organization",
"primary_scene":SCENES[0],"comparison_scenes":SCENES[1:],"predictors":["SSI","E_fraction"],"response":"LST_mean_C",
"observation_unit":"One full 1000m square per date. Three habitat rows deduplicated. Product pixels and repeated dates not counted as independent grid replication.",
"correlation":"Unweighted Spearman coefficient with average ranks for ties; no added transformations or thermal coverage thresholds.",
"statistical_inference":"Descriptive coefficients only. No ordinary iid P values, confidence intervals, spatial significance, or causal/whole-ER validation claim.",
"selection_rule":dedup["eligible_rule"],"quadrant_definition":str((PROC/"quadrant_definition.json").relative_to(ROOT)),
"deduplication":dedup,"inputs":inputs,"versions":{"numpy":np.__version__,"pandas":pd.__version__,"scipy":scipy.__version__,"geopandas":gpd.__version__},
"output_paths":[str(x.relative_to(ROOT)) for x in sorted(OUT.glob("*.csv"))]}
dump(PROC/"association_receipt.json",receipt)
print(pd.DataFrame(stats).query("domain == 'ALL'").to_string(index=False))
print(pd.DataFrame(coverage)[["date","domain","n_eligible_graygreen_grids","n_paired_grids","valid_area_fraction_of_eligible_full_grids"]].to_string(index=False))
print("ASSOCIATION COMPLETE")
