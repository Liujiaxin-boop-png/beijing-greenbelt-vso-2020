from pathlib import Path
import hashlib,json,pandas as pd,numpy as np
B=Path(__file__).resolve().parent; R=B.parents[1];src=R/'计算结果与核验'/'01_全区与格网'
s=pd.read_csv(B/'CLCD地类转换_计分精确贡献.csv');s=s[s.格网组=='全区'].set_index('阶段');q=pd.read_csv(B/'生境质量变化_四输入精确分解.csv').set_index('阶段');l=pd.read_csv(B/'地类计分闭合核验.csv').set_index('阶段');assert np.allclose(s.groupby(level=0)['对C_HQI地类输入的带符号贡献'].sum(),q.delta_ER_land_class,atol=1e-11);assert np.allclose(s.groupby(level=0)['对C_LRI带符号贡献'].sum(),l.原分项加权变化,atol=1e-11)
p=pd.read_csv(B/'两套底图_像元级同位置转换对照.csv');assert np.all(p['两套同位置同转移_km2']<=np.minimum(p['CLCD转换面积_km2'],p['Esri转换面积_km2'])+1e-9)
m=pd.read_csv(B/'两套底图_格网增减方向一致和不一致.csv');z=m.groupby(['阶段','类型','净变化容差_百分点']).agg(n=('格数','sum'),pct=('占研究区_pct','sum'));assert (z.n==4478).all() and np.isclose(z.pct,100).all()
v=pd.read_csv(B/'不透水转水_容许一格30米错位复核.csv').set_index('阶段');p=p[(p.格网组=='全区')&(p.期初地类=='不透水或建设')&(p.期末地类=='开敞水面')].set_index('阶段');assert np.allclose(v.同像元_pct,p['CLCD转换获两套完整确认_pct'],atol=1e-5)
sources=[src/'六项逐格逐年原值与得分.csv.gz',src/'annual_grid_500.gpkg',Path('D:/ER219_work/annual_actual/hq/sensitivity_3threat.csv'),Path('D:/ER219_work/shp11/core/parameters.json')]+[Path('D:/ER219_work/annual_actual')/'years/model'/f'CLCD_{y}.tif' for y in [2015,2019,2021,2025]]+[R/'高韧性空间因素_2020实证'/'02_过程'/'生态空间'/f'Esri{y}_mosaic.tif' for y in [2019,2021,2025]]
def sha(f):
 with f.open('rb') as t:return hashlib.file_digest(t,'sha256').hexdigest()
(B/'核对回执.json').write_text(json.dumps(dict(输入及指纹={str(f):sha(f) for f in sources},模型恢复潜力逐格最大误差=float(l.逐格最大重构误差.max()),全部分期与空间核对='通过',三期HQ阈值及原始栅格闭合='见各期HQ分项/HQI_input_audit.json'),ensure_ascii=False,indent=2),encoding='utf8')
