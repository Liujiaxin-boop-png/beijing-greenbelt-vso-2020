# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os,sys,glob,json,io,arcpy
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if isinstance(root,str):root=root.decode(sys.getfilesystemencoding())
ff=os.path.join(root,'图件_ArcMap10.8'); m=glob.glob(os.path.join(ff,'*.mxd'))[0]
d=arcpy.mapping.MapDocument(m);assert not arcpy.mapping.ListBrokenDataSources(d);d.relativePaths=True;d.save();del d
d=arcpy.mapping.MapDocument(m);assert d.relativePaths and not arcpy.mapping.ListBrokenDataSources(d)
res={'relative':d.relativePaths,'frames':len(arcpy.mapping.ListDataFrames(d)),'layers':[(l.name,int(arcpy.GetCount_management(l)[0])) for l in arcpy.mapping.ListLayers(d) if l.isFeatureLayer]}
assert sorted(x[1] for x in res['layers'])==[1,1,4478,4478]
with io.open(os.path.join(ff,'工程核验.json'),'w',encoding='utf8') as fh:fh.write(unicode(json.dumps(res,ensure_ascii=False,indent=2)))

