from common import *
import sys
sys.path.insert(0,'D:/ER219_work/annual_actual/refocus10/figures')
from chart_native import Chart
from matplotlib.ticker import MaxNLocator
reg=pd.read_csv(D/'区域六项逐年指数与分项.csv').set_index('year');d=pd.read_csv(D/'六项逐格逐年原值与得分.csv.gz');wide=d.pivot(index='grid_id',columns='year',values='ER6');a=d.query('year==2015').set_index('grid_id').loc[wide.index,'area_km2']
town=pd.read_csv(T/'82镇街首末年分型与敏感性.csv'); ex=pd.read_csv(T/'四类入选镇街指标与增减地段强度.csv').set_index('base_type').sort_index();ty=dict(A='普遍下降型',B='普遍上升型',C='局部上升主导型',D='局部下降主导型')
mut='#526158';ink='#27362E';gridcol='#D9E2DB';green='#357767';rust='#A3654D';tk='#718077';yellow='#AE984F';blue='#578091'
def new(k,h):
 t=Chart(k,h,'','','');t.e=[];t.w=17.7;return t
def put(t,k):config(k,dict(page=dict(width_cm=t.w,height_cm=t.h,font='SimHei'),expected_maps=0,maps=[],elements=t.e,scales=[],north_arrows=[],dpi=480))
def nice(vals,num=3):
 vals=np.array(vals);lo,hi=vals.min(),vals.max();dif=max(hi-lo,abs(lo)*.000001,1e-7);loc=MaxNLocator(nbins=num,min_n_ticks=3);ticks=loc.tick_values(lo-.08*dif,hi+.08*dif);return ticks
def lineplot(t,key,yr,vals,box,fmt,ticks,colour=green,endlabel=False):
 l,top,ww,hh=box;low,hi=ticks[0],ticks[-1];bot=top+hh; x=lambda y:l+ww*(y-min(yr))/(max(yr)-min(yr)); yp=lambda v:bot-hh*(v-low)/(hi-low)
 assert min(vals)>=low-1.e-11 and max(vals)<=hi+1.e-11,(key,min(vals),max(vals),low,hi)
 for v in ticks:
  y=yp(v);t.line(key+'刻'+str(v),[(l,y),(l+ww,y)],tk if abs(v)<1e-12 else gridcol,.55 if abs(v)<1e-12 else .33);t.text(key+'值'+str(v),fmt(v),l-.10,y,7.1,False,mut,'right')
 pts=[(x(i),yp(v)) for i,v in zip(yr,vals)];t.line(key+'曲线',pts,colour,1.35)
 for i,(xx,yy) in enumerate(pts):t.dot(key+'点'+str(i),xx,yy,colour,3.5)
 for i in (2015,2019,2021,2025):t.text(key+'年'+str(i),str(i),x(i),bot+.27,7.1,False,mut,'center')
 if endlabel:t.text(key+'端点',f'{vals[-1]:+.4f}',l+ww+.15,yp(vals[-1]),7.2,True,colour)
def f2():
 t=new('2',8.65);yrs=reg.index.to_list(); vals=reg.ER6.to_numpy()
 t.text('标题','(a)　全区年均指数',.39,.38,10.1,True,ink)
 lineplot(t,'均值',yrs,vals,(1.65,1.0,15.05,2.50),lambda v:f'{v:.3f}',nice(vals,3))
 t.text('下标题','(b)　较上年得分下降的面积占比（%）',.39,4.42,10.1,True,ink)
 base=7.86;left=1.12;hh=2.67;right=17.1
 for v in [0,50,100]:
  y=base-hh*v/100;t.line('刻线'+str(v),[(left,y),(right,y)],gridcol,.45);t.text('刻度'+str(v),str(v),.91,y,7.7,False,mut,'right')
 rows=[]
 for i in range(2016,2026):
  v=(a[wide[i]<wide[i-1]].sum()/a.sum())*100;b=left+(i-2016+.5)*(right-left)/10;high=hh*v/100;t.rect('下降比例'+str(i),b-.32,base-high,.64,high,rust);t.text('年度'+str(i),str(i),b,base+.28,7.4,False,mut,'center');t.text('占比'+str(i),f'{v:.1f}',b,base-high-.19,7.2,False,ink,'center');rows.append({'年份':i,'面积加权平均ER':reg.at[i,'ER6'],'与上年比下降面积占比_pct':v})
 save_data(pd.DataFrame([{'年份':2015,'面积加权平均ER':reg.at[2015,'ER6']},*rows]),'2','年度数值.csv');put(t,'2')
