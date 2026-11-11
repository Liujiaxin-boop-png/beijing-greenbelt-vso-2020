from common import *
import re,sys
s=pd.read_csv(D/'六项逐格逐年原值与得分.csv.gz');raw=gp.read_file(D/'annual_grid_500.gpkg',layer='grid500')
gr=s.query('year==2015')[['ix','iy','grid_id','area_km2']]
g=raw[['ix','iy','geometry']].merge(gr,on=['ix','iy'],validate='1:1').set_index('grid_id').sort_index()
scope=gp.read_file(D/'scope.gpkg',layer='planning_scope')[['geometry']]
wide=s.pivot(index='grid_id',columns='year',values='ER6').reindex(g.index);N=len(g)
assert len(s)==N*11 and np.max(np.abs(g.area/1e6-g.area_km2))<1e-6
a=g.area_km2.to_numpy();sen=pd.read_csv(D/'六项格网十年变化.csv').set_index('grid_id').loc[g.index,'Sen']
root=Path('D:/ER219_work'); R=root/'readerplate11'; fn={'3':root/'litlogic11/types/region/map_region.json','A2':R/'appindices/sp0.json','A3':R/'appindices/sp1.json','A4':R/'appindices/sp2.json',**{k:R/f'appannual/map_{k}.json' for k in ['A5','A6','A9']}}
def classif(u,n):
 if n==5:return np.select([u<-.001,u<-.0002,u<=.0002,u<=.001],['1','2','3','4'],default='5')
 return np.select([u<-.004,u<-.001,u<-.0002,u<=.0002,u<=.001,u<=.004],list('123456'),default='7')
def share(v):return float(100*np.sum(a[np.asarray(v)<0])/a.sum())
metrics=['LDI','HQI','LBI','MCR','ALLDIST','LRI']; cutsdict={};labels={}
for j,m in enumerate(metrics):
 ix=np.argsort(s[m]);vals=s[m].to_numpy()[ix];wa=s.area_km2.to_numpy()[ix];v=vals[np.searchsorted(np.cumsum(wa),np.array([.25,.5,.75])*wa.sum())]/(10000 if m=='MCR' else 1)
 level=1 if m=='MCR' else -1 if m=='ALLDIST' else 2
 cuts=np.round(v,level);cutsdict[m]=list(cuts);f=lambda x:(f'{x:.0f}' if m=='ALLDIST' else f'{x:.1f}' if m=='MCR' else f'{x:.2f}')
 labels[j]=['≤'+f(cuts[0]),'('+f(cuts[0])+', '+f(cuts[1])+']','('+f(cuts[1])+', '+f(cuts[2])+']','>'+f(cuts[2])]
(W/'map_quantiles.json').write_text(json.dumps(cutsdict,ensure_ascii=False,indent=2),'utf8')
for k in sys.argv[1:]:
 c=json.loads(fn[k].read_text('utf-8-sig'));fram=g[['ix','iy','area_km2','geometry']].copy();changed={};kk=0
 for j,m in enumerate(c['maps']):
  ly=m['layers'][0];fc=ly['fc'];fld=ly['field']
  if k in ('A2','A3','A4'):
   item,yr=m['name'].split('_');yr=int(yr);idx=metrics.index(item);rr=s[s.year==yr].set_index('grid_id').loc[g.index,item].to_numpy()/(10000 if item=='MCR' else 1)
   cl=(1+np.searchsorted(cutsdict[item],rr,side='left')).astype(str)
   for h,v in enumerate(ly['values']):v['label']=labels[idx][h];changed['原值范围'+str(j//3)+str(h)]=labels[idx][h]
  elif k=='A5':
   yr=2015+j;rr=wide[yr];cl=(1+np.searchsorted([.15,.2,.3,.4],rr,side='left')).astype(str);changed['mean_'+str(yr)]=f'均值 {np.average(rr,weights=a):.4f}'
  elif k=='A6':
   yr=2016+j;rr=wide[yr]-wide[yr-1];cl=classif(rr,7);changed['percent_'+str(yr)]=f'下降面积 {share(rr):.1f}%'
  elif k=='A9':
   years=[(2015,2019),(2019,2021),(2021,2025)]
   if j<3:
    yr0,yr1=years[j];rr=(wide[yr1]-wide[yr0])/(yr1-yr0)
   else:rr=sen
   cl=classif(rr,7);changed['decline'+str(j)]=f'下降面积 {share(rr):.1f}%'
  else:
   rr=sen if j==0 else (wide[2021]-wide[2019])/2;cl=classif(rr,5);changed['long全区' if j==0 else 'rise全区']=f'下降面积占比 {share(rr):.1f}%'
  fram[fld]=np.asarray(cl);fram['v'+fld]=np.asarray(rr)
  m['extent']=ext(scope,m['w'],m['h'])
  for ly in m['layers']:ly['gdb']=str(db(k));ly['name']=ly['name'].replace('公开图重建规划边界','项目原始二道绿隔边界').replace('规划图重建边界','项目原始二道绿隔边界')
 for e in c['elements']:
  if e.get('name') in changed:e['text']=changed[e['name']]
 fram=fram.reset_index();geo(k,fc,fram);geo(k,'scope',scope)
 if k=='3':
  c['elements']=[e for e in c['elements'] if e.get('name') not in {'10公里标尺','标尺刻度0','标尺刻度1','标尺刻度2','零千米','十千米'}]
  c['scales']=[dict(name='两图共用比例尺',map=c['maps'][0]['name'],x=7.0,y=2.34,w=2.2,h=.12,division_km=5,divisions=2,font_size=6.8,color='#34423A')]
 config(k,c);print(k,len(fram),flush=True)
