"""Independent numerical/statistical QA of the real six-indicator evaluation.

Production functions are not imported or executed. Scalar formulae, original
indicator records, actual square bounds and township intersections are used.
Only the QA JSON is written. Missing real inputs/results produce BLOCKED;
there is no simulation, imputation, or creation of observational scores.
"""
from pathlib import Path
import bisect, collections, csv, datetime, hashlib, json, math, statistics, sys

ROOT=Path(__file__).resolve().parents[2]
IND=ROOT/"03_结果文件/indicators"
OUT=ROOT/"03_结果文件/evaluation"
WORK=ROOT/"02_过程文件/evaluation"
QA=WORK/"final_scientific_QA.json"
METRICS=("HQ_H","NTL","CLUMPY","MCR","SSI","E_fraction")
DIRECTION={"HQ_H":1,"NTL":-1,"CLUMPY":1,"MCR":-1,"SSI":-1,"E_fraction":1}
DIMENSIONS={"V":("HQ_H","NTL"),"S":("CLUMPY","MCR"),"O":("SSI","E_fraction")}
HABITATS=("forest_shrub","grassland","water_wetland")
PARAMETERS=("core35_land_road","core100_land_road","core10_land_only")
CANDIDATES=("worldcover",)+PARAMETERS+("crop_in_ecological_space",)
PRIMARY=CANDIDATES+("scale500_to1000_full_coverage",)
REQUIRED=("scores_all_scenarios.csv","normalization.csv","entropy_weights.csv","paired_sensitivity.csv",
          "scenario_coverage.csv","reestimated_weights.csv","indicator_correlations.csv","indicator_descriptives.csv",
          "classification.json","scores_classified.csv","township_results.csv","regional_results.csv",
          "class_agreement.csv","spatial_stability.csv","evaluation_maps.gpkg")
CHECKS=[]
TOL={"score_absolute":2e-10,"score_relative":2e-9,"area_absolute_m2":1e-4,"area_relative":1e-10,
     "fine_complete_fraction_absolute":1e-8,"Jenks_objective_absolute":1e-10,"Jenks_objective_relative":1e-9}

class QAError(Exception):pass

def require(ok,message):
    if not ok:raise QAError(message)

def read_json(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))

def read_csv(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def number(v):
    if v is None or str(v).strip().lower() in ("","nan","none","null","<na>"):return math.nan
    return float(v)

def boolean(v):
    s=str(v).strip().lower()
    if s in ("true","1","1.0"):return True
    if s in ("false","0","0.0"):return False
    raise QAError("Unrecognized boolean value: "+str(v))

def finite(v):return math.isfinite(number(v))

def close(a,b,label,area=False):
    a,b=number(a),number(b)
    if math.isnan(a) and math.isnan(b):return
    require(math.isfinite(a) and math.isfinite(b),label+": finite/missing mismatch")
    atol=TOL["area_absolute_m2"] if area else TOL["score_absolute"]
    rtol=TOL["area_relative"] if area else TOL["score_relative"]
    require(abs(a-b)<=atol+rtol*max(abs(a),abs(b)),label+": observed="+repr(a)+", expected="+repr(b))

def key(row):return (row["grid_id"],int(number(row["scale_m"])),row["product"],row["habitat"])

def index(rows,fields,label):
    answer={}
    for row in rows:
        k=tuple(row[x] for x in fields)
        require(k not in answer,label+": duplicate key "+repr(k));answer[k]=row
    return answer

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda:f.read(8*1024*1024),b""):h.update(part)
    return h.hexdigest()

def note(section,**kwargs):CHECKS.append({"section":section,"status":"PASS",**kwargs})

def readiness():
    reasons=[]
    ntlp=ROOT/"02_过程文件/aggregation/ntl_aggregation_receipt.json"
    mcrp=ROOT/"02_过程文件/aggregation/mcr_aggregation_receipt.json"
    if not ntlp.exists() or read_json(ntlp).get("status")!="PASS":
        reasons.append("Actual original EOG2020 radiance/cf_cvg aggregation has not passed.")
    if not (IND/"ntl_by_grid.csv").exists():reasons.append("Real ntl_by_grid.csv is absent.")
    if not mcrp.exists() or read_json(mcrp).get("status")!="COMPLETE":
        reasons.append("All declared real MCR scenarios are not complete.")
    master=IND/"six_indicator_records.csv"
    if not master.exists():reasons.append("six_indicator_records.csv is absent.")
    else:
        with master.open(encoding="utf-8-sig",newline="") as f:
            found=any(finite(r.get("NTL")) for r in csv.DictReader(f))
        if not found:reasons.append("The real six-indicator table contains no finite NTL observations.")
    missing=[name for name in REQUIRED if not (OUT/name).exists()]
    if missing:reasons.append("Real evaluation/reporting outputs absent: "+", ".join(missing))
    return reasons

def favourable(row,limits):
    result={}
    for m in METRICS:
        x=number(row[m]);lo,hi=limits[m]
        require(math.isfinite(x),"Nonfinite scored indicator "+m)
        require(lo-1e-10<=x<=hi+1e-10,"Scored value outside frozen union limits: "+m)
        if hi==lo:z=0.0
        else:
            z=(x-lo)/(hi-lo)
            if DIRECTION[m]<0:z=1-z
        result[m]=min(1.0,max(0.0,z))
    return result

