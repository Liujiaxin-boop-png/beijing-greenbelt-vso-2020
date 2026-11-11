"""在一个此前不存在的目录重算镇街边界、分型、赋权检验和政策组对照。只读既有成果。"""
from pathlib import Path
import argparse, shutil, subprocess, sys, os, json
import pandas as pd

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--out", required=True, type=Path, help="新建输出目录，若已存在则停止")
p.add_argument("--core", type=Path, default=Path("D:/ER219_work/shp11/core"), help="放本人重算后的5张输入表/参数文件，文件名同原表")
arg=p.parse_args()
t=Path("D:/ER219_work/shp11")
work=arg.out.resolve()
if work.exists(): raise SystemExit("该输出目录已经存在。请新建一个不同名称。")
if any(work.is_relative_to(x.resolve()) for x in [t,Path("D:/ER219_code"),Path("D:/ER219_raw")]):raise SystemExit("请在计算档案目录以外另建练习文件夹。")
inputs=["parameters.json","六项逐格逐年原值与得分_1000m.csv.gz","六项逐格逐年原值与得分.csv.gz","区域六项逐年指数与分项.csv","六项格网十年变化.csv"]
for f in inputs:
    if not (arg.core/f).is_file(): raise FileNotFoundError(arg.core/f)
work.mkdir(parents=True)
for name in ("towns","core","method_clarify"): (work/name).mkdir()
for f in inputs: shutil.copy2(arg.core/f, work/"core"/f)
steps=[("towns",f) for f in ["territories.py","common_domain.py","summarize_towns.py","classify.py"]]+[("method_clarify","entropy_reference_scale.py")]
env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
for folder,f in steps:
    dst=work/folder/f;shutil.copy2(t/folder/f,dst)
    print("正在计算："+f,flush=True)
    with (work/(f+".log")).open("w", encoding="utf-8") as log:
        proc=subprocess.run([sys.executable,"-B",str(dst)],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT)
    if proc.returncode: raise SystemExit(str(dst)+"运行失败，请打开 "+str(work/(f+".log")))
j=json.loads((work/"towns"/"全域分型摘要.json").read_text(encoding="utf-8"))
f=pd.read_csv(work/"towns"/"试点组分层对照.csv")
g=pd.read_csv(work/"core"/"六项逐格逐年原值与得分.csv.gz",usecols=["year","area_km2","ER_equal"])
weighted=lambda yr:(g.loc[g.year==yr,"area_km2"]*g.loc[g.year==yr,"ER_equal"]).sum()/g.loc[g.year==yr,"area_km2"].sum()
vals={"地区类型数量":{k:j["groups"][k]["n"] for k in "ABCD"},"各类选例0_1_2平方公里":{k:j["groups"][k]["selected"] for k in "ABCD"},"等权十年全区净分差":float(weighted(2025)-weighted(2015)),"等权仍同型":j["equal_match"],"Sen仍同型":j["sen_match"],"内缩后同型及有效数":[j["inner_match"],j["inner_n_valid"]],"试点减对照_区内及基线分层":dict(zip(f.bins.astype(str),f.difference))}
printed=json.dumps(vals,ensure_ascii=False,indent=2)
(work/"请先看_本轮结果.json").write_text(printed,encoding="utf-8")
print(printed,flush=True)
