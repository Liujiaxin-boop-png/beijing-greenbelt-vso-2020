# -*- coding: utf-8 -*-
from __future__ import print_function
import sys, json, os, io, time, collections
import arcpy

w=os.path.dirname(os.path.abspath(__file__)); index=json.load(io.open(os.path.join(w,'index.json'),'r',encoding='utf8'))
root=os.path.join(w,'relocated')
results={}
which=sys.argv[1:] or [str(n) for n in range(1,7)]+['A'+str(n) for n in range(1,10)]
for k in which:
    f=os.path.join(root,u'图'+k,os.path.basename(index[k])); d=arcpy.mapping.MapDocument(f)
    elements=arcpy.mapping.ListLayoutElements(d)
    frames=arcpy.mapping.ListDataFrames(d);layer_rows=[]
    for df in frames:
        for layer in arcpy.mapping.ListLayers(d,'',df):
            if not layer.supports('DATASOURCE'):continue
            source=layer.dataSource
            within=os.path.normcase(os.path.normpath(source)).startswith(os.path.normcase(os.path.dirname(f)+os.sep))
            layer_rows.append(dict(frame=df.name,layer=layer.name,path=source,in_copied_package=within,broken=layer.isBroken))
    bad=arcpy.mapping.ListBrokenDataSources(d)
    counts=collections.Counter(e.type for e in elements)
    labels=[e.text for e in elements if e.type=='TEXT_ELEMENT']
    results[k]=dict(file=f,relative_paths=d.relativePaths,broken=len(bad),frames=len(frames),layers=layer_rows,element_counts=dict(counts),labels=labels,version=arcpy.GetInstallInfo()['Version'])
    del d
    target=os.path.join(w,'reopen_'+k+'.json')
    with io.open(target,'w',encoding='utf8') as out:out.write(unicode(json.dumps(results[k],ensure_ascii=False,indent=2)))
    print(k,len(frames),len(layer_rows),len(bad),all(x['in_copied_package'] for x in layer_rows));sys.stdout.flush()
