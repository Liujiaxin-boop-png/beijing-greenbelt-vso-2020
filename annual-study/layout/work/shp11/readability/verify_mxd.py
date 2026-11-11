# -*- coding: utf-8 -*-
import arcpy, os, io, json, collections

w=os.path.dirname(os.path.abspath(__file__))
index=json.load(io.open(os.path.join(w,'pack_index.json'),encoding='utf8'))
report={}
def canonical(s):
    return os.path.normcase(os.path.realpath(os.path.abspath(s)))
for k,f in sorted(index.items()):
    doc=arcpy.mapping.MapDocument(f)
    assert doc.relativePaths and not arcpy.mapping.ListBrokenDataSources(doc),k
    layers=[]
    for df in arcpy.mapping.ListDataFrames(doc):
        for layer in arcpy.mapping.ListLayers(doc,'',df):
            if layer.supports('DATASOURCE'):
                assert not layer.isBroken and canonical(layer.dataSource).startswith(canonical(os.path.dirname(f))+os.sep),(k,layer.dataSource)
                layers.append(layer.name)
    report[k]={'layers':len(layers),'frames':len(arcpy.mapping.ListDataFrames(doc)),'version':arcpy.GetInstallInfo()['Version'],'relative':doc.relativePaths,'broken':0}
    del doc
with io.open(os.path.join(w,'delivery_mxd_check.json'),'w',encoding='utf8') as out:
    out.write(unicode(json.dumps(report,ensure_ascii=False,indent=2)))
print(len(report),sum(v['layers'] for v in report.values()))