def f4():
 t=new('4',8.50);h=pd.read_csv(D/'HQI_input_attribution.csv').query('id=="all"').iloc[0];m=['LDI','HQI','LBI','MCR','ALLDIST','LRI'];n=['地类多样性','生境质量','景观干扰','源地间通行条件','蓝绿空间邻近条件','地类恢复潜力'];v=(reg.loc[2025]-reg.loc[2015])[[f'C_{i}' for i in m]].to_numpy();inputs=['land_class','road_field','crop_field','built_field'];nn=['地类及生境属性','道路干扰','耕地干扰','建设用地干扰'];u=np.array([h['delta_HQI_'+key]/h.delta_HQI*100 for key in inputs])
 t.text('面板一','(a)　六项指标对指数变化的贡献',.30,.40,10,True,ink);t.text('面板二','(b)　模型生境质量降幅的来源',9.06,.40,10,True,ink)
 xbase=6.52;bx=12.13
 t.text('净差','2015—2025年综合指数净变化 '+f'{v.sum():+.5f}',.38,1.06,8.0,False,mut)
 t.text('总降幅','模型生境质量变化 '+f'{h.delta_HQI:+.5f}',9.12,1.06,8.0,False,mut)
 cap=max(abs(v));bw=2.55
 t.line('零轴',[(xbase,1.73),(xbase,7.39)],tk,.63)
 for i,(name,sv) in enumerate(zip(n,v)):
  yy=2.05+.94*i;wid=abs(sv)/cap*bw;t.text('指标'+name,name,.35,yy+.13,8.15,False,ink);t.rect('柱'+name,xbase-wid if sv<0 else xbase,yy,wid,.30,rust if sv<0 else green);t.text('值'+name,f'{sv:+.5f}',8.83,yy+.13,7.4,False,mut,'right')
 for i,(name,sv) in enumerate(zip(nn,u)):
  yy=2.12+1.28*i;t.text('指标'+name,name,9.08,yy+.13,8.2,False,ink);t.rect('柱'+name,bx,yy,4.13*abs(sv)/100,.31,rust if sv>0 else green);t.text('占比'+name,f'{sv:.1f}%',17.25,yy+.13,8.0,True,ink,'right')
 t.text('单位','负值表示减分，正值表示增分。',.39,7.95,8.0,False,mut);t.text('计量','按模型净降幅计算占比。',9.08,7.95,8.0,False,mut)
 save_data(pd.DataFrame({'指标':n,'贡献':v}),'4','六项增减贡献.csv');save_data(pd.DataFrame({'生境质量输入':nn,'占模型净降幅_pct':u}),'4','生境质量输入分解.csv');put(t,'4')
