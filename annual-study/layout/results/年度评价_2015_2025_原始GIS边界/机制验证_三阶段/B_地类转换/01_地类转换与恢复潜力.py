from pathlib import Path
import json,numpy as np,pandas as pd,rasterio as rio
B=Path(__file__).resolve().parent;arch=B.parents[1]/'计算结果与核验'/'01_全区与格网';A=Path('D:/ER219_work/annual_actual');srcdir=Path('D:/ER219_work/shp11/core')
panel=pd.read_csv(arch/'六项逐格逐年原值与得分.csv.gz').set_index(['grid_id','year']);geo=panel.xs(2020,level='year').reset_index();pars=json.loads((srcdir/'parameters.json').read_text(encoding='utf8'))
co=np.array([0,.5,1,.8,.7,1,0,.1,.4,.9]);mode=pars['weights']['LRI']/(pars['max']['LRI']-pars['min']['LRI'])
name=['缺值','耕地','林地','灌丛','草地','水体','冰雪','裸地','不透水面','湿地']
stages=[(2015,2019),(2019,2021),(2021,2025)]
pix={}
for y in (2015,2019,2021,2025):
 with rio.open(A/'years/model'/f'CLCD_{y}.tif') as ds:
  pix[y]=ds.read(1);tr=ds.transform
ixt=geo.ix.to_numpy();iyt=geo.iy.to_numpy();w=geo.area_km2.to_numpy()
rows=[];audit=[];catrows=[];detail=[]
for a,b in stages:
 stage=f'{a}_{b}';g0=panel.xs(a,level='year').loc[geo.grid_id];g1=panel.xs(b,level='year').loc[geo.grid_id];er=(g1.ER6-g0.ER6).to_numpy();mats=np.zeros((len(geo),10,10)); 
 for i,(ix,iy) in enumerate(zip(ixt,iyt)):
  xx=ix*500;yy=iy*500;cc=np.arange(int(np.floor((xx-tr.c)/30)),int(np.ceil((xx+500-tr.c)/30)));rr=np.arange(int(np.floor((tr.f-yy-500)/30)),int(np.ceil((tr.f-yy)/30)))
  dx=np.maximum(0,np.minimum(tr.c+30*(cc+1),xx+500)-np.maximum(tr.c+30*cc,xx));dy=np.maximum(0,np.minimum(tr.f-30*rr,yy+500)-np.maximum(tr.f-30*(rr+1),yy))
  wt=np.outer(dy,dx).ravel()/250000;codes=(pix[a][np.ix_(rr,cc)]*10+pix[b][np.ix_(rr,cc)]).ravel()
  mats[i]=np.bincount(codes,weights=wt,minlength=100).reshape(10,10)
 dr=co[None,:]-co[:,None];calc=(mats*dr*mode).sum(axis=(1,2));reference=(g1.C_LRI-g0.C_LRI).to_numpy();err=np.abs(calc-reference).max()
 assert err<2e-8 and np.abs(mats.sum((1,2))-1).max()<1e-8 and (mats[:,0,:].sum()+mats[:,:,0].sum())<1e-8,(err,stage)
 aux=pd.read_csv(B/'HQ分项'/stage/'HQI_transition_grids.csv.gz');aux=aux.assign(c=aux.phi_land*aux.area_km2*pars['weights']['HQI']/(pars['max']['HQI']-pars['min']['HQI']))
 for label,mask in [('全区',np.ones(len(w),bool)),('得分上升',er>1e-10),('得分下降',er< -1e-10)]:
  area=w[mask].sum(); occ=np.einsum('i,ijk->jk',w[mask],mats[mask]);cl=occ/area*dr*mode;rr=aux[aux.grid_id.isin(geo.grid_id[mask])].groupby(['from','to']).c.sum()/area
  for u,v in zip(*np.where(occ>0)):
   if u!=v: rows.append([stage,label,area,name[u],name[v],occ[u,v],cl[u,v],rr.get((u,v),0)])
  for prot,cats in [('耕地',[1]),('林灌',[2,3]),('不透水面',[8]),('水湿地',[5,9])]:
   different=[x for x in range(1,10) if x not in cats];r_in=occ[np.ix_(different,cats)].sum();r_out=occ[np.ix_(cats,different)].sum();catrows.append([stage,label,prot,r_in,r_out,r_in-r_out])
 audit.append([stage,err,np.average(calc,weights=w),np.average(reference,weights=w)])
pd.DataFrame(rows,columns=['阶段','格网组','组界内面积_km2','转出地类','转入地类','格网占比按界内面积折算_km2','对C_LRI带符号贡献','对C_HQI地类输入的带符号贡献']).to_csv(B/'CLCD地类转换_计分精确贡献.csv',encoding='utf-8-sig',index=False)
pd.DataFrame(catrows,columns=['阶段','格网组','类型','转入折算_km2','转出折算_km2','净增折算_km2']).to_csv(B/'CLCD主要地类_组别转入转出.csv',encoding='utf-8-sig',index=False)
pd.DataFrame(audit,columns=['阶段','逐格最大重构误差','重构全区加权变化','原分项加权变化']).to_csv(B/'地类计分闭合核验.csv',encoding='utf-8-sig',index=False)
t=pd.read_csv(B/'CLCD地类转换_计分精确贡献.csv');t=t[t.格网组=='全区'];k='对C_LRI带符号贡献';h='对C_HQI地类输入的带符号贡献'
for st,g in t.groupby('阶段'):
 print(st);print(pd.concat([g.nlargest(3,k),g.nsmallest(3,k)])[['转出地类','转入地类',k,h]].round(6).to_string(index=False))

