"""Named execution entrypoints for the recorded Windows research environment.

Run `python pipeline.py --plan` first. Each stage calls the same implementation
used for the retained run; sources are supplied under the sibling raw folder.
This command never downloads credentials, removes previous work, or fabricates
an absent input. Complete native MCR runs have their own hash-checked resume.
"""
from pathlib import Path
import argparse,json,subprocess,sys,datetime
CODE=Path(__file__).resolve().parent;ROOT=CODE.parent;SRC=CODE/'src'
DEFAULTS={'python':r'C:\Users\LJX\AppData\Local\Programs\Python\Python312\python.exe',
 'propy':r'F:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat',
 'qgis':r'F:\Program Files\QGIS 3.28.2\bin\python-qgis.bat'}
runtime=CODE/'local_runtime.json'
ENV=json.loads(runtime.read_text(encoding='utf8')) if runtime.exists() else DEFAULTS
def cmd(engine,script,*args):return [ENV[engine],str(SRC/script)]+list(map(str,args))
work=ROOT/'02_过程文件';res=ROOT/'03_结果文件'
STAGES={
 'spatial':[cmd('python','prepare_spatial.py'),cmd('propy','native_fishnet.py',work/'spatial/native_config.json'),cmd('propy','agent_export_grid_bounds.py',work/'spatial/native_config.json',work/'native_clumpy')],
 'hq':[cmd('python','prepare_hq.py'),[r'D:\Apps\InVEST-3.20.2\invest.exe','run','habitat_quality','-d',str(work/'hq/clcd_pilot.json'),'--no-report'],cmd('python','run_hq.py')],
 'euclidean':[cmd('python','prepare_distance_inputs.py'),cmd('propy','native_euclidean.py',work/'distance/tasks.json')],
 'clumpy':[cmd('python','agent_batch_clumpy.py',work/'spatial/native_config.json',work/'native_clumpy',res/'clumpy')],
 'mspa':[cmd('python','agent_mspa.py')],
 'mcr':[cmd('python','prepare_mcr.py'),cmd('python','agent_mcr_queue.py',work/'mcr_inputs/regional_queue.json',ENV['propy']),cmd('python','agent_mcr_cross_scenario_qa.py',work/'mcr_inputs/regional_queue.json'),cmd('python','agent_publish_mcr.py',work/'mcr_inputs/regional_queue.json',res/'mcr')],
 'ntl':[cmd('python','agent_ntl_aggregate.py','--config',work/'aggregation/ntl_inputs.json')],
 'aggregate':[cmd('python','aggregate_basics.py'),cmd('python','aggregate_mcr.py'),cmd('python','join_indicator_records.py')],
 'arithmetic_qa':[cmd('python','validate_evaluation_math.py')],
 'evaluate':[cmd('python','evaluate_resilience.py'),cmd('qgis','qgis_classify_scores.py'),cmd('python','summarize_evaluation.py')],
 'context_maps':[cmd('python','prepare_figure_layers.py'),cmd('qgis','qgis_study_map.py'),cmd('qgis','qgis_method_diagram.py'),cmd('qgis','qgis_verify_context_projects.py')],
 'thermal':[cmd('python','agent_thermal_prepare.py'),cmd('python','agent_thermal_validate.py'),cmd('python','agent_thermal_association.py'),cmd('python','agent_thermal_association_validate.py')],
 'thermal_figure':[cmd('qgis','agent_thermal_qgis_figure6.py'),cmd('qgis','agent_thermal_qgis_figure6_validate.py')],
 'result_maps':[cmd('qgis','qgis_result_maps.py')],
 'final_qa':[cmd('python','verify_final_analysis.py')],
 'manifest':[cmd('python','build_project_manifest.py')]
}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan',action='store_true');ap.add_argument('--stage',choices=STAGES);args=ap.parse_args()
    if args.plan or not args.stage:
        print(json.dumps({'stages':STAGES,'required_before_evaluate':'real EOG2020 average_masked and cf_cvg; native NTL aggregation PASS; all15 MCR scenarios complete','native_software':'licensed ArcGISPro3.1.6, InVEST3.20.2, FRAGSTATS4.2.1.612, MSPA2.4, QGIS3.28.2','raw_sources_not_uploaded':True,'run_policy':'Select named stages in order; do not rerun already-frozen native stages during an active queue. Read each receipt; this plan is not proof of completion.'},ensure_ascii=False,indent=2));return
    logdir=work/'pipeline_runs';logdir.mkdir(exist_ok=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');record={'stage':args.stage,'started_utc':stamp,'commands':[],'status':'RUNNING'}
    path=logdir/(stamp+'_'+args.stage+'.json')
    try:
        for command in STAGES[args.stage]:
            assert Path(command[0]).is_file(),command[0]
            proc=subprocess.run(command,cwd=str(ROOT),check=False)
            record['commands'].append({'command':command,'exit_code':proc.returncode})
            path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
            if proc.returncode:raise RuntimeError('Stage failed without substitution: '+str(command))
        record['status']='COMMANDS_COMPLETED_REVIEW_STAGE_RECEIPTS'
    except Exception as err:record.update(status='FAILED',error=str(err));raise
    finally:path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':main()
