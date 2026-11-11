from pathlib import Path
import json, datetime as dt, zipfile, tempfile, csv
from hashlib import sha256
import pandas as pd, numpy as np, geopandas as gp, shapely as sh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
W=Path('D:/ER219_work/shp11/core')
P=Path('D:/ER219_results/年度评价_2015_2025_原始GIS边界/两次转折_空间分析准备')
P.mkdir(parents=True,exist_ok=True)
src=W/'annual_grid_500.gpkg'
g=gp.read_file(src,layer='grid500').sort_values(['iy','ix']).reset_index(drop=True)
g['gid']=np.arange(1,len(g)+1,dtype='int32')
g['ix']=g.ix.astype('int32');g['iy']=g.iy.astype('int32')
assert len(g)==4478 and g.grid_id.is_unique and g.crs.is_projected and g.is_valid.all() and not g.geometry.is_empty.any()
assert all(g.grid_id==('500_'+g.ix.astype(str)+'_'+g.iy.astype(str)))
assert g.crs.axis_info[0].unit_name=='metre'
C=g.geometry.to_numpy();F=sh.box(g.ix*500,g.iy*500,(g.ix+1)*500,(g.iy+1)*500)
assert sh.covers(F,C).all() and np.all(sh.area(F)==250000) and abs(sh.area(C)-g['area']).max()<1e-5
u=gp.read_file(W/'scope.gpkg',layer='planning_scope').geometry.iloc[0]
sh.prepare(u);inter=~sh.covers(u,F);oc=F.copy();oc[inter]=sh.intersection(F[inter],u)
diff=sh.area(sh.symmetric_difference(C,oc)); assert diff.max()<1e-4,diff.max()
t=pd.read_csv(W/'六项逐格逐年原值与得分.csv.gz',usecols=['grid_id','year','ER6','area_km2'])
assert not t.isna().any().any()
e=t.pivot(index='grid_id',columns='year',values='ER6').reindex(g.grid_id);assert e.shape==(4478,11) and not e.isna().any().any()
v=e.to_numpy();yrs=e.columns.to_numpy();assert list(yrs)==list(range(2015,2026))
a=g['area'].to_numpy()/1.e6;ta=t.groupby('grid_id').area_km2.agg(['min','max']).reindex(g.grid_id)
assert (abs(ta['min']-a).max()<1.e-12 and abs(ta['max']-a).max()<1.e-12)
s=pd.DataFrame({'gid':g.gid,'grid_id':g.grid_id,'ix':g.ix,'iy':g.iy,'area_km2':a,'in_frac':a/.25})
for i,y in [(0,15),(4,19),(6,21),(10,25)]:s['ER'+str(y)]=v[:,i]
for name,a1,b in [('r1519',0,4),('r1921',4,6),('r2125',6,10)]:s[name]=(v[:,b]-v[:,a1])/(b-a1)
for d,v2 in [('D19',s.r1921-s.r1519),('D21',s.r2125-s.r1921)]:
 s[d]=v2;s[d.replace('D','cont')]=v2*a/a.sum()
