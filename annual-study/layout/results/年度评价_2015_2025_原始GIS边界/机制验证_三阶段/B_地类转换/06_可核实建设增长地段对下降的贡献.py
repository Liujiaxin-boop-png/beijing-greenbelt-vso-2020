from pathlib import Path
import pandas as pd,numpy as np
B=Path(__file__).resolve().parent
d=pd.read_csv(B/'界内可比建设地类_逐格流入流出.csv.gz');out=[]
for st,t in d.groupby('阶段'):
 y=t['阶段得分变化'];w=t['相交面积_km2'];zz=t.C_l if 'C_l' in t else (t.CLCD建设转入比例-t.CLCD建设转出比例)*100;ee=(t.Esri建设转入比例-t.Esri建设转出比例)*100
 for th in [.001,1,2]:
  m=(zz>th)&(ee>th);gross=w*(-y).clip(lower=0);net=w*y;out.append([st,th,m.sum(),w[m].sum(),100*w[m].sum()/sum(w),100*w[m&(y< -1e-10)].sum()/sum(w[m]),np.average(y[m],weights=w[m]),100*gross[m].sum()/sum(gross),100*net[m].sum()/sum(net)])
r=pd.DataFrame(out,columns=['阶段','建设比例增幅超过_百分点','两套均增格数','两套均增面积_km2','两套均增占全区面积_pct','两套均增内综合得分下降面积_pct','组ΔER','占全区负向变化总量_pct','组净变化占全区净变化_pct']);r.to_csv(B/'两套均见建设增加的地段对区域下降的贡献.csv',index=False,encoding='utf-8-sig');print(r.round(3).to_string(index=False))
