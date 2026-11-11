from pathlib import Path
import pandas as pd, numpy as np
D=Path(__file__).resolve().parent;z=pd.read_csv(D/'三个阶段的年均变化量_逐格.csv.gz');ds=pd.read_csv(D/'03_不按Y优化的统一分组阈值.csv').query("检验=='阶段'").set_index('因素');out=[]
for tt,h in z.groupby('时期'):
 for k in ds.index:
  s=h.dropna(subset=[k]);v=s.Y.to_numpy();x=s[k].to_numpy();w=s.area_km2.to_numpy();c=ds.loc[k,'主分界绝对值_50']
  if not len(s): continue
  av=lambda u:np.average(u,weights=w)
  out.append([tt,k,len(s),w.sum(),av(x),av(v),*(100*av(b) for b in [x>0,x>c,x< -c,v>0,(v>0)&(x>0),(v<0)&(x<0)])])
r=pd.DataFrame(out,columns=['时期','因素','有效格数','界内面积_km2','该范围因素年均变化','该范围韧性年均变化','因素为正面积_pct','因素明显增加面积_pct','因素明显减少面积_pct','韧性为正面积_pct','同为正面积_pct','同为负面积_pct']);r.to_csv(D/'07_区域是否同步变化_与格间q分开.csv',encoding='utf-8-sig',index=False);print(r.round(4).to_string(index=False))

