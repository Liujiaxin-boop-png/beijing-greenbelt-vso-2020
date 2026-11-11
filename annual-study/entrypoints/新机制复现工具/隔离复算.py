# -*- coding: utf-8 -*-
"""Reproduce the staged experiments in new folders. Original archives are read-only."""
from pathlib import Path
import argparse,os,shutil,sys,subprocess,datetime,time,json,hashlib
from importlib import metadata
P=Path(__file__).resolve().parent
s=argparse.ArgumentParser();s.add_argument('--archive',default='D:/ER219_results/年度评价_2015_2025_原始GIS边界');s.add_argument('--dest',default='D:/ER_StagePractice');s.add_argument('--task',choices=['All','D','A','B','C','Map'],default='All');s.add_argument('--maps',action='store_true');s.add_argument('--observations');s.add_argument('--panel');a=s.parse_args()
r=Path(a.archive).resolve();de=Path(a.dest).resolve()
refs=r/'机制验证_三阶段';ro=Path('D:/ER219_work/annual_actual');core=Path('D:/ER219_work/shp11/core');mp=Path('D:/ER219_code/arcmap_hi_20261106')
if not refs.is_dir(): sys.exit(f'成果档案不存在：{r}')
if de.is_relative_to(r) or any(de.is_relative_to(q.resolve()) for q in (ro,core,mp)):sys.exit('练习目录不可设在原成果或原代码里。')
dst=de/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');dst.mkdir(parents=True,exist_ok=False)
w=dst/'机制验证_三阶段';w.mkdir();log=dst/'日志';log.mkdir();env=os.environ.copy();env.update(PYTHONIOENCODING='utf-8',PYTHONUTF8='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
print('练习目录：'+str(dst),flush=True)
labels={'D':'D_阶段分解','A':'A_外部观测','B':'B_地类转换','C':'C_镇街核查'}
tasks=list('DABC') if a.task=='All' else (['D'] if a.task=='Map' else [a.task])
draw=a.maps or a.task=='Map'
if draw and 'D' not in tasks:tasks=['D']+tasks
for label in tasks:shutil.copytree(P/'实验脚本'/labels[label],w/labels[label])
q=w/'复核与复现';q.mkdir();shutil.copy2(P/'实验脚本'/'工程相对路径.py',q)
y=[2015,2019,2021,2025];g=Path('计算结果与核验/01_全区与格网');t=Path('计算结果与核验/02_镇街与案例');pr=Path('高韧性空间因素_2020实证/02_过程');eco=pr/'生态空间';base=[g/'六项逐格逐年原值与得分.csv.gz'];extra=[]
if draw or 'B' in tasks or 'C' in tasks:base+=[g/'annual_grid_500.gpkg']
if draw:base +=[g/'scope.gpkg'];extra+=[Path('D:/ER219_work/shp11/maps/fig3.json'),mp/'context_fig1.json',mp/'run_native.ps1',Path('C:/Python27/ArcGIS10.8/python.exe')]
if 'A' in tasks:
 base +=[eco/'worldcover500.csv']+[eco/f'ndvi_main_{j}.csv' for j in y]+[eco/f'esri_built_{j}.csv' for j in y[1:]]+[pr/'人类活动'/f'pop_{j}_grid500.csv' for j in y];nt=list((r/pr/'跨年夜光').glob('OpenGeoHub_逐年500米夜光*.csv'));assert len(nt)==1,nt;base+=[nt[0].relative_to(r)]
if 'B' in tasks:
 base +=[eco/f'Esri{j}_mosaic.tif' for j in y[1:]]
 extra +=[core/k for k in ['hq_attribution.py','parameters.json','六项格网十年变化.csv','六项逐格逐年原值与得分.csv.gz']]+[ro/'hq'/k for k in ['sensitivity_3threat.csv','full_scope_frozen_k.json']]
 for j in y:extra +=[ro/f'years/model/CLCD_{j}.tif',ro/f'hq/results/HQI_{j}.tif']+[ro/f'hq/native/{j}/intermediate/filtered_linear_{k}_c.tif' for k in ['built','crop','road']]
if 'C' in tasks:
 base +=[t/k for k in ['town_catalogue.csv','pieces_full.csv','镇街六项逐年指数与分项.csv','planning_towns.gpkg','全镇街CLCD逐年地类面积_公顷.csv']]+[Path('计算结果与核验/03_检验与溯源/02_指标和底图检验/宋庄及两永定河格网逐年水面复核.csv'),pr/'年度建设比例_30米等积网格.csv.gz']+[eco/f'Esri{j}_mosaic.tif' for j in [2017,2019,2020,2021,2025]]+[eco/f'esri_built_{j}.csv' for j in y[1:]]
obs=Path(a.observations).resolve() if a.observations else None
panel=Path(a.panel).resolve() if a.panel else None
if obs and not obs.is_dir():sys.exit('观测练习根目录不存在：'+str(obs))
if panel and (not panel.is_file() or not panel.name.endswith('.csv.gz')):sys.exit('面板必须是存在的 .csv.gz 文件：'+str(panel))
panel_rel=g/'六项逐格逐年原值与得分.csv.gz'
# Inputs eligible to be rebuilt, no silent fallback to the frozen archive if supplied.
def origin(f):
 if f==panel_rel and panel:return panel
 if obs and (f.parent==eco or f.parent==pr/'跨年夜光' or f.parent==pr/'人类活动'):return obs/f
 return r/f
picks={f:origin(f) for f in dict.fromkeys(base)}
if panel:
 extra=[v for v in extra if v!=core/'六项逐格逐年原值与得分.csv.gz']
 import pandas as pd,numpy as np
 fp=pd.read_csv(panel);ref=pd.read_csv(r/panel_rel)
 if set(ref.columns)-set(fp.columns):raise ValueError('自算面板缺正文原列：'+str(set(ref.columns)-set(fp.columns)))
 key=['grid_id','year'];assert len(fp)==49258 and not fp.duplicated(key).any(), '应为4,478格×11年的唯一配对'
 assert fp.year.nunique()==11 and set(fp.year)==set(range(2015,2026)), '年份必须2015—2025齐全'
 ff=fp.set_index(key).sort_index();rr=ref.set_index(key).sort_index()
 if not ff.index.equals(rr.index):raise ValueError('研究范围或ID与论文冻结格网不同')
 for k in ['ix','iy','area_km2']:
  if not np.allclose(ff[k],rr[k],atol=1e-10,rtol=1e-9):raise ValueError('空间范围或面积不同：'+k)
 if 'B' in tasks:
  # Route B02's generated script to the supplied panel, not the archived duplicate.
  bb=w/labels['B']/'02_分期HQ四输入分解.py'; ss=bb.read_text(encoding='utf-8-sig')
  old="""pd.read_csv(Path(r'D:/ER219_work/shp11/core')/'六项逐格逐年原值与得分.csv.gz'"""
  assert ss.count(old)==1
  repl="pd.read_csv(Path("+repr((dst/panel_rel).as_posix())+")"
  bb.write_text(ss.replace(old,repl),encoding='utf-8')
checks=list(dict.fromkeys(list(picks.values())+extra));missing=[str(f) for f in checks if not f.is_file()]
if missing:sys.exit('缺少文件（先复原原始归档，不要填零）：\n'+'\n'.join(missing))
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def dump(name,z):(dst/name).write_text(json.dumps(z,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
deps={k:metadata.version(k) for k in ['pandas','numpy','scipy','geopandas','shapely','rasterio','exactextract','pyogrio']};dump('软件环境.json',{'Python':sys.version,'解释器':sys.executable,**deps})
manifest=[]
for f in dict.fromkeys(base):
 target=dst/f;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(picks[f],target)
dump('链式输入来源.json',{'自算观测根目录':str(obs) if obs else None,'自算面板':str(panel) if panel else None,'选择':[{ '暂存相对路径':str(f),'实际读取':str(orig)} for f,orig in picks.items()]})
for f in checks:manifest.append({'路径':str(f),'字节':f.stat().st_size,'sha256':sha(f)})
dump('输入清单与指纹.json',manifest)
jobs={'D':['时段分解.py'],'A':['阶段验证.py','植被起始条件复核.py','均值与格间差异.py'],'B':['02_分期HQ四输入分解.py','01_地类转换与恢复潜力.py','03_双产品同位置变化核对.py','04_水面转移30米容差.py','05_校核输出.py','06_可核实建设增长地段对下降的贡献.py'],'C':['镇街阶段贡献.py','典型地段水面复核.py','镇内两套建设变化空间匹配.py']}
times=[]
def run(script,python=sys.executable):
 file=log/(str(len(times)+1).zfill(2)+'_'+script.stem+'.txt');print('运行：'+script.name,flush=True);tic=time.monotonic()
 with file.open('wb') as fh:proc=subprocess.run([str(python),str(script)],cwd=script.parent,stdout=fh,stderr=subprocess.STDOUT,env=env)
 times.append({'步骤':script.name,'耗时秒':round(time.monotonic()-tic,2),'退出码':proc.returncode,'日志':file.name});dump('运行记录.json',times)
 if proc.returncode:
  print(file.read_bytes()[-4000:].decode('utf-8','replace'),flush=True);sys.exit(f'运行中止，请打开 {file}')
for label in tasks:
 for name in jobs[label]:run(w/labels[label]/name)
if draw:
 run(w/labels['D']/'转折图ArcMap.py');run(q/'工程相对路径.py','C:/Python27/ArcGIS10.8/python.exe')
import pandas as pd
checked=[]; static=['永定河补水_时段与地段官方记录.csv']
for label in tasks:
 src=refs/labels[label];out=w/labels[label]
 for native in sorted(src.rglob('*')):
  if not (native.name.endswith('.csv') or native.name.endswith('.csv.gz')) or native.name in static:continue
  rebuilt=out/native.relative_to(src)
  if not rebuilt.exists():raise RuntimeError('未输出：'+str(rebuilt))
  x=pd.read_csv(native);y_=pd.read_csv(rebuilt)
  pd.testing.assert_frame_equal(x,y_,check_dtype=False,check_exact=False,atol=1e-10,rtol=1e-9)
  checked.append({'结果表':str(rebuilt.relative_to(w)),'行数':len(x),'列数':len(x.columns)})
dump('复算逐表核对.json',{'通过表数':len(checked),'比较依据':'数值 rtol=1e-9、atol=1e-10；文字、顺序与缺失位置须一致；归档中的静态政策摘录不属于计算输出。','表':checked})
print(f'完成。与原归档逐表对齐：{len(checked)} 张。结果：{dst}',flush=True)

