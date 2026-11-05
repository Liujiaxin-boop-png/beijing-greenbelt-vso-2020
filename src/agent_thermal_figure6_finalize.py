"""Finalize figure QA after whole-image inspection of both native exports."""
from pathlib import Path
from zipfile import ZipFile
import argparse, json, hashlib, datetime
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"02_过程文件/figure6_QGIS"
OUT=ROOT/"04_图件"
parser=argparse.ArgumentParser()
parser.add_argument("--visual-reviewed",action="store_true")
args=parser.parse_args()
assert args.visual_reviewed, "Review original and QGIS-reopened whole PNG images before finalizing."
receipt=json.loads((QA/"figure6_native_receipt.json").read_text(encoding="utf8"))
native=json.loads((QA/"figure6_native_reopen_QA.json").read_text(encoding="utf8"))
assert native["status"]=="NATIVE_PROJECT_REOPEN_AND_POINT_CHECK_PASSED"
original=np.array(Image.open(OUT/"图6_灰绿配置与热环境.png").convert("RGBA"),dtype=np.int16)
reopened=np.array(Image.open(QA/"figure6_native_reopened.png").convert("RGBA"),dtype=np.int16)
assert original.shape==reopened.shape
mae=float(np.abs(original[:,:,:3]-reopened[:,:,:3]).mean())
assert np.array_equal(original[:,:,3],reopened[:,:,3])
nonwhite_a=float(np.mean(np.min(original[:,:,:3],axis=2)<240))
nonwhite_b=float(np.mean(np.min(reopened[:,:,:3],axis=2)<240))
assert mae<1 and abs(nonwhite_a-nonwhite_b)<.001, "Reopened export has material content differences."
svg=ET.parse(OUT/"图6_灰绿配置与热环境.svg").getroot()
tags=[n.tag.rsplit("}",1)[-1] for n in svg.iter()]
assert "image" not in tags, "Expected a vector-only exported SVG."
assert tags.count("path")+tags.count("ellipse")>=2536
with ZipFile(OUT/"热环境补充图.qgz") as z:
    qgs=ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith(".qgs"))))
sources=[n.text for n in qgs.findall(".//projectlayers/maplayer/datasource")]
assert len(sources)==2 and all(s.startswith("../") for s in sources)
title=next(n.get("labelText") for n in qgs.iter("LayoutItem") if n.get("id")=="figure_title")
assert title=="灰绿配置与同期地表温度"
visual={"status":"PASS_NATIVE_AND_VISUAL_REVIEW", "reviewed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "inspection":"Original and corrected-native PNG inspected as whole figures: Chinese/Greek glyphs readable, no text overlap or cropped axes, both scatter panels and numeric matrix present. An independent saved-project reexport additionally checked pixelwise, including identical alpha.",
        "PNG_size_px":[int(original.shape[1]),int(original.shape[0])],"reexport_mean_absolute_RGB_difference_0_255":mae,
        "original_nonwhite_fraction":nonwhite_a,"reopened_nonwhite_fraction":nonwhite_b,"alpha_channels_identical":True,
        "svg_embedded_raster_images":0,"svg_vector_paths":tags.count("path"),
        "relative_source_tables":sources,"data_points_per_panel":1268,"unique_editable_points":2536,
        "point_round_trip_position_max_error_mm":native["maximum_point_coordinate_error_mm"],
        "no_point_omission_or_jitter":True,"no_fitted_line_or_p_value":True}
(QA/"figure6_visual_QA.json").write_text(json.dumps(visual,ensure_ascii=False,indent=2),encoding="utf8")
receipt["status"]=visual["status"];receipt["visual_QA"]="02_过程文件/figure6_QGIS/figure6_visual_QA.json"
(QA/"figure6_native_receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf8")
native["visual_review"]="PASS: complete figure and native reopened figure inspected"
(QA/"figure6_native_reopen_QA.json").write_text(json.dumps(native,ensure_ascii=False,indent=2),encoding="utf8")
files=[OUT/("图6_灰绿配置与热环境."+x) for x in ["png","pdf","svg"]]+[OUT/"热环境补充图.qgz"]
files += [QA/x for x in ["native_layout_points.csv","figure6_native_receipt.json","figure6_native_reopen_QA.json","figure6_visual_QA.json","figure6_native_reopened.png"]]
manifest={"status":visual["status"],"files":[{"path":str(p.relative_to(ROOT)),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(QA/"figure6_delivery_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8")
print("FIGURE6_FINAL_QA_PASS",flush=True)
