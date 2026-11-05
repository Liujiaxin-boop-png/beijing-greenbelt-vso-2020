import os,json
os.environ['QT_QPA_PLATFORM']='offscreen'
from qgis.core import QgsApplication,Qgis,QgsProject,QgsVectorLayer
from qgis.PyQt.QtGui import QFontDatabase
app=QgsApplication([],False);app.initQgis()
p=QgsVectorLayer('D:/ER219_work/spatial/scope.gpkg|layername=study_scope','scope','ogr')
print(json.dumps({'qgis':Qgis.QGIS_VERSION,'scope_valid':p.isValid(),'count':p.featureCount()}))
print('EXTENT',p.extent().toString(),'CRS_VALID',p.crs().isValid(),'CRS',p.crs().toProj())
print('FONT_COUNT',len(QFontDatabase().families()),'FONT_LOAD',QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'))
print('NEW_FONT_COUNT',len(QFontDatabase().families()))
del p
QgsProject.instance().removeAllMapLayers()
app.exitQgis()