def scalar_entropy(rows,limits):
    n=len(rows)
    if n<2:raise ValueError("fewer than two observations")
    zs=[favourable(r,limits) for r in rows];entropies={};divergences={}
    for m in METRICS:
        v=[z[m] for z in zs];total=math.fsum(v)
        probs=[x/total for x in v] if total>0 else [0.0]*n
        ent=-math.fsum(p*math.log(p) for p in probs if p>0)/math.log(n)
        d=0.0 if max(v)-min(v)<=1e-14 else max(0.0,1-ent)
        entropies[m]=ent;divergences[m]=d
    den=math.fsum(divergences.values())
    if den<=1e-14:raise ValueError("all indicators constant")
    return {m:divergences[m]/den for m in METRICS},entropies,divergences

def scalar_score(row,limits,weights):
    z=favourable(row,limits);contrib={m:z[m]*weights[m] for m in METRICS}
    answer={"ER":math.fsum(contrib.values())}
    for dim,metrics in DIMENSIONS.items():
        den=math.fsum(weights[m] for m in metrics)
        answer[dim+"_score"]=math.fsum(contrib[m] for m in metrics)/den if den>0 else math.nan
    best=min(v for k,v in answer.items() if k!="ER" and math.isfinite(v))
    answer["limiting_dimension"]=",".join(d for d in DIMENSIONS if math.isfinite(answer[d+"_score"]) and abs(answer[d+"_score"]-best)<=1e-12)
    for m in METRICS:answer["z_"+m]=z[m];answer["contribution_"+m]=contrib[m]
    return answer

def average_ranks(values):
    order=sorted(range(len(values)),key=lambda i:values[i]);ranks=[0.0]*len(values);i=0
    while i<len(order):
        j=i+1
        while j<len(order) and values[order[j]]==values[order[i]]:j+=1
        rank=(i+1+j)/2
        for k in order[i:j]:ranks[k]=rank
        i=j
    return ranks

def scalar_spearman(x,y):
    if len(x)<2 or len(set(x))<2 or len(set(y))<2:return math.nan
    rx,ry=average_ranks(x),average_ranks(y);mx=statistics.mean(rx);my=statistics.mean(ry)
    top=math.fsum((a-mx)*(b-my) for a,b in zip(rx,ry))
    den=math.sqrt(math.fsum((a-mx)**2 for a in rx)*math.fsum((b-my)**2 for b in ry))
    return top/den

def weighted_stats(values,weights):
    if not values:return math.nan,math.nan,0.0
    total=math.fsum(weights);require(total>0,"Nonpositive reporting weight")
    mean=math.fsum(x*w for x,w in zip(values,weights))/total
    sd=math.sqrt(max(0,math.fsum(w*(x-mean)**2 for x,w in zip(values,weights))/total))
    return mean,sd,total

def parent_from_bounds(grid_info):
    mains=[g for g in grid_info if g["scale_m"]==1000];columns=collections.defaultdict(list)
    for g in mains:columns[g["bounds"][0]].append(g)
    xs=sorted(columns);parents={}
    for f in (g for g in grid_info if g["scale_m"]==500):
        fb=f["bounds"];j=bisect.bisect_right(xs,fb[0]+1e-6)-1
        require(j>=0,"Fine grid has no possible parent: "+f["grid_id"])
        hits=[]
        for m in columns[xs[j]]:
            b=m["bounds"]
            if b[0]-1e-6<=fb[0] and b[1]-1e-6<=fb[1] and b[2]+1e-6>=fb[2] and b[3]+1e-6>=fb[3]:hits.append(m["grid_id"])
        require(len(hits)==1,"Fine grid does not have exactly one whole-box parent: "+f["grid_id"])
        parents[f["grid_id"]]=hits[0]
    return parents

def jenks_optimum(values,k=5):
    """Independent weighted-unique-value dynamic programming, no QGIS import."""
    counts=collections.Counter(values);x=sorted(counts);n=len(x)
    require(n>=k,"Fewer unique baseline values than requested Jenks classes")
    c=[0];s=[0.0];q=[0.0]
    for v in x:c.append(c[-1]+counts[v]);s.append(s[-1]+v*counts[v]);q.append(q[-1]+v*v*counts[v])
    def loss(j,i):return max(0.0,(q[i]-q[j])-(s[i]-s[j])**2/(c[i]-c[j]))
    previous=[math.inf]*(n+1);previous[0]=0.0;choices=[]
    for groups in range(1,k+1):
        current=[math.inf]*(n+1);where=[-1]*(n+1)
        for i in range(groups,n+1):
            best=math.inf;split=-1
            for j in range(groups-1,i):
                candidate=previous[j]+loss(j,i)
                if candidate<best:best=candidate;split=j
            current[i]=best;where[i]=split
        choices.append(where);previous=current
    cut=[];at=n
    for groups in range(k,0,-1):cut.append(x[at-1]);at=choices[groups-1][at]
    return previous[n],list(reversed(cut))

def fixed_class(value,uppers):return min(4,bisect.bisect_left(uppers,value))+1

