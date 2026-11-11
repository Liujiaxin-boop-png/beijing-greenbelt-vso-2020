from pathlib import Path
from pptx import Presentation
from pptx.util import Cm,Pt
from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN,MSO_ANCHOR,MSO_AUTO_SIZE
from pptx.dml.color import RGBColor
from pptx.oxml.xmlchemy import OxmlElement
from pptx.oxml.ns import qn
import json
Q=Path(__file__).resolve().parent;DISPLAY=json.loads((Q/'diagram_labels.local.json').read_text(encoding='utf-8-sig'));OUT=Q.parent/'新增图件与可编辑源文件';OUT.mkdir(exist_ok=True)
ink='243630';teal='326656';stroke='86A69A';pale='E8F0EC';light='F6F8F7';gray='64736E';rust='92563E'
rgb=RGBColor.from_string
def canvas(h):
 global prs,sl
 prs=Presentation();prs.slide_width=Cm(16.4);prs.slide_height=Cm(h);sl=prs.slides.add_slide(prs.slide_layouts[6]);sl.background.fill.solid();sl.background.fill.fore_color.rgb=rgb('FFFFFF')
def box(x,y,w,h,fill='FFFFFF',edge=None,th=.6):
 s=sl.shapes.add_shape(MSO_SHAPE.RECTANGLE,Cm(x),Cm(y),Cm(w),Cm(h));s.fill.solid();s.fill.fore_color.rgb=rgb(fill)
 if edge:s.line.color.rgb=rgb(edge);s.line.width=Pt(th)
 else:s.line.fill.background()
 return s
def label(x,y,w,h,text,size=9,bold=False,color=ink,align='center'):
 s=sl.shapes.add_textbox(Cm(x),Cm(y),Cm(w),Cm(h));tf=s.text_frame;tf.word_wrap=False;tf.auto_size=MSO_AUTO_SIZE.NONE;tf.margin_bottom=tf.margin_top=Pt(0);tf.margin_left=tf.margin_right=Pt(0);tf.vertical_anchor=MSO_ANCHOR.MIDDLE
 for i,st in enumerate(text.split('\n')):
  p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.space_before=Pt(0);p.space_after=Pt(0);p.line_spacing=1.02;p.alignment=PP_ALIGN.CENTER if align=='center' else PP_ALIGN.LEFT
  r=p.add_run();r.text=st;r.font.size=Pt(size);r.font.name='SimHei';r.font.bold=bold;r.font.color.rgb=rgb(color)
  rpr=r._r.get_or_add_rPr();ea=OxmlElement('a:ea');ea.set('typeface','黑体');rpr.append(ea)
 return s
def node(x,y,w,h,txt,sz=8.9,fill='FFFFFF',edge=stroke,bold=False):
 box(x,y,w,h,fill,edge);label(x+.04,y+.02,w-.08,h-.04,txt,sz,bold)
def line(x1,y1,x2,y2,arrow=False,color=stroke,wt=.75):
 s=sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Cm(x1),Cm(y1),Cm(x2),Cm(y2));s.line.color.rgb=rgb(color);s.line.width=Pt(wt)
 if arrow:
  e=OxmlElement('a:tailEnd');e.set('type','triangle');e.set('len','sm');e.set('w','med');s.line._get_or_add_ln().append(e)
def save(name):
 for sh in sl.shapes:
  sh.shadow.inherit=False
 prs.save(OUT/(name+'.pptx'))
def colheader(x,w,t):box(x,.12,w,.65,pale);label(x,.12,w,.65,t,10.5,True,teal)
def route():
 canvas(12.25)
 for x,w,t in [(.12,2.92,'研究任务'),(3.47,8.67,'评价与分析'),(12.55,3.73,'资料与检验')]:colheader(x,w,t)
 rows=[(1.02,1.57,'统一评价范围\n与观测单元','公开规划图重建边界\n年度土地覆盖与历史道路\n地形及水系资料'),
       (2.98,3.40,'评价支撑生态\n韧性的景观条件','2020年指标适用性检验\n多尺度与估权参照对照'),
       (6.85,2.13,'识别年度变化\n及两次转折','独立地类图、植被绿度\n建设占比、夜光、人口'),
       (9.46,2.46,'确定镇街内部\n优先核查地段','历史影像、工程记录\n规划边界与管护要求')]
 for y,h,left,right in rows:
  node(.12,y,2.92,h,left,9.6,light,stroke,True);node(12.55,y,3.73,h,right,8.85,light);line(3.04,y+h/2,3.40,y+h/2,True);line(12.55,y+h/2,12.18,y+h/2,True)
 node(3.47,1.02,8.67,1.57,'2015—2025年固定边界与格网原点\n比较200、500与1 000 m正方形格网',9.4)
 for i,t in enumerate(['结构指标','评价维度','功能指标']):label([3.47,6.69,9.20][i],3.00,[2.80,2.18,2.94][i],.52,t,9.6,True,teal)
 for i,(a,m,b) in enumerate([('地类多样性','脆弱性','生境质量'),('景观干扰','敏感性','源地间通行成本'),('全格蓝绿距离','自组织','地类恢复潜力')]):
  y=3.63+i*.83
  node(3.47,y,2.8,.69,a);node(6.72,y,2.05,.69,m,9.1,pale);node(9.24,y,2.90,.69,b)
  line(6.29,y+.345,6.68,y+.345,True);line(9.22,y+.345,8.81,y+.345,True)
 node(3.47,6.85,8.67,.87,'固定熵权合成500 m年度格网得分',9.4)
 node(3.47,7.96,4.03,1.02,'全区均值与升降面积\n六项指标贡献分解',8.85)
 node(7.75,7.96,4.39,1.02,'分阶段比较地类转换\n面积加权 q 与空间分块检验',8.6)
 line(7.82,7.72,7.82,7.82);line(5.48,7.82,9.96,7.82);line(5.48,7.82,5.48,7.94,True);line(9.96,7.82,9.96,7.94,True)
 node(3.47,9.46,8.67,.86,'镇均指数变化 × 纳入研究面积中下降地段的占比',9.35)
 node(3.47,10.64,4.05,1.28,'四类镇街与代表案例\n比较镇内升降地段',8.85);node(7.93,10.64,4.21,1.28,'结合地块与工程资料\n确定巡查位置与内容',8.85)
 line(7.53,11.28,7.89,11.28,True)
 for a,b in [(2.60,2.91),(6.40,6.78),(9.02,9.38)]:line(7.80,a,7.80,b,True,teal,.95)
 save('研究技术路线')
