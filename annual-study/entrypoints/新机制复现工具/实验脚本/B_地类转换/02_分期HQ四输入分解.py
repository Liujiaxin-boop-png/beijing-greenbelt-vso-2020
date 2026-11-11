"""按三阶段逐个运行既有四输入精确Shapley分解。原模型不覆盖，只更改对照年份和输出位置。"""
from pathlib import Path
import pandas as pd, shutil, sys
base=Path(__file__).resolve().parent
root=Path('D:/ER219_work/shp11/core')
src=(root/'hq_attribution.py').read_text(encoding='utf-8-sig')
for a,b in [(2015,2019),(2019,2021),(2021,2025)]:
 d=base/'HQ分项'/f'{a}_{b}';d.mkdir(parents=True,exist_ok=True)
 s=src.replace('YEARS=(2015,2025)',f'YEARS=({a},{b})').replace("g=pd.read_csv(out/'六项格网十年变化.csv')","g=pd.read_csv(Path(r'D:/ER219_work/shp11/core')/'六项格网十年变化.csv')").replace("pd.read_csv(out/'六项逐格逐年原值与得分.csv.gz'","pd.read_csv(Path(r'D:/ER219_work/shp11/core')/'六项逐格逐年原值与得分.csv.gz'").replace("cfile=out/'parameters.json'","cfile=Path('D:/ER219_work/shp11/core/parameters.json')").replace('np.average(g.delta_HQI,weights=g.area_km2)','np.average(target[:,1]-target[:,0],weights=g.area_km2)*scale').replace("'HQI_2015'","'HQI_"+str(a)+"'").replace("'HQI_2025'","'HQI_"+str(b)+"'")
 (d/'代码_HQ.py').write_text(s,encoding='utf8');exec(compile(s,'HQ '+str(a),'exec'),dict(__file__=str(d/'代码_HQ.py'),__name__='__main__'))
rows=[]
for f in sorted((base/'HQ分项').glob('*/HQI_input_attribution.csv')):
 t=pd.read_csv(f);t.insert(0,'阶段',f.parent.name);rows.append(t)
pd.concat(rows).to_csv(base/'生境质量变化_四输入精确分解.csv',index=False,encoding='utf-8-sig')