def verify_inputs(master,grid_lookup):
    require(len({key(r) for r in master})==len(master),"Duplicate raw indicator composite keys")
    hq={key(r):r for r in read_csv(IND/"hq_graygreen_by_grid.csv")}
    cl={}
    for product,disk in [("clcd","clcd"),("wc","worldcover")]:
        for scale in [1000,500]:
            for r in read_csv(ROOT/"03_结果文件/clumpy"/("clumpy_"+disk+"_"+str(scale)+".csv")):
                habitat="grassland" if r["habitat_type"]=="grass" else r["habitat_type"]
                k=(r["Grid_ID"],scale,product,habitat);require(k not in cl,"Duplicate original CLUMPY key");cl[k]=r
    mcr_rows=read_csv(IND/"mcr_by_grid.csv")
    mcr=index(mcr_rows,("scenario","grid_id","scale_m","product","habitat"),"MCR original")
    ntl=index(read_csv(IND/"ntl_by_grid.csv"),("grid_id","scale_m"),"NTL original")
    for (gid,scale),row in ntl.items():
        geom=grid_lookup[(gid,int(number(scale)))];whole=number(row["ntl_grid_area_m2"]);observed=number(row["ntl_valid_area_m2"])
        close(whole,geom["grid_area_m2"],"Native NTL whole-square area",area=True)
        tolerance=max(1e-6,whole*1e-10)
        require(-tolerance<=observed<=whole+tolerance,"Native NTL observed area outside complete square")
        expected_complete=abs(whole-observed)<=tolerance
        require(boolean(row["ntl_support_complete"])==expected_complete,"NTL complete flag disagrees with actual observed area")
        close(row["ntl_valid_fraction"],min(1,max(0,observed/whole)),"Native NTL valid-area fraction")
        require(finite(row["NTL"])==expected_complete,"Partial/unobserved native NTL entered the main metric")
        if expected_complete:close(row["NTL"],row["NTL_partial_mean"],"Complete native NTL mean")
    for row in master:
        k=key(row);gid,scale,product,habitat=k
        require(k in hq and k in cl,"Missing source HQ/CLUMPY record: "+repr(k))
        for field in ("HQ_H","SSI","E_fraction","SSI_crop_included","E_fraction_crop_included"):
            close(row[field],hq[k][field],"Source "+field+" "+repr(k))
        close(row["CLUMPY"],cl[k]["CLUMPY"],"Original CLUMPY "+repr(k))
        require(row["CLUMPY_status"]==cl[k]["status"],"Original CLUMPY support status changed")
        mk=(product+"_"+habitat+"_core10_land_road",gid,str(scale),product,habitat)
        require(mk in mcr,"No corresponding baseline product/habitat MCR: "+repr(mk))
        close(row["MCR"],mcr[mk]["MCR"],"Original baseline MCR "+repr(k))
        for field in ("MCR_valid_m2","MCR_valid_fraction","MCR_partial_mean","MCR_euclidean_m","target_truncated_fraction","destination_truncated_fraction"):
            close(row[field],mcr[mk][field],"Original baseline MCR support "+field,area=field.endswith("_m2"))
        require(row["MCR_status"]==mcr[mk]["MCR_status"],"Original baseline MCR status changed")
        nr=ntl.get((gid,str(scale)));require(nr is not None,"Missing original NTL key")
        close(row["NTL"],nr["NTL"],"Original NTL "+repr(k))
        support=boolean(nr["ntl_support_complete"])
        require(finite(nr["NTL"])==support,"Main NTL not restricted to complete native observation support")
        geom=grid_lookup[(gid,scale)]
        close(row["scope_area_m2"],geom["scope_area_m2"],"Original union-grid area",area=True)
        close(row["grid_area_m2"],geom["grid_area_m2"],"Original full-square area",area=True)
        valid=all(finite(row[m]) for m in METRICS)
        require(boolean(row["six_valid"])==valid,"six_valid disagrees with six real finite indicators: "+repr(k))
    ntlqa=read_json(ROOT/"02_过程文件/aggregation/ntl_aggregation_receipt.json")
    require(digest(IND/"ntl_by_grid.csv")==ntlqa["result_sha256"],"NTL result changed after native support QA")
    for source in ntlqa["inputs"]:
        p=Path(source["path"]);p=p if p.is_absolute() else ROOT/p
        require(p.exists() and p.stat().st_size==source["bytes"],"Original EOG file absent/size changed")
        require(digest(p)==source["sha256"],"Original EOG file checksum changed")
    note("original_products_and_six_valid",master_rows=len(master),physical_EOG_source_hashes_verified=True,
         policy="Product/habitat/scale-specific HQ, CLUMPY, baseline MCR and original same-release NTL matched; no scenario uses a different base unnoticed")
    return mcr_rows

