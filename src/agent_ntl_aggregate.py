"""Aggregate the actual original EOG 2020 v2.1 radiance/count pair.

No network, authentication, raster resampling, imputation, observation-count
weighting, or arbitrary brightness/valid-coverage threshold is used here.
The absent-input path stops before creating any indicator result or PASS.
Run with local Python 3.12 and rasterio/geopandas/shapely>=2/scipy/pyproj.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, math, re, sys
from urllib.parse import urlparse, unquote
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.windows import Window
from pyproj import CRS, Transformer
from scipy import sparse
import shapely

ROOT = Path(__file__).resolve().parents[2]
PROCESS = ROOT / "02_过程文件/aggregation"
WORK = PROCESS / "ntl_native"
RESULT = ROOT / "03_结果文件/indicators/ntl_by_grid.csv"
RECEIPT = PROCESS / "ntl_aggregation_receipt.json"
NAME = re.compile(r"^(VNL_v21_npp_2020_global_vcmslcfg_c[0-9]{12})\.(average_masked|cf_cvg)\.dat\.tif$")
NATIVE_RESOLUTION_DEG = 15.0 / 3600.0
EDGE_SEGMENTS = 8


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def rel(path):
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def fail_closed(status, message, config_path):
    record = {"status": status, "message": message, "config": rel(config_path),
              "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "indicator_result_created": False, "imputation": False}
    # A configuration-only attempt never invalidates an existing completed run.
    destination = RECEIPT
    if RECEIPT.exists() and json.loads(RECEIPT.read_text(encoding="utf8")).get("status") == "PASS":
        destination = PROCESS / "ntl_input_check_nonrun.json"
    save_json(destination, record)
    raise RuntimeError(message)


def resolve_input(s):
    if not isinstance(s, str) or not s.strip() or "REPLACE_" in s:
        return None
    p = Path(s)
    return p if p.is_absolute() else ROOT / p


def inspect_inputs(config_path):
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    paths = {k: resolve_input(config.get(k + "_tif")) for k in ["average_masked", "cf_cvg"]}
    absent = [k for k, p in paths.items() if p is None or not p.is_file()]
    if absent:
        fail_closed("BLOCKED_MISSING_INPUT", "Original EOG 2020 v2.1 input file(s) absent: " + ", ".join(absent), config_path)
    if config.get("official_source_files_verified") is not True:
        fail_closed("BLOCKED_UNVERIFIED_PROVENANCE", "Verify original EOG files/source URLs before aggregation.", config_path)
    prefixes = []
    for product, path in paths.items():
        match = NAME.fullmatch(path.name)
        if not match or match.group(2) != product:
            raise ValueError("Input must retain its original EOG 2020 v2.1 product filename: " + str(path))
        prefixes.append(match.group(1))
        u = urlparse(config.get(product + "_source_url", ""))
        if u.scheme != "https" or u.hostname != "eogdata.mines.edu" or u.query or u.fragment or u.username or u.password:
            raise ValueError("Source must be the non-secret official HTTPS download URL.")
        if not u.path.startswith("/nighttime_light/annual/v21/2020/"):
            raise ValueError("Source URL must identify the official 2020/v21 directory.")
        source_name = unquote(u.path.rsplit("/", 1)[1])
        if source_name not in [path.name, path.name + ".gz"]:
            raise ValueError("Input name does not match the preserved official source URL.")
    if len(set(prefixes)) != 1 or config.get("release_prefix") != prefixes[0]:
        raise ValueError("Radiance/count products must share the same declared EOG release prefix.")
    return config, paths, prefixes[0]


def dataset_record(ds):
    nodata = ds.nodata
    if nodata is not None and not math.isfinite(nodata):
        nodata = str(nodata)
    return {"shape": list(ds.shape), "crs": ds.crs.to_wkt(), "transform": list(ds.transform),
            "resolution_degrees": list(ds.res), "dtype": ds.dtypes[0], "nodata": nodata,
            "scale": ds.scales[0], "offset": ds.offsets[0], "unit": ds.units[0],
            "mask_flags": [str(f) for f in ds.mask_flag_enums[0]], "tags": ds.tags()}


def check_rasters(a, c):
    if a.count != 1 or c.count != 1 or a.shape != c.shape or a.transform != c.transform or a.crs != c.crs:
        raise ValueError("Original radiance and observation counts do not have identical one-band spatial support.")
    if not a.crs or a.crs.to_epsg() != 4326:
        raise ValueError("Expected original EOG WGS84 geographic grid.")
    if a.transform.b != 0 or a.transform.d != 0 or a.transform.a <= 0 or a.transform.e >= 0:
        raise ValueError("Expected the original unrotated north-up grid.")
    if not np.allclose(a.res, [NATIVE_RESOLUTION_DEG] * 2, rtol=0, atol=1e-12):
        raise ValueError("Input is not the original 15 arc-second product.")
    if any(x.scales[0] != 1 or x.offsets[0] != 0 for x in [a, c]):
        raise ValueError("Unexpected scale/offset: verify original product encoding rather than silently converting.")
    if a.nodata == 0:
        raise ValueError("Radiance declares zero as NoData. Verify original metadata before deciding which zero pixels are true observations; no zero-value recoding is automatic.")


def valid_pair(radiance, counts, radiance_mask, counts_mask):
    # Real observed zero radiance is retained. Counts are a quality gate only.
    count_known = np.isfinite(counts) & counts_mask
    if np.any(counts[count_known] < 0) or np.any(np.abs(counts[count_known] - np.rint(counts[count_known])) > 1e-6):
        raise ValueError("cf_cvg must contain nonnegative raw observation counts, not rescaled probabilities.")
    valid = radiance_mask & count_known & np.isfinite(radiance) & (counts > 0)
    return valid


def source_polygons(transform, to_albers, rows, columns, segments=EDGE_SEGMENTS):
    offsets = []
    for j in range(segments): offsets.append((j / segments, 0))
    for j in range(segments): offsets.append((1, j / segments))
    for j in range(segments): offsets.append((1 - j / segments, 1))
    for j in range(segments): offsets.append((0, 1 - j / segments))
    offsets.append(offsets[0]); off = np.asarray(offsets)
    x = transform.c + (columns[:, None] + off[None, :, 0]) * transform.a
    y = transform.f + (rows[:, None] + off[None, :, 1]) * transform.e
    xx, yy = to_albers.transform(x, y)
    return shapely.polygons(np.stack([xx, yy], axis=2))


def numeric_area_tolerance(area):
    # Numerical intersection tolerance only: 0.0001 m2 for a 1 km square.
    # This is not an ecological missing-coverage eligibility threshold.
    return np.maximum(1e-6, np.asarray(area, dtype=float) * 1e-10)


def aggregate_arrays(weights, areas, raw, counts, valid, grid_ids, scale):
    source_area = np.asarray(weights.sum(axis=1)).ravel()
    good_area = weights @ valid.astype(float)
    tolerance = numeric_area_tolerance(areas)
    if np.any(np.abs(source_area - areas) > tolerance):
        raise ValueError("Native window does not cover every complete grid within floating-point area tolerance.")
    if np.any(good_area > areas + tolerance):
        raise ValueError("Valid source area exceeds grid area.")
    observed = good_area > 0
    means = np.divide(weights @ np.where(valid, raw, 0), good_area, out=np.full(len(areas), np.nan), where=observed)
    count_means = np.divide(weights @ np.where(valid, counts, 0), good_area, out=np.full(len(areas), np.nan), where=observed)
    complete = np.abs(areas - good_area) <= tolerance
    number = np.diff(weights.indptr).astype(int)
    nvalid = np.asarray((weights > 0) @ valid.astype(np.int64)).ravel()
    df = pd.DataFrame({"grid_id": grid_ids, "scale_m": scale,
                       "NTL": np.where(complete, means, np.nan), "NTL_partial_mean": means,
                       "ntl_valid_fraction": np.minimum(1, np.maximum(0, good_area / areas)),
                       "ntl_support_complete": complete, "cf_cvg_mean": count_means,
                       "ntl_grid_area_m2": areas, "ntl_valid_area_m2": good_area,
                       "ntl_source_footprint_area_m2": source_area,
                       "ntl_n_native_pixels": number, "ntl_n_valid_native_pixels": nvalid,
                       "ntl_numerical_area_tolerance_m2": tolerance})
    if not df.grid_id.is_unique:
        raise ValueError("Duplicate grid IDs.")
    return df


def independent_grid_check(g, polygons_fine, raw, counts, valid, summary):
    # Query the native-pixel tree from selected grid polygons, opposite to the
    # production grid-tree/pixel-query traversal; refine projected edges 2x.
    tree = shapely.STRtree(polygons_fine)
    ids = np.unique(np.linspace(0, len(g) - 1, min(len(g), 12), dtype=int))
    errors = []
    for i in ids:
        geom = g.geometry.iloc[i]
        pix = tree.query(geom, predicate="intersects")
        area = shapely.area(shapely.intersection(polygons_fine[pix], geom))
        select = (area > 0) & valid[pix]
        pixels, w = pix[select], area[select]
        own_area = float(w.sum())
        own_mean = float(np.dot(w, raw[pixels]) / own_area) if own_area > 0 else None
        own_count = float(np.dot(w, counts[pixels]) / own_area) if own_area > 0 else None
        target = summary.iloc[i]
        area_error = abs(own_area - float(target.ntl_valid_area_m2))
        # Refined geographic-edge approximation can perturb a boundary area;
        # tolerances below are numerical convergence checks, not missing gates.
        if area_error > 0.01:
            raise ValueError("Native-pixel edge-densification area convergence failed.")
        mean_error = abs(own_mean - target.NTL_partial_mean) if own_mean is not None else 0.0
        count_error = abs(own_count - target.cf_cvg_mean) if own_count is not None else 0.0
        if own_mean is not None and mean_error > 1e-7 * max(1, abs(own_mean)):
            raise ValueError("Independent radiance intersection check failed.")
        if own_count is not None and count_error > 1e-7 * max(1, abs(own_count)):
            raise ValueError("Independent count-description check failed.")
        errors.append({"grid_id": str(g.Grid_ID.iloc[i]), "valid_area_error_m2": area_error,
                       "NTL_partial_mean_error": float(mean_error), "cf_cvg_mean_error": float(count_error)})
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PROCESS / "ntl_inputs_TEMPLATE.json")
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--replace-generated", action="store_true", help="Replace this script's generated NTL result, never raw inputs")
    args = parser.parse_args()
    config, paths, release = inspect_inputs(args.config)
    with rasterio.open(paths["average_masked"]) as a, rasterio.open(paths["cf_cvg"]) as c:
        check_rasters(a, c)
        native_metadata = {"average_masked": dataset_record(a), "cf_cvg": dataset_record(c)}
    if args.check_inputs_only:
        save_json(PROCESS / "ntl_input_check_nonrun.json", {"status": "INPUT_GEOMETRY_CHECKED_NOT_AGGREGATED", "release": release, "metadata": native_metadata})
        print("Input metadata checked; no NTL result or PASS created.")
        return
    if RESULT.exists() and not args.replace_generated:
        raise FileExistsError("NTL result already exists; use --replace-generated only for intentional rerun.")
    WORK.mkdir(parents=True, exist_ok=True)
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    save_json(RECEIPT, {"status": "RUNNING_NOT_VALIDATED", "release": release, "imputation": False})
    grids = {}
    for scale in [1000, 500]:
        g = gpd.read_file(ROOT / "02_过程文件/spatial/analysis.gdb", layer="grid_" + str(scale)).sort_values("Grid_ID").reset_index(drop=True)
        if not g.Grid_ID.is_unique or not g.geometry.is_valid.all() or not g.crs.is_projected:
            raise ValueError("Invalid or nonunique frozen grid support.")
        if not all(axis.unit_name.lower() in ["metre", "meter"] for axis in g.crs.axis_info):
            raise ValueError("Analysis CRS must be the frozen metre-based equal-area projection.")
        if not np.allclose(g.area, scale * scale, rtol=0, atol=1e-3):
            raise ValueError("Expected complete square grids, not study-boundary-clipped polygons.")
        grids[scale] = g
    if grids[500].crs != grids[1000].crs:
        raise ValueError("The two frozen square grids have different CRSs.")
    analysis_crs = grids[1000].crs
    bounds = np.vstack([g.total_bounds for g in grids.values()])
    xmin, ymin = bounds[:, :2].min(axis=0); xmax, ymax = bounds[:, 2:].max(axis=0)
    to_native = Transformer.from_crs(analysis_crs, 4326, always_xy=True)
    native_bounds = to_native.transform_bounds(xmin, ymin, xmax, ymax, densify_pts=41)
    with rasterio.open(paths["average_masked"]) as a, rasterio.open(paths["cf_cvg"]) as c:
        ulc, ulr = ~a.transform * (native_bounds[0], native_bounds[3])
        lrc, lrr = ~a.transform * (native_bounds[2], native_bounds[1])
        c0, r0 = math.floor(ulc) - 1, math.floor(ulr) - 1
        c1, r1 = math.ceil(lrc) + 1, math.ceil(lrr) + 1
        if min(c0, r0) < 0 or c1 > a.width or r1 > a.height:
            raise ValueError("Original source extent does not cover the required whole-square window.")
        window = Window(c0, r0, c1 - c0, r1 - r0)
        transform = a.window_transform(window)
        radiance = a.read(1, window=window)
        counts = c.read(1, window=window)
        rmask, cmask = a.read_masks(1, window=window) > 0, c.read_masks(1, window=window) > 0
        valid = valid_pair(radiance, counts, rmask, cmask)
        if not valid.any():
            raise ValueError("No jointly valid observed native pixels in study window.")
        for product, dataset, array in [("average_masked", a, radiance), ("cf_cvg", c, counts)]:
            profile = dataset.profile.copy()
            profile.update(width=int(window.width), height=int(window.height), transform=transform,
                           tiled=True, blockxsize=256, blockysize=256, compress="DEFLATE")
            target = WORK / (release + "." + product + "_native_window.tif")
            with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
                with rasterio.open(target, "w", **profile) as dst:
                    dst.write(array, 1)
                    dst.write_mask((rmask if product == "average_masked" else cmask).astype(np.uint8) * 255)
                    dst.update_tags(source_file=paths[product].name, source_url=config[product + "_source_url"],
                                    window_policy="unaltered native pixels; no reprojection or interpolation")
    height, width = radiance.shape
    raw = radiance.astype(float).ravel(); cvg = counts.astype(float).ravel(); valid = valid.ravel()
    rr, cc = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
    rr, cc = rr.ravel(), cc.ravel()
    to_albers = Transformer.from_crs(4326, analysis_crs, always_xy=True)
    polys = source_polygons(transform, to_albers, rr, cc, EDGE_SEGMENTS)
    finer = source_polygons(transform, to_albers, rr, cc, EDGE_SEGMENTS * 2)
    if not shapely.is_valid(polys).all() or not shapely.is_valid(finer).all():
        raise ValueError("Invalid projected native-pixel geometry.")
    input_records = [{"product": product, "path": rel(path), "bytes": path.stat().st_size,
                      "sha256": sha(path), "source_url": config[product + "_source_url"]} for product, path in paths.items()]
    outputs, geometry_receipts = [], []
    for scale, g in grids.items():
        tree = shapely.STRtree(g.geometry.values)
        pi, gi = tree.query(polys, predicate="intersects")
        areas = shapely.area(shapely.intersection(polys[pi], g.geometry.values[gi]))
        keep = areas > 0  # no area/coverage eligibility cutoff
        matrix = sparse.coo_matrix((areas[keep], (gi[keep], pi[keep])), shape=(len(g), height * width)).tocsr()
        summary = aggregate_arrays(matrix, g.area.to_numpy(), raw, cvg, valid, g.Grid_ID.to_numpy(), scale)
        check = independent_grid_check(g, finer, raw, cvg, valid, summary)
        matrix_file = WORK / ("native_area_weights_" + str(scale) + ".npz")
        sparse.save_npz(matrix_file, matrix)
        geomhash = hashlib.sha256(b"".join(shapely.to_wkb(g.geometry.values))).hexdigest()
        rec = {"scale_m": scale, "grid_rows": len(g), "geometry_sha256": geomhash,
               "weights_file": rel(matrix_file), "matrix_shape": list(matrix.shape), "positive_intersections": int(matrix.nnz),
               "complete_support_grids": int(summary.ntl_support_complete.sum()),
               "partial_support_grids": int((~summary.ntl_support_complete & (summary.ntl_valid_fraction > 0)).sum()),
               "no_valid_support_grids": int((summary.ntl_valid_fraction == 0).sum()),
               "max_full_grid_area_partition_error_m2": float(np.max(abs(summary.ntl_source_footprint_area_m2 - summary.ntl_grid_area_m2))),
               "edge_convergence_independent_samples": check}
        geometry_receipts.append(rec); outputs.append(summary)
        print("NTL native-area aggregation and independent checks completed", scale, flush=True)
    combined = pd.concat(outputs, ignore_index=True)
    if combined.duplicated(["grid_id", "scale_m"]).any():
        raise ValueError("Duplicate output grid IDs/scale.")
    if combined.NTL.notna().sum() == 0:
        raise ValueError("No fully observed complete grid: final main NTL cannot be produced.")
    temp = RESULT.with_suffix(".csv.partial")
    combined.to_csv(temp, index=False, encoding="utf-8-sig", float_format="%.12g")
    reread = pd.read_csv(temp)
    if len(reread) != len(combined) or not np.array_equal(reread.NTL.notna(), combined.NTL.notna()):
        raise ValueError("Written CSV failed null/support verification.")
    if not np.allclose(reread.NTL_partial_mean, combined.NTL_partial_mean, rtol=1e-10, atol=1e-10, equal_nan=True):
        raise ValueError("Written CSV failed numerical round-trip verification.")
    temp.replace(RESULT)
    record = {"status": "PASS", "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "release": release, "inputs": input_records, "source_metadata": native_metadata,
              "result": rel(RESULT), "result_sha256": sha(RESULT), "rows": len(combined),
              "analysis_support": "complete fixed 1 km and 500 m square grids; native pixel polygon overlap area in frozen Albers equal-area CRS",
              "analysis_crs": CRS(analysis_crs).to_wkt(), "window": list(window.flatten()), "window_shape": [height, width],
              "window_transform": list(transform), "native_pixel_edge_segments": EDGE_SEGMENTS,
              "quality_policy": "both original products non-NoData/valid-mask and finite; original cf_cvg > 0; real observed zero radiance retained",
              "main_missing_policy": "NTL is NA unless all complete-square area is valid within max(1e-6 m2, grid_area*1e-10) floating-point tolerance",
              "NTL_partial_mean": "area-weighted mean on the observed part, retained separately and never substituted into main NTL",
              "cf_cvg_mean": "area-weighted descriptive observation count over jointly valid area; NEVER a radiance weight",
              "radiance_unit": "nW cm^-2 sr^-1", "radiance_transform": "none", "threshold_or_imputation": None,
              "observed_zero_native_pixels_in_window": int(np.sum(valid & (raw == 0))),
              "observed_negative_native_pixels_in_window": int(np.sum(valid & (raw < 0))),
              "independent_check": "12 deterministic grids per scale; reverse STRtree traversal and twice-densified native pixel edges",
              "grids": geometry_receipts}
    save_json(RECEIPT, record)
    print("NTL_AGGREGATION_PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if RECEIPT.exists():
            prior = json.loads(RECEIPT.read_text(encoding="utf8"))
            if prior.get("status") == "RUNNING_NOT_VALIDATED":
                prior.update(status="FAILED_NOT_VALIDATED", error=type(exc).__name__ + ": " + str(exc))
                save_json(RECEIPT, prior)
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(2)