assert s.notna().all().all()
aw=np.average(v,axis=0,weights=a)
reg=pd.read_csv(W/'区域六项逐年指数与分项.csv').sort_values('year').ER6.to_numpy()
assert abs(aw-reg).max()<1.e-11
slope=[(aw[4]-aw[0])/4,(aw[6]-aw[4])/2,(aw[-1]-aw[6])/4]
con=np.array([s.cont19.sum(),s.cont21.sum()])
assert max(abs(con-np.diff(slope)))<1.e-13 and con[0]>0 and con[1]<0
keys=s[['gid','grid_id','area_km2']]; long=keys.loc[keys.index.repeat(10)].reset_index(drop=True)
long['year0']=np.tile(yrs[:-1],len(s));long['year1']=np.tile(yrs[1:],len(s))
long['stage']=np.repeat(0,len(long));long.loc[:,'stage']=np.select([long.year1<=2019,long.year1<=2021],[1,2],default=3)
long['ERstart']=v[:,:-1].flatten();long['ERend']=v[:,1:].flatten();long['dER']=long.ERend-long.ERstart
assert len(long)==44780 and not long.duplicated(['gid','year1']).any() and long['dER'].notna().all()
long.to_csv(P/'年度变化面板.csv',index=False,float_format='%.15g',encoding='utf-8-sig')
zipf=P/'500米格网_两次转折.zip'
idmap={(int(x),int(y)):int(i) for x,y,i in zip(s.ix,s.iy,s.gid)}
neigh={};rows=[];cols=[]
for (x,y),i in idmap.items():
 n=sorted(idmap[(x+dx,y+dy)] for dx in (-1,0,1) for dy in (-1,0,1) if (dx or dy) and (x+dx,y+dy) in idmap)
 neigh[i]=n;rows.extend([i-1]*len(n));cols.extend([j-1 for j in n])
cc,nc=connected_components(coo_matrix((np.ones(len(rows)),(rows,cols)),shape=(len(neigh),len(neigh))).tocsr(),directed=False)
assert cc==4 and min(map(len,neigh.values()))>=2
with tempfile.TemporaryDirectory() as wd:
 wd=Path(wd)
 for name,geom in [('turn500',F),('turn_clip',C)]:
  fl=wd/(name+'.shp');gout=gp.GeoDataFrame(s.copy(),geometry=geom,crs=g.crs)
  gout.to_file(fl,index=False,driver='ESRI Shapefile',encoding='UTF-8')
  chk=gp.read_file(fl);assert chk.crs.equals(g.crs,ignore_axis_order=True) and list(chk.drop(columns='geometry'))==list(s) and (chk.gid==s.gid).all()
  assert sh.equals(chk.geometry.to_numpy(),geom).all() and not chk.isna().any().any() and chk.geometry.is_valid.all()
  for field in s:
   if field!='grid_id': assert np.max(abs(chk[field]-s[field]))<1e-12
 with (wd/'queen500.gal').open('w',encoding='ascii',newline='\n') as f:
  f.write(f'0 {len(s)} turn500 gid\n')
  for k,n in neigh.items():f.write(str(k)+' '+str(len(n))+'\n'+' '.join(map(str,n))+'\n')
 with zipfile.ZipFile(zipf,'w',zipfile.ZIP_DEFLATED) as z:
  for fl in sorted(wd.iterdir()):z.write(fl,arcname=fl.name)
with zipfile.ZipFile(zipf) as z:assert z.testzip() is None
reread=pd.read_csv(P/'年度变化面板.csv');assert len(reread)==44780 and set(reread.gid)==set(s.gid) and np.array_equal(reread[['gid','grid_id']].drop_duplicates().to_numpy(),s[['gid','grid_id']].to_numpy())
for j,(a1,b) in enumerate([(2015,2019),(2019,2021),(2021,2025)]):
 avg=reread.loc[(reread.year0>=a1)&(reread.year1<=b)].groupby('gid').dER.mean()
 assert np.max(abs(avg.to_numpy()-s[['r1519','r1921','r2125'][j]].to_numpy()))<1e-13
