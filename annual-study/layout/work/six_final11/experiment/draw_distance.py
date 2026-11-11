from pathlib import Path
import sys, json
import numpy as np
from scipy.ndimage import distance_transform_edt
here=Path(__file__).resolve().parent
sys.path.insert(0,r'D:/ER219_work/annual_actual/refocus10/figures')
import chart_native as drawing
drawing.BASE=here
drawing.DEST=Path(r'D:/ER219_figures/年度评价_三维六指标定稿/距离计算示意')
drawing.DEST.mkdir(parents=True,exist_ok=True)
c=drawing.Chart('how',7.6,'同样面积的蓝绿空间可以有不同的邻近条件','计算示例　｜　每幅图25个像元，边长均为30 m　｜　两图蓝绿面积相同', '距离算法示意')
distances=[]
for j,(label,x,coords) in enumerate([('（a）蓝绿空间集中在一角',.75,[(0,0),(0,1),(1,0),(1,1)]),
                                      ('（b）蓝绿空间分布在不同位置',8.30,[(1,1),(1,3),(3,1),(3,3)])]):
    m=np.zeros((5,5),bool)
    for pos in coords:m[pos]=1
    dis=distance_transform_edt(~m,sampling=30);distances.append(float(dis.mean()))
    c.text('组名'+str(j),label,x,1.67,10.2,True)
    cell=.60
    for i in range(5):
        for k in range(5):
            left=x+cell*k;top=2.0+cell*i
            c.rect(f'像元{j}_{i}_{k}',left,top,cell,cell,'#477F6C' if m[i,k] else '#F3F5F1','#ABBAB2',.48)
            c.text(f'距离{j}_{i}_{k}',str(round(dis[i,k])),left+cell/2,top+cell/2,7.5,False,'#FFFFFF' if m[i,k] else '#35483E','center')
    c.text('面积'+str(j),'蓝绿用地占比',x+3.32,2.57,8.7,False,drawing.muted)
    c.text('比例'+str(j),'4 / 25 ＝ 16%',x+3.32,3.08,11.2,True)
    c.text('平均'+str(j),'全格平均距离',x+3.32,3.88,8.7,False,drawing.muted)
    c.text('数值'+str(j),f'{dis.mean():.1f} m',x+3.32,4.44,13.3,True,drawing.green)
c.line('分隔线',[(.6,5.38),(15.18,5.38)],drawing.gray,.5)
c.text('读法','绿色像元本身就在蓝绿空间，距离为0。其他像元取到最近绿色像元中心的直线距离。',.68,5.82,9.05)
c.text('算法','格内数字为距离（m，取整展示）。右侧均值由未取整的25个距离计算，每个像元面积相同。',.68,6.38,8.75)
c.text('跨界','示例假定图外没有更近的绿色像元；实际制图从格外继续搜索，跨格的林地和河流也计入。',.68,6.94,8.7,False,drawing.muted)
c.export()
print(distances)
