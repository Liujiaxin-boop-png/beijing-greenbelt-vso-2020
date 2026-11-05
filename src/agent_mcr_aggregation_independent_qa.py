"""Independently audit real native MCR -> full-square area aggregation.

This audit imports no production aggregation function. Native pixel polygons
are intersected with frozen full-square geometries using GEOS/Shapely. It is
a deterministic stratified sample audit, not ecological external validation.
No modeled or missing MCR value is invented and no production output is edited.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import time
import traceback
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "02_过程文件"
RESULT = ROOT / "03_结果文件"
REPORT = WORK / "mcr_aggregation_independent_QA.json"
DETAIL = WORK / "aggregation/mcr_independent_sample_comparisons.csv"
H_CODES = {"forest_shrub": (2, 3), "grassland": (4,), "water_wetland": (5, 9)}
LAND_NAMES = {"clcd": "clcd2020.tif", "wc": "worldcover2020_common30m.tif"}
NUMERIC_FIELDS = (
    "habitat_m2", "MCR_valid_m2", "MCR_valid_fraction", "MCR",
    "MCR_partial_mean", "MCR_euclidean_m", "target_truncated_fraction",
    "destination_truncated_fraction",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump_report(report):
    REPORT.parent.mkdir(exist_ok=True, parents=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                 allow_nan=False), encoding="utf-8")


def finite(value):
    try:
        return math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def is_nodata(value, nodata):
    return not finite(value) or (nodata is not None and
                                ((math.isnan(nodata) and math.isnan(value)) or value == nodata))


def tolerance(field, expected):
    # Explicit numerical comparison tolerances, not scientific thresholds.
    if field.endswith("m2"):
        return 1e-5 + abs(expected) * 1e-10
    return 1e-8 + abs(expected) * 1e-10


def choose_samples(frame, grid_by_key):
    """Select observed strata; absent no-alternative-source strata stay absent."""
    chosen = defaultdict(set)
    inventory = {}
    for scale, part in frame.groupby("scale_m", sort=True):
        part = part.copy()
        part["scope_fraction"] = [
            grid_by_key[(int(scale), gid)]["scope_area_m2"] /
            grid_by_key[(int(scale), gid)]["grid_area_m2"] for gid in part.grid_id]
        part["boundary"] = part.scope_fraction < 1 - 1e-10
        counts = Counter(part.MCR_status)
        inventory[str(int(scale))] = {"status_counts": dict(counts),
                                    "boundary_grid_n": int(part.boundary.sum()),
                                    "strata": {}}

        def pick(label, subset, sort_cols, ascending=True, number=1):
            inventory[str(int(scale))]["strata"][label] = {"available_n": len(subset)}
            if not len(subset):
                inventory[str(int(scale))]["strata"][label]["selected_ids"] = []
                return
            selected = subset.sort_values(sort_cols + ["grid_id"], ascending=ascending).head(number)
            gids = []
            for _, row in selected.iterrows():
                chosen[(int(scale), row.grid_id)].add(label)
                gids.append(row.grid_id)
            inventory[str(int(scale))]["strata"][label]["selected_ids"] = gids

        valid = part[part.MCR_status == "VALID"]
        pick("valid_boundary_min_scope", valid[valid.boundary], ["scope_fraction"])
        pick("valid_boundary_max_scope", valid[valid.boundary], ["scope_fraction"], False)
        pick("valid_interior_low_cost", valid[~valid.boundary], ["MCR"])
        pick("valid_interior_high_cost", valid[~valid.boundary], ["MCR"], False)
        pick("valid_smallest_habitat", valid, ["habitat_m2"])
        pick("valid_largest_habitat", valid, ["habitat_m2"], False)
        pick("valid_median_cost", valid.assign(median_distance=(valid.MCR-valid.MCR.median()).abs()),
             ["median_distance"])
        pick("truncated_target", valid[valid.target_truncated_fraction > 0],
             ["target_truncated_fraction"], False)
        pick("truncated_destination", valid[valid.destination_truncated_fraction > 0],
             ["destination_truncated_fraction"], False)
        no_h = part[part.MCR_status == "NO_FOCAL_HABITAT"]
        pick("no_focal_boundary", no_h[no_h.boundary], ["scope_fraction"])
        pick("no_focal_interior", no_h[~no_h.boundary], ["grid_id"])
        partial = part[part.MCR_status == "PARTIAL_OR_NO_ALTERNATIVE_SOURCE"]
        pick("no_alternative_or_partial_boundary", partial[partial.boundary],
             ["MCR_valid_fraction"], number=2)
        pick("no_alternative_or_partial_interior", partial[~partial.boundary],
             ["MCR_valid_fraction"], number=2)
    return chosen, inventory


def independent_grid(grid, datasets, truncated_ids):
    """Polygon intersections, scalar math.fsum, and raw land-class support."""
    parent_ds, cost_ds, dest_ds, distance_ds, land_ds = datasets
    square = box(*grid["bounds"])
    aff = parent_ds.transform
    inv = ~aff
    coords = [inv * xy for xy in square.exterior.coords]
    c0 = max(0, math.floor(min(x for x, y in coords)) - 1)
    r0 = max(0, math.floor(min(y for x, y in coords)) - 1)
    c1 = min(parent_ds.width, math.ceil(max(x for x, y in coords)) + 1)
    r1 = min(parent_ds.height, math.ceil(max(y for x, y in coords)) + 1)
    window = Window(c0, r0, c1-c0, r1-r0)
    parent, cost, dest, distance, land = [ds.read(1, window=window) for ds in datasets]
    land_valid = land_ds.read_masks(1, window=window) > 0
    h_codes = H_CODES[grid["habitat"]]
    terms = defaultdict(list)
    pixel_counts = Counter()
    observed_parents = set()
    invalid_parents = set()
    for rr in range(r1-r0):
        for cc in range(c1-c0):
            row, col = r0+rr, c0+cc
            pixel = Polygon([aff*(col, row), aff*(col+1, row),
                             aff*(col+1, row+1), aff*(col, row+1)])
            area = square.intersection(pixel).area
            if area <= 0:
                continue
            terms["covered"].append(area)
            pixel_counts["all_intersected_pixels"] += 1
            pid = int(parent[rr, cc])
            habitat = bool(land_valid[rr, cc] and land[rr, cc] in h_codes)
            if habitat != (pid > 0):
                raise AssertionError(f"parent/H mismatch at native pixel {row},{col}")
            if not habitat:
                continue
            pixel_counts["focal_pixels"] += 1
            observed_parents.add(pid)
            terms["habitat"].append(area)
            if pid in truncated_ids:
                terms["target_truncated"].append(area)
            cv, did, dv = float(cost[rr, cc]), int(dest[rr, cc]), float(distance[rr, cc])
            valid = not is_nodata(cv, cost_ds.nodata) and did > 0
            if not valid:
                pixel_counts["invalid_focal_pixels"] += 1
                invalid_parents.add(pid)
                continue
            if did == pid:
                raise AssertionError(f"same-parent destination at native pixel {row},{col}")
            if is_nodata(dv, distance_ds.nodata):
                raise AssertionError("valid-cost pixel has invalid Euclidean companion")
            pixel_counts["valid_focal_pixels"] += 1
            terms["valid"].append(area)
            terms["cost_x_area"].append(cv * area)
            terms["distance_x_area"].append(dv * area)
            if did in truncated_ids:
                terms["destination_truncated"].append(area)
    sums = {key: math.fsum(value) for key, value in terms.items()}
    ha, va = sums.get("habitat", 0.0), sums.get("valid", 0.0)
    covered = sums.get("covered", 0.0)
    if not math.isclose(covered, square.area, abs_tol=1e-5, rel_tol=1e-10):
        raise AssertionError("full square extends beyond native raster coverage")
    complete = ha > 0 and abs(va-ha) <= 1e-5 + 1e-10*abs(ha)
    numerator = sums.get("cost_x_area", 0.0)
    computed = {
        "habitat_m2": ha, "MCR_valid_m2": va,
        "MCR_valid_fraction": va/ha if ha else None,
        "MCR": numerator/ha if complete else None,
        "MCR_partial_mean": numerator/va if va else None,
        "MCR_euclidean_m": sums.get("distance_x_area", 0.0)/ha if complete else None,
        "target_truncated_fraction": sums.get("target_truncated", 0.0)/ha if ha else None,
        "destination_truncated_fraction": sums.get("destination_truncated", 0.0)/va if va else None,
        "MCR_status": "VALID" if complete else "NO_FOCAL_HABITAT" if not ha else
                      "PARTIAL_OR_NO_ALTERNATIVE_SOURCE",
    }
    diagnostics = {
        "full_square_geometric_area_m2": square.area,
        "native_pixel_intersection_area_m2": covered,
        "scope_area_m2": grid["scope_area_m2"],
        "pixel_counts": dict(pixel_counts),
        "focal_parent_n": len(observed_parents),
        "invalid_parent_ids": sorted(invalid_parents),
        "parent_and_landcover_H_support_agree": True,
        "valid_destinations_exclude_focal_parent": True,
    }
    return computed, diagnostics


def check_native_no_alternative(records, datasets, source_path, grid_geometries,
                                grid_tree, grids, table):
    """Inspect real undefined parent pixels even if outside all study squares."""
    bad = [r for r in records if r["status"] != "VALID"]
    if not bad:
        return []
    parent_ds, cost_ds, dest_ds, distance_ds, land_ds = datasets
    full_parent = parent_ds.read(1)
    with rasterio.open(source_path) as ds:
        assert ds.transform == parent_ds.transform and ds.shape == parent_ds.shape
        source_ids = set(map(int, np.unique(ds.read(1)))) - {0}
    checks = []
    for record in bad:
        pid = int(record["parent_id"])
        rows, cols = np.where(full_parent == pid)
        assert len(rows) > 0
        c0, c1, r0, r1 = int(cols.min()), int(cols.max()+1), int(rows.min()), int(rows.max()+1)
        win = Window(c0, r0, c1-c0, r1-r0)
        focus = full_parent[r0:r1, c0:c1] == pid
        cv, did, dv = [ds.read(1, window=win)[focus] for ds in datasets[1:4]]
        assert all(is_nodata(float(v), cost_ds.nodata) for v in cv), "undefined native parent contains filled cost"
        assert np.all(did <= 0), "undefined native parent contains a selected destination"
        assert all(is_nodata(float(v), distance_ds.nodata) for v in dv), "undefined native parent contains filled distance"
        affected = defaultdict(list)
        for row, col in zip(rows, cols):
            aff = parent_ds.transform
            pixel = Polygon([aff*(int(col), int(row)), aff*(int(col)+1, int(row)),
                             aff*(int(col)+1, int(row)+1), aff*(int(col), int(row)+1)])
            for idx in grid_tree.query(pixel):
                area = pixel.intersection(grid_geometries[int(idx)]).area
                if area > 0:
                    grid = grids[int(idx)]
                    affected[(int(grid["scale_m"]), grid["grid_id"])].append(area)
        affected_rows = []
        for key, values in sorted(affected.items()):
            area = math.fsum(values)
            observed = table.loc[key]
            assert observed.MCR_status == "PARTIAL_OR_NO_ALTERNATIVE_SOURCE" and pd.isna(observed.MCR)
            affected_rows.append({"scale_m": key[0], "grid_id": key[1], "undefined_habitat_m2": area})
        checks.append({"parent_id": pid, "native_record_status": record["status"],
                       "native_pixels_checked": len(rows), "native_parent_area_m2": len(rows)*abs(parent_ds.transform.determinant),
                       "cost_and_distance_all_original_nodata": True, "no_destination_selected": True,
                       "other_selected_source_parent_n": len(source_ids-{pid}),
                       "intersecting_study_full_grids_n": len(affected_rows),
                       "intersecting_grids": affected_rows,
                       "interpretation": "Actual native undefined case; if zero study-square intersections, this NA is outside the reporting grid domain and no absent grid case is manufactured"})
    return checks


def main():
    started = time.time()
    report = {
        "status": "RUNNING", "started_unix": started,
        "audit_scope": "Independent stratified numerical/spatial aggregation audit, not external ecological validation",
        "method": "Native Albers raster pixel polygons intersect frozen complete 1000m/500m squares in GEOS; scalar math.fsum; raw land classes independently identify H",
        "no_production_function_import": True,
        "NTL_dependency": False,
        "support": "Whole-square focal-habitat pixel area; study-boundary intersections only select/describe boundary samples, never replace aggregation support",
        "missing_policy": "Partial/no-alternative native support leaves primary MCR NA; partial mean remains separate; zero is never substituted",
        "sample_limit": "Observed deterministic strata from every published scenario and both scales; not an exhaustive recomputation of all grid values",
        "numerical_tolerances": {"completeness_area_m2": "1e-5 + 1e-10 * habitat_area", "comparison_area_m2": "1e-5 + 1e-10 * abs(expected)", "comparison_other": "1e-8 + 1e-10 * abs(expected)"},
        "interpretation": "MCR habitat_m2 is actual focal land-class pixel area inside a full square. Later valid/lowest-class study or township grid-cover areas are different quantities; habitat-specific reporting domains may overlap and must not be added.",
    }
    queue_path = WORK / "mcr_inputs/regional_queue.json"
    aggregate_receipt_path = WORK / "aggregation/mcr_aggregation_receipt.json"
    published_path = RESULT / "mcr/published_mcr_manifest.json"
    csv_path = RESULT / "indicators/mcr_by_grid.csv"
    grid_path = WORK / "spatial/grid_identity.json"
    required = [queue_path, aggregate_receipt_path, published_path, csv_path, grid_path]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        report.update(status="BLOCKED", missing=missing)
        dump_report(report)
        return 2
    queue, aggregate_receipt, published = map(read_json, required[:3])
    pending = aggregate_receipt.get("pending", [])
    if (aggregate_receipt.get("status") != "COMPLETE" or pending or
            published.get("status") != "COMPLETE_VERIFIED_PUBLISHED_COPY"):
        report.update(status="BLOCKED", reason="Final native publication and grid aggregation not complete",
                      aggregate_status=aggregate_receipt.get("status"), pending=pending,
                      published_status=published.get("status"))
        dump_report(report)
        return 2
    tasks = queue["tasks"]
    scenarios = [t["scenario"] for t in tasks]
    assert len(tasks) == len(set(scenarios)) == 15, "expected frozen 15 scenarios"
    assert set(aggregate_receipt["completed"]) == set(scenarios)
    pub_by_scenario = {s["scenario"]: s for s in published["scenarios"]}
    assert set(pub_by_scenario) == set(scenarios)
    inputs = {}

    def snapshot(path):
        path = Path(path).resolve()
        key = str(path)
        if key not in inputs:
            stat = path.stat()
            inputs[key] = {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256(path)}
        return inputs[key]

    for p in required + [Path(__file__), ROOT / "05_代码/src/aggregate_mcr.py"]:
        snapshot(p)
    grids = read_json(grid_path)["grids"]
    grid_by_key = {(int(g["scale_m"]), g["grid_id"]): g for g in grids}
    grid_geometries = [box(*g["bounds"]) for g in grids]
    grid_tree = STRtree(grid_geometries)
    assert len(grid_by_key) == len(grids)
    data = pd.read_csv(csv_path, encoding="utf-8-sig")
    assert len(data) == len(grids)*15 == aggregate_receipt["rows"]
    assert not data.duplicated(["scenario", "scale_m", "grid_id"]).any()
    assert set(data.scenario) == set(scenarios)
    detail_rows, scenario_results, failures = [], [], []
    max_errors = {k: 0.0 for k in NUMERIC_FIELDS}
    numeric_comparisons, na_comparisons = 0, 0
    for task in tasks:
        scenario = task["scenario"]
        part = data[data.scenario == scenario].copy()
        assert set(zip(part.scale_m.astype(int), part.grid_id)) == set(grid_by_key)
        cfg_path = Path(task["config"])
        cfg = read_json(cfg_path)
        snapshot(cfg_path)
        assert set(part["product"]) == {cfg["product"]}
        assert set(part["habitat"]) == {cfg["habitat"]}
        assert cfg["synthetic_only"] is False
        native = WORK / "mcr_native" / scenario
        receipt_path = native / "mcr_run_receipt.json"
        native_receipt = read_json(receipt_path)
        assert native_receipt["status"] == "COMPLETE" and native_receipt["synthetic_only"] is False
        snapshot(receipt_path)
        paths = [Path(cfg["parent_raster"]), native/"mcr_patch_min_cost.tif",
                 native/"mcr_patch_destination_parent.tif", native/"mcr_patch_euclidean_m.tif",
                 WORK/"spatial"/LAND_NAMES[cfg["product"]]]
        artifacts = {Path(a["process_original"]).name: a for a in pub_by_scenario[scenario]["artifacts"]}
        for p in paths:
            digest = snapshot(p)["sha256"]
            if p.name in artifacts:
                assert digest == artifacts[p.name]["sha256"], "native/published source-version mismatch"
        catalog_path = paths[0].parent/"parent_catalog.csv"
        snapshot(catalog_path)
        catalog = pd.read_csv(catalog_path)
        truncated_ids = set(int(r.parent_id) for r in catalog.itertuples()
                            if str(r.background_truncated).lower() == "true")
        chosen, availability = choose_samples(part, grid_by_key)
        table = part.set_index(["scale_m", "grid_id"])
        local_errors = {key: 0.0 for key in NUMERIC_FIELDS}
        local_diagnostics = []
        records_path = native/"mcr_patch_records.json"
        snapshot(records_path)
        native_records = read_json(records_path)
        assert sum(r["status"] != "VALID" for r in native_records) == native_receipt["nodata_parent_count"]
        if native_receipt["nodata_parent_count"]:
            snapshot(Path(cfg["source_parent_raster"]))
        with ExitStack() as stack:
            datasets = [stack.enter_context(rasterio.open(p)) for p in paths]
            reference = datasets[0]
            for ds in datasets:
                assert ds.transform == reference.transform and ds.shape == reference.shape and ds.crs == reference.crs
                assert ds.count == 1
            assert reference.crs.is_projected
            assert math.isclose(reference.transform.a, 30.0) and math.isclose(reference.transform.e, -30.0)
            native_na_checks = check_native_no_alternative(native_records, datasets, Path(cfg["source_parent_raster"]),
                                                           grid_geometries, grid_tree, grids, table)
            # Compare publication raster values on the audited windows without
            # invoking any production helper or trusting only filename/version.
            published_datasets = [stack.enter_context(rasterio.open(artifacts[p.name]["published"]))
                                  for p in paths[1:4]]
            for pds, nds in zip(published_datasets, datasets[1:4]):
                assert pds.transform == nds.transform and pds.shape == nds.shape and pds.crs == nds.crs
            for (scale, gid), reasons in sorted(chosen.items()):
                grid = dict(grid_by_key[(scale, gid)], habitat=cfg["habitat"])
                expected, diagnostic = independent_grid(grid, datasets, truncated_ids)
                observed = table.loc[(scale, gid)]
                bounds = grid["bounds"]
                win = rasterio.windows.from_bounds(*bounds, transform=reference.transform).round_offsets().round_lengths()
                for pds, nds in zip(published_datasets, datasets[1:4]):
                    assert np.array_equal(pds.read(1, window=win), nds.read(1, window=win), equal_nan=True)
                status_ok = expected["MCR_status"] == observed.MCR_status
                if not status_ok:
                    failures.append(f"{scenario}:{gid}: status mismatch")
                for field in NUMERIC_FIELDS:
                    exp, obs = expected[field], observed[field]
                    na = exp is None
                    okay = bool(pd.isna(obs)) if na else finite(obs) and abs(float(obs)-exp) <= tolerance(field, exp)
                    error = None if na or not finite(obs) else abs(float(obs)-exp)
                    if na:
                        na_comparisons += 1
                    else:
                        numeric_comparisons += 1
                    if error is not None:
                        max_errors[field] = max(max_errors[field], error)
                        local_errors[field] = max(local_errors[field], error)
                    if not okay:
                        failures.append(f"{scenario}:{gid}:{field} expected={exp} observed={obs}")
                    detail_rows.append({"scenario": scenario, "product": cfg["product"], "habitat": cfg["habitat"],
                                        "scale_m": scale, "grid_id": gid, "selection_strata": ";".join(sorted(reasons)),
                                        "field": field, "independent_expected": exp, "production_observed": float(obs) if finite(obs) else None,
                                        "absolute_difference": error, "pass": bool(okay),
                                        "native_derived_status": expected["MCR_status"], "production_status": observed.MCR_status,
                                        "status_pass": bool(status_ok), "scope_area_m2": grid["scope_area_m2"],
                                        "full_grid_area_m2": grid["grid_area_m2"]})
                local_diagnostics.append({"grid_id": gid, "scale_m": scale, "selection_strata": sorted(reasons),
                                          "native_derived_values": expected, **diagnostic})
        scenario_results.append({"scenario": scenario, "product": cfg["product"], "habitat": cfg["habitat"],
                                 "grid_rows_checked_structurally": len(part), "sample_n": len(chosen),
                                 "native_parent_counts": {"valid": native_receipt["valid_parent_count"],
                                                          "nodata": native_receipt["nodata_parent_count"]},
                                 "native_no_alternative_parent_checks": native_na_checks,
                                 "stratum_availability": availability, "max_absolute_differences": local_errors,
                                 "sample_diagnostics": local_diagnostics})
        print(json.dumps({"scenario": scenario, "samples": len(chosen), "status": "PASS" if not failures else "FAIL"}), flush=True)
    changed_inputs = []
    for key, entry in inputs.items():
        stat = Path(key).stat()
        if stat.st_size != entry["bytes"] or stat.st_mtime_ns != entry["mtime_ns"]:
            changed_inputs.append(key)
    # The whole CSV is hashed again; native rasters are frozen publication
    # inputs and are checked for writes by size+mtime throughout this audit.
    if sha256(csv_path) != inputs[str(csv_path.resolve())]["sha256"]:
        changed_inputs.append(str(csv_path))
    failures.extend("input changed during audit: "+p for p in changed_inputs)
    DETAIL.parent.mkdir(exist_ok=True, parents=True)
    pd.DataFrame(detail_rows).to_csv(DETAIL, index=False, encoding="utf-8-sig")
    report.update(status="PASS" if not failures else "FAIL", elapsed_seconds=time.time()-started,
                  scenarios_n=len(scenario_results), complete_structural_grid_rows=len(data),
                  grid_samples_n=sum(r["sample_n"] for r in scenario_results),
                  numeric_field_comparisons=numeric_comparisons, missing_value_comparisons=na_comparisons,
                  max_absolute_differences=max_errors, failures=failures,
                  native_publication_sample_values_identical=True,
                  input_stability="All snapshots retained size+mtime; production CSV rehashed at finish",
                  scenario_results=scenario_results, input_snapshots=inputs,
                  sample_comparison_csv=str(DETAIL), sample_comparison_sha256=sha256(DETAIL))
    dump_report(report)
    print(json.dumps({k: report[k] for k in ["status", "scenarios_n", "grid_samples_n", "numeric_field_comparisons", "missing_value_comparisons", "max_absolute_differences"]}), flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        dump_report({"status": "FAIL", "error": repr(error), "traceback": traceback.format_exc(),
                     "scope": "Independent numerical/spatial MCR aggregation audit; production data unmodified"})
        raise