def main_checks():
    master=read_csv(IND/"six_indicator_records.csv")
    grid_info=read_json(ROOT/"02_过程文件/spatial/grid_identity.json")["grids"]
    grid_lookup={(g["grid_id"],g["scale_m"]):g for g in grid_info};parents=parent_from_bounds(grid_info)
    mcr=verify_inputs(master,grid_lookup)
    scores=read_csv(OUT/"scores_all_scenarios.csv")
    actual=index(scores,("habitat","scenario","grid_id"),"All scores")
    norm=index(read_csv(OUT/"normalization.csv"),("habitat","indicator"),"Normalization")
    ent=index(read_csv(OUT/"entropy_weights.csv"),("habitat","indicator"),"Entropy weights")
    rew=index(read_csv(OUT/"reestimated_weights.csv"),("habitat","scenario","indicator"),"Reestimated weights")
    require(set(norm)=={(h,m) for h in HABITATS for m in METRICS},"Missing/extra normalization entries")
    require(set(ent)==set(norm),"Missing/extra baseline entropy entries")
    expected={};expected_pairs={};expected_coverage={};expected_reweight_keys=set();baselines={};weight_sets={};limits_sets={}
    def add_score(h,scenario,rows,limits,weights):
        for row in rows:
            k=(h,scenario,row["grid_id"]);require(k not in expected,"Duplicate expected score")
            rec=dict(row);rec.update(scalar_score(row,limits,weights));rec["scenario"]=scenario;expected[k]=rec
    def add_pair(h,scenario,reference,alternative,partial=False):
        expected_pairs[(h,scenario)]=(reference,alternative,partial)
    for habitat in HABITATS:
        valid=[r for r in master if r["habitat"]==habitat and boolean(r["six_valid"])]
        baseline={r["grid_id"]:r for r in valid if r["product"]=="clcd" and int(r["scale_m"])==1000}
        require(len(baseline)>=2,"Insufficient real baseline observations: "+habitat);baselines[habitat]=baseline
        candidates={"worldcover":{r["grid_id"]:r for r in valid if r["product"]=="wc" and int(r["scale_m"])==1000 and r["grid_id"] in baseline}}
        for scenario in PARAMETERS:
            source={r["grid_id"]:r for r in mcr if r["scenario"]=="clcd_"+habitat+"_"+scenario and int(r["scale_m"])==1000 and r["product"]=="clcd" and r["habitat"]==habitat}
            changed={}
            for gid,row in baseline.items():
                require(gid in source,"Declared MCR scenario omits a baseline spatial record: "+scenario+" "+gid)
                new=dict(row)
                for name,value in source[gid].items():
                    if name.startswith("MCR") or name in ("target_truncated_fraction","destination_truncated_fraction"):new[name]=value
                if all(finite(new[m]) for m in METRICS):changed[gid]=new
            candidates[scenario]=changed
        changed={}
        for gid,row in baseline.items():
            new=dict(row);new["SSI"]=row["SSI_crop_included"];new["E_fraction"]=row["E_fraction_crop_included"]
            if all(finite(new[m]) for m in METRICS):changed[gid]=new
        candidates["crop_in_ecological_space"]=changed
        fine=[]
        for row in valid:
            if row["product"]=="clcd" and int(row["scale_m"])==500 and parents[row["grid_id"]] in baseline:
                r=dict(row);r["parent_grid_id"]=parents[row["grid_id"]];fine.append(r)
        pool=list(baseline.values())+[r for c in candidates.values() for r in c.values()]+fine
        limits={m:(min(number(r[m]) for r in pool),max(number(r[m]) for r in pool)) for m in METRICS};limits_sets[habitat]=limits
        weights,e,d=scalar_entropy(list(baseline.values()),limits);weight_sets[habitat]=weights
        close(math.fsum(weights.values()),1,"Weight sum")
        close(math.fsum(number(ent[(habitat,m)]["weight"]) for m in METRICS),1,"Observed baseline weight sum")
        require(all(number(ent[(habitat,m)]["weight"])>=0 for m in METRICS),"Negative reported baseline entropy weight")
        for m in METRICS:
            row=norm[(habitat,m)];close(row["minimum"],limits[m][0],"Union minimum "+habitat+" "+m);close(row["maximum"],limits[m][1],"Union maximum "+habitat+" "+m)
            require(int(row["direction"])==DIRECTION[m],"Incorrect favorable indicator direction")
            er=ent[(habitat,m)]
            for col,value in [("weight",weights[m]),("entropy",e[m]),("divergence",d[m])]:close(er[col],value,"Baseline entropy "+col)
            require(int(er["baseline_n"])==len(baseline),"Entropy fitted on a wrong sample domain")
        add_score(habitat,"baseline",baseline.values(),limits,weights)
        bs={gid:expected[(habitat,"baseline",gid)] for gid in baseline}
        expected_coverage[(habitat,"baseline")]=baseline
        for scenario,domain in candidates.items():
            add_score(habitat,scenario,domain.values(),limits,weights)
            alt={gid:expected[(habitat,scenario,gid)] for gid in domain}
            add_pair(habitat,scenario,bs,alt);expected_coverage[(habitat,scenario)]=domain
            if not domain:continue
            paired_base=[baseline[gid] for gid in domain]
            for m in METRICS:
                expected_reweight_keys.add((habitat,scenario,m))
                rr=rew[(habitat,scenario,m)]
                require(int(number(rr["paired_n"]))==len(domain),"Incorrect paired weight sample n")
                close(rr["baseline_full_weight"],weights[m],"Paired table full baseline weight")
            try:wb,_,_=scalar_entropy(paired_base,limits);wa,_,_=scalar_entropy(list(domain.values()),limits)
            except ValueError:
                for m in METRICS:
                    r=rew[(habitat,scenario,m)];require(r["status"]=="NOT_ESTIMABLE","Nonestimable paired weights not flagged")
                    require(not finite(r["baseline_paired_weight"]) and not finite(r["scenario_paired_weight"]),"Invented unidentifiable paired weights")
            else:
                for m in METRICS:
                    r=rew[(habitat,scenario,m)];require(r["status"]=="VALID","Estimable paired weights mislabeled")
                    close(r["baseline_full_weight"],weights[m],"Full baseline weight")
                    close(r["baseline_paired_weight"],wb[m],"Baseline weight reestimated on same paired domain")
                    close(r["scenario_paired_weight"],wa[m],"Alternative weight reestimated on same paired domain")
                    require(int(r["paired_n"])==len(domain),"Incorrect paired weight sample n")
                s=scenario+"_reweighted";ref="baseline_paired_"+scenario+"_reweighted"
                add_score(habitat,s,domain.values(),limits,wa);add_score(habitat,ref,paired_base,limits,wb)
                add_pair(habitat,scenario+"_paired_reestimated_weights",{gid:expected[(habitat,ref,gid)] for gid in domain},{gid:expected[(habitat,s,gid)] for gid in domain})
        for omitted in METRICS:
            den=math.fsum(w for m,w in weights.items() if m!=omitted)
            if den<=1e-14:continue
            w={m:(0.0 if m==omitted else weights[m]/den) for m in METRICS};scenario="omit_"+omitted
            add_score(habitat,scenario,baseline.values(),limits,w)
            add_pair(habitat,scenario,bs,{gid:expected[(habitat,scenario,gid)] for gid in baseline});expected_coverage[(habitat,scenario)]=baseline
        if fine:
            add_score(habitat,"scale500_native",fine,limits,weights)
            groups=collections.defaultdict(list)
            for r in fine:groups[r["parent_grid_id"]].append(expected[(habitat,"scale500_native",r["grid_id"])])
            agg_full={};agg_partial={}
            for gid,rows in groups.items():
                ar=[number(r["scope_area_m2"]) for r in rows];area=math.fsum(ar);fraction=area/number(baseline[gid]["scope_area_m2"])
                require(fraction<=1+1e-8,"Fine valid area exceeds its actual parent study-grid area")
                full=abs(fraction-1)<=TOL["fine_complete_fraction_absolute"]
                scenario="scale500_to1000_full_coverage" if full else "scale500_to1000_partial_coverage"
                rec={"grid_id":gid,"habitat":habitat,"scenario":scenario,"scale_m":1000,"product":"clcd","scope_area_m2":area,"fine_valid_fraction":fraction}
                for col in ("ER","V_score","S_score","O_score"):
                    vals=[number(r[col]) for r in rows]
                    rec[col]=weighted_stats(vals,ar)[0] if all(math.isfinite(v) for v in vals) else math.nan
                expected[(habitat,scenario,gid)]=rec
                (agg_full if full else agg_partial)[gid]=rec
            for scenario,domain in [("scale500_to1000_full_coverage",agg_full),("scale500_to1000_partial_coverage",agg_partial)]:
                if domain:expected_coverage[(habitat,scenario)]=domain
            add_pair(habitat,"scale500_to1000_full_coverage",bs,agg_full)
            add_pair(habitat,"scale500_to1000_partial_coverage",bs,agg_partial,partial=True)
    require(set(actual)==set(expected),"Scored scenario/grid domains differ from independent reconstruction: missing="+str(len(set(expected)-set(actual)))+", extra="+str(len(set(actual)-set(expected))))
    require(set(rew)==expected_reweight_keys,"Missing/extra paired reweighting rows")
    for k,ex in expected.items():
        ob=actual[k];require(ob["product"]==ex["product"] and int(ob["scale_m"])==int(ex["scale_m"]),"Wrong original product/scale in scenario "+repr(k))
        for col in ("ER","V_score","S_score","O_score"):close(ob[col],ex[col],"Scalar score "+col+" "+repr(k))
        close(ob["scope_area_m2"],ex["scope_area_m2"],"Score support area "+repr(k),area=True)
        if "fine_valid_fraction" in ex:close(ob["fine_valid_fraction"],ex["fine_valid_fraction"],"Fine coverage fraction")
        else:
            for m in METRICS:
                close(ob[m],ex[m],"Scenario original value "+m+" "+repr(k))
                close(ob["z_"+m],ex["z_"+m],"Favorable normalized value "+m)
                close(ob["contribution_"+m],ex["contribution_"+m],"Indicator contribution "+m)
            require(ob["limiting_dimension"]==ex["limiting_dimension"],"Incorrect tied limiting dimension")
            for field in ("MCR_valid_m2","MCR_valid_fraction","MCR_partial_mean","MCR_euclidean_m","target_truncated_fraction","destination_truncated_fraction"):
                close(ob[field],ex[field],"Scenario MCR provenance/support "+field+" "+repr(k),area=field.endswith("_m2"))
            require(ob["MCR_status"]==ex["MCR_status"],"Scenario MCR support status changed")
            if ex["scenario"]=="scale500_native":require(ob["parent_grid_id"]==ex["parent_grid_id"],"Incorrect fine-parent geometry association")
    note("domains_normalization_entropy_and_scalar_scores",score_rows=len(expected),habitats=3,
         baseline_n={h:len(b) for h,b in baselines.items()},paired_reweight_reference="same exact grid IDs on both sides, independently reestimated",fine_rule="whole-square nesting from actual bounds; parent comparison restricted to complete within-study support")
    verify_pair_tables(expected_pairs,expected_coverage,baselines,limits_sets)
    classified,classes=verify_classes(expected,baselines)
    verify_reporting(classified,classes,grid_lookup)
    verify_stability(classified,classes)
    return {"score_rows_verified":len(expected),"habitats":list(HABITATS),"baseline_n":{h:len(b) for h,b in baselines.items()}}

