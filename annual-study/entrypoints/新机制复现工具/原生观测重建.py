from pathlib import Path
import shutil,sys,subprocess,datetime,os,json
import pandas as pd
import rasterio,numpy as np
here=Path(__file__).resolve().parent;source=Path('D:/ER219_results/年度评价_2015_2025_原始GIS边界')
dest=Path('D:/ER_StagePractice')/('观测_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));dest.mkdir(parents=True,exist_ok=False)
print('原生观测重建目录：'+str(dest),flush=True); rel=Path('高韧性空间因素_2020实证');p=Path('02_过程');ec=p/'生态空间';hu=p/'人类活动';lt=p/'跨年夜光';src=source/rel;out=dest/rel
for sub in [ec,hu/'raw',lt,'01_原始数据']:(out/sub).mkdir(parents=True,exist_ok=True)
orig=source/'计算结果与核验'/'01_全区与格网';new=dest/'计算结果与核验'/'01_全区与格网';new.mkdir(parents=True)
for f in ['annual_grid_500.gpkg','六项逐格逐年原值与得分.csv.gz']:shutil.copy2(orig/f,new/f)
for name in ['ESA_WorldCover2020_v100','Esri_v003_2019_2020_2021']+[f'MOD13Q1_{y}_生长季' for y in [2015,2019,2021,2025]]:
 shutil.copytree(src/'01_原始数据'/name,out/'01_原始数据'/name)
for y in [2015,2019,2021,2025]:shutil.copy2(src/hu/'raw'/f'worldpop_api_beijing_{y}.tif',out/hu/'raw')
shutil.copytree(src/lt/'发布者COG的北京范围',out/lt/'发布者COG的北京范围')
shutil.copy2(src/hu/'ntl_2020_grid500.csv',out/hu)
for f,sub in [('calc_ndvi.py',ec),('calc_worldcover.py',ec),('esri_check.py',ec),('grid_population_light.py',hu),('04_逐格汇总.py',lt)]:
 # Redirect the archival grid lookup to the same unchanged grid in the practice folder.
 txt=(here/'观测脚本'/f).read_text(encoding='utf-8-sig').replace('D:/ER219_results/年度评价_2015_2025_原始GIS边界/计算结果与核验',str((dest/'计算结果与核验').as_posix()))
 (out/sub/f).write_text(txt,encoding='utf-8')
from concurrent.futures import ThreadPoolExecutor
def run(arg):
 sub,f,*args=arg;file=out/sub/f;log=dest/('_'.join([f]+args)+'.log');print('运行：'+f+' '+' '.join(args),flush=True)
 with log.open('wb') as h:
  k=subprocess.run([sys.executable,str(file),*args],env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OPENBLAS_NUM_THREADS='1'),stdout=h,stderr=subprocess.STDOUT)
 if k.returncode:raise RuntimeError('检查日志：'+str(log))
jobs=[[ec,'calc_ndvi.py','season',str(y)] for y in [2015,2019,2021,2025]]+[[hu,'grid_population_light.py',str(y),'pop'] for y in [2015,2019,2021,2025]]+[[ec,'calc_worldcover.py'],[ec,'esri_check.py','2017','2019','2020','2021','2025'],[lt,'04_逐格汇总.py']]
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,jobs))
names=[ec/f'ndvi_main_{y}.csv' for y in [2015,2019,2021,2025]]+[hu/f'pop_{y}_grid500.csv' for y in [2015,2019,2021,2025]]+[ec/f'esri_built_{y}.csv' for y in [2017,2019,2020,2021,2025]]+[ec/'worldcover500.csv',lt/'OpenGeoHub_逐年500米夜光_禁止拼接EOG.csv']
for f in names:pd.testing.assert_frame_equal(pd.read_csv(out/f),pd.read_csv(src/f),check_dtype=False,check_exact=False,atol=1e-10,rtol=1e-9)
for year in [2017,2019,2020,2021,2025]:
 f=ec/f'Esri{year}_mosaic.tif'
 with rasterio.open(src/f) as a,rasterio.open(out/f) as b:
  assert a.crs==b.crs and a.transform==b.transform and a.shape==b.shape
  for _,w in a.block_windows():assert np.array_equal(a.read(1,window=w),b.read(1,window=w))
(dest/'原生观测重建核对.json').write_text(json.dumps({'逐表通过':list(map(str,names)),'逐像元核对通过':[2017,2019,2020,2021,2025],'生成目录':str(dest)},ensure_ascii=False,indent=2),encoding='utf8')
print('完成：15张格网观测表及5期Esri镶嵌影像已与归档逐表/逐像元核对。',flush=True)

