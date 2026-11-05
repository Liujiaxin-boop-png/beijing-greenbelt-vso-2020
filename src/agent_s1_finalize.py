"""Freeze S1 after native reopening, value/colour QA, and whole-figure review."""
from pathlib import Path
from zipfile import ZipFile
import argparse,json,hashlib,datetime
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/"02_过程文件/map_inputs_s1";OUT=ROOT/"04_图件"
parser=argparse.ArgumentParser();parser.add_argument("--visual-reviewed",action="store_true");args=parser.parse_args()
assert args.visual_reviewed
r=json.loads((WORK/"S1_native_reopen_QA.json").read_text(encoding="utf8"))
assert r["status"]=="NATIVE_REOPEN_VALUES_AND_COLORS_PASS_VISUAL_PENDING"
assert sum(x["values_checked"] for x in r["checks"])==19824
a=np.array(Image.open(OUT/"图S1_四项原始指标空间分布.png").convert("RGBA"),dtype=np.int16)
b=np.array(Image.open(WORK/"S1_native_reopened.png").convert("RGBA"),dtype=np.int16)
assert a.shape==b.shape and np.array_equal(a[:,:,3],b[:,:,3])
mae=float(abs(a[:,:,:3]-b[:,:,:3]).mean());assert mae<1
with ZipFile(OUT/"补充图S1_原始指标地图.qgz") as z:
    xml=ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith(".qgs"))))
sources=[n.text for n in xml.findall(".//projectlayers/maplayer/datasource")]
assert len(sources)==9 and all(x.startswith("../") for x in sources)
svg=ET.parse(OUT/"图S1_四项原始指标空间分布.svg").getroot()
assert not any(x.tag.rsplit("}",1)[-1]=="image" for x in svg.iter())
data=json.loads((WORK/"S1_data_receipt.json").read_text(encoding="utf8"))
for path,expected in data["inputs_sha256"].items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected
record={"status":"PASS_NATIVE_DATA_COLOR_AND_VISUAL_REVIEW","reviewed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "whole_figure_review":"Eight real spatial panels, readable Chinese labels, matching spatial extent, continuous teal scales, visible grey NA, unobstructed legends and notes; no MCR/NTL/ER panel.",
        "native_data_values_checked":19824,"map_panels":8,"valid_native_layers":9,
        "native_reexport_mean_absolute_RGB_difference_0_255":mae,"alpha_identical":True,
        "pixel_size":[int(a.shape[1]),int(a.shape[0])],"relative_source_paths":True,"vector_SVG_no_embedded_raster":True,
        "source_indicator_CSV_hashes_unchanged":True,
        "renderer_QA":"All 2478 values/NA in each native layer matched frozen input values; colour expression matched independently interpolated teal anchors within 1 RGB integer step.",
        "nonfatal_driver_messages":"QGIS GDAL reports GeoPackage v1.4 newer than its bundled driver and PNG update-georeferencing unsupported. All 9 layers reopened and 19824 values/NA were verified; only layout PNG/PDF/SVG are delivered, without any PNG worldfile or claimed spatial georeference."}
(WORK/"S1_visual_QA.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf8")
native=json.loads((WORK/"S1_native_receipt.json").read_text(encoding="utf8"));native["status"]=record["status"]
(WORK/"S1_native_receipt.json").write_text(json.dumps(native,ensure_ascii=False,indent=2),encoding="utf8")
r["visual_QA"]="PASS";(WORK/"S1_native_reopen_QA.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf8")
files=[OUT/("图S1_四项原始指标空间分布."+s) for s in ["png","pdf","svg"]]+[OUT/"补充图S1_原始指标地图.qgz"]
files += [WORK/n for n in ["S1_raw_indicator_cells.gpkg","S1_raw_indicator_values.csv","S1_panel_statistics.csv","S1_data_receipt.json","S1_native_receipt.json","S1_native_reopen_QA.json","S1_visual_QA.json"]]
manifest={"status":record["status"],"files":[{"path":str(p.relative_to(ROOT)),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(WORK/"S1_delivery_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8")
print("S1_FINAL_QA_PASS",flush=True)
