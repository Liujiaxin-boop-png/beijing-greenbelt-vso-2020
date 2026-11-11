from pathlib import Path
from io import StringIO
import csv, hashlib, json
import xlsxwriter

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCE = ROOT / '机制验证_三阶段'
def read(group, name):
    path = SOURCE / group / name
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
pa='D_阶段分解';pb='B_地类转换';pc='A_外部观测'
in1='各类地段对全区转折的带符号贡献.csv'
in2='两套底图_共同裁剪范围转入转出.csv'
in3='不透水转水_容许一格30米错位复核.csv'
in4='01_分阶段外部关联检验.csv'
fname='三阶段统计图_可编辑.xlsx'
VALIDATION=json.loads((OUT/'chart_checks.local.json').read_text(encoding='utf-8-sig'))
wb=xlsxwriter.Workbook(OUT/fname)
teal='#286C60';rust='#A35E43';ink='#1E2929';graph='#C6CECA';font='微软雅黑'
h=wb.add_format({'font_name':'黑体','bold':True,'font_size':17,'font_color':ink,'valign':'vcenter'})
h2=wb.add_format({'font_name':font,'font_size':12,'font_color':ink,'valign':'vcenter'})
hdr=wb.add_format({'font_name':font,'bold':True,'bg_color':'#E5EEEA','valign':'vcenter','text_wrap':True,'bottom':1,'border_color':'#93A79D'})
rawtxt=wb.add_format({'font_name':font,'font_size':10,'valign':'top','text_wrap':True})
numeric=wb.add_format({'font_name':'Calibri','num_format':'0.000000;[Red]-0.000000;0','font_size':11})
L,R='A','B'
W=490;H=282
def panel(name, headings,units):
    s=wb.add_worksheet(name);s.hide_gridlines(2)
    s.set_column_pixels(0,15,62);s.set_default_row(17)
    s.set_row(0,24);s.set_row(1,18)
    for group,(title,unit) in enumerate(zip(headings,units)):
        begin=8*group;s.merge_range(0,begin,0,begin+7,title,h);s.merge_range(1,begin,1,begin+7,unit,h2)
    s.set_paper(9);s.set_landscape();s.center_horizontally()
    s.fit_to_pages(1,1);s.set_margins(0.25,0.25,0.25,0.25);s.print_area(0,0,15,15);s.set_header('',{'margin':0});s.set_footer('',{'margin':0})
    return s
s1=panel('A_转折与地段',['a   不同升降组合的面积占比','b   各类地段对全区转折的贡献'],['面积占研究区的比例（%）','全区年均指数变化率之差（10⁻³ 分/年）'])
s2=panel('B_水面产品对照',['a   两种土地覆盖图的水面净变化','b   两图同时识别为不透水面转水的比例'],['开敞水面净增面积（km²）','占 CLCD 识别为不透水面转水面积的比例（%）'])
s3=panel('C_植被分组与覆盖',['a   各时段所有有效观测格网','b   三个时段均有观测的同一组格网'],['植被增绿组与减绿组的韧性年均变化差（10⁻³ 分/年）','植被增绿组与减绿组的韧性年均变化差（10⁻³ 分/年）'])
def raws(name,headers,rows,widths=None):
    s=wb.add_worksheet(name);s.freeze_panes(1,1);s.hide_gridlines(2);s.set_row(0,40);s.set_column(0,len(headers)-1,22)
    for j,width in enumerate(widths or []): s.set_column(j,j,width)
    for i,t in enumerate(headers): s.write(0,i,t,hdr)
    for i,rec in enumerate(rows,1):
        for j,val in enumerate(rec):
            s.write(i,j,val, numeric if isinstance(val,(float,int)) else rawtxt)
    s.autofilter(0,0,len(rows),len(headers)-1);return s
