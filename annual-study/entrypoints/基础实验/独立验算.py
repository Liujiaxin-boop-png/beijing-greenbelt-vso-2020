# -*- coding: utf-8 -*-
"""从三套格网的六列原值重新计算；仅使用 Python 3 标准库。不执行原评分程序。"""
import argparse, csv, gzip, math, statistics as st
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

F = 'LDI HQI LBI MCR ALLDIST LRI'.split()
POS = [True,True,False,False,False,True]
Y = list(range(2015,2026))

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('D:/ER219_work/shp11'),help='包含 core、towns 的目录')
    p.add_argument('--panel',type=Path,help='改读你从原始数据重跑后生成的 panel 目录，例如 D:/ER_Replay_study/panel')
    p.add_argument('--towns',type=Path,help='可选：替换用于镇街叠置的目录，内有 town_catalogue.csv、pieces_full.csv')
    p.add_argument('--out',type=Path,default=Path.home()/'Documents'/'二道绿隔独立验算',help='结果存放位置；每次新建时间子目录')
    args=p.parse_args()
    c=args.panel or args.root/'core'; t=args.towns or args.root/'towns'
    def rows(path):
        op=gzip.open if path.suffix=='.gz' else open
        with op(path,'rt',encoding='utf-8-sig',newline='') as h:
            yield from csv.DictReader(h)
    files={s:c/('六项逐格逐年原值与得分'+('' if s==500 else f'_{s}m')+'.csv.gz') for s in (200,500,1000)}
    mn=[math.inf]*6;mx=[-math.inf]*6; coarse=[]; counts={}
    for s,fn in files.items():
        print('读取',s,'米原值…',flush=True)
        n=0
        for r in rows(fn):
            x=[float(r[f]) for f in F]
            assert all(map(math.isfinite,x)),(s,r['grid_id'])
            for j,v in enumerate(x):
                mn[j]=min(mn[j],v);mx[j]=max(mx[j],v)
            n+=1
            if s==1000: coarse.append(x)
        counts[s]=n
    assert counts=={200:275638,500:49258,1000:14267},counts
    def norm(x,j):
        return ((x-mn[j]) if POS[j] else (mx[j]-x))/(mx[j]-mn[j])
    u=[]
    for j in range(6):
        z=[norm(v[j],j) for v in coarse];total=math.fsum(z)
        pcol=[a/total for a in z if a>0]
        u.append(1+math.fsum(a*math.log(a) for a in pcol)/math.log(len(z)))
    w=[v/sum(u) for v in u]
    score={};area={};err=0; parts=defaultdict(list)
    for r in rows(files[500]):
        gid=r['grid_id'];y=int(r['year']);a=float(r['area_km2'])
        assert (gid,y) not in score
        v=[norm(float(r[f]),j)*w[j] for j,f in enumerate(F)];e=math.fsum(v)
        err=max(err,abs(e-float(r['ER6'])));score[gid,y]=e
        assert gid not in area or area[gid]==a
        area[gid]=a
        for j,val in enumerate(v): parts[y,j].append(val*a)
    assert len(area)==4478 and err<1e-10,(len(area),err)
    A=math.fsum(area.values())
    means={y:math.fsum(a*score[g,y] for g,a in area.items())/A for y in Y}
    orig={int(r['year']):float(r['ER6']) for r in rows(c/'区域六项逐年指数与分项.csv')}
    assert max(abs(means[y]-orig[y]) for y in Y)<1e-10
    out=args.out/datetime.now().strftime('%Y%m%d_%H%M%S_%f');out.mkdir(parents=True)
    def save(name,header,data):
        with (out/name).open('w',newline='',encoding='utf-8-sig') as h:
            dst=csv.writer(h);dst.writerow(header);dst.writerows(data)
    save('自己计算的权重.csv',['指标','全期全尺度最小','最大','信息效用','权重'],zip(F,mn,mx,u,w))
    save('自己计算的年度统计.csv',['year','area_km2','ER6']+['C_'+j for j in F],([y,A,means[y]]+[math.fsum(parts[y,j])/A for j in range(6)] for y in Y))
    stage=[]
    for a,b in [(2015,2025),(2015,2019),(2019,2021),(2021,2025)]:
        down=math.fsum(ar for g,ar in area.items() if score[g,b]-score[g,a]<-1e-10)
        stage.append((a,b,means[b]-means[a],(means[b]-means[a])/(b-a),down,100*down/A))
    save('自己计算的阶段统计.csv',['start','end','净差','年均分差','下降平方公里','下降面积百分比'],stage)
    catalog={r['town_seq']:r for r in rows(t/'town_catalogue.csv')}; pieces=defaultdict(list)
    for r in rows(t/'pieces_full.csv'):
        if not catalog[r['town_seq']]['town_id'].startswith('UN_'):
            g=r['grid_id'];a=float(r['poly_area'])/1e6
            pieces[r['town_seq']].append((a,score[g,2025]-score[g,2015]))
    outtown=[];freq=Counter()
    for seq,l in pieces.items():
        ta=math.fsum(a for a,d in l);td=math.fsum(a*d for a,d in l)/ta
        sh=100*math.fsum(a for a,d in l if d<0)/ta
        cl=('A' if sh>50 else 'D') if td<0 else ('C' if sh>50 else 'B')
        assert abs(sh-50)>1e-9 and abs(td)>1e-14
        freq[cl]+=1;outtown.append((seq,catalog[seq]['display_name'],ta,td,sh,cl))
    assert freq==dict(A=59,B=10,C=7,D=6)
    save('自己计算的镇街.csv',['town_seq','名称','可归属面积km2','平均变化','下降面积百分比','类型'],sorted(outtown,key=lambda x:(x[-1],int(x[0]))))
    def ranks(vals):
        order=sorted(range(len(vals)),key=lambda i:vals[i]); rank=[0.]*len(vals);i=0
        while i<len(vals):
            k=i+1
            while k<len(vals) and vals[order[k]]==vals[order[i]]: k+=1
            for j in range(i,k):rank[order[j]]=(i+1+k)/2
            i=k
        return rank
    reps=[]
    for typ in 'ABCD':
        group=[r for r in outtown if r[-1]==typ];n=len(group)
        r1=ranks([r[3] for r in group]);r2=ranks([r[4] for r in group])
        candidates=[(round(math.hypot((i-.5)/n-.5,(j-.5)/n-.5),12),-r[2],r[1]) for r,i,j in zip(group,r1,r2)]
        for threshold in [0,1,2]:
            res=min(item for item in candidates if -item[1]>=threshold)
            reps.append((typ,threshold,res[2],res[0],-res[1]))
    assert [r[2] for r in reps if r[1]==1]==['东小口地区','北臧村镇','拱辰街道','李桥镇']
    save('自己计算的案例筛选.csv',['类型','最少纳入面积km2','入选镇街','到类中心的秩距离','纳入面积km2'],reps)
    print('重算两种子格的完整父格对照…',flush=True)
    full={}
    for r in rows(files[1000]):
        if float(r['area_km2'])>=.999999:
            full[int(r['ix']),int(r['iy']),int(r['year'])]=math.fsum(norm(float(r[f]),j)*w[j] for j,f in enumerate(F))
    assert len(full)==570*11
    multi=[]
    for s in [200,500]:
        ratio=1000//s; vals=defaultdict(list)
        for r in rows(files[s]):
            parent=(int(r['ix'])//ratio,int(r['iy'])//ratio,int(r['year']))
            if parent in full:
                v=math.fsum(norm(float(r[f]),j)*w[j] for j,f in enumerate(F))
                vals[parent].append(v)
        assert set(full)==set(vals) and all(len(v)==ratio*ratio for v in vals.values())
        for year in Y:
            keys=[k for k in full if k[2]==year]
            pred=[st.mean(vals[k]) for k in keys];ref=[full[k] for k in keys]
            a,b=ranks(pred),ranks(ref)
            aa,bb=st.mean(a),st.mean(b); den=math.sqrt(sum((v-aa)**2 for v in a)*sum((v-bb)**2 for v in b))
            rho=sum((i-aa)*(j-bb) for i,j in zip(a,b))/den
            multi.append((year,s,len(keys),rho,st.mean(abs(v-t) for v,t in zip(pred,ref)),st.median(max(vals[k])-min(vals[k]) for k in keys)))
    orig_multi={(int(r['year']),int(r['child_m'])):r for r in rows(c/'年度六项综合分_嵌套尺度对照.csv')}
    assert max(abs(rec[j]-float(orig_multi[rec[:2]][col])) for rec in multi for j,col in [(3,'rho'),(4,'mean_abs_gap'),(5,'median_child_range')])<1e-9
    save('自己计算的格网尺度对照.csv',['year','child_m','父格数','Spearman','平均绝对差','子格极差的中位数'],multi)
    print('六项权重:',*[round(v,9) for v in w]);print('与已存得分的最大绝对偏差:',err)
    print('区域面积:',A,'首末均值:',means[2015],means[2025],'镇街数:',dict(freq));print('输出位置:',out)
if __name__=='__main__':run()
