"""Independent CLUMPY arithmetic checks against the actual FRAGSTATS binary.

No generated cases represent Beijing. The comparison uses the min-perimeter
definition documented by landscapemetrics 2.2.1; FRAGSTATS is the production
engine. FRAGSTATS' N/A edge cases are preserved rather than imputed.
"""
from pathlib import Path
import json
import math
import random
import urllib.request
from agent_fragstats_clumpy import WORK, EXE, MODEL, run_ascii_grids, sha256


def scalar_reference(arr, focal):
    height,width=len(arr),len(arr[0])
    area=sum(v==focal for row in arr for v in row)
    total=height*width
    if area in (0,1,total):
        return None
    minimum_side=math.isqrt(area)
    rem=area-minimum_side**2
    perimeter=4*minimum_side+(0 if rem==0 else (2 if area<=minimum_side*(minimum_side+1) else 4))
    same=0
    for r in range(height):
        for c in range(width):
            if arr[r][c]!=focal:continue
            for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
                rr,cc=r+dr,c+dc
                if 0<=rr<height and 0<=cc<width and arr[rr][cc]==focal:same+=1
    g=same/(4*area-perimeter)
    p=area/total
    return (g-p)/(p if g<p and p<0.5 else 1-p)


def main():
    rng=random.Random(219)
    cases={}
    for i in range(20):
        cases[f'random_{i:02d}']=[[1 if rng.random()<(i+2)/24 else 2 for _ in range(17)] for _ in range(17)]
    cases['checker']=[[1 if (r+c)%2 else 2 for c in range(20)] for r in range(20)]
    cases['block']=[[1 if c<10 else 2 for c in range(20)] for r in range(20)]
    result=run_ascii_grids(cases,WORK/'independent_validation')
    checks=[]
    for row in result['rows']:
        name=Path(row['LID']).stem
        cls=int(row['TYPE'].split('_')[-1])
        expected=scalar_reference(cases[name],cls)
        actual=None if row['CLUMPY']=='N/A' else float(row['CLUMPY'])
        delta=None if expected is None or actual is None else abs(expected-actual)
        checks.append({'case':name,'class':cls,'expected':expected,'actual':actual,'absolute_error':delta,
                       'pass':(expected is None and actual is None) or (delta is not None and delta<=0.000050001)})
    report={'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','synthetic_only':True,
            'comparisons':len(checks),'output_precision_decimals':4,'checks':checks,
            'definition_source':'https://r-spatialecology.github.io/landscapemetrics/reference/lsm_c_clumpy.html',
            'current_FRAGSTATS_web_definition_difference':'Current C4 webpage image omits min-perimeter correction. Production FRAGSTATS4.2.1.612 binary applies the correction in these independently checked cases; cite exact version and do not substitute the current webpage image as the equation.',
            'special_cases':'Absent focal class: no row; one-pixel or full-landscape focal class: native N/A. A class occupying all but one pixel also returned N/A in the separate 6x6 edge-case test; preserve native result.'}
    (WORK/'clumpy_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={'software':'FRAGSTATS','version':'4.2.1.612','binary_build':'2020-04-17',
      'author_repository':'https://github.com/kmcgarigal/Fragstats','commit':'91b03d143c4acc0e42304d2961253340720604a2',
      'license':'GPL-3.0 in the author repository at the pinned commit',
      'archives':[{'file':p.name,'bytes':p.stat().st_size,'sha256':sha256(p),
                   'source':'https://raw.githubusercontent.com/kmcgarigal/Fragstats/91b03d143c4acc0e42304d2961253340720604a2/'+p.name}
                  for p in (WORK/'fragstats64.zip',WORK/'Tutorial.zip')],
      'executable_sha256':sha256(EXE),'template_sha256':sha256(MODEL),
      'command_syntax':'frg_cmd /m clumpy.fca /b inputs.fbt /o ./clumpy_results',
      'local_execution':'Portable package, no system installation modified; caller sets local process cwd; model is a copy of the official tutorial model.'}
    for name,url in [('LICENSE_GPL3.txt','https://raw.githubusercontent.com/kmcgarigal/Fragstats/91b03d143c4acc0e42304d2961253340720604a2/LICENSE'),
                     ('landscapemetrics_clumpy_reference.html','https://r-spatialecology.github.io/landscapemetrics/reference/lsm_c_clumpy.html')]:
        dest=WORK/name
        if not dest.exists():
            with urllib.request.urlopen(url,timeout=30) as response:dest.write_bytes(response.read())
    (WORK/'software_provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'comparisons':len(checks),'failed':[c for c in checks if not c['pass']]}))


if __name__=='__main__':main()
