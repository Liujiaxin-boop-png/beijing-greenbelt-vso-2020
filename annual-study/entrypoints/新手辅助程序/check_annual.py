# -*- coding: utf-8 -*-
"""Read-only archive/own-panel checkpoint. Pure Python 3.12 standard library."""
import argparse, csv, gzip, json, math, sys
from collections import defaultdict
from pathlib import Path
def check(panel):
    def readj(n):
        return json.loads((panel/n).read_text(encoding='utf-8-sig'))
    domain, par = readj('domain.json'), readj('parameters.json')
    area=domain['area_km2']
    print('实际读取的面板：', panel.resolve())
    print('重建边界源文件：',domain['source'])
    if not math.isclose(area,922.18601113,rel_tol=0,abs_tol=1e-6): raise ValueError('与本文报告边界面积不一致。')
    print(f'边界测得 {area:.6f} km²；全期固定 k = {domain["new_hq_k"]:.12f}。')
    if (par['n'],par['entropy_balanced_1km_cells'])!=(14267,1297):raise ValueError('恒定1 km估权样本不一致。')
    w=par['weights']; positive={'LDI','HQI','LRI'}; keys=par['fields']
    if len(keys)!=6 or not math.isclose(math.fsum(w.values()),1.,abs_tol=5e-12):raise ValueError('权重表不合要求。')
    print('固定权重：','，'.join(f'{k} = {w[k]:.6f}' for k in keys))
    ids=defaultdict(set); area_y=defaultdict(list); total=defaultdict(list)
    maxdiff=0.; count=0; sample=None
    with gzip.open(panel/'六项逐格逐年原值与得分.csv.gz','rt',encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            y=int(r['year']); g=r['grid_id']; a=float(r['area_km2'])
            if a<=0 or g in ids[y]: raise ValueError(f'{y}/{g}：边界内面积非正或格网重复。')
            ids[y].add(g); area_y[y].append(a); count+=1
            partial=[]
            for k in keys:
                x=float(r[k]); lo,hi=par['min'][k],par['max'][k]
                u=(x-lo)/(hi-lo) if k in positive else (hi-x)/(hi-lo)
                partial.append(w[k]*u)
            er=math.fsum(partial);maxdiff=max(maxdiff,abs(er-float(r['ER6'])))
            total[y].append(a*er)
            if y==2020 and g=='500_1955_8712': sample=er
    if sorted(ids)!=list(range(2015,2026)) or len(ids[2015])!=4478 or count!=49258: raise ValueError('年度或有效格数与本文不符。')
    if any(ids[y]!=ids[2015] or abs(math.fsum(area_y[y])-area)>1e-6 for y in ids):raise ValueError('各年有效格或相交总面积不一致。')
    if sample is None or abs(sample-0.2551460158)>1e-7 or maxdiff>1e-8: raise ValueError('同向、权重、参考极值或格网配对不一致。')
    print(f'500米：每年 {len(ids[2015])} 格，11年 {count} 行；2020年示范格 {sample:.10f}；格均分最大差 {maxdiff:.3g}。')
    avg={y:math.fsum(total[y])/math.fsum(area_y[y]) for y in ids}
    for y in sorted(avg):print(f'{y}: {avg[y]:.9f}')
    print('四个端点的相邻分差：','，'.join(f'{avg[b]-avg[a]:+.8f}' for a,b in [(2015,2019),(2019,2021),(2021,2025)]))
    print('通过。此处从格网六项原值重建得分和年度均值；没有重新生成遥感分类、模型场或地理探测器结果。')
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--panel',type=Path,default=Path('D:/ER219_work/shp11/core'),help='可改为自己的 panel 或 panel_archived 目录')
    args=ap.parse_args()
    try:check(args.panel)
    except Exception as ex:
        print('未通过：',ex,file=sys.stderr);sys.exit(1)