def f5():
 t=new('5',8.9)
 for j,clause in enumerate([np.full(len(town),True),town.delta.abs()<=.015]):
  tab=town.loc[clause]; xmin,xmax=(1.29+j*8.7,8.22+j*8.7);yt,yb=1.49,7.15; ranges=nice(tab.delta,4) if j==0 else np.array([-.015,-.01,-.005,0,.005,.01,.015]);l,h=ranges[0],ranges[-1]
  px=lambda v:xmin+(xmax-xmin)*v/100
  py=lambda v:yb-(yb-yt)*(v-l)/(h-l)
  t.text('面板'+str(j),['(a)　全部镇街','(b)　纵轴放大'][j]+f'（{len(tab)}个）',xmin-.65,.38,10,True,ink);t.text('纵轴'+str(j),'镇均指数变化',xmin-.62,.97,8.0,False,mut)
  for tv in ranges:
   yy=py(tv);t.line(str(j)+'网'+str(tv),[(xmin,yy),(xmax,yy)],tk if abs(tv)<1e-8 else gridcol,.58 if abs(tv)<1e-8 else .32);t.text(str(j)+'纵'+str(tv),f'{tv:+.3f}' if abs(tv)>1e-8 else '0',xmin-.08,yy,7.15,False,mut,'right')
  for pp in [0,25,50,75,100]:
   xx=px(pp);t.text(str(j)+'横'+str(pp),str(pp),xx,yb+.23,7.1,False,mut,'center')
  t.line(str(j)+'半数',[(px(50),yt),(px(50),yb)],tk,.7,True);t.text(str(j)+'横轴','镇内下降面积占比（%）',(xmin+xmax)/2,yb+.63,8.1,False,ink,'center')
  for rr in tab.itertuples():
   xx,yy=px(rr.decline_pct),py(rr.delta); col={'A':rust,'B':green,'C':yellow,'D':blue}[rr.base_type];t.e.append(dict(kind='marker',name=f'{j}镇_{rr.display_name}',shape='circle',x=xx,y=t.h-yy,size=4.4 if rr.km2>=.25 else 3.7,fill=col if rr.km2>=.25 else '#FFFFFF',stroke=col,width=.57))
 for k,x,col in zip('ABCD',[.31,3.25,6.22,9.66],[rust,green,yellow,blue]):
  t.dot('图例样点'+k,x,8.48,col,4.7);t.text('分类图例'+k,k+' '+ty[k],x+.17,8.48,7.55,False,ink)
 t.text('面积图例','空心：评价面积小于0.25 km²',13.04,8.48,7.5,False,mut)
 save_data(town[['display_name','district','km2','delta','decline_pct','base_type']],'5','82个镇街绘图数据.csv');put(t,'5')
def f6():
 t=new('6',9.9);tt=pd.read_csv(T/'四类入选镇街十一期指数与贡献.csv');z=tt.copy();z['较2015年指数差']=z.groupby('town_seq').ER6.transform(lambda v:v-v.iloc[0]);ticks=nice(z['较2015年指数差'],4)
 for i,(k,r) in enumerate(ex.iterrows()):
  rr=z[z.town_seq==r.town_seq].sort_values('year');row,col=divmod(i,2);x=col*8.75+.24;y=row*4.55+.43;t.text('镇'+k,'('+chr(97+i)+')　'+r.display_name+' · '+ty[k],x,y,9.45,True,ink)
  lineplot(t,k,rr.year.to_numpy(),rr['较2015年指数差'].to_numpy(),(x+1.05,y+.72,6.37,2.61),lambda v:f'{v:+.3f}' if v else '0',ticks,green if r.delta>0 else rust,True)
 t.text('图脚','纵轴为各年指数与该镇2015年指数之差；四图共用纵轴。',.4,9.61,7.9,False,mut)
 save_data(z,'6','四镇各年得分.csv');put(t,'6')
def fa7():
 t=new('A7',12.0);met=['LDI','HQI','LBI','MCR','ALLDIST','LRI'];names=['地类多样性','生境质量','景观干扰','源地间通行成本（万成本单位）','至蓝绿空间平均距离（m）','地类恢复潜力']
 for i,m in enumerate(met):
  row,col=divmod(i,2);x=col*8.75+.28;y=row*3.88+.45;t.text('指标'+m,'('+chr(97+i)+')　'+names[i],x,y,9.3,True,ink)
  vals=reg[m].to_numpy()/(10000 if m=='MCR' else 1);ticks=nice(vals,3);delta=abs(ticks[1]-ticks[0]);dig=max(0,min(5,math.ceil(-math.log10(delta))+1))
  lineplot(t,m,reg.index.to_numpy(),vals,(x+1.34,y+.65,6.65,2.12),lambda v:f'{v:.{dig}f}',ticks)
 save_data(reg[met].reset_index(),'A7','原值年度均值.csv');put(t,'A7')
if __name__=='__main__':f2();f4();f5();f6();fa7()