def scale():
 canvas(8.6)
 label(.13,.12,8.1,.59,DISPLAY['scale_000'],10.0,True,teal,'left')
 for i,(n,t,sub) in enumerate([(5,'200 m','25个子格'),(2,'500 m','4个子格'),(1,'1 000 m','1个参照格')]):
  x=.67+i*2.36;y=1.52;side=1.64;box(x,y,side,side,pale if n==2 else light,teal if n==2 else gray,.9)
  for k in range(1,n):line(x+side*k/n,y,x+side*k/n,y+side,False,stroke,.55);line(x,y+side*k/n,x+side,y+side*k/n,False,stroke,.55)
  label(x-.25,.88,side+.5,.46,t,9.6,True);label(x-.32,3.28,side+.64,.48,sub,9)
 line(8.0,.23,8.0,5.56,False,'CDD9D3',.7)
 label(8.28,.12,7.9,.59,DISPLAY['scale_001'],9.3,True,teal,'left')
 # Common zero baseline; units are index points.
 x0=10.02;axisw=4.62;top=1.55
 for n,(name,v,col) in enumerate([('200 m',DISPLAY['scale_007'],gray),('500 m',DISPLAY['scale_008'],teal)]):
  yy=top+n*1.03;label(8.38,yy,1.45,.47,name,9.0,False,ink,'left');box(x0,yy+.05,axisw*v/.020,.38,col);label(x0+axisw*v/.020+.10,yy-.02,1.25,.5,f'{v:.4f}',8.7,False,ink,'left')
 line(x0,3.55,x0+axisw,3.55,False,gray)
 for j in range(3):
  xx=x0+j*axisw/2;line(xx,3.55,xx,3.67,False,gray);label(xx-.6,3.72,1.2,.4,('0','0.010','0.020')[j],8.2)
 label(8.25,4.35,7.65,.76,DISPLAY['scale_002'],8.75,False,gray)
 label(.30,4.12,7.1,1.03,DISPLAY['scale_003'],8.55,False,gray)
 line(.13,5.86,16.25,5.86,False,stroke)
 label(.13,6.05,16,.54,DISPLAY['scale_004'],9.8,True,teal,'left')
 node(.22,6.92,7.64,1.39,DISPLAY['scale_005'],9.25,light)
 node(8.24,6.92,7.92,1.39,DISPLAY['scale_006'],9.2,light)
 save('格网尺度比较')
def management():
 canvas(9.35)
 for x,w,t in [(.13,3.16,'镇街与变化类型'),(3.62,5.39,'优先核查的位置'),(9.40,6.87,'应核实的地表变化')]:colheader(x,w,t)
 vals=[(DISPLAY['management_010'],DISPLAY['management_011'],DISPLAY['management_012']),(DISPLAY['management_013'],DISPLAY['management_014'],DISPLAY['management_015']),(DISPLAY['management_016'],DISPLAY['management_017'],DISPLAY['management_018']),(DISPLAY['management_019'],DISPLAY['management_020'],DISPLAY['management_021'])]
 for i,(a,b,c) in enumerate(vals):
  y=1.03+i*1.65
  node(.13,y,3.16,1.36,a,9.0,light,stroke,True);node(3.62,y,5.39,1.36,b,9.15);node(9.4,y,6.87,1.36,c,9.2)
  line(3.31,y+.68,3.59,y+.68,True);line(9.03,y+.68,9.38,y+.68,True)
 line(.14,7.75,16.25,7.75,False,stroke)
 label(.22,7.95,15.9,.94,DISPLAY['management_009'],8.9,False,ink,'left')
 save('四类镇街管护核查')
route();scale();management()