txt="""北京第二道绿化隔离地区　2015—2025年两个年度转折｜字段与使用说明

一、使用哪个文件
解压 500米格网_两次转折.zip 时保留 .shp、.shx、.dbf、.prj、.cpg 在同一目录。turn500.shp 是全方格，供 ArcMap 10.8 或 GeoDa 建邻接、运行空间统计；turn_clip.shp 是同一批格网与研究区的相交形状，供呈现边界内的结果。两层具有相同字段和数值。不要用裁剪后的小碎片重新定义全方格邻接。
queen500.gal 是完整方格的二元 Queen 邻接表（共享角或边；键 gid）。输入只有邻居名单，没有提前做行标准化。需行标准化时在统计软件中设置。行标准化邻接与按界内面积加权是两种不同操作。
年度变化面板.csv 为 4,478格 × 10个相邻年度区间；以(gid,year1)或(grid_id,year1)关联年度外部资料。三个方法尚未运行，本包不含外部解释变量，缺资料不填零。

二、格网图层字段
gid：本包稳定整数键，从1到4478，按 iy、ix 升序排列；GeoDa权重取此字段，勿用FID/OID。
grid_id：原计算表格网键，格式500_ix_iy；用于追加原始指标或回连现有工程。
ix / iy：500 m固定方格横、纵序号，原点(0,0)。Albers等积投影，基准WGS84，中央经线105°、标准纬线25°和47°，单位米。
area_km2：方格落在研究边界内的面积（km²），不是完整方格统一的0.25 km²。
in_frac：界内面积/0.25 km²，范围(0,1]，研究边缘小格敏感性可据此筛选。筛选后重新建立与样本一致的W。
ER15 / ER19 / ER21 / ER25：分别为2015、2019、2021、2025年的原模型综合得分；采用同一套固定熵权。
r1519=(ER19−ER15)/4；r1921=(ER21−ER19)/2；r2125=(ER25−ER21)/4。单位均为指数分/年，是该阶段首末分差的年均值。
D19=r1921−r1519；D21=r2125−r1921。均为相邻两阶段的年均变化量之差。正值表示后段向上变化（包括降得较慢）；负值表示向下变化（包括升得较慢）。其正负不意味着单元一定由负转正或反之，须结合两段原变化率。
cont19 / cont21：格网对全区转折的净贡献=相应D×本格界内面积/全区面积。每个字段全域求和等于相应全区年均变化量之差。分析格网自身变化选D19、D21，而非贡献字段；普通地理探测器和LISA不用这两个贡献充当因变量。

三、年度长表
gid、grid_id、area_km2 同上。year0、year1 为区间起止；stage 1=2015—2019、2=2019—2021、3=2021—2025。ERstart、ERend 为该格区间首末得分；dER=ERend−ERstart。
例：year1=2020 表示2019至2020年的变化。外部数据应使用相同年度/区间或事先说明的滞后定义。单一镇街试点标签不能替代格网级工程实施记录。

四、来源与校核
shp11/core/annual_grid_500.gpkg 中 grid500 层保存实际界内几何。全方格按该层的 ix、iy 及 domain.py 的固定原点重建，并与同源 scope.gpkg 重新叠合，逐格核对面积及形状。年度输入为同目录 六项逐格逐年原值与得分.csv.gz 的 ER6。按正式结果 区域六项逐年指数与分项.csv 校验全部11期区域均值。详细数值见 数据核验.json。
"""
(P/'字段与使用说明.txt').write_text(txt,encoding='utf-8-sig')
q={'N_grids':len(s),'N_grid_intervals':len(reread),'N_intervals_per_grid':10,'N_years':11,'area_km2':float(a.sum()),'grid_source':'annual_grid_500.gpkg:grid500 ix/iy and clipped shape; domain.py: original grid origin (0,0), 500 m','regional_slopes':slope,'regional_turns_D19_D21':con.tolist(),'independent_regional_means_mae_max':float(abs(aw-reg).max()),'boundary_reintersection_max_symdiff_m2':float(diff.max()),'queen_components':sorted(np.bincount(nc).tolist(),reverse=True),'queen_neighbor_min_max':[min(map(len,neigh.values())),max(map(len,neigh.values()))],'geo_wkt':g.crs.to_wkt(),'annual_keys_unique':True,'missing_or_infinite_outcomes':0,'zip_sha256':sha256(zipf.read_bytes()).hexdigest(),'annual_csv_sha256':sha256((P/'年度变化面板.csv').read_bytes()).hexdigest()}
(P/'数据核验.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:q[k] for k in ['N_grids','N_grid_intervals','area_km2','regional_slopes','regional_turns_D19_D21','boundary_reintersection_max_symdiff_m2','queen_components']},ensure_ascii=False))