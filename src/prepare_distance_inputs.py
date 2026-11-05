"""Prepare source masks with explicit NoData for native Esri distance tools."""
from pathlib import Path
import json
import numpy as np
import rasterio
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'02_过程文件/distance';P.mkdir(exist_ok=True)
SP=ROOT/'02_过程文件/spatial'
tasks=[]
for product,filename in [('clcd','clcd2020.tif'),('wc','worldcover2020_common30m.tif')]:
    with rasterio.open(SP/filename) as s:a=s.read(1);pp=s.profile
    pp.update(dtype='uint8',nodata=0,compress='deflate')
    for ecology,codes in [('base',[2,3,4,5,9]),('crop_included',[1,2,3,4,5,9])]:
        name=product+'_'+ecology
        with rasterio.open(P/(name+'_sources.tif'),'w',**pp) as d:d.write(np.isin(a,codes).astype(np.uint8),1)
        tasks.append({'name':name,'source':'D:/ER219_work/distance/'+name+'_sources.tif','output':'D:/ER219_work/distance/'+name+'_euclidean_m.tif'})
with rasterio.open(ROOT/'02_过程文件/hq/road.tif') as s:a=s.read(1);pp=s.profile
pp.update(dtype='uint8',nodata=0,compress='deflate')
with rasterio.open(P/'road_sources.tif','w',**pp) as d:d.write((a==1).astype(np.uint8),1)
tasks.append({'name':'roads','source':'D:/ER219_work/distance/road_sources.tif','output':'D:/ER219_work/distance/road_euclidean_m.tif'})
(P/'tasks.json').write_text(json.dumps({'tasks':tasks,'work':'D:/ER219_work/distance','template':'D:/ER219_work/spatial/clcd2020.tif'},indent=2),encoding='utf8')
print('PREPARED '+str(len(tasks))+' source masks; zero is NoData, not a source')
