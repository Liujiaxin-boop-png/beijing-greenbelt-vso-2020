# -*- coding: utf-8 -*-
from pathlib import Path
import os,sys,csv,hashlib,importlib.util,shutil,subprocess
from datetime import datetime
P=Path(__file__).resolve().parent
W=Path('D:/ER219_work')
R=Path('D:/ER219_raw')
C=W/'shp11/core'; LAB=Path('D:/ER_Replay_study')
DOC=Path.home()/'Documents'/'绿隔复现实验'
def init():
 checks=[R/'CLCD_v105_2015_2025/CLCD_2020_Beijing_native.tif', C/'domain.json',C/'六项逐格逐年原值与得分.csv.gz',W/'annual_actual/analysis/Landscape.exe', W/'feng_round2/source_mcr/TwoSource.exe',Path('D:/Apps/InVEST-3.20.2/invest.exe'),Path('F:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe'),Path('C:/Python27/ArcGIS10.8/python.exe')]
 print('独立Python：',sys.executable,sys.version[:7])
 for x in checks:print('找到' if x.exists() else '缺少',x)
 for m in 'numpy pandas scipy rasterio geopandas shapely pyproj exactextract tifffile pyogrio'.split():print('可以加载' if importlib.util.find_spec(m) else '未找到',m)
 print('D盘空闲：%.1f GiB，年度模型输出位置：%s'%(shutil.disk_usage('D:/').free/2**30,LAB))
def launch(script,*args):
 DOC.mkdir(exist_ok=True,parents=True)
 path=DOC/('步骤日志_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.txt')
 cmd=[sys.executable,'-B','-u',str(P/script),*map(str,args)]
 print('日志：',path,flush=True)
 e=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
 with path.open('w',encoding='utf-8-sig') as f:
  f.write(' '.join(cmd)+'\n');f.flush()
  with subprocess.Popen(cmd,cwd=P,env=e,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace') as p:
   for line in p.stdout: print(line,end='');f.write(line);f.flush()
   rc=p.wait()
 if rc:raise RuntimeError('该步没有通过，请保留最后一段错误及日志 '+str(path))
 print('此步正常结束。',flush=True)
def sha_check():
 import json
 dom=json.loads((C/'domain.json').read_text('utf8'));src=Path(dom['source'])
 rows=[{'file':str(src.with_name(n)),'sha256':v} for n,v in dom['sha256'].items()]
 with (C/'原始与模型输入文件指纹.csv').open(encoding='utf-8-sig',newline='') as h:rows+=list(csv.DictReader(h))
 xx=[];print('正在读取',len(rows),'条原始/模型输入指纹……',flush=True)
 for row in rows:
  p=Path(row['file'])
  if not p.is_file():actual='文件不在'
  else:
   with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
  xx.append((str(p),row['sha256'],actual,actual==row['sha256']))
 DOC.mkdir(exist_ok=True,parents=True);dest=DOC/('指纹核对_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.csv')
 with dest.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['文件','归档指纹','实算指纹','一致']);w.writerows(xx)
 print(sum(v[-1] for v in xx),'/',len(xx),'字节一致。明细：',dest)
def menu():
 print('北京二道绿隔  实验复现工作台\n每次输入一个数字并按回车。首次请依次做 0 → 1 → 2。')
 while True:
  print('\n0 检查本机环境   1 单格六项验算   2 全期权重、格网与镇街验算\n3 从原始数据重跑2020   4 复核2020指标选择   5 复核变化机制与四个案例\n6 从已存模型场重建十一年面板   7 从原始数据逐年重跑并计分（耗时较长）\n8 核查输入文件指纹   9 打开个人日志目录   Q 退出')
  try:
   v=input('选项：').strip().upper()
   if v in ['Q','QUIT']:return
   if v=='0':init()
   elif v=='1':launch('单格从原图复算.py')
   elif v=='2':launch('独立验算.py','--out',DOC)
   elif v=='3':launch('从原始数据重跑年度模型.py','all','--year','2020','--root',LAB)
   elif v=='4':launch('独立核对指标选择.py','--out',DOC)
   elif v=='5':launch('复核机制与案例.py','--out',DOC)
   elif v=='6':launch('从原始数据重跑年度模型.py','score-audit','--root','D:/ER_Replay_ArchivePanels_study')
   elif v=='7':
    print('此项从本机原始档案重建11年的模型，再计分。输出独立目录：',LAB)
    if input('确认已预留磁盘空间并准备开始，请键入 RUN：').strip()!='RUN':continue
    for year in range(2015,2026):launch('从原始数据重跑年度模型.py','all','--year',str(year),'--root',LAB)
    launch('从原始数据重跑年度模型.py','score','--root',LAB)
    launch('独立验算.py','--panel',LAB/'panel','--out',DOC)
   elif v=='8':sha_check()
   elif v=='9':DOC.mkdir(exist_ok=True,parents=True);os.startfile(DOC)
   else:print('请输入上述数字之一。')
  except (KeyboardInterrupt,EOFError):return
  except Exception as ex:print('停止：',ex)
if __name__=='__main__':menu()

