# -*- coding: utf-8 -*-
from __future__ import print_function
import os,sys,json,io,arcpy
w=os.path.dirname(os.path.abspath(__file__)); pkg=os.path.join(os.path.dirname(w),'arcmap_delivery')
records={}
for k in ['1','3','7','8','9','10']:
    dr=os.path.join(pkg,u'图'+k)
    mxd=next(os.path.join(dr,f) for f in os.listdir(dr) if f.lower().endswith('.mxd')); doc=arcpy.mapping.MapDocument(mxd)
    layers=[]; frames=[]
    for df in arcpy.mapping.ListDataFrames(doc):
        ex=df.extent
        frames.append(dict(name=df.name,width=df.elementWidth,height=df.elementHeight,extent=[ex.XMin,ex.YMin,ex.XMax,ex.YMax],scale=df.scale))
        for layer in arcpy.mapping.ListLayers(doc,'',df):
            if not layer.supports('DATASOURCE'):continue
            norm=lambda p:os.path.normcase(os.path.normpath(p)); source=norm(layer.dataSource);local=source.startswith(norm(os.path.join(dr,'data'))+os.sep)
            assert not layer.isBroken and local,(source,dr)
            layers.append(dict(frame=df.name,layer=layer.name,source=layer.dataSource,broken=layer.isBroken,local=local))
    assert doc.relativePaths and not arcpy.mapping.ListBrokenDataSources(doc)
    records[k]=dict(relative_paths=doc.relativePaths,layers=layers,frames=frames,version=arcpy.GetInstallInfo()['Version'])
    del doc
with io.open(os.path.join(w,'native_data_health.json'),'w',encoding='utf8') as f:f.write(unicode(json.dumps(records,ensure_ascii=False,indent=2)))
print('Verified',sum(len(r['layers']) for r in records.values()),'layer instances')

