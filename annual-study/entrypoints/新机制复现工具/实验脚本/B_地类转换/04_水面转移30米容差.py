from pathlib import Path
import numpy as np,pandas as pd,rasterio as rio, exactextract as ex, geopandas as gp
from scipy.ndimage import distance_transform_edt
from rasterio.windows import Window
B=Path(__file__).resolve().parent; arch=B.parents[1]/'计算结果与核验'/'01_全区与格网';g=gp.read_file(arch/'annual_grid_500.gpkg');ga=g.geometry.area/1e6; g=g[['grid_id','geometry']].copy();g['geometry']=g.geometry.segmentize(25);g=g.to_crs(32650);utm=g.geometry.area
co=['缺值','不透水或建设','耕地','林地或树木','开敞水面','其他'];its=[];nv=[]
for stage in ['2019_2021','2021_2025']:
 inp=B/'临时格网'/f'pair_{stage}.tif'
 with rio.open(inp) as ds:
  # Decode 1(from),4(to): target for CLCD and Esri. Keep rows in chunks to avoid memory-intensive full city distance grid.
  out=B/'临时格网'/f'water30_{stage}.tif';meta=ds.profile.copy();meta.update(dtype='uint8',nodata=0,compress='deflate')
  with rio.open(out,'w',**meta) as f:
   for _,win in ds.block_windows(1):
    # >=3 pixel halo; radius 30m on 10m lattice, no tile seams.
    r0=int(win.row_off);c0=int(win.col_off);re=r0+int(win.height);ce=c0+int(win.width)
    row=max(0,r0-4);col=max(0,c0-4);exr=min(ds.height,re+4);exc=min(ds.width,ce+4);a=ds.read(1,window=Window(col,row,exc-col,exr-row));valid=a!=0;cl=a//36;es=a%36;observed=(es==10)&valid;near=(distance_transform_edt(~observed)<=3) if observed.any() else np.zeros(a.shape,bool)
    p=np.where(valid,1,0).astype('uint8');cnt=(cl==10)&valid;p[cnt]=2+es[cnt]//6;p[cnt&near]=p[cnt&near]+10;p[cnt&observed]=p[cnt&observed]+10
    f.write(p[r0-row:re-row,c0-col:ce-col],1,window=win)
 rr=ex.exact_extract(str(out),g,['unique','frac','count'],output='pandas');area=ga.to_numpy()*np.clip(rr['count']*100/utm.to_numpy(),0,1);acc=np.zeros(40)
 for i,rec in enumerate(rr.itertuples()):np.add.at(acc,np.asarray(rec.unique,dtype=int),rec.frac*area.iloc[i])
 total=acc[3:].sum()
 for c in range(1,6):
  j=2+c;aa=sum(acc[[j,j+10,j+20]]);its.append([stage,co[c],aa,aa/total*100])
 nv.append([stage,total,acc[23:].sum(),acc[13:].sum(),acc[23:].sum()/total*100,acc[13:].sum()/total*100])
pd.DataFrame(its,columns=['阶段','Esri识别期初地类','CLCD不透水转水范围内的面积_km2','所占百分比']).to_csv(B/'不透水转水_分歧在哪种期初分类.csv',index=False,encoding='utf-8-sig')
n=pd.DataFrame(nv,columns=['阶段','CLCD不透水转水_km2','Esri同像元确认_km2','Esri30m内含对应变化_km2','同像元_pct','容许30m位置误差_pct']);n.to_csv(B/'不透水转水_容许一格30米错位复核.csv',index=False,encoding='utf-8-sig');print(n.round(3).to_string(index=False));print(pd.DataFrame(its).round(3).to_string(index=False))

