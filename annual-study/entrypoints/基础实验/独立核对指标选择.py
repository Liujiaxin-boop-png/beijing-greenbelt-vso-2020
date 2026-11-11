# -*- coding: utf-8 -*-
"""仅复制必要输入到新目录，使用本机存档的原始CLCD/MODIS与模型中间数据重跑正文表3。"""
from pathlib import Path
from datetime import datetime
import argparse, csv, hashlib, importlib.util, json, os, platform, shutil, subprocess, sys

CORE = Path('D:/ER219_work/shp11/core')
WORK = Path('D:/ER219_work/annual_actual')
RAW = Path('D:/ER219_raw/年度分析_2015_2025/MOD13Q1_2020_夏季独立观测')
FILES = ['position.py','compute.py','ndvi.py','compare_six.py','swap_slots.py','build_candidates.py','cells_500_0.csv','annual_grid_500.gpkg','基准及SSI.csv.gz','候选指标_500m.csv.gz','WorldCover2020候选指标_500m.csv','old_scores.csv','parameters.json']
RUN = ['position.py','ndvi.py','compare_six.py','swap_slots.py']
OUT = ['灰绿配置检验.json','ndvi500.csv','指标替换_覆盖冗余与底图.csv','六项方案与2020独立植被绿度.csv','2020六指标逐项替换_独立夏季绿度.csv']

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''): h.update(part)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out','--output',type=Path,default=Path.home()/'Documents'/'绿隔复现实验',help='存放新输出子文件夹的位置')
    args=ap.parse_args()
    if any(args.out.resolve().is_relative_to(p.resolve()) for p in [CORE,WORK,Path('D:/ER219_raw'),Path('D:/ER219_results'),Path('D:/ER219_figures')]):
        raise RuntimeError('请选择自己的练习目录，不要在研究原档的输入或结果目录运行。')
    lab=args.out.resolve()/('指标选择_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    lab.mkdir(parents=True,exist_ok=False); print('本次输出：',lab,flush=True)
    packages='numpy pandas scipy rasterio geopandas shapely tifffile requests pyproj'.split()
    missing=[k for k in packages if importlib.util.find_spec(k) is None]
    if missing:raise RuntimeError('当前 Python 缺少：'+', '.join(missing)+'。请选择手册中的 Python 3 环境。')
    dep=[WORK/'analysis/surfaces.py',WORK/'landscape/2020/fields_500_0.bin',WORK/'years/model/CLCD_2020.tif',
         WORK/'alternative_model/fields_500_0.bin',WORK/'alternative_model/invest/quality_c.tif',WORK/'alternative_model/mcr/2020/MCR_2020.tif',RAW/'STAC_10_items.json']
    for p in dep+[CORE/f for f in FILES+OUT]:
        if not p.is_file():raise FileNotFoundError(f'缺少输入/标准答案：{p}')
    for item in json.loads((RAW/'STAC_10_items.json').read_text('utf8')):
        for band in ['NDVI','QA']:
            p=RAW/(item['id']+'_'+band+'.tif')
            if not p.is_file():raise FileNotFoundError(p)
    for f in FILES:shutil.copyfile(CORE/f,lab/f)
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    for i,f in enumerate(RUN,1):
        print(f'{i}/4 正在运行 {f} …',flush=True)
        with (lab/('日志_'+f+'.txt')).open('wb') as log:
            code=subprocess.run([sys.executable,'-B',str(lab/f)],cwd=lab,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
        if code:raise RuntimeError(f'{f} 未完成。打开输出目录中的 日志_{f}.txt，看最后一段报错。')
    rows=[]
    for f in OUT:
        actual=sha(lab/f);ref=sha(CORE/f)
        rows.append((f,actual,ref,actual==ref)); print(f,'：','逐字节一致' if actual==ref else '不同，请查输入版本、样本数和数值精度')
    with (lab/'五份文件对照.csv').open('w',encoding='utf-8-sig',newline='') as o:
        w=csv.writer(o);w.writerow(['输出文件','本次SHA256','归档SHA256','字节一致']);w.writerows(rows)
    note=dict(output=str(lab),python=sys.executable,version=platform.python_version(),steps=RUN,archived_inputs={f:sha(lab/f) for f in FILES},agree=sum(u[-1] for u in rows),total=len(rows),scope='从原始2020 CLCD及MODIS原生窗口进行重排和卫星绿度处理；从归档候选模型输入重新运行同域套系比较。未从头生产旧方案和WorldCover模型场。')
    (lab/'运行记录.json').write_text(json.dumps(note,ensure_ascii=False,indent=2),'utf8')
    print(f'结果保存在 {lab}',flush=True);return 0 if note['agree']==5 else 2
if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc:
        print('停止：'+str(exc),file=sys.stderr);sys.exit(1)