titles={'降升':'由降转升','升升':'连续上升','降降':'连续下降','升降':'由升转降'}
d1=read(pa,in1); src={(x['年份'],x['格网前后方向']): x for x in d1}
a=[]
for code,label in [*titles.items(),('平','含持平')]:
    rec=[label]
    cells=[src[t,y if code=='平' else code] for t,y in [('2019','降平'),('2021','平降')]]
    for key,factor in [('面积占比_pct',1),('ER6',1000),('界内面积_km2',1),('格数',1)]:
        rec.extend([float(z[key])*factor for z in cells])
    a.append(rec)
assert all(abs(sum(q[i] for q in a)-100)<1e-8 for i in [1,2])
assert abs(sum(q[3] for q in a)-VALIDATION['turn_0'])<1e-8 and abs(sum(q[4] for q in a)+VALIDATION['turn_1'])<1e-8
ws1=raws('数据A',['相邻阶段方向','2019面积占比（%）','2021面积占比（%）','2019速率转折贡献（10⁻³分/年）','2021速率转折贡献（10⁻³分/年）','2019面积（km²）','2021面积（km²）','2019格数','2021格数'],a)
ds=read(pb,in2); ds={r['阶段']:r for r in ds if r['类型']=='开敞水面'}
tol={r['阶段']:r for r in read(pb,in3)}
b=[]
for y in ['2019_2021','2021_2025']:
    r=ds[y];z=tol[y]
    b.append([y.replace('_','—'),float(r['CLCD净增_km2']),float(r['Esri净增_km2']),float(z['同像元_pct']),float(z['容许30m位置误差_pct']),float(z['CLCD不透水转水_km2']),float(z['Esri同像元确认_km2']),float(z['Esri30m内含对应变化_km2'])])
ws2=raws('数据B',['时段','CLCD净增加（km²）','Esri净增加（km²）','同一像元（%）','容许30 m错位（%）','CLCD转换面积（km²）','同像元面积（km²）','容许30 m范围面积（km²）'],b)
ext=read(pc,in4);c=[]
for yr in ['2015–2019','2019–2021','2021–2025']:
    rec=[yr.replace('–','—')]
    for sample in ['本阶段有效域','本因素跨阶段共同域']:
        entry=next(k for k in ext if k['时期']==yr and k['检验']=='阶段' and k['因素']=='植被绿度' and k['样本口径']==sample)
        est=float(entry['增加减减少差'])*1000;lo=float(entry['8km差异CI下限'])*1000;up=float(entry['8km差异CI上限'])*1000
        rec.extend([est,lo,up,est-lo,up-est,int(entry['格数']),float(entry['面积_km2'])])
    c.append(rec)
ws3=raws('数据C',['时段']+[f'{域}：{项}' for 域 in ['当期','三期共同'] for 项 in ['组间差（10⁻³分/年）','区间下限','区间上限','误差下半长','误差上半长','格数','覆盖面积（km²）']],c)
def base(typ,yrange,unit,legend=True,zero=False):
    ch=wb.add_chart({'type':typ});ch.set_size({'width':W,'height':H});ch.set_title({'none':True})
    ch.set_chartarea({'border':{'none':True},'fill':{'color':'#FFFFFF'}})
    ch.set_plotarea({'border':{'none':True},'fill':{'color':'#FFFFFF'}})
    if legend:ch.set_legend({'position':'bottom','font':{'name':font,'size':12,'color':ink}})
    else:ch.set_legend({'none':True})
    xf={'name':font,'size':12,'color':ink};yf={'name':'Arial','size':12,'color':ink}
    ch.set_x_axis({'num_font':xf,'label_position':'low','line':{'color':'#7C8A83','width':0.8},'major_tick_mark':'none','minor_tick_mark':'none','interval_unit':1})
    yl={'min':yrange[0],'max':yrange[1],'major_unit':yrange[2],'num_format':unit,'num_font':yf,'line':{'none':True},'major_tick_mark':'none','minor_tick_mark':'none','major_gridlines':{'visible':True,'line':{'color':'#DCE2DF','width':0.6}},'crossing':0}
    ch.set_y_axis(yl);return ch
