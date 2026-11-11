import argparse,json,hashlib,os
from pathlib import Path
import numpy as np,pandas as pd,rasterio
from scipy.sparse import coo_matrix
A=Path(os.environ.get('ER219_ANNUAL_WORK','D:/ER219_work/annual_actual'));P=A/'product_check';P.mkdir(parents=True,exist_ok=True);T=A/'towns'
OUT=Path(r'D:\ER219_results\年度评价_2015_2025\产品对照');OUT.mkdir(exist_ok=True)
names=pd.read_csv(T/'town_catalogue.csv',dtype={'town_id':str})
focus=['宋庄镇','金盏地区','空港街道','亦庄地区','长辛店镇','王佐镇','马池口地区','四季青地区']
idx=names.town_seq.to_numpy()
grp=np.array([0,1,2,2,3,4,5,5,6,4])
labels=['其他或无数据','耕地','林灌','草地','水体湿地','裸地等','建设']
def sha(path):
 d=hashlib.sha256()
 with open(path,'rb') as f:
  for k in iter(lambda:f.read(1<<20),b''):d.update(k)
 return d.hexdigest()
def run(year,alternate,label):
 with np.load(T/'weights_full.npz') as z:
  tw=z['town'][z['fid']];px=z['pixel'];ar=z['area_m2'].astype(np.float64)*1e-6
 ref=A/'years'/'model'/f'CLCD_{year}.tif'
 with rasterio.open(ref) as a,rasterio.open(alternate) as b:
  assert a.shape==b.shape and a.crs==b.crs and np.max(np.abs(np.array(a.transform)-np.array(b.transform)))<1e-7
  ca=a.read(1).ravel()[px];cb=b.read(1).ravel()[px];assert max(ca.max(),cb.max())<=9
  lc=grp[ca];wc=grp[cb]
 N=len(names);L=len(labels)
 cube=np.bincount(tw*(L*L)+lc*L+wc,weights=ar,minlength=N*L*L).reshape(N,L,L)
 cube=np.concatenate([cube,cube.sum(axis=0,keepdims=True)])
 all_=pd.concat([names,pd.DataFrame([dict(town_id='ALL',display_name='规划范围全部',district='全域',town_seq=N)])],ignore_index=True)
 vals=[];mx=[]
 def ratio(a,b):return float(a/b) if b>0 else np.nan
 for i,gg in enumerate(cube):
  rec=all_.iloc[i]
  point={'年份':year,'对照产品':label,'镇街编号':rec.town_id,'所属区':rec.district,'统计单元':rec.display_name}
  full=float(gg.sum());both=float(gg[1:,1:].sum())
  for c in range(1,L):
   for d in range(1,L):
    mx.append({**point,'CLCD类别':labels[c],'对照类别':labels[d],'面积_km2':float(gg[c,d])})
  for target,group in [('林灌草',[2,3]),('林灌',[2]),('草地',[3]),('水体湿地',[4]),('蓝绿合计',[2,3,4])]:
   lo=np.isin(np.arange(L),group);yes=np.arange(L)>0
   b0=float(gg[np.ix_(lo,yes)].sum());b1=float(gg[np.ix_(yes,lo)].sum());inter=float(gg[np.ix_(lo,lo)].sum());union=b0+b1-inter
   vals.append({**point,'比较对象':target,'范围面积_km2':full,'共同有数据面积_km2':both,'CLCD面积_km2':b0,'对照面积_km2':b1,'对照减CLCD_km2':b1-b0,'两图同判该类_km2':inter,'仅CLCD判该类_km2':b0-inter,'仅对照判该类_km2':b1-inter,'两图同判其他_km2':both-union,'交并比_Jaccard':ratio(inter,union),'CLCD该类与对照同判比例':ratio(inter,b0),'对照该类与CLCD同判比例':ratio(inter,b1),'全域二分类一致率':ratio(both-union+inter,both)})
 t=pd.DataFrame(vals);ms=pd.DataFrame(mx);tag=f'{year}_CLCD对照{label}'
 t.to_csv(OUT/(tag+'_分乡镇面积及同判.csv'),index=False,encoding='utf-8-sig')
 ms.to_csv(OUT/(tag+'_六类面积交叉表.csv'),index=False,encoding='utf-8-sig')
 f=t[t['统计单元'].isin(focus+['规划范围全部']) & (t['比较对象']=='林灌草')].copy()
 f.to_csv(OUT/(tag+'_重点乡镇林灌草.csv'),index=False,encoding='utf-8-sig')
 check=t[(t['统计单元']=='规划范围全部') & (t['比较对象']=='林灌草')].iloc[0];assert abs(check['范围面积_km2']-915.007)<.01 and abs(check['范围面积_km2']-check['共同有数据面积_km2'])<1e-5
 bytown=all_.iloc[:-1].area_km2.to_numpy();assert np.max(abs(bytown-cube[:-1].sum(axis=(1,2))))<5e-5
 receipt=dict(year=year,CLCD=str(ref),CLCDsha=sha(ref),other=str(alternate),other_sha=sha(alternate),area_basis='exact polygon-pixel intersection weights; 79 fixed town/street rows plus two unassigned categories in all-region total',weight_sha=sha(T/'weights_full.npz'),scheme='green=CLCD2,3,4 or WorldCover10,20,30; water-wetland separate; no farmland or urban green subpixel estimates; fractions denominator explicitly named; co-classified area not accuracy or independent truth',weighted_confusion_units='square km',green_entire_plan=check.dropna().to_dict())
 (P/(tag+'_audit.json')).write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
 print(f[['统计单元','CLCD面积_km2','对照面积_km2','两图同判该类_km2','交并比_Jaccard']].round(3).to_string(index=False))
if __name__=='__main__':
 import argparse
 cli=argparse.ArgumentParser();cli.add_argument('year',type=int);cli.add_argument('other',type=Path);cli.add_argument('label');a=cli.parse_args();run(a.year,a.other,a.label)