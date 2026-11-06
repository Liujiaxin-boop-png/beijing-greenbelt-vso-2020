"""ArcGIS Pro native NaturalBreaks diagnostic; final classes are not written."""
import arcpy,csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
WORK=Path('D:/ER219_work/evaluation/native_jenks_diagnostic');WORK.mkdir(parents=True,exist_ok=True)
source=ROOT/'03_结果文件/evaluation/scores_all_scenarios.csv'
before=hashlib.sha256(source.read_bytes()).hexdigest()
rows=list(csv.DictReader(source.open(encoding='utf-8-sig',newline='')))
grid=r'D:\ER219_work\spatial\analysis.gdb\grid_1000'
sr=arcpy.Describe(grid).spatialReference
geom={str(gid):shape for gid,shape in arcpy.da.SearchCursor(grid,['Grid_ID','SHAPE@'])}
gdb=str(WORK/'native_jenks.gdb')
if not arcpy.Exists(gdb):arcpy.management.CreateFileGDB(str(WORK),'native_jenks.gdb')
result={'engine':arcpy.GetInstallInfo(),'source_sha256':before,'habitats':{}}
for habitat in ('forest_shrub','grassland','water_wetland'):
    baseline=[r for r in rows if r['habitat']==habitat and r['scenario']=='baseline']
    fc=gdb+'\\'+habitat
    assert not arcpy.Exists(fc),'Diagnostic outputs already exist; no overwrite'
    arcpy.management.CreateFeatureclass(gdb,habitat,'POLYGON',spatial_reference=sr)
    arcpy.management.AddField(fc,'Grid_ID','TEXT',field_length=40)
    arcpy.management.AddField(fc,'ER','DOUBLE')
    with arcpy.da.InsertCursor(fc,['Grid_ID','ER','SHAPE@']) as cursor:
        for r in baseline:cursor.insertRow([r['grid_id'],float(r['ER']),geom[r['grid_id']]])
    layer=arcpy.management.MakeFeatureLayer(fc,'jenks_'+habitat).getOutput(0)
    lyrpath=str(WORK/(habitat+'.lyrx'))
    arcpy.management.SaveToLayerFile(layer,lyrpath,'RELATIVE')
    lf=arcpy.mp.LayerFile(lyrpath);lyr=lf.listLayers()[0]
    sym=lyr.symbology;sym.updateRenderer('GraduatedColorsRenderer')
    sym.renderer.classificationField='ER';sym.renderer.classificationMethod='NaturalBreaks';sym.renderer.breakCount=5
    lyr.symbology=sym
    breaks=[{'upper':b.upperBound,'label':b.label} for b in lyr.symbology.renderer.classBreaks]
    lf.save()
    result['habitats'][habitat]={'n':len(baseline),'native_method':lyr.symbology.renderer.classificationMethod,'breaks':breaks}
    del lyr,lf,layer,sym
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(WORK/'native_breaks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