def verify_pair_tables(expected_pairs,expected_coverage,baselines,limits):
    observed=index(read_csv(OUT/"paired_sensitivity.csv"),("habitat","scenario"),"Pair descriptions")
    require(set(observed)==set(expected_pairs),"Missing/extra paired sensitivity scenario")
    for k,(ref,alt,partial) in expected_pairs.items():
        row=observed[k];common=sorted(set(ref)&set(alt));require(int(row["n"])==len(common),"Incorrect paired n "+repr(k))
        if partial:
            require(row["status"]=="NOT_COMPARABLE_DIFFERENT_WITHIN_GRID_SUPPORT","Partial500m support treated as comparable")
            for col in ("spearman_rho","weighted_mean_difference","weighted_MAE"):require(not finite(row.get(col)),"Invented comparison of partial500m support")
            close(row["fine_valid_area_m2"],math.fsum(number(alt[g]["scope_area_m2"]) for g in common),"Partial fine area",area=True)
            close(row["corresponding_baseline_area_m2"],math.fsum(number(ref[g]["scope_area_m2"]) for g in common),"Partial corresponding baseline area",area=True)
        elif not common:require(row["status"]=="NO_PAIRED_VALID_DOMAIN","Empty paired domain not flagged")
        else:
            require(row["status"]=="VALID","Valid paired comparison mislabeled")
            x=[number(ref[g]["ER"]) for g in common];y=[number(alt[g]["ER"]) for g in common];w=[number(ref[g]["scope_area_m2"]) for g in common]
            require(int(number(row["baseline_valid_n"]))==len(ref),"Wrong baseline reference population in paired report")
            close(row["baseline_valid_area_m2"],math.fsum(number(r["scope_area_m2"]) for r in ref.values()),"Paired reference baseline area",area=True)
            close(row["paired_area_m2"],math.fsum(w),"Paired area",area=True)
            close(row["spearman_rho"],scalar_spearman(x,y),"Manual-rank Spearman "+repr(k))
            close(row["weighted_mean_difference"],weighted_stats([b-a for a,b in zip(x,y)],w)[0],"Paired weighted difference")
            close(row["weighted_MAE"],weighted_stats([abs(b-a) for a,b in zip(x,y)],w)[0],"Paired weighted MAE")
    coverage=index(read_csv(OUT/"scenario_coverage.csv"),("habitat","scenario"),"Scenario coverage")
    require(set(coverage)==set(expected_coverage),"Scenario coverage domain list mismatch")
    for k,domain in expected_coverage.items():
        require(int(coverage[k]["n"])==len(domain),"Scenario coverage n mismatch")
        close(coverage[k]["area_m2"],math.fsum(number(r["scope_area_m2"]) for r in domain.values()),"Scenario coverage area",area=True)
    correlations=index(read_csv(OUT/"indicator_correlations.csv"),("habitat","indicator_1","indicator_2"),"Indicator correlations")
    descriptives=index(read_csv(OUT/"indicator_descriptives.csv"),("habitat","indicator"),"Indicator descriptives")
    require(len(correlations)==45 and len(descriptives)==18,"Missing/extra baseline descriptive records")
    for h,b in baselines.items():
        rows=list(b.values());w=[number(r["scope_area_m2"]) for r in rows]
        for i,m in enumerate(METRICS):
            v=[number(r[m]) for r in rows];mean,sd,_=weighted_stats(v,w);o=descriptives[(h,m)]
            require(int(o["n"])==len(rows),"Descriptive n differs from full valid baseline")
            for col,value in [("minimum",min(v)),("maximum",max(v)),("area_weighted_mean",mean),("area_weighted_sd",sd),("unweighted_median",statistics.median(v))]:close(o[col],value,"Baseline descriptive "+col)
            for other in METRICS[i+1:]:
                o=correlations[(h,m,other)];require(int(o["n"])==len(rows),"Correlation n mismatch")
                close(o["spearman_rho"],scalar_spearman(v,[number(r[other]) for r in rows]),"Independent indicator correlation")
    note("paired_statistics_and_indicator_diagnostics",paired_scenarios=len(observed),scalar_Spearman="Pearson correlation of independently computed average ranks; no scipy/pandas correlation used",partial_fine_support_never_compared=True)

