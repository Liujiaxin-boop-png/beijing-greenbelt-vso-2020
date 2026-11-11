# -*- coding: utf-8 -*-
"""Read-only, independently recomputed six-field worked example. No output is written to the archive."""
import argparse,csv,json,hashlib,sys,warnings
sys.stdout.reconfigure(encoding='utf-8');warnings.filterwarnings('ignore',category=DeprecationWarning)
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio as rio
from scipy.ndimage import distance_transform_edt,label
from rasterio.windows import Window
root=Path('D:/ER219_work'); A=root/'annual_actual'; C=root/'shp11/core'; RAW=Path('D:/ER219_raw')
def run(y,grid):
 s,ix,iy=map(int,grid.split('_'))
 if s!=500 or y not in range(2015,2026):raise ValueError('主表为500米，年度2015至2025')
 par=json.loads((C/'parameters.json').read_text('utf8')); keys=par['fields']
 rr=json.loads((RAW/f'CLCD_v105_2015_2025/CLCD_{y}_source.json').read_text('utf8'))
 y0,c0,nw,nh=rr['large_window_rcwh']; mx,my,w,h=rr['model_window_colrowwh']
 win=Window(mx-c0,my-y0,w,h)
 with rio.open(RAW/f'CLCD_v105_2015_2025/CLCD_{y}_Beijing_native.tif') as f:
  land=f.read(1,window=win);tr=f.window_transform(win)
 digest=hashlib.sha256(land.tobytes()).hexdigest()
 assert digest==rr['model_native_pixel_sha256'],'原生像元指纹不符，请核对年份、窗口、产品版本'
 x0=(ix*s-tr.c)/30;x1=((ix+1)*s-tr.c)/30;y0=(tr.f-(iy+1)*s)/30;y1=(tr.f-iy*s)/30
 x=np.arange(int(np.floor(x0)),int(np.ceil(x1)));yrows=np.arange(int(np.floor(y0)),int(np.ceil(y1)))
 sub=Window(x[0],yrows[0],len(x),len(yrows));b=(np.minimum(x1,x+1)-np.maximum(x0,x))[None,:]*(np.minimum(y1,yrows+1)-np.maximum(y0,yrows))[:,None]*900
 valid=((x+.5>=x0)&(x+.5<x1))[None,:]&((yrows+.5>=y0)&(yrows+.5<y1))[:,None];lc=land[np.ix_(yrows,x)]
 g=np.array([0,1,2,2,3,4,0,5,6,4])[lc]
 assert abs(b.sum()-250000)<.001 and g.min()>0
 ps=np.bincount(g.ravel(),weights=b.ravel(),minlength=7)[1:]/b.sum();nz=ps[ps>0]
 ldi=-sum(nz*np.log(nz))
 sz=[]
 for k in range(1,7):
  z,_=label(valid&(g==k),np.ones((3,3),np.uint8));sz.extend(np.bincount(z.ravel())[1:])
 frac=np.array(sz)/valid.sum();v=sum(frac*frac)
 com=np.array([len(sz)/(.0009*valid.sum()),1/v,1-v]);lo=np.array(par['LBI_component_lo']);hi=np.array(par['LBI_component_hi'])
 lbi=((com-lo)/(hi-lo))@np.array([.5,.3,.2])
 rec=np.array([0,.5,1,.8,.7,1,0,.1,.4,.9])
 lri=np.average(rec[lc],weights=b)
 # Grow a genuine 30m window until even the largest observed answer is nearer than its edge.
 bg=np.isin(land,[2,3,4,5,9])
 dmax=None; da=None
 for pad in [32,128,512,2048,max(land.shape)]:
  xmin=max(0,x[0]-pad);xmax=min(land.shape[1],x[-1]+1+pad);yt=max(0,yrows[0]-pad);yb=min(land.shape[0],yrows[-1]+1+pad)
  chunk=bg[yt:yb,xmin:xmax]
  if not chunk.any():continue
  ed=distance_transform_edt(~chunk,sampling=30);da=ed[np.ix_(yrows-yt,x-xmin)];dmax=da.max()
  if dmax < pad*30 or (xmin==0 and xmax==land.shape[1] and yt==0 and yb==land.shape[0]):break
 else:raise ValueError('蓝绿距离背景不足')
 alld=np.average(da,weights=b)
 def take(p):
  with rio.open(p) as f:
   assert np.allclose(f.transform,tr,rtol=0,atol=.00001) and f.shape==land.shape
   return f.read(1,window=sub).astype('float64')
 d=take(A/f'hq/degradation/D_{y}.tif')
 sens=pd.read_csv(A/'hq/sensitivity_3threat.csv').set_index('lucode').habitat.to_dict()
 hh=np.vectorize(sens.__getitem__)(lc);k=par['k']
 hqi=np.average(hh*k**2.5/(d**2.5+k**2.5),weights=b)
 mcr=np.average(take(A/f'mcr/{y}/MCR_{y}.tif'),weights=b)
 vals=np.array([ldi,hqi,lbi,mcr,alld,lri])
 mins=np.array([par['min'][key] for key in keys]);maxs=np.array([par['max'][key] for key in keys]);weights=np.array([par['weights'][key] for key in keys])
 rawz=(vals-mins)/(maxs-mins);zs=np.where([1,1,0,0,0,1],rawz,1-rawz);Cj=zs*weights
 f=pd.read_csv(C/'六项逐格逐年原值与得分.csv.gz')
 hit=f[(f.year==y)&(f.grid_id==grid)]
 if len(hit)!=1:raise ValueError('网格不在研究区或年份错误')
 ref=hit.iloc[0];tol=np.array([1e-9,3e-7,1e-8,1e-4,1e-4,1e-9])
 print('年度',y,'grid_id',grid,'边界内面积km²',ref.area_km2,'完整方格面积m²',b.sum())
 print('格内六地类面积占比（耕/林灌/草/水湿/裸/建设）',ps,'中心像元数',valid.sum(),'八邻接斑块数',len(sz),'LBI三个原始分量',com)
 for key,a,z,c,t in zip(keys,vals,zs,Cj,tol):print(f'{key:7s} 复算原值={a:.9f}  对照={ref[key]:.9f}  差={a-ref[key]:+.8g}  同向标准分={z:.8f}  加权贡献={c:.8f}')
 er=float(Cj.sum())
 print(f'ER6 复算={er:.10f} 正式={ref.ER6:.10f}  差={er-ref.ER6:+.3g}')
 assert np.all(abs(vals-ref[keys].to_numpy(float))<tol) and abs(er-ref.ER6)<1e-6, '至少一项超容差，请逐项查输入与计算'
 print('通过。CLCD窗口来自原始北京栅格，LDI/LBI/LRI/ALLDIST重新计算。HQI从归档退化面重建；MCR复核格均值；本步骤没有重跑InVEST、MSPA和全域路径。')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--year',type=int,default=2020);p.add_argument('--grid',default='500_1955_8712')
 a=p.parse_args();run(a.year,a.grid)

