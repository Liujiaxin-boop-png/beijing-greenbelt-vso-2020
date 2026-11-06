"""Read-only diagnosis comparing native Jenks against original exported scores."""
import json,math,statistics,collections
import verify_final_analysis as q
rows=q.read_csv(q.OUT/'scores_all_scenarios.csv')
cls=q.read_json(q.OUT/'classification.json')['habitats']
answer=[]
for habitat in q.HABITATS:
    vals=[float(r['ER']) for r in rows if r['habitat']==habitat and r['scenario']=='baseline']
    upper=[c['upper'] for c in cls[habitat]['classes']]
    optimum,bounds=q.jenks_optimum(vals);groups=collections.defaultdict(list)
    for v in vals:groups[q.fixed_class(v,upper)].append(v)
    cost=math.fsum(math.fsum((v-statistics.mean(g))**2 for v in g) for g in groups.values())
    answer.append({'habitat':habitat,'original_score_SSE':cost,'optimal_SSE':optimum,'difference':cost-optimum,'reported':upper,'independent':bounds})
out=q.ROOT/'02_过程文件/evaluation/jenks_boundary_diagnosis.json'
out.write_text(json.dumps(answer,indent=2),encoding='utf8')
print(json.dumps(answer))
