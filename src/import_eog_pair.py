"""Archive the user-downloaded original EOG pair without altering Downloads.

Wait until a requested time, copy stable completed gzip files, verify each gzip
to EOF, and retain the decompressed original TIFF. No authentication or network
access is performed; no alternative input or missing-value substitution exists.
"""
from pathlib import Path
import argparse, datetime as dt, gzip, hashlib, json, os, shutil, sys, time
import rasterio

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '02_过程文件/ntl_ingest'
RAW = ROOT / '01_原始数据/EOG2020官方原件'
PREFIX = 'VNL_v21_npp_2020_global_vcmslcfg_c202205302300'
PRODUCTS = ('average_masked', 'cf_cvg')
BASE_URL = 'https://eogdata.mines.edu/nighttime_light/annual/v21/2020/'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def current_status(stage, **extra):
    state = {'status': stage, 'pid': os.getpid(),
             'at_utc': dt.datetime.now(dt.timezone.utc).isoformat(), **extra}
    save(WORK / 'import_status.json', state)
    print(json.dumps(state, ensure_ascii=False), flush=True)


def publish(source, destination, digest):
    assert RAW.resolve() in destination.resolve().parents
    if destination.exists():
        assert sha(destination) == digest, 'Existing raw file differs; original is not overwritten.'
        return
    assert WORK.resolve() in source.resolve().parents
    source.replace(destination)
    assert sha(destination) == digest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--downloads', type=Path, default=Path(r'D:\下载'))
    ap.add_argument('--not-before', required=True)
    args = ap.parse_args()
    target = dt.datetime.fromisoformat(args.not_before)
    assert target.tzinfo is not None
    WORK.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    current_status('WAITING_REQUESTED_TIME', not_before=target.isoformat(), downloads=str(args.downloads))
    while True:
        seconds = (target - dt.datetime.now(dt.timezone.utc)).total_seconds()
        if seconds <= 0:
            break
        time.sleep(min(seconds, 30))
    sources = {p: args.downloads / f'{PREFIX}.{p}.dat.tif.gz' for p in PRODUCTS}
    missing = [p for p, f in sources.items() if not f.is_file()]
    if missing:
        current_status('WAITING_COMPLETED_DOWNLOAD_FILES', missing=missing,
                       completed_files=[str(f) for f in sources.values() if f.is_file()],
                       partial_files=[{'name': f.name, 'bytes': f.stat().st_size,
                                       'mtime_ns': f.stat().st_mtime_ns}
                                      for f in args.downloads.glob('*.crdownload')])
        return
    first = {p: (f.stat().st_size, f.stat().st_mtime_ns) for p, f in sources.items()}
    time.sleep(30)
    if any((f.stat().st_size, f.stat().st_mtime_ns) != first[p] for p, f in sources.items()):
        current_status('WAITING_FILE_STABILITY', message='A completed-name file changed during observation; nothing copied.')
        return
    staging = WORK / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    staging.mkdir(exist_ok=False)
    entries = []
    for product, source in sources.items():
        current_status('COPYING_COMPLETED_ORIGINAL', product=product, source=str(source))
        gz_stage = staging / source.name
        with source.open('rb') as inp, gz_stage.open('xb') as out:
            shutil.copyfileobj(inp, out, 8 * 1024 * 1024)
        assert (source.stat().st_size, source.stat().st_mtime_ns) == first[product]
        original_hash = sha(source)
        assert sha(gz_stage) == original_hash
        tif_stage = staging / source.name[:-3]
        current_status('VERIFYING_GZIP_AND_DECOMPRESSING', product=product)
        decoded_hash = hashlib.sha256(); total = 0
        with gzip.open(gz_stage, 'rb') as inp, tif_stage.open('xb') as out:
            for block in iter(lambda: inp.read(8 * 1024 * 1024), b''):
                out.write(block); decoded_hash.update(block); total += len(block)
        # Reading gzip through EOF validates CRC and uncompressed size.
        with rasterio.open(tif_stage) as ds:
            from agent_ntl_aggregate import dataset_record
            metadata = dataset_record(ds)
        entries.append({'product': product, 'download_file': str(source),
                        'source_url': BASE_URL + source.name,
                        'gzip_bytes': first[product][0], 'gzip_sha256': original_hash,
                        'gzip_crc_verified': True, 'tif_bytes': total,
                        'tif_sha256': decoded_hash.hexdigest(), 'metadata': metadata})
    for entry in entries:
        name = f"{PREFIX}.{entry['product']}.dat.tif"
        publish(staging / (name + '.gz'), RAW / (name + '.gz'), entry['gzip_sha256'])
        publish(staging / name, RAW / name, entry['tif_sha256'])
    provenance = {'status': 'ORIGINAL_PAIR_COPIED_CRC_AND_HASH_VERIFIED',
                  'release_prefix': PREFIX,
                  'acquisition': 'User downloaded from the authenticated official directory; exact filenames and source links were observed in the browser.',
                  'provider_checksum_available': False,
                  'download_originals_unchanged': True, 'files': entries}
    save(RAW / '来源与完整性核验.json', provenance)
    from agent_ntl_aggregate import check_rasters
    with rasterio.open(RAW / f'{PREFIX}.average_masked.dat.tif') as a, rasterio.open(RAW / f'{PREFIX}.cf_cvg.dat.tif') as c:
        check_rasters(a, c)
    config = {'official_source_files_verified': True, 'release_prefix': PREFIX}
    for product in PRODUCTS:
        name = f'{PREFIX}.{product}.dat.tif'
        config[product + '_tif'] = str((RAW / name).relative_to(ROOT))
        config[product + '_source_url'] = BASE_URL + name + '.gz'
    config_path = ROOT / '02_过程文件/aggregation/ntl_inputs.json'
    if config_path.exists():
        assert json.loads(config_path.read_text(encoding='utf-8-sig')) == config, 'Existing config differs; review required.'
    else:
        save(config_path, config)
    current_status('ORIGINAL_PAIR_READY_FOR_AGGREGATION', config=str(config_path),
                   provenance=str(RAW / '来源与完整性核验.json'),
                   source_files_unchanged=True, scores_not_run=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if WORK.exists():
            current_status('FAILED_REVIEW_REQUIRED', error_type=type(error).__name__, message=str(error))
        raise