def verify_classes(expected,baselines):
    spec=read_json(OUT/"classification.json");require(spec["method"]=="natural_breaks_Jenks","Unexpected classification method")
    require(set(spec["habitats"])==set(HABITATS),"Classification missing/extra habitat")
    bounds={};jenks_checks=[]
    for h in HABITATS:
        info=spec["habitats"][h];cs=info["classes"]
        values=[expected[(h,"baseline",gid)]["ER"] for gid in baselines[h]]
        require(len(cs)==5 and info["n"]==len(values),"Jenks fitted on wrong class count or baseline n")
        upper=[float(c["upper"]) for c in cs];require(all(upper[i]<upper[i+1] for i in range(4)),"Jenks class upper bounds not strictly ordered")
        close(cs[0]["lower"],min(values),"Baseline class lower extent");close(upper[-1],max(values),"Baseline class upper extent")
        for i in range(1,5):close(cs[i]["lower"],upper[i-1],"Adjacent class bound continuity")
        optimum,independent_bounds=jenks_optimum(values)
        groups=collections.defaultdict(list)
        for x in values:groups[fixed_class(x,upper)].append(x)
        require(len(groups)==5,"Empty baseline Jenks class")
        cost=math.fsum(math.fsum((v-statistics.mean(g))**2 for v in g) for g in groups.values())
        require(abs(cost-optimum)<=TOL["Jenks_objective_absolute"]+TOL["Jenks_objective_relative"]*max(abs(cost),abs(optimum)),"Reported Jenks breaks do not achieve independent minimum within-class SSE")
        require(all(any(abs(x-u)<=2e-10 for x in values) for u in upper),"Jenks upper bound is not an observed baseline value")
        bounds[h]=upper;jenks_checks.append({"habitat":h,"baseline_n":len(values),"reported_SSE":cost,"independent_minimum_SSE":optimum,"independent_optimal_upper_bounds":independent_bounds,"reported_upper_bounds":upper,"ties_policy":"Equivalent minimum-SSE partitions accepted; all scenarios still use the one reported baseline partition"})
    obs=index(read_csv(OUT/"scores_classified.csv"),("habitat","scenario","grid_id"),"Classified scores")
    require(set(obs)==set(expected),"Classification added/dropped scored observations")
    for k,row in obs.items():
        close(row["ER"],expected[k]["ER"],"Classified ER changed")
        require(int(row["ER_class"])==fixed_class(expected[k]["ER"],bounds[k[0]]),"Scenario class does not use fixed baseline thresholds: "+repr(k))
    note("independent_Jenks_and_fixed_scenario_classes",fits=jenks_checks,classified_rows=len(obs),fixed_thresholds_for_all_comparisons=True)
    return obs,bounds

