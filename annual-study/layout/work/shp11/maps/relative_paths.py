# -*- coding: utf-8 -*-
import arcpy, io, json, os
w=os.path.dirname(os.path.abspath(__file__)); idx=json.load(io.open(os.path.join(w,'index.json'),encoding='utf8'))
for k in idx:
    doc=arcpy.mapping.MapDocument(idx[k])
    if arcpy.mapping.ListBrokenDataSources(doc): raise ValueError(k)
    doc.relativePaths=True
    doc.save();del doc
    doc=arcpy.mapping.MapDocument(idx[k]); assert doc.relativePaths, k
    del doc
