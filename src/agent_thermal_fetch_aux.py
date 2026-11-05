"""Fetch source-native ST_EMIS windows for the three frozen Landsat scenes.
No new dates, interpolation, or credentials are introduced.
"""
from pathlib import Path
import json, hashlib, datetime
import requests, rasterio
from rasterio.windows import from_bounds
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"01_原始数据"
PROC=ROOT/"02_过程文件/thermal"
PROC.mkdir(parents=True,exist_ok=True)
records=[]
for source in sorted((RAW/"Landsat8_2020已有原生窗口").glob("LC08*")):
    item=source.name
    st_path=next(source.glob("*_ST_B10_DN_window.tif"))
    stac_path=RAW/"Landsat8_2020补充质量层"/item/"stac_original.json"
    stac=json.loads(stac_path.read_text(encoding="utf8"))
    asset=stac["assets"]["emis"]
    target=RAW/"Landsat8_2020补充质量层"/item/(item+"_ST_EMIS_native_window.tif")
    if not target.exists():
        signed=requests.get("https://planetarycomputer.microsoft.com/api/sas/v1/sign",params={"href":asset["href"]},timeout=60).json()["href"]
        with rasterio.open(st_path) as ref, rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
            with rasterio.open(signed) as src:
                w=from_bounds(*ref.bounds,src.transform).round_offsets().round_lengths()
                a=src.read(1,window=w)
                assert a.shape==ref.shape
                assert src.window_transform(w)==ref.transform
                profile=src.profile.copy()
                profile.update(width=ref.width,height=ref.height,transform=ref.transform,
                               compress="DEFLATE",tiled=True,blockxsize=256,blockysize=256)
                with rasterio.open(target,"w",**profile) as dst: dst.write(a,1)
    with rasterio.open(target) as dst:
        rec={"scene":item,"asset_url":asset["href"],"stac_asset":asset,
             "selection":"Source-native integer pixel window exactly matching frozen ST_B10 window",
             "output":str(target.relative_to(ROOT)),"sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
             "shape":list(dst.shape),"transform":list(dst.transform),"crs":str(dst.crs),
             "nodata":dst.nodata,"retrieved_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    records.append(rec)
    print(item,"ST_EMIS available",flush=True)
(PROC/"aux_download_manifest.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf8")
url="https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1619_Landsat-8-9-C2-L2-ScienceProductGuide-v4.pdf"
dest=RAW/"来源记录/USGS_LSDS_1619_C2_L2_Guide_v4.pdf"
if not dest.exists():
    r=requests.get(url,timeout=60); r.raise_for_status()
    assert r.content.startswith(b"%PDF")
    dest.write_bytes(r.content)
(PROC/"official_guide_source.json").write_text(json.dumps({"url":url,"path":str(dest.relative_to(ROOT)),
"sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),"accessed":"2026-11-06"},indent=2),encoding="utf8")
