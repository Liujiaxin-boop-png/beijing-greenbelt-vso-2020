# -*- coding:utf8 -*-
from __future__ import print_function
import arcpy,os,sys,json,io
w=os.path.dirname(__file__);dst=os.path.join(os.path.dirname(w),'arcmap_delivery')
src=io.open(os.path.join(w,'source.txt'),encoding='utf8').read().strip()
results={}
for k in ['A2','A3','A4','A5','A6','A8','A9']:
 results[k]={}
 for test,base in [('original',src),('delivered',dst)]:
  folder=os.path.join(base,u'图'+k)
  filename=next(p for p in os.listdir(folder) if p.endswith('.mxd'))
  m=arcpy.mapping.MapDocument(os.path.join(folder,filename))
  rows=[]
  for f in arcpy.mapping.ListDataFrames(m):
   x=f.extent
   ly=arcpy.mapping.ListLayers(m,'',f)
   sources=[l.dataSource for l in ly if l.supports('DATASOURCE')]
   local=all(os.path.normcase(q).startswith(os.path.normcase(folder+os.sep)) for q in sources)
   rows.append(dict(name=f.name,scale=f.scale,extent=[x.XMin,x.YMin,x.XMax,x.YMax],w=f.elementWidth,h=f.elementHeight,linearunits=f.spatialReference.linearUnitName,broken=sum(l.isBroken for l in ly),sources=sources,local=local))
  results[k][test]=dict(relative=m.relativePaths,frames=rows,broken=len(arcpy.mapping.ListBrokenDataSources(m)))
  del m
 with io.open(os.path.join(w,'frames.json'),'w',encoding='utf8') as out:out.write(unicode(json.dumps(results,ensure_ascii=False,indent=2)))
 print(k, [round(j['scale'],2) for j in rows]);sys.stdout.flush()