def verify_reporting(classified,classes,grid_lookup):
    baseline={h:{k[2]:r for k,r in classified.items() if k[0]==h and k[1]=="baseline"} for h in HABITATS}
    weight_rows=read_csv(IND/"town_grid_weights_1000.csv");parts=collections.defaultdict(list)
    for row in weight_rows:
        gid,town=row["Grid_ID"],row["Name"];area=number(row["intersect_m2"])
        require((gid,1000) in grid_lookup and area>0,"Invalid actual town-grid intersection")
        require(area<=grid_lookup[(gid,1000)]["scope_area_m2"]+1e-3,"Town intersection exceeds study part of a square")
        parts[(town,gid)].append(area)
    weights={k:math.fsum(v) for k,v in parts.items()};towns=sorted({k[0] for k in weights})
    require(len(towns)==35,"Expected all 35 original township coverage units")
    obs=index(read_csv(OUT/"township_results.csv"),("town","habitat"),"Township results")
    require(set(obs)=={(t,h) for t in towns for h in HABITATS},"Township table must include all105 combinations including zero-valid ones")
    for t in towns:
        local={gid:ar for (town,gid),ar in weights.items() if town==t};total=math.fsum(local.values())
        for h in HABITATS:
            b=baseline[h];ids=sorted(set(local)&set(b));row=obs[(t,h)]
            ar=[local[g] for g in ids];vals=[number(b[g]["ER"]) for g in ids]
            mean,sd,area=weighted_stats(vals,ar)
            require(int(number(row["grid_n"]))==len(ids),"Town valid-grid count mismatch")
            for col,value in [("covered_town_area_m2",total),("six_valid_area_m2",area),("lowest_class_area_m2",math.fsum(local[g] for g in ids if int(b[g]["ER_class"])==1))]:close(row[col],value,"Town grid coverage "+t+" "+h+" "+col,area=True)
            close(row["six_valid_fraction"],area/total,"Town valid-grid area fraction")
            close(row["ER_mean"],mean,"Town area-weighted ER");close(row["ER_within_town_sd"],sd,"Town within-area population SD")
            for dim in DIMENSIONS:
                good=[g for g in ids if finite(b[g][dim+"_score"])]
                expected=weighted_stats([number(b[g][dim+"_score"]) for g in good],[local[g] for g in good])[0]
                close(row[dim+"_mean"],expected,"Town dimension mean")
    region=index(read_csv(OUT/"regional_results.csv"),("habitat",),"Regional results");require(len(region)==3,"Regional rows mismatch")
    for h,b in baseline.items():
        rows=list(b.values());ar=[grid_lookup[(r["grid_id"],1000)]["scope_area_m2"] for r in rows];v=[number(r["ER"]) for r in rows]
        mean,sd,total=weighted_stats(v,ar);r=region[(h,)]
        require(int(r["valid_grid_n"])==len(rows),"Regional valid-grid n mismatch")
        for col,x in [("ER_area_weighted_mean",mean),("ER_area_weighted_sd",sd),("ER_min",min(v)),("ER_max",max(v))]:close(r[col],x,"Regional "+col)
        close(r["valid_scope_area_m2"],total,"Regional valid grid coverage",area=True)
        close(r["lowest_class_area_m2"],math.fsum(a for a,row in zip(ar,rows) if int(row["ER_class"])==1),"Regional low-value grid coverage",area=True)
    note("all_35_townships_and_region",town_habitat_rows=105,zero_valid_combinations_preserved=True,
         interpretation="All valid_scope_area_m2, six_valid_area_m2 and lowest_class_area_m2 are valid/low-value GRID COVERAGE areas containing the focal habitat, not actual forest/grass/water habitat areas. Habitat-specific grid domains overlap and must not be summed as the regional area. Original town overlaps are preserved separately; regional reporting uses union-grid areas.")

