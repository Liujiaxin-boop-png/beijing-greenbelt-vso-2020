"""Implementation checks only. Synthetic arrays never enter research results.
No downloaded NTL observations are claimed by this test.
"""
from pathlib import Path
import importlib.util, json, subprocess, sys
import numpy as np
from scipy import sparse
from affine import Affine
from pyproj import Transformer
import geopandas as gpd
import shapely

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ntl", Path(__file__).with_name("agent_ntl_aggregate.py"))
ntl = importlib.util.module_from_spec(spec); spec.loader.exec_module(ntl)
checks = []

weights = sparse.csr_matrix([[4., 6.], [10., 0.], [0., 10.]])
areas = np.full(3, 10.)
raw, counts = np.array([0., 4.]), np.array([2., 10.])
good = ntl.valid_pair(raw, counts, np.ones(2, bool), np.ones(2, bool))
result = ntl.aggregate_arrays(weights, areas, raw, counts, good, ["unit_a", "unit_b", "unit_c"], 1000)
assert np.allclose(result.NTL, [2.4, 0, 4])
assert np.allclose(result.cf_cvg_mean, [6.8, 2, 10])
assert result.ntl_support_complete.all()
assert result.NTL.iloc[0] != np.average(raw, weights=np.array([4, 6]) * counts)
checks.append("Observed zero brightness is retained and observation counts never weight radiance.")

invalid = ntl.valid_pair(raw, np.array([2., 0.]), np.ones(2, bool), np.ones(2, bool))
partial = ntl.aggregate_arrays(weights, areas, raw, counts, invalid, ["unit_a", "unit_b", "unit_c"], 1000)
assert np.array_equal(partial.NTL.notna(), [False, True, False])
assert np.isclose(partial.NTL_partial_mean.iloc[0], 0)
assert np.allclose(partial.ntl_valid_fraction, [.4, 1, 0])
checks.append("Any substantive unobserved part makes main NTL NA; partial zero is retained separately.")

masked = ntl.valid_pair(raw, counts, np.array([True, False]), np.ones(2, bool))
assert np.array_equal(masked, [True, False])
negative = ntl.aggregate_arrays(weights, areas, np.array([-2., 4.]), counts, good, ["unit_a", "unit_b", "unit_c"], 1000)
assert np.isclose(negative.NTL.iloc[0], 1.6)
checks.append("Explicit product masks are respected and no ad hoc brightness threshold is applied.")

try:
    ntl.valid_pair(raw, np.array([2., 0.3]), np.ones(2, bool), np.ones(2, bool))
except ValueError:
    checks.append("Noninteger cf_cvg is rejected rather than silently treated as raw counts.")
else:
    raise AssertionError("Fractional observation counts accepted")

# A real frozen grid supplies geometry only. Values below are explicit in-memory
# numeric test signals and never written as raster data or indicator observations.
g = gpd.read_file(ROOT / "02_过程文件/spatial/analysis.gdb", layer="grid_1000").iloc[:1].copy().reset_index(drop=True)
to_native = Transformer.from_crs(g.crs, 4326, always_xy=True)
lon, lat = to_native.transform(g.geometry.iloc[0].centroid.x, g.geometry.iloc[0].centroid.y)
transform = Affine(1/240, 0, lon - .04, 0, -1/240, lat + .04)
rr, cc = np.meshgrid(np.arange(20), np.arange(20), indexing="ij"); rr, cc = rr.ravel(), cc.ravel()
to_albers = Transformer.from_crs(4326, g.crs, always_xy=True)
p = ntl.source_polygons(transform, to_albers, rr, cc, 8)
fine = ntl.source_polygons(transform, to_albers, rr, cc, 16)
pi, gi = shapely.STRtree(g.geometry.values).query(p, predicate="intersects")
aa = shapely.area(shapely.intersection(p[pi], g.geometry.values[gi])); sel = aa > 0
m = sparse.coo_matrix((aa[sel], (gi[sel], pi[sel])), shape=(1, 400)).tocsr()
signal = (rr * .5 + cc).astype(float); nobs = np.full(400, 20.)
test = ntl.aggregate_arrays(m, g.area.to_numpy(), signal, nobs, np.ones(400, bool), g.Grid_ID, 1000)
independent = ntl.independent_grid_check(g, fine, signal, nobs, np.ones(400, bool), test)
assert test.ntl_support_complete.all()
checks.append("Native geographic pixels partition a real Albers square; independent twice-densified intersection agrees for an in-memory test signal.")

outpath = ROOT / "03_结果文件/indicators/ntl_by_grid.csv"
had_output = outpath.exists()
old_hash = ntl.sha(outpath) if had_output else None
run = subprocess.run([sys.executable, str(Path(__file__).with_name("agent_ntl_aggregate.py"))], capture_output=True, text=True)
assert run.returncode == 2 and "absent" in run.stderr
assert outpath.exists() == had_output
if had_output: assert ntl.sha(outpath) == old_hash
receipt = json.loads(ntl.RECEIPT.read_text(encoding="utf8"))
assert receipt["status"] != "PASS"
checks.append("Absent real inputs exit before any observational CSV or PASS receipt is created.")

report = {"implementation_test_status": "PASS", "observational_aggregation_status": "NOT_RUN_MISSING_ORIGINAL_INPUT_PAIR",
          "synthetic_test_arrays": "memory only; no synthetic observations or rasters in raw/results folders",
          "checks": checks, "geometric_test_independent_differences": independent,
          "main_receipt_status": receipt["status"], "real_indicator_created": False}
ntl.save_json(ROOT / "02_过程文件/aggregation/ntl_implementation_checks.json", report)
print("NTL_IMPLEMENTATION_CHECKS_PASS_REAL_INPUT_STILL_MISSING", flush=True)
