from pathlib import Path
import json,shutil,math,pandas as pd,numpy as np,geopandas as gp
W=Path(__file__).resolve().parent;ROOT=W.parent;D=ROOT/'core';T=ROOT/'towns'; B=Path('D:/ER219_figures/原始GIS边界_年度论文图_ArcMap10.8').resolve();B.mkdir(parents=True,exist_ok=True)
ORIG=Path('D:/ER219_figures/全文图件_熵权与镇街类型_ArcMap10.8')
TITLES={'1':'中国北京市与二道绿隔研究范围','2':'全区生态韧性年均值与下降面积','3':'全域生态韧性的长期趋势与回升期变化','4':'各景观指标的得分贡献与生境质量降幅','5':'镇街指数变化与下降面积占比','6':'四类镇街的生态韧性年度轨迹','A1':'蓝绿空间平均距离示例','A2':'地类多样性与生境质量','A3':'景观干扰与源地间通行成本','A4':'蓝绿空间距离与地类恢复潜力','A5':'十一期格网生态韧性指数','A6':'十个相邻年度格网指数差','A7':'六项指标的区域年度均值','A8':'镇街生态韧性变化类型','A9':'分阶段变化率与全期趋势'}
def target(k):q=B/('图'+k);q.mkdir(parents=True,exist_ok=True);return q
def db(k):q=target(k)/'data';q.mkdir(exist_ok=True);return q/'geodata.gdb'
def geo(k,fc,frame):
 dd=db(k); frame.to_file(dd,layer=fc,driver='OpenFileGDB',promote_to_multi=True,index=False,layer_options={'TARGET_ARCGIS_VERSION':'ALL'})
def pathnorm(x):return str(Path(x).resolve())
def config(k,cfg,name=None):
 cfg['output_mxd']=str(target(k)/((name or TITLES[k])+'.mxd'));cfg['export_stem']=str(W/('export'+k)); cfg['dpi']=max(420,int(cfg.get('dpi',450)))
 (W/f'fig{k}.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=1),'utf8');return cfg
def poly(fc,dbpath,n,field=None,hues=None,lab=None):
 d=dict(name=n,kind='polygon',fc=fc,gdb=str(dbpath));return dict(d,renderer='unique',field=field,values=[dict(value=str(i+1),label=l,color=c) for i,(c,l) in enumerate(zip(hues,lab))]) if field else dict(d,fill='none',stroke='#6E8578',width=.24)
def ext(scope,width,height,pad=1.07):
 x,y,X,Y=scope.total_bounds;W=max((X-x),(Y-y)*width/height)*pad;H=W*height/width;cx=(X+x)/2;cy=(Y+y)/2;return [cx-W/2,cy-H/2,cx+W/2,cy+H/2]
def save_data(q,k,name):q.to_csv(target(k)/name,index=False,encoding='utf-8-sig')
