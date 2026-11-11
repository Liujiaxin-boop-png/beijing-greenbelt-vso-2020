# -*- coding: utf-8 -*-
"""Write an independently rescored 500 m panel from three scales of six raw indicators; Python 3.12 standard library."""
import argparse,csv,gzip,hashlib,math,json,io
from pathlib import Path
from collections import Counter
F='LDI HQI LBI MCR ALLDIST LRI'.split(); P=[1,1,0,0,0,1]
BASE=['grid_id','ix','iy','year','area_km2']+F
H=BASE+['C_'+j for j in F]+['ER6','ER_equal']
FN='六项逐格逐年原值与得分.csv.gz'
def rd(p):
 with gzip.open(p,'rt',encoding='utf-8-sig',newline='') as h:
  yield from csv.DictReader(h)
def dig(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def work(src,out):
 source=src.resolve();dest=out.resolve()
 protected=[Path(s).resolve() for s in ('D:/ER219_work','D:/ER219_raw','D:/ER219_figures','D:/ER219_results','D:/ER219_code')]
 if any(dest==p or p in dest.parents for p in protected+[source]):raise ValueError('必须使用个人独立的新输出目录。')
 if dest.exists():raise ValueError('输出目录已存在。请指定另一个尚不存在的目录。')
 paths={i:source/(FN if i==500 else FN.replace('.csv',f'_{i}m.csv')) for i in [200,500,1000]}
 xmn=[math.inf]*6;xmx=[-math.inf]*6;coarse=[]; counts={}; year_ids={}
 for size,p in paths.items():
  n=0;ids={}
  for r in rd(p):
   x=[float(r[k]) for k in F]
   if not all(map(math.isfinite,x)): raise ValueError((size,r['grid_id'],r['year'],'非有限原值'))
   for j,v in enumerate(x):xmn[j]=min(xmn[j],v);xmx[j]=max(xmx[j],v)
   if size==1000:coarse.append(x)
   ids.setdefault(int(r['year']),set())
   if r['grid_id'] in ids[int(r['year'])]:raise ValueError('重复格号/年度')
   ids[int(r['year'])].add(r['grid_id']);n+=1
  if set(ids)!=set(range(2015,2026)) or not all(ids[y]==ids[2015] for y in ids):raise ValueError('不是平衡面板')
  counts[size]=n;year_ids[size]=len(ids[2015]);print(f'{size} m：{n}行、每年{year_ids[size]}格')
 assert counts=={200:275638,500:49258,1000:14267}
 def zz(x,j):
  return ((x-xmn[j]) if P[j] else (xmx[j]-x))/(xmx[j]-xmn[j])
 u=[]
 for j in range(6):
  v=[zz(x[j],j) for x in coarse]; total=math.fsum(v); pos=[z/total for z in v if z>0]
  u.append(1+math.fsum(q*math.log(q) for q in pos)/math.log(len(coarse)))
 wt=[a/sum(u) for a in u]
 dest.mkdir(parents=True,exist_ok=False)
 output=dest/FN;err={k:0. for k in H[len(BASE):]}
 # Historic computed columns are consulted below for checks only; no computed column is copied to output.
 with output.open('xb') as raw, gzip.GzipFile(fileobj=raw,mode='wb',compresslevel=6,mtime=0) as gz, io.TextIOWrapper(gz,encoding='utf-8-sig',newline='') as h:
  writer=csv.DictWriter(h,fieldnames=H,lineterminator='\n');writer.writeheader()
  for r in rd(paths[500]):
   if list(r)!=H:raise ValueError('归档列名或列序已有变化，请检查。')
   z=[zz(float(r[k]),j) for j,k in enumerate(F)]; w=[p*q for p,q in zip(z,wt)]
   new={**{'C_'+f:v for f,v in zip(F,w)},'ER6':math.fsum(w),'ER_equal':math.fsum(z)/len(z)}
   for k in err:err[k]=max(err[k],abs(float(r[k])-new[k]))
   writer.writerow({**{k:r[k] for k in BASE},**{k:format(v,'.14g') for k,v in new.items()}})
 if max(err.values())>1e-9:raise ValueError(f'归档与新算得分偏差超限：{err}')
 reread=Counter(int(r['year']) for r in rd(output));assert len(reread)==11 and set(reread.values())=={4478}
 rec=dict(scope='从三尺度归档格网的六项原值重取极值，仅用完整年序列的1 km样本估熵权。500 m几何编号、年份、面积和六项原值逐项沿用；六个贡献、ER6、ER_equal重新计算，不读取原评分程序或参数表，也不重跑遥感/景观上游。',
           input_counts=counts,grids_per_year=year_ids,fields=H,year_counts=dict(reread),min=dict(zip(F,xmn)),max=dict(zip(F,xmx)),weights=dict(zip(F,wt)),max_abs_difference_from_saved=err,
           inputs=[{'path':str(p),'sha256':dig(p)} for p in paths.values()],output={'path':str(output),'sha256':dig(output)})
 (dest/'from_raw_indicator_columns_receipt.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),'utf-8')
 print(output);print('最大绝对差：',err)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=Path('D:/ER219_work/shp11/core'));p.add_argument('--out',required=True,type=Path);args=p.parse_args();work(args.source,args.out)

