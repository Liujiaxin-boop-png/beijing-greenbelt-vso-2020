"""Synthetic arithmetic QA, explicitly separate from empirical outcomes."""
from pathlib import Path
import math,json
import numpy as np
import pandas as pd
from evaluate_resilience import normalise,entropy,score,METRICS
ROOT=Path(__file__).resolve().parents[2]
checks=[]
z=np.array([[0,1,.2,.1,.6,.7],[1,0,.5,.4,.2,.1],[.5,.6,.9,1,1,.5]])
w,e,d=entropy(z)
manual=[]
for j in range(z.shape[1]):
    vals=[float(z[i,j]) for i in range(len(z))];s=sum(vals)
    ee=-sum((v/s)*math.log(v/s) for v in vals if v>0)/math.log(len(vals))
    manual.append(1-ee)
expected=np.array(manual)/sum(manual)
assert np.allclose(w,expected,atol=1e-14)
checks.append({'id':'entropy_scalar_independent','status':'PASS','max_abs_difference':float(np.max(abs(w-expected)))})
constant=np.ones((5,6))
try:entropy(constant)
except ValueError:checks.append({'id':'constant_matrix_fails_closed','status':'PASS'})
else:raise AssertionError('constant data assigned invented weights')
x=np.array([[.4,3,-.2,100,50,.2],[.8,1,.8,200,10,.6],[.6,2,.5,150,30,.4]])
lo=x.min(0);hi=x.max(0)
norm=normalise(x,lo,hi)
assert norm[1,0]==1 and norm[1,1]==1 and norm[1,3]==0 and norm[1,4]==1
scale=np.array([2,8,1,1000,1000,1]);shift=np.arange(6)*3
assert np.allclose(norm,normalise(x*scale+shift,lo*scale+shift,hi*scale+shift))
checks.append({'id':'favorable_direction_positive_unit_invariance','status':'PASS'})
df=pd.DataFrame(x,columns=METRICS)
weights,_,_=entropy(norm)
s=score(df,lo,hi,weights)
assert np.allclose(s.ER,norm@weights)
for omit in range(6):
    wr=weights.copy();wr[omit]=0;wr/=wr.sum()
    a=score(df,lo,hi,wr)
    reference=(norm@weights-norm[:,omit]*weights[omit])/(1-weights[omit])
    assert np.allclose(a.ER,reference,atol=1e-14)
checks.append({'id':'linear_score_and_each_omission_identity','status':'PASS'})
grid=json.loads((ROOT/'02_过程文件/spatial/grid_identity.json').read_text(encoding='utf8'))['grids']
ox,oy=json.loads((ROOT/'02_过程文件/spatial/native_config.json').read_text(encoding='utf8'))['origin_xy']
big={(round((g['bounds'][0]-ox)/1000),round((g['bounds'][1]-oy)/1000)):g for g in grid if g['scale_m']==1000}
counts={};areas={}
for g in grid:
    if g['scale_m']!=500:continue
    x,y=g['bounds'][:2];key=(math.floor((x-ox+1e-7)/1000),math.floor((y-oy+1e-7)/1000))
    assert key in big
    counts[key]=counts.get(key,0)+1;areas[key]=areas.get(key,0)+g['scope_area_m2']
assert max(counts.values())<=4
err=max(abs(areas[k]-v['scope_area_m2']) for k,v in big.items())
assert err<1e-4
checks.append({'id':'real_grid500_to1000_scope_area_conservation','status':'PASS','max_area_error_m2':err,'fine_grid_count':sum(counts.values())})
out=ROOT/'02_过程文件/evaluation';out.mkdir(exist_ok=True)
(out/'arithmetic_validation.json').write_text(json.dumps({'status':'PASS','empirical_composite_calculated':False,'checks':checks},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(checks))
