# -*- coding: utf-8 -*-
"""ArcMap 10.8 (its own Python 2.7). Copies and exports ONE editable layout to its own private directory."""
from __future__ import print_function
import sys, os, json, shutil, datetime
import arcpy
number=(sys.argv[1] if len(sys.argv)>1 else '11').upper()
valid=[str(i) for i in range(1,12)]+['A'+str(i) for i in range(1,10)]
if number not in valid: raise SystemExit('Choose 1 through 11, or A1 through A9.')
edition=arcpy.GetInstallInfo()
if not edition.get('Version','').startswith('10.8'): raise RuntimeError('Run C:/Python27/ArcGIS10.8/python.exe; do not run ArcGIS Pro Python.')
base=u'D:/ER219_figures/年度论文图_简式比例尺_ArcMap10.8'
source=os.path.join(base,u'图'+number)
if number=='11':
    source=u'D:/ER219_results/年度评价_2015_2025_原始GIS边界/机制验证_三阶段/图件_ArcMap10.8'
work=os.path.join(u'D:/ER_Replay_Layout_Copies',datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
os.makedirs(work)
copy=os.path.join(work,u'layout')
shutil.copytree(source,copy,ignore=shutil.ignore_patterns('*.lock','*.sr.lock'))
mxds=[os.path.join(copy,f) for f in os.listdir(copy) if f.lower().endswith('.mxd')]
if len(mxds)!=1:raise RuntimeError('Expected exactly one MXD in a copied figure folder.')
m=arcpy.mapping.MapDocument(mxds[0])
broken=arcpy.mapping.ListBrokenDataSources(m)
if broken:raise RuntimeError('Broken layers in COPY: '+repr([ly.name for ly in broken]))
out=os.path.join(work,'Figure_'+number+'.pdf')
arcpy.mapping.ExportToPDF(m,out,resolution=300,image_quality='BEST')
if not os.path.isfile(out) or os.path.getsize(out)<1000:raise RuntimeError('PDF missing or empty.')
with open(os.path.join(work,'export_receipt.json'),'wb') as f:
 f.write(json.dumps({'original_folder':source,'opened_copy':mxds[0],'exported_pdf':out,'arcpy_version':edition['Version'],'broken_layers':len(broken),'page_dpi':300,'output_bytes':os.path.getsize(out)},ensure_ascii=True,indent=2).encode('ascii'))
del m
print('Created: '+str(out));print('The project was reopened and exported; this does not recompute the GIS data.')