def bar(sheet,dw,rows,paired,which,bounds,fmt='0',labels=False,labfmt='0.00'):
    chart=base('column',bounds,fmt); raw=dw.name
    for j,(name,idx) in enumerate(paired):
        color=(teal,rust)[j]
        s={'name':name,'categories':[raw,1,0,rows,0],'values':[raw,1,idx,rows,idx],'fill':{'color':color},'border':{'none':True},'gap':75}
        if labels:s['data_labels']={'value':True,'position':'outside_end','num_format':labfmt,'font':{'name':'Arial','size':11,'color':ink}}
        chart.add_series(s)
    sheet.insert_chart(2,8*which,chart,{'x_offset':0,'y_offset':0})
bar(s1,ws1,4,[('2019年前后',1),('2021年前后',2)],0,(0,50,10))
bar(s1,ws1,4,[('2019年前后',3),('2021年前后',4)],1,(-1.5,1.5,0.5),'0.0')
bar(s2,ws2,2,[('CLCD',1),('Esri',2)],0,(-1,6,1),labels=True)
bar(s2,ws2,2,[('同一像元',3),('容许30 m错位',4)],1,(0,4.5,1),labels=True)
def errpanel(which,start,color):
    name=ws3.name;ch=base('line',(-6,6,2),'0',False)
    from xlsxwriter.utility import xl_range_formula
    f=lambda col: '='+xl_range_formula(name,1,col,3,col)
    ser={'name':'增绿组减减绿组','categories':[name,1,0,3,0],'values':[name,1,start,3,start],
         'line':{'none':True},'marker':{'type':'circle' if which==0 else 'diamond','size':8,'fill':{'color':color},'border':{'color':color}},
         'y_error_bars':{'type':'custom','plus_values':f(start+4),'minus_values':f(start+3),'end_style':1,'line':{'color':color,'width':1.7}}}
    ch.add_series(ser);s3.insert_chart(2,8*which,ch)
errpanel(0,1,teal);errpanel(1,8,rust)
s3.merge_range(15,0,15,7,'有效格网依次为 2,225、2,700、3,002 个',h2)
s3.merge_range(15,8,15,15,'各期均为 2,123 个格网，覆盖 436.55 km²',h2)
refs=[(pa,in1,'图A' ),(pa,'区域两次转折的分解.csv','图A，核对各组贡献之和'),(pb,in2,'图B，净面积'),(pb,in3,'图B，同像元及邻域'),(pb,'不透水转水_分歧在哪种期初分类.csv','图B，解释起点分歧'),(pc,in4,'图C，阶段分组、8 km空间区块95%区间'),(pc,'数据与方法说明.md','图C，术语与重抽口径')]
data=[]
for gp,n,use in refs:
    path=SOURCE/gp/n
    data.append([use,str(path),hashlib.sha256(path.read_bytes()).hexdigest()])
ws=raws('出处及读法',['用途','归档文件','SHA-256'],data,[42,108,72])
ws.set_row(len(data)+3,40);ws.write(len(data)+2,0,'A仅绘出升降的四种主要组合。另有0.446 km²在一段持平，明细和贡献均在数据A内。',rawtxt)
ws.merge_range(len(data)+2,0,len(data)+2,2,'A仅绘四种主要组合；一段持平的0.446 km²和对应贡献已列在数据A的第6行。',rawtxt)
ws.merge_range(len(data)+3,0,len(data)+3,2,'C区间来自8 km空间区块999次有放回重抽的2.5%和97.5%分位。正值表示较明显增绿组韧性变化率高于较明显减绿组；变绿组自身也可能仍在下降。两个样本范围内均使用同一分组阈值。',rawtxt)
wb.close()
print(fname)

