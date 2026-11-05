"""Independently reopen S1, audit native layer values/colours, then render."""
import os,csv,json,gc,hashlib
from pathlib import Path
os.environ["QT_QPA_PLATFORM"]="offscreen"
from qgis.core import *
from qgis.PyQt.QtGui import QFontDatabase,QColor
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/"02_过程文件/map_inputs_s1"
app=QgsApplication([],False);app.initQgis();assert QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")>=0

def validate():
    receipt=json.loads((WORK/"S1_native_receipt.json").read_text(encoding="utf8"))
    with (WORK/"S1_raw_indicator_values.csv").open(encoding="utf-8-sig",newline="") as f:
        data={r["grid_id"]:r for r in csv.DictReader(f)}
    project=QgsProject();assert project.read(str(ROOT/"04_图件/补充图S1_原始指标地图.qgz"))
    layers=list(project.mapLayers().values());assert len(layers)==9 and all(l.isValid() for l in layers)
    assert len(project.layoutManager().layouts())==1
    layout=project.layoutManager().layouts()[0];refs=layout.items()
    maps=[x for x in refs if isinstance(x,QgsLayoutItemMap)];assert len(maps)==8
    assert len({x.extent().toString() for x in maps})==1
    palette=[QColor(x) for x in receipt["palette"]];missing=QColor(receipt["NA"])
    checks=[]
    for panel in receipt["maps"]:
        field=panel["field"];layer=project.mapLayer(panel["source_layer_id"]);assert layer and layer.featureCount()==2478
        prop=layer.renderer().symbol().symbolLayer(0).dataDefinedProperties().property(QgsSymbolLayer.PropertyFillColor)
        assert prop.isActive() and prop.expressionString()==panel["fill_expression"]
        expr=QgsExpression(prop.expressionString());ctx=QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        lo,hi=panel["continuous_min_max"];nvalid=0;nmissing=0;errmax=0
        for feat in layer.getFeatures():
            gid=feat["grid_id"];source=data[gid][field];v=feat[field]
            is_missing=source==""
            if is_missing:
                assert v is None or v==NULL;nmissing+=1;expected=missing
            else:
                value=float(source);assert abs(float(v)-value)<1e-10;nvalid+=1
                t=max(0,min(4,(value-lo)/(hi-lo)*4));i=min(3,int(t));u=t-i
                expected=QColor(*[round(getattr(palette[i],c)()*(1-u)+getattr(palette[i+1],c)()*u) for c in ["red","green","blue"]])
            ctx.setFeature(feat);actual=QgsSymbolLayerUtils.decodeColor(str(expr.evaluate(ctx)));assert not expr.hasEvalError(),expr.evalErrorString()
            err=max(abs(actual.red()-expected.red()),abs(actual.green()-expected.green()),abs(actual.blue()-expected.blue()))
            assert err<=1;errmax=max(errmax,err)
        checks.append({"field":field,"valid_n":nvalid,"NA_n":nmissing,"values_checked":nvalid+nmissing,"max_RGB_rounding_difference":errmax})
    layout.refresh();app.processEvents()
    native=Path("D:/ER219_work/s1_exports/S1_native_reopened.png")
    settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=300
    assert QgsLayoutExporter(layout).exportToImage(str(native),settings)==QgsLayoutExporter.Success
    import shutil
    shutil.copy2(native,WORK/"S1_native_reopened.png")
    report={"status":"NATIVE_REOPEN_VALUES_AND_COLORS_PASS_VISUAL_PENDING","engine":Qgis.QGIS_VERSION,
            "project_sha256":hashlib.sha256((ROOT/"04_图件/补充图S1_原始指标地图.qgz").read_bytes()).hexdigest(),
            "native_maps":len(maps),"valid_layers":len(layers),"same_extent":True,"checks":checks,
            "reopened_render":"02_过程文件/map_inputs_s1/S1_native_reopened.png"}
    (WORK/"S1_native_reopen_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    project.clear();del refs;del layout;del layers;del maps;del project;gc.collect()
    print("S1_NATIVE_REOPEN_VALUE_COLOR_PASS",flush=True)

validate()
gc.collect();app.exitQgis()
