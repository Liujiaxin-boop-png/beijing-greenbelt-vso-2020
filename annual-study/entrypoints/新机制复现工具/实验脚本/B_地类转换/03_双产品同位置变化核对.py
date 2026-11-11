"""两期逐像元对照：以Esri原10m UTM格网为比较支撑，将30m CLCD最近邻映射到比较点。研究区边界内的面积用精确像元与裁剪格网交叠比例计算。"""
import numpy as np,pandas as pd,geopandas as gp,shapely,rasterio as rio,exactextract as ex,json,gc
from rasterio.warp import reproject,Resampling
from pathlib import Path
B=Path(__file__).resolve().parent;root=B.parents[1];arch=root/'计算结果与核验'/'01_全区与格网';eco=root/'高韧性空间因素_2020实证'/'02_过程'/'生态空间';A=Path('D:/ER219_work/annual_actual');T=B/'临时格网';T.mkdir(exist_ok=True)
grid=gp.read_file(arch/'annual_grid_500.gpkg');d=pd.read_csv(arch/'六项逐格逐年原值与得分.csv.gz',usecols=['grid_id','area_km2','year','ER6','C_LRI','C_HQI']);g=grid[['grid_id','geometry']].copy();g['geometry']=g.geometry.segmentize(25);g=g.to_crs(32650);g['clip_utm_m2']=g.area;g=g.merge(d[d.year==2020][['grid_id','area_km2']],on='grid_id',validate='1:1');assert len(g)==4478
t=pd.read_csv(B/'CLCD地类转换_计分精确贡献.csv');curves=[(2019,2021),(2021,2025)]
# Additional nearest-neighbour grid check only, no Esri 2015.
ln=['缺值','不透水或建设','耕地','林地或树木','开敞水面','其他']
ce=np.zeros(256,np.uint8);ce[[1,2,4,5,7,8,9,11]]=5;ce[7]=1;ce[5]=2;ce[2]=3;ce[1]=4
cc=np.zeros(256,np.uint8);cc[1:10]=5;cc[8]=1;cc[1]=2;cc[2]=3;cc[5]=4
gd=[];net=[];comp=[];pairout=[];agreement=[];typed=[];qcheck=[]
for a,b in curves:
 stage=f'{a}_{b}';ref=eco/'Esri2019_mosaic.tif'
 with rio.open(ref) as f:sh=f.shape;crs=f.crs;tr=f.transform
 def read_native(path,lut):
  with rio.open(path) as ds:
   o=np.zeros(sh,np.uint8);reproject(rio.band(ds,1),o,src_crs=ds.crs,src_transform=ds.transform,dst_crs=crs,dst_transform=tr,src_nodata=0,dst_nodata=0,resampling=Resampling.nearest,num_threads=2)
   return lut[o]
 cl1=read_native(A/'years/model'/f'CLCD_{a}.tif',cc);cl2=read_native(A/'years/model'/f'CLCD_{b}.tif',cc);es1=read_native(eco/f'Esri{a}_mosaic.tif',ce);es2=read_native(eco/f'Esri{b}_mosaic.tif',ce)
 valid=(cl1!=0)&(cl2!=0)&(es1!=0)&(es2!=0);combined=(cl1.astype('uint16')*6+cl2)*36 + es1*6+es2
 combined[~valid]=0;graph=T/f'pair_{a}_{b}.tif'
 with rio.open(graph,'w',driver='GTiff',height=sh[0],width=sh[1],count=1,dtype='uint16',nodata=0,crs=crs,transform=tr,compress='deflate',tiled=True) as f:f.write(combined,1)
 del cl1,cl2,es1,es2,combined,valid;gc.collect()
 f=ex.exact_extract(str(graph),g,['unique','frac','count'],include_cols=['grid_id'],output='pandas');f=f.merge(g[['grid_id','area_km2','clip_utm_m2']],on='grid_id',validate='1:1');i=f.grid_id
 lo=d[d.year==a].set_index('grid_id').loc[i];hi=d[d.year==b].set_index('grid_id').loc[i];r=((hi.ER6-lo.ER6).to_numpy());l=((hi.C_LRI-lo.C_LRI).to_numpy());h=((hi.C_HQI-lo.C_HQI).to_numpy())
 # Each parcel's absolute area in equal-area CRS, scaled by exactly covered fraction of UTM geometry (removes UTM scale).
 coverage=np.clip(100*f['count'].values/f.clip_utm_m2,0,1);area=f.area_km2.to_numpy()*coverage
 assert coverage.min()>.98,(stage,coverage.min());qcheck.append([stage,len(area),area.sum(),coverage.min(),g.area_km2.sum()]);cum=np.zeros((36,36))
 C=np.zeros((len(f),36));E=np.zeros_like(C)
 P=np.zeros((len(f),36));S=np.zeros_like(P);U=np.zeros_like(P)
 for ix,rec in enumerate(f.itertuples()):
  u=np.asarray(rec.unique,dtype=int);v=np.asarray(rec.frac,dtype=float);cd=u//36;ed=u%36;np.add.at(cum,(cd,ed),v*area[ix]);C[ix]=np.bincount(cd,weights=v,minlength=36);E[ix]=np.bincount(ed,weights=v,minlength=36)
  ok=cd==ed;P[ix]=np.bincount(cd[ok],weights=v[ok],minlength=36)
  ok=(cd%6==ed%6);S[ix]=np.bincount(cd[ok],weights=v[ok],minlength=36)
  ok=(cd//6==ed//6);U[ix]=np.bincount(cd[ok],weights=v[ok],minlength=36)
 nas=np.arange(36);va=nas//6;vb=nas%6
 for c in range(1,6):
  for e in range(1,6):
   if c==e:continue
   j=c*6+e
   for label,mask in [('全区',np.ones(len(f),bool)),('综合得分上升',r>1e-10),('综合得分下降',r< -1e-10)]:
    def wsum(x):return np.dot(x[mask],area[mask])
    ar=wsum(C[:,j]);aa=wsum(E[:,j]);both=wsum(P[:,j]);ct=wsum(S[:,j]);bt=wsum(U[:,j]);pairout.append([stage,label,ln[c],ln[e],sum(area[mask]),ar,aa,both,np.nan if ar<1e-12 else both/ar*100,np.nan if ar<1e-12 else ct/ar*100,np.nan if ar<1e-12 else bt/ar*100])
 for c in [1,2,3,4]:
  cin=C[:,(vb==c)&(va!=c)].sum(1);cout=C[:,(va==c)&(vb!=c)].sum(1);ein=E[:,(vb==c)&(va!=c)].sum(1);eout=E[:,(va==c)&(vb!=c)].sum(1)
  dc=cin-cout;de=ein-eout
  net.append([stage,ln[c],*[(z*area).sum() for z in [cin,cout,dc,ein,eout,de]]])
  for k in [0.001,1,2]:
   sign=lambda z:np.select([100*z>k,100*z< -k],[1,-1],default=0)
   sc,se=sign(dc),sign(de);grp=np.select([(sc==1)&(se==1),(sc==-1)&(se==-1),(sc*se==-1),(sc==0)&(se==0)],['同增','同减','反向','均无明显变化'],default='仅一套有变化')
   for cat in np.unique(grp):
    m=grp==cat;w=area[m];agreement.append([stage,ln[c],k,cat,sum(m),sum(w),sum(w)/sum(area)*100,np.average(r[m],weights=w),np.average(l[m],weights=w),np.average(h[m],weights=w)])
  if c==1:
   gd.append(pd.DataFrame({'阶段':stage,'grid_id':i.to_numpy(),'相交面积_km2':area,'CLCD建设转入比例':cin,'CLCD建设转出比例':cout,'Esri建设转入比例':ein,'Esri建设转出比例':eout,'阶段得分变化':r,'分项恢复潜力变化':l,'分项HQ变化':h}))
 print(stage,'common km2',area.sum(),flush=True)
pd.DataFrame(pairout,columns=['阶段','格网组','期初地类','期末地类','共同有效面积_km2','CLCD转换面积_km2','Esri转换面积_km2','两套同位置同转移_km2','CLCD转换获两套完整确认_pct','CLCD转换末期同类_pct','CLCD转换初期同类_pct']).to_csv(B/'两套底图_像元级同位置转换对照.csv',encoding='utf-8-sig',index=False)
pd.DataFrame(net,columns=['阶段','类型','CLCD转入_km2','CLCD转出_km2','CLCD净增_km2','Esri转入_km2','Esri转出_km2','Esri净增_km2']).to_csv(B/'两套底图_共同裁剪范围转入转出.csv',encoding='utf-8-sig',index=False)
pd.DataFrame(agreement,columns=['阶段','类型','净变化容差_百分点','两产品方向','格数','面积_km2','占研究区_pct','组平均ΔER','组平均ΔC_LRI','组平均ΔC_HQI']).to_csv(B/'两套底图_格网增减方向一致和不一致.csv',encoding='utf-8-sig',index=False)
pd.concat(gd).to_csv(B/'界内可比建设地类_逐格流入流出.csv.gz',encoding='utf-8-sig',index=False)
pd.DataFrame(qcheck,columns=['阶段','格数','共同有效面积_km2','格网有效覆盖最低比例','基准范围面积_km2']).to_csv(B/'双产品空间支持核验.csv',encoding='utf-8-sig',index=False)

