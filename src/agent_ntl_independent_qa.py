"""Independent audit of actual EOG 2020 v2.1 whole-square NTL aggregation.

Run only after the official paired originals have been archived and the
production aggregation has completed. This script never downloads, extracts,
copies, alters raw products, imports a production function, or generates NTL.
It reads native pixels from the archived originals and checks real grid rows.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import re
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "02_过程文件/aggregation"
REPORT = WORK / "ntl_independent_QA.json"
DETAIL = WORK / "ntl_independent_sample_comparisons.csv"
CONFIG = WORK / "ntl_inputs.json"
PRODUCTION_RECEIPT = WORK / "ntl_aggregation_receipt.json"
PRODUCTION_CSV = ROOT / "03_结果文件/indicators/ntl_by_grid.csv"
NAME = re.compile(r"^(VNL_v21_npp_2020_global_vcmslcfg_c\d{12})\.(average_masked|cf_cvg)\.dat\.tif$")
# Two exact encodings, not a widened tolerance interval. The second is the
# independently observed 10-decimal GeoTIFF header of both archived official
# 2020 release c202205302300 originals. All geometry uses ds.transform itself.
ACCEPTED_NATIVE_STEPS_DEG = (15.0/3600.0, 0.0041666667)
VALUE_FIELDS = ("NTL", "NTL_partial_mean", "cf_cvg_mean", "ntl_valid_fraction",
                "ntl_grid_area_m2", "ntl_valid_area_m2", "ntl_source_footprint_area_m2",
                "ntl_n_native_pixels", "ntl_n_valid_native_pixels",
                "ntl_numerical_area_tolerance_m2")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_report(value):
    REPORT.parent.mkdir(exist_ok=True, parents=True)
    REPORT.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def resolve(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT/p


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(16*1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(value):
    return value is not None and math.isfinite(float(value))


def truth(value):
    if str(value).lower() not in {"true", "false"}:
        raise ValueError("Unexpected complete-support boolean: "+str(value))
    return str(value).lower() == "true"


def scalar_valid(radiance, count, radiance_mask, count_mask):
    return bool(radiance_mask and count_mask and finite(radiance) and finite(count) and count > 0)


def pixel_polygon(transform, row, col, transformer, divisions):
    """Build each geographic cell edge separately, then project scalar points."""
    corners = [(col, row), (col+1, row), (col+1, row+1), (col, row+1)]
    projected = []
    for edge in range(4):
        x0, y0 = corners[edge]
        x1, y1 = corners[(edge+1) % 4]
        for n in range(divisions):
            fraction = n/divisions
            lon, lat = transform*(x0+(x1-x0)*fraction, y0+(y1-y0)*fraction)
            projected.append(transformer.transform(lon, lat))
    polygon = Polygon(projected)
    if not polygon.is_valid or polygon.area <= 0:
        raise ValueError("Invalid native pixel footprint")
    return polygon


def native_window(bounds, native_transformer, raster, padding=2):
    xmin, ymin, xmax, ymax = native_transformer.transform_bounds(*bounds, densify_pts=65)
    inverse = ~raster.transform
    col0, row0 = inverse*(xmin, ymax)
    col1, row1 = inverse*(xmax, ymin)
    c0, r0 = math.floor(col0)-padding, math.floor(row0)-padding
    c1, r1 = math.ceil(col1)+padding, math.ceil(row1)+padding
    if c0 < 0 or r0 < 0 or c1 > raster.width or r1 > raster.height:
        raise ValueError("Original native grid does not fully cover the required square")
    return Window(c0, r0, c1-c0, r1-r0)


def independent_square(grid, radiance_ds, count_ds, to_native, to_albers, divisions):
    square = box(*grid["bounds"])
    window = native_window(grid["bounds"], to_native, radiance_ds)
    radiance = radiance_ds.read(1, window=window)
    counts = count_ds.read(1, window=window)
    rmask = radiance_ds.read_masks(1, window=window)
    cmask = count_ds.read_masks(1, window=window)
    terms = defaultdict(list)
    native_n = valid_n = zero_n = negative_n = 0
    valid_zero_area = 0.0
    invalid_cases = Counter()
    for rr in range(int(window.height)):
        for cc in range(int(window.width)):
            row, col = int(window.row_off)+rr, int(window.col_off)+cc
            footprint = pixel_polygon(radiance_ds.transform, row, col, to_albers, divisions)
            area = square.intersection(footprint).area
            if area <= 0:
                continue
            native_n += 1
            terms["all_area"].append(area)
            value, count = float(radiance[rr, cc]), float(counts[rr, cc])
            valid = scalar_valid(value, count, rmask[rr, cc] > 0, cmask[rr, cc] > 0)
            if not valid:
                if not rmask[rr, cc]: invalid_cases["radiance_original_mask_invalid"] += 1
                if not cmask[rr, cc]: invalid_cases["count_original_mask_invalid"] += 1
                if finite(count) and count <= 0: invalid_cases["nonpositive_observation_count"] += 1
                if not finite(value) or not finite(count): invalid_cases["nonfinite"] += 1
                continue
            if count < 0 or abs(count-round(count)) > 1e-6:
                raise ValueError("Observation counts are not raw integer counts")
            valid_n += 1
            terms["valid_area"].append(area)
            terms["radiance_area"].append(value*area)
            terms["count_area"].append(count*area)
            terms["count_radiance_area"].append(count*value*area)
            if value == 0:
                zero_n += 1
                valid_zero_area += area
            if value < 0:
                negative_n += 1
    sums = {k: math.fsum(v) for k, v in terms.items()}
    observed_area, full_area = sums.get("valid_area", 0.0), square.area
    numerical_tolerance = max(1e-6, full_area*1e-10)
    if abs(sums.get("all_area", 0)-full_area) > numerical_tolerance:
        raise ValueError("Independent native polygons fail to partition the complete square")
    complete = abs(full_area-observed_area) <= numerical_tolerance
    mean = sums.get("radiance_area", 0)/observed_area if observed_area else None
    mean_count = sums.get("count_area", 0)/observed_area if observed_area else None
    values = {
        "NTL": mean if complete else None, "NTL_partial_mean": mean,
        "cf_cvg_mean": mean_count, "ntl_support_complete": complete,
        "ntl_valid_fraction": min(1.0, max(0.0, observed_area/full_area)),
        "ntl_grid_area_m2": full_area, "ntl_valid_area_m2": observed_area,
        "ntl_source_footprint_area_m2": sums.get("all_area", 0.0),
        "ntl_n_native_pixels": native_n, "ntl_n_valid_native_pixels": valid_n,
        "ntl_numerical_area_tolerance_m2": numerical_tolerance,
    }
    diagnostic = {
        "edge_divisions": divisions, "valid_zero_pixels": zero_n,
        "valid_zero_area_m2": valid_zero_area, "valid_negative_pixels": negative_n,
        "invalid_native_pixel_cases": dict(invalid_cases),
        "count_weighted_mean_counterfactual_NOT_USED": sums.get("count_radiance_area", 0)/sums["count_area"] if sums.get("count_area", 0) else None,
    }
    return values, diagnostic


def sample_rows(frame, grid_lookup):
    selected = defaultdict(set)
    strata = {}
    for scale, part in frame.groupby("scale_m"):
        part = part.copy()
        part["scope_fraction"] = [grid_lookup[(int(scale), gid)]["scope_area_m2"] /
                                  grid_lookup[(int(scale), gid)]["grid_area_m2"] for gid in part.grid_id]
        complete = part[part.ntl_support_complete.map(truth)]
        boundary = part.scope_fraction < 1-1e-10

        def pick(label, subset, column, ascending=True):
            strata[str(int(scale))+":"+label] = len(subset)
            if len(subset):
                row = subset.sort_values([column, "grid_id"], ascending=ascending).iloc[0]
                selected[(int(scale), row.grid_id)].add(label)

        pick("boundary_min_scope", part[boundary], "scope_fraction")
        pick("boundary_max_scope", part[boundary], "scope_fraction", False)
        pick("interior_low_NTL", part[~boundary & part.NTL.notna()], "NTL")
        pick("interior_high_NTL", part[~boundary & part.NTL.notna()], "NTL", False)
        pick("overall_low_NTL", complete, "NTL")
        pick("overall_high_NTL", complete, "NTL", False)
        pick("median_NTL", complete.assign(median_delta=(complete.NTL-complete.NTL.median()).abs()), "median_delta")
        pick("low_mean_observation_count", part[part.cf_cvg_mean.notna()], "cf_cvg_mean")
        pick("high_mean_observation_count", part[part.cf_cvg_mean.notna()], "cf_cvg_mean", False)
        pick("zero_grid_NTL", part[part.NTL == 0], "scope_fraction")
        pick("negative_grid_NTL", part[part.NTL < 0], "NTL")
        pick("partial_support", part[(part.ntl_valid_fraction > 0) & ~part.ntl_support_complete.map(truth)], "ntl_valid_fraction")
        pick("no_valid_support", part[part.ntl_valid_fraction == 0], "scope_fraction")
        for axis in (0, 1):
            part["center_coordinate"] = [(grid_lookup[(int(scale), gid)]["bounds"][axis] +
                                         grid_lookup[(int(scale), gid)]["bounds"][axis+2])/2 for gid in part.grid_id]
            pick("coordinate_"+str(axis)+"_min", part, "center_coordinate")
            pick("coordinate_"+str(axis)+"_max", part, "center_coordinate", False)
    return selected, strata


def add_observed_pixel_cases(selected, grids, radiance_ds, counts_ds, to_native, to_albers):
    geometries = [box(*g["bounds"]) for g in grids]
    tree = STRtree(geometries)
    bounds = (min(g["bounds"][0] for g in grids), min(g["bounds"][1] for g in grids),
              max(g["bounds"][2] for g in grids), max(g["bounds"][3] for g in grids))
    window = native_window(bounds, to_native, radiance_ds)
    radiance, counts = radiance_ds.read(1, window=window), counts_ds.read(1, window=window)
    rmask, cmask = radiance_ds.read_masks(1, window=window) > 0, counts_ds.read_masks(1, window=window) > 0
    known_counts = cmask & np.isfinite(counts)
    assert not np.any(counts[known_counts] < 0)
    assert not np.any(np.abs(counts[known_counts]-np.rint(counts[known_counts])) > 1e-6)
    valid = rmask & cmask & np.isfinite(radiance) & np.isfinite(counts) & (counts > 0)
    masks = {"native_valid_zero": valid & (radiance == 0),
             "native_valid_negative": valid & (radiance < 0),
             "native_invalid_observation": ~valid}
    availability = {}
    for label, mask in masks.items():
        candidates = np.argwhere(mask)
        added_scales = set()
        touched_n = 0
        for rr, cc in candidates:
            footprint = pixel_polygon(radiance_ds.transform, int(window.row_off+rr),
                                      int(window.col_off+cc), to_albers, 32)
            for index in tree.query(footprint):
                i = int(index)
                if footprint.intersection(geometries[i]).area <= 0:
                    continue
                touched_n += 1
                g = grids[i]
                if g["scale_m"] not in added_scales:
                    selected[(int(g["scale_m"]), g["grid_id"])].add(label)
                    added_scales.add(g["scale_m"])
            if added_scales == {500, 1000}:
                break
        availability[label] = {"native_window_candidate_pixels": len(candidates),
                               "selected_scales": sorted(added_scales),
                               "has_actual_study_grid_intersection": touched_n > 0}
    return availability


def inspect_native_metadata(radiance, counts, archive_files):
    assert radiance.count == counts.count == 1
    assert radiance.shape == counts.shape and radiance.transform == counts.transform
    assert radiance.crs == counts.crs and radiance.crs.to_epsg() == 4326
    assert radiance.transform.a in ACCEPTED_NATIVE_STEPS_DEG
    assert radiance.transform.e == -radiance.transform.a
    assert radiance.transform.b == radiance.transform.d == 0
    assert all(ds.scales[0] == 1 and ds.offsets[0] == 0 for ds in [radiance, counts])
    if radiance.nodata == 0:
        raise ValueError("Original radiance metadata declares zero NoData: product semantics require review before any zero masking decision")
    output = {}
    for key, ds in [("average_masked", radiance), ("cf_cvg", counts)]:
        archived = archive_files[key]["metadata"]
        assert list(ds.transform) == archived["transform"], "Original affine differs from archive receipt"
        assert list(ds.shape) == archived["shape"], "Original dimensions differ from archive receipt"
        assert ds.nodata == archived["nodata"], "Original NoData differs from archive receipt"
        nd = ds.nodata
        output[key] = {"shape": list(ds.shape), "transform": list(ds.transform), "crs": ds.crs.to_wkt(),
                       "resolution_degrees": list(ds.res), "dtype": ds.dtypes[0],
                       "nodata": str(nd) if nd is not None and not math.isfinite(nd) else nd,
                       "scale": ds.scales[0], "offset": ds.offsets[0], "unit_metadata": ds.units[0],
                       "mask_flags": [str(x) for x in ds.mask_flag_enums[0]],
                       "complete_original_affine_matches_archive": True,
                       "resolution_encoding": "mathematical_15_arcseconds" if ds.transform.a == 15.0/3600.0 else "official_observed_10_decimal_encoding"}
    return output


def check_saved_native_windows(production, paths):
    window = Window(*production["window"])
    summary = {}
    original_values, masks = {}, {}
    for key, path in paths.items():
        derived = WORK/"ntl_native"/(production["release"]+"."+key+"_native_window.tif")
        with rasterio.open(path) as source, rasterio.open(derived) as clip:
            expected = source.read(1, window=window)
            expected_mask = source.read_masks(1, window=window)
            assert clip.transform == source.window_transform(window)
            assert clip.crs == source.crs and clip.shape == expected.shape
            assert np.array_equal(clip.read(1), expected, equal_nan=True)
            assert np.array_equal(clip.read_masks(1), expected_mask)
            original_values[key], masks[key] = expected, expected_mask > 0
            summary[key] = {"native_clip_identical_to_original_pixels": True,
                            "original_mask_preserved": True, "shape": list(expected.shape)}
    raw, n = original_values["average_masked"], original_values["cf_cvg"]
    valid = masks["average_masked"] & masks["cf_cvg"] & np.isfinite(raw) & np.isfinite(n) & (n > 0)
    zero_n = int(np.count_nonzero(valid & (raw == 0)))
    negative_n = int(np.count_nonzero(valid & (raw < 0)))
    assert zero_n == production["observed_zero_native_pixels_in_window"]
    assert negative_n == production["observed_negative_native_pixels_in_window"]
    summary["jointly_valid_zero_pixels"] = zero_n
    summary["jointly_valid_negative_pixels"] = negative_n
    return summary


def numeric_equal(field, expected, observed):
    if expected is None:
        return bool(pd.isna(observed)), None
    if not finite(observed):
        return False, None
    error = abs(expected-float(observed))
    if field.startswith("ntl_n_"):
        allowance = 0.0
    elif field.endswith("area_m2"):
        allowance = max(1e-6, abs(expected)*1e-10)
    else:
        allowance = 1e-8+abs(expected)*1e-9
    return error <= allowance, error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    args = parser.parse_args()
    missing = [str(p) for p in [args.config, PRODUCTION_RECEIPT, PRODUCTION_CSV] if not p.exists()]
    if missing:
        write_report({"status": "BLOCKED", "missing": missing, "observational_audit_run": False})
        return 2
    production = read_json(PRODUCTION_RECEIPT)
    if production.get("status") != "PASS":
        write_report({"status": "BLOCKED", "reason": "Real production aggregation is not PASS",
                      "production_status": production.get("status"), "observational_audit_run": False})
        return 2
    cfg = read_json(args.config)
    assert cfg.get("official_source_files_verified") is True
    paths = {k: resolve(cfg[k+"_tif"]) for k in ["average_masked", "cf_cvg"]}
    if not all(p.is_file() for p in paths.values()):
        write_report({"status": "BLOCKED", "reason": "Archived official pair absent", "observational_audit_run": False})
        return 2
    for key, path in paths.items():
        match = NAME.fullmatch(path.name)
        assert match and match.group(2) == key and match.group(1) == cfg["release_prefix"] == production["release"]
        url = urlparse(cfg[key+"_source_url"])
        assert url.scheme == "https" and url.hostname == "eogdata.mines.edu"
        assert not (url.query or url.fragment or url.username or url.password)
        assert url.path.startswith("/nighttime_light/annual/v21/2020/")
        assert unquote(url.path.rsplit("/", 1)[1]) in {path.name, path.name+".gz"}
    assert paths["average_masked"].parent.resolve() == paths["cf_cvg"].parent.resolve()
    archive_path = paths["average_masked"].parent/"来源与完整性核验.json"
    archive = read_json(archive_path)
    assert archive["status"] == "ORIGINAL_PAIR_COPIED_CRC_AND_HASH_VERIFIED"
    assert archive["release_prefix"] == production["release"]
    archive_files = {row["product"]: row for row in archive["files"]}
    assert set(archive_files) == set(paths)
    assert production["native_pixel_edge_segments"] == 8
    grid_path = ROOT/"02_过程文件/spatial/grid_identity.json"
    spatial_path = ROOT/"02_过程文件/spatial/native_config.json"
    grids = read_json(grid_path)["grids"]
    grid_lookup = {(int(g["scale_m"]), g["grid_id"]): g for g in grids}
    assert len(grids) == len(grid_lookup)
    crs = CRS.from_wkt(read_json(spatial_path)["crs_wkt"])
    assert crs == CRS(production["analysis_crs"])
    assert crs.is_projected and crs.coordinate_operation.method_name == "Albers Equal Area"
    to_albers, to_native = Transformer.from_crs(4326, crs, always_xy=True), Transformer.from_crs(crs, 4326, always_xy=True)
    snapshots = {}
    for path in list(paths.values()) + [args.config, PRODUCTION_CSV, PRODUCTION_RECEIPT, archive_path, grid_path, spatial_path, Path(__file__)]:
        stat = path.stat()
        snapshots[str(path.resolve())] = {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256(path)}
    for input_record in production["inputs"]:
        key = input_record["product"]
        assert paths[key].resolve() == resolve(input_record["path"]).resolve()
        assert snapshots[str(paths[key].resolve())]["sha256"] == input_record["sha256"]
        assert snapshots[str(paths[key].resolve())]["sha256"] == archive_files[key]["tif_sha256"]
        assert archive_files[key]["source_url"] == cfg[key+"_source_url"]
        assert archive_files[key]["gzip_crc_verified"] is True
    assert snapshots[str(PRODUCTION_CSV.resolve())]["sha256"] == production["result_sha256"]
    frame = pd.read_csv(PRODUCTION_CSV, encoding="utf-8-sig")
    assert len(frame) == len(grids) == production["rows"]
    assert not frame.duplicated(["scale_m", "grid_id"]).any()
    assert set(zip(frame.scale_m.astype(int), frame.grid_id)) == set(grid_lookup)
    assert np.array_equal(frame.NTL.notna(), frame.ntl_support_complete.map(truth))
    assert ((frame.ntl_valid_fraction >= 0) & (frame.ntl_valid_fraction <= 1)).all()
    assert (frame.ntl_n_valid_native_pixels <= frame.ntl_n_native_pixels).all()
    selected, strata = sample_rows(frame, grid_lookup)
    samples, comparisons, failures = [], [], []
    max_errors = {key: 0.0 for key in VALUE_FIELDS}
    table = frame.set_index(["scale_m", "grid_id"])
    with rasterio.open(paths["average_masked"]) as radiance, rasterio.open(paths["cf_cvg"]) as counts:
        metadata = inspect_native_metadata(radiance, counts, archive_files)
        native_cases = add_observed_pixel_cases(selected, grids, radiance, counts, to_native, to_albers)
        clip_checks = check_saved_native_windows(production, paths)
        for (scale, gid), reasons in sorted(selected.items()):
            grid = grid_lookup[(scale, gid)]
            same, same_diagnostic = independent_square(grid, radiance, counts, to_native, to_albers, 8)
            dense, _ = independent_square(grid, radiance, counts, to_native, to_albers, 32)
            finer, _ = independent_square(grid, radiance, counts, to_native, to_albers, 64)
            observed = table.loc[(scale, gid)]
            if same["ntl_support_complete"] != truth(observed.ntl_support_complete):
                failures.append(gid+": complete-support semantics differ")
            for field in VALUE_FIELDS:
                okay, error = numeric_equal(field, same[field], observed[field])
                if error is not None:
                    max_errors[field] = max(max_errors[field], error)
                if not okay:
                    failures.append(gid+":"+field+" differs")
                comparisons.append({"grid_id": gid, "scale_m": scale, "selection_strata": ";".join(sorted(reasons)),
                                    "field": field, "independent_expected": same[field],
                                    "production_observed": float(observed[field]) if finite(observed[field]) else None,
                                    "absolute_difference": error, "pass": bool(okay)})
            convergence = {}
            for label, first, second in [("8_to_32", same, dense), ("32_to_64", dense, finer)]:
                delta = {}
                for field in ["ntl_valid_area_m2", "NTL_partial_mean", "cf_cvg_mean"]:
                    a, b = first[field], second[field]
                    if a is None or b is None:
                        assert a is None and b is None
                        delta[field] = None
                        continue
                    delta[field] = abs(a-b)
                    allowed = 0.01 if field == "ntl_valid_area_m2" else 1e-7*max(1, abs(b))
                    if delta[field] > allowed:
                        failures.append(gid+":"+label+":"+field+" failed geometric convergence")
                convergence[label] = delta
            samples.append({"grid_id": gid, "scale_m": scale, "selection_strata": sorted(reasons),
                            "scope_area_m2": grid["scope_area_m2"], "whole_square_values": same,
                            "native_pixel_diagnostics": same_diagnostic, "edge_densification_convergence": convergence})
            print(json.dumps({"grid_id": gid, "scale_m": scale, "sample_checked": True}), flush=True)
    for path, snap in snapshots.items():
        stat = Path(path).stat()
        if stat.st_size != snap["bytes"] or stat.st_mtime_ns != snap["mtime_ns"]:
            failures.append("Input changed during audit: "+path)
    assert sha256(PRODUCTION_CSV) == production["result_sha256"]
    pd.DataFrame(comparisons).to_csv(DETAIL, index=False, encoding="utf-8-sig")
    report = {
        "status": "PASS" if not failures else "FAIL", "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "observational_audit_run": True, "production_functions_imported": False,
        "scope": "Independent numerical and spatial-support QA; not external ecological validation",
        "release": production["release"], "structural_grid_rows": len(frame),
        "sample_n": len(samples), "field_comparisons_n": len(comparisons),
        "missing_field_comparisons_n": sum(c["independent_expected"] is None for c in comparisons),
        "same_year_release_native_15_arcsecond_pair": True, "native_metadata": metadata,
        "resolution_recognition": {"allowed_exact_degree_encodings": list(ACCEPTED_NATIVE_STEPS_DEG),
                                   "widened_tolerance_interval": False, "original_affine_used_without_change": True,
                                   "archive_integrity_receipt": str(archive_path)},
        "zero_semantics": "A valid average_masked product zero with cf_cvg>0 is retained, including background-treated zeros; it is not interpreted as proof of no human activity",
        "quality_semantics": "Original masks, finite paired values, raw cf_cvg>0; no extra brightness cutoff or imputation; cf_cvg is never a radiance weight",
        "spatial_support": "Actual projected native geographic-cell intersections with complete frozen 1km/500m squares; study-area boundary is not used to clip the averaging square",
        "completeness": "Primary NTL only when valid area covers the complete square within max(1e-6m2, area*1e-10); partial mean retained separately",
        "independent_geometry": "Scalar native pixel polygon construction, GEOS intersection, math.fsum; 8 segments reproduces declared geometry independently; 32 and 64 test densification convergence",
        "comparison_tolerances": {"area": "max(1e-6m2, abs(expected)*1e-10)", "other": "1e-8+abs(expected)*1e-9", "pixel_counts": "exact", "convergence_area": "0.01m2", "convergence_mean": "1e-7*max(1,abs(refined))"},
        "max_absolute_differences": max_errors, "stratum_availability": strata,
        "native_case_availability": native_cases, "native_clip_checks": clip_checks,
        "samples": samples, "failures": failures, "inputs": snapshots,
        "input_stability": "All raw original hashes matched production receipt; unchanged size/mtime during audit; result CSV rehashed at finish",
        "comparison_csv": str(DETAIL), "comparison_csv_sha256": sha256(DETAIL),
        "absent_cases_policy": "Missing/negative/zero scenarios are tested only when present in actual originals; no artificial observations are written",
    }
    write_report(report)
    print(json.dumps({k: report[k] for k in ["status", "structural_grid_rows", "sample_n", "field_comparisons_n", "max_absolute_differences"]}), flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        write_report({"status": "FAIL", "error": repr(error), "traceback": traceback.format_exc(),
                      "production_data_modified": False, "scope": "Independent actual-input NTL audit"})
        raise
