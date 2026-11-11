# -*- coding:utf-8 -*-
from __future__ import print_function
import json,os,io
import arcpy
work=os.path.dirname(os.path.abspath(__file__))
records=json.load(io.open(os.path.join(work,'case_maps.json'),'r',encoding='utf8'))
for record in records:
    d=arcpy.mapping.MapDocument(record['mxd'])
    frame=arcpy.mapping.ListDataFrames(d,u'综合指数变化')[0]
    roadname=u'定位道路（2025年末 OSM，片区内）'
    src=os.path.join(record['destination'],'data',u'镇内变化.gdb','roads_2025')
    assert arcpy.Exists(src)
    lyr=arcpy.mapping.Layer(src)
    lyr.name=roadname
    if lyr.supports('LABELCLASSES'):
        for lc in lyr.labelClasses:lc.expression='[road_name]'
        lyr.showLabels=True
    lyr.visible=False
    if not any(l.name==roadname for l in arcpy.mapping.ListLayers(d,'',frame)):
        arcpy.mapping.AddLayer(frame,lyr,'TOP')
    d.relativePaths=True;d.save()
    del lyr,d,frame
print('Auxiliary layers installed')