def verify_stability(classified,classes):
    stability=index(read_csv(OUT/"spatial_stability.csv"),("habitat","grid_id"),"Spatial stability")
    agreement=index(read_csv(OUT/"class_agreement.csv"),("habitat","scenario"),"Class agreement")
    base={(h,gid):r for (h,s,gid),r in classified.items() if s=="baseline"};require(set(stability)==set(base),"Stability does not cover exactly all baseline-valid cells")
    for (h,gid),b in base.items():
        observed=stability[(h,gid)];available=[s for s in PRIMARY if (h,s,gid) in classified]
        labels=[int(b["ER_class"])]+[int(classified[(h,s,gid)]["ER_class"]) for s in available]
        require(set(observed["available_scenarios"].split(";"))-{ "" }==set(available),"Wrong primary comparison membership")
        require(int(observed["comparison_count"])==len(available) and int(observed["planned_comparison_count"])==6,"Wrong planned/available stability count")
        require(int(observed["baseline_class"])==labels[0],"Wrong baseline class in stability")
        complete=len(available)==6;low=all(c==1 for c in labels)
        require(boolean(observed["complete_comparison_set"])==complete,"Incomplete comparison set silently considered complete")
        require(boolean(observed["low_in_all_available_schemes"])==(bool(available) and low),"Available-only low flag mismatch")
        require(boolean(observed["consistent_low_complete_set"])==(complete and low),"Stable low lacks all six primary comparisons plus baseline")
        require(int(observed["class_span"])==max(labels)-min(labels),"Class-span mismatch")
    grouped=collections.defaultdict(dict)
    for (h,s,gid),r in classified.items():
        if int(number(r["scale_m"]))==1000:grouped[(h,s)][gid]=r
    expected_keys=set()
    for (h,scenario),alternative in grouped.items():
        if scenario in ("baseline","scale500_to1000_partial_coverage") or scenario.startswith("baseline_paired_"):continue
        refname="baseline"
        if scenario.endswith("_reweighted"):refname="baseline_paired_"+scenario[:-len("_reweighted")]+"_reweighted"
        reference=grouped.get((h,refname),{});ids=sorted(set(reference)&set(alternative))
        if not ids:continue
        expected_keys.add((h,scenario));r=agreement[(h,scenario)]
        require(r["reference_scenario"]==refname,"Reweighted class agreement used wrong baseline reference")
        require(int(r["paired_n"])==len(ids),"Class agreement n mismatch")
        areas={g:number(reference[g]["scope_area_m2"]) for g in ids};total=math.fsum(areas.values())
        equal=[g for g in ids if int(reference[g]["ER_class"])==int(alternative[g]["ER_class"])]
        intersection=[g for g in ids if int(reference[g]["ER_class"])==1 and int(alternative[g]["ER_class"])==1]
        union=[g for g in ids if int(reference[g]["ER_class"])==1 or int(alternative[g]["ER_class"])==1]
        close(r["paired_area_m2"],total,"Class agreement area",area=True)
        close(r["same_class_fraction_area"],math.fsum(areas[g] for g in equal)/total,"Fixed-class agreement fraction")
        den=math.fsum(areas[g] for g in union)
        close(r["lowest_class_Jaccard_area"],math.fsum(areas[g] for g in intersection)/den if den>0 else math.nan,"Low-value grid Jaccard")
    require(set(agreement)==expected_keys,"Extra/missing class comparisons; partial fine support must be excluded")
    # Also verify saved map attributes against these same tables and native geometry.
    import geopandas as gpd
    for h in HABITATS:
        layer=gpd.read_file(OUT/"evaluation_maps.gpkg",layer=h)
        require(layer.grid_id.is_unique,"Duplicate saved map grid")
        expected_ids={r["grid_id"] for r in read_csv(IND/"six_indicator_records.csv") if r["habitat"]==h and r["product"]=="clcd" and int(r["scale_m"])==1000}
        require(set(layer.grid_id)==expected_ids,"Saved map dropped invalid grid locations instead of representing NA")
        for row in layer.itertuples():
            k=(h,row.grid_id)
            if k in base:
                close(row.ER,base[k]["ER"],"Map ER source")
                require(int(row.map_class)==int(base[k]["ER_class"]),"Map class differs from fixed baseline class")
                require(boolean(row.consistent_low_complete_set)==boolean(stability[k]["consistent_low_complete_set"]),"Map stable-low flag differs from validated table")
            else:require(not finite(row.ER) and int(row.map_class)==0,"Invalid raw grid fabricated as an ER score or low class")
    note("fixed_reference_class_agreement_and_complete_stable_low",baseline_cells=len(base),required_primary_comparisons=list(PRIMARY),
         stable_low_rule="baseline AND all six named main comparisons class1; availability alone never enough",reweighted_reference="matching paired baseline reestimated on the same domain",partial_500m_never_in_stability=True,map_attributes_checked=True)

def execute():
    WORK.mkdir(parents=True,exist_ok=True)
    report={"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"BLOCKED",
            "scope":"Independent numerical, spatial-support and statistical reporting QA; NOT ecological external validation or evidence of causal effects",
            "area_interpretation":"Reported valid/low-class areas are habitat-specific valid GRID COVERAGE areas, not actual habitat extent. Domains can overlap across habitats and cannot be summed into a regional total.",
            "numeric_tolerances":TOL,"production_outputs_written":False,"simulation_or_imputation":False,"checks":CHECKS,
            "verification_code_sha256":digest(Path(__file__)),
            "read_only_production_code_sha256":{name:digest(ROOT/"05_代码/src"/name) for name in ("evaluate_resilience.py","summarize_evaluation.py","qgis_classify_scores.py")}}
    try:reasons=readiness()
    except (OSError,ValueError) as error:reasons=["Input readiness cannot be verified: "+type(error).__name__+": "+str(error)]
    if reasons:
        report["blocking_reasons"]=reasons
        report["execution"]="Readiness/fail-closed path only; no composite score, classification, or report was generated."
        QA.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
        print("FINAL_SCIENTIFIC_QA_BLOCKED: "+" | ".join(reasons),flush=True)
        return 2
    tracked=[IND/"six_indicator_records.csv",IND/"hq_graygreen_by_grid.csv",IND/"mcr_by_grid.csv",IND/"ntl_by_grid.csv",IND/"town_grid_weights_1000.csv"]
    tracked += [OUT/name for name in REQUIRED]
    tracked += [ROOT/"05_代码/src"/name for name in ("evaluate_resilience.py","summarize_evaluation.py","qgis_classify_scores.py")]
    tracked += [ROOT/"02_过程文件/spatial/grid_identity.json"]
    signatures={str(p.relative_to(ROOT)):digest(p) for p in tracked}
    try:
        result=main_checks()
        require(all(digest(ROOT/p)==h for p,h in signatures.items()),"Source/output file changed while independent QA was running")
        report.update(status="PASS",summary=result,checked_file_sha256=signatures,
                      interpretation="PASS means the real numerical results, scenario domains, fixed classification and reporting tables match independent recomputation. It does not establish observed ecological resistance/recovery, independent ecological truth, or causality.")
    except QAError as error:
        report.update(status="FAIL",failure=str(error),checked_file_sha256=signatures)
    except Exception as error:
        report.update(status="ERROR_NOT_VALIDATED",failure=type(error).__name__+": "+str(error),checked_file_sha256=signatures)
    QA.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf8")
    print("FINAL_SCIENTIFIC_QA_"+report["status"],flush=True)
    return 0 if report["status"]=="PASS" else 1

if __name__=="__main__":sys.exit(execute())
