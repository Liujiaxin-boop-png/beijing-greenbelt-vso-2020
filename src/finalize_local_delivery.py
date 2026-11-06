"""Finalize organized delivery only after scientific, document and Git gates.

Historical failure and access records are preserved. This creates a current
source/continuation ledger without rewriting raw originals or the protocol.
"""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件'
GIT=Path('C:/Program Files/Git/cmd/git.exe')

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')

def main():
    gates={'science':'02_过程文件/evaluation/final_scientific_QA.json',
           'nightlight':'02_过程文件/aggregation/ntl_independent_QA.json',
           'maps':'02_过程文件/map_results/visual_QA.json',
           'word':'02_过程文件/manuscript/final_delivery_QA.json',
           'text_numbers':'02_过程文件/manuscript/final_numeric_text_QA.json',
           'git':'02_过程文件/delivery/git_publication.json'}
    proof={}
    for name,p in gates.items():
        item=read(p)
        assert item['status'] in ['PASS','PASS_FINAL_DELIVERY','PUSH_VERIFIED'],(name,item['status'])
        proof[name]={'path':p,'sha256':sha(ROOT/p),'status':item['status']}
    proposal=ROOT/'01_原始数据/研究依据/北京二道绿隔生态韧性评价_开题报告_组会汇报清稿_20261106.docx'
    expected='e31da3054ae9c7e95d705a9e92718704c9ca5b92ce13ba5059d03f8143519db7'
    assert sha(proposal)==expected
    original=ROOT.parent/'2020年论文成果/05_投稿文件/汇报清稿218_20261106'/proposal.name
    assert sha(original)==expected
    pub=read(gates['git'])
    head=subprocess.check_output([str(GIT),'-C',str(ROOT/'05_代码'),'rev-parse','HEAD'],text=True).strip()
    assert head==pub['local_head']==pub['remote_head']
    assert not subprocess.check_output([str(GIT),'-C',str(ROOT/'05_代码'),'status','--porcelain'],text=True).strip()
    content=read('02_过程文件/manuscript/manuscript_content.json')
    word=ROOT/'03_结果文件/论文'/content['filename']
    assert word.is_file()
    wqa=read(gates['word']);assert sha(word)==wqa['docx_sha256']
    nums=read(gates['text_numbers'])
    assert nums['content_sha256']==sha(ROOT/'02_过程文件/manuscript/manuscript_content.json')
    # Consolidate existing source evidence, distinguishing complete originals
    # from unresampled extraction windows and ancillary data.
    data=read('02_过程文件/delivery/pre_delivery_data_audit.json')
    ntl=read('01_原始数据/EOG2020官方原件/来源与完整性核验.json')
    source_ledger={'status':'COMPLETE_FOR_APPROVED_SIX_INDICATORS','source_ledger':data['source_ledger'],
       'nightlight_actual_originals':ntl,'native_engines':['ArcGIS Pro 3.1.6','InVEST 3.20.2','FRAGSTATS 4.2.1.612','JRC MSPA 2.4','jenkspy 0.4.1','QGIS 3.28.2'],
       'current_QA':proof,'historical_audit':'219_data_audit_final.json is the preserved earlier acquisition snapshot; this file supersedes its missing-NTL status.'}
    save(WORK/'数据审计/220_数据来源与执行总表.json',source_ledger)
    pd.DataFrame(data['source_ledger']).to_csv(WORK/'数据审计/220_数据来源与用途.csv',index=False,encoding='utf-8-sig')
    raster=pd.read_csv(WORK/'数据审计/219_raster_inventory.csv')
    new=[]
    for rec in ntl['files']:
        m=rec['metadata'];stem=Path(rec['download_file']).name[:-3]
        new.append({'file':'01_原始数据/EOG2020官方原件/'+stem,'group':'EOG2020官方原件','bytes':rec['tif_bytes'],
          'sha256':rec['tif_sha256'],'crs':m['crs'],'shape':str(m['shape']),'resolution':str(m['resolution_degrees']),
          'nodata':None,'source_url':rec['source_url'],'role':'original whole global raster; native footprint used for aggregation'})
    pd.concat([raster,pd.DataFrame(new)],ignore_index=True).to_csv(WORK/'数据审计/220_完整栅格索引.csv',index=False,encoding='utf-8-sig')
    old=WORK/'继续执行说明.json';archive=WORK/'project_audit/继续执行说明_缺夜光历史快照.json'
    if old.exists() and not archive.exists():shutil.copy2(old,archive)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary={'status':'PASS_FINAL_DELIVERY','completed_utc':now,'approved_proposal_sha256':expected,
      'manuscript':str(word.relative_to(ROOT)).replace('\\','/'),'docx_sha256':sha(word),'quality_gates':proof,
      'git':pub['repository'],'git_commit':head,'native_GIS_projects':[str(x.relative_to(ROOT)).replace('\\','/')for x in (ROOT/'04_图件').glob('*.qgz')],
      'inventory':'02_过程文件/project_audit/file_inventory.json',
      'limitations':['Static landscape/pressure proxy assessment, not observed recovery dynamics.','Independent numerical QA is not ecological ground validation.','Habitat-specific effective grid domains; no cross-habitat ER ranking.','2026 regular conference call is closed; no actual submission made.']}
    save(WORK/'delivery/final_delivery_receipt.json',summary)
    save(old,{'at_utc':now,'status':'COMPLETED_LOCAL_RESEARCH_AND_DELIVERY','main_blocker':None,
      'approved_method':str(proposal.relative_to(ROOT)).replace('\\','/'),'git':pub['repository'],'pushed_commit':head,
      'final_manuscript':summary['manuscript'],'delivery_receipt':'02_过程文件/delivery/final_delivery_receipt.json',
      'remaining_required':[],'historical_blocker_resolved':'Original same-release EOG brightness/count pair imported, CRC/hash/native alignment and independent aggregation verified.'})
    (WORK/'aggregation/NTL汇总运行说明_完成版.txt').write_text(
       '2020年EOG夜光已完成。\n原件：01_原始数据/EOG2020官方原件。\n'
       '批次：VNL_v21_npp_2020_global_vcmslcfg_c202205302300。\n'
       '输出：03_结果文件/indicators/ntl_by_grid.csv，11479条格网记录。\n'
       '采用原生像元投影后面积交叠权重；cf_cvg>0为质量条件，不作亮度权重；保留有效产品零值。\n'
       '独立复核：02_过程文件/aggregation/ntl_independent_QA.json。\n'
       '旧缺数据说明为执行历史，当前以本文件及交付回执为准。\n',encoding='utf8')
    (ROOT/'成果阅读说明.txt').write_text(
      '北京二道绿隔及周边地区2020年生态韧性研究\n\n'
      '论文：'+summary['manuscript']+'\n'
      '01_原始数据：原始影像、边界、道路、参考文献、软件来源和确认开题报告。\n'
      '02_过程文件：处理数据库、中间栅格、运行记录、独立核验和原生文档渲染。\n'
      '03_结果文件：六指标、综合评分、乡镇统计、对照结果、论文和参数补充材料。\n'
      '04_图件：6幅正文图、补充图S1及可编辑QGIS工程；PNG/PDF/SVG齐备。\n'
      '05_代码：与GitHub一致的分析和制图代码。\n\n'
      '打开04_图件内QGZ时请保留项目目录结构，其图层通过相对路径读取02/03中的数据。\n'
      '所有生态韧性比较限同类生境的有效格网；灰色未评价不等于低值。\n'
      '本成果为2020年历史景观条件评价。投稿正文采用匿名格式；实际作者、单位及基金由作者提交时补入。\n'
      '2026年规划年会常规征稿已结束，未进行投稿或承诺录用。\n\n代码：'+pub['repository']+'\n提交：'+head+'\n',encoding='utf8')
    print(json.dumps({'status':summary['status'],'manuscript':summary['manuscript'],'git_commit':head},ensure_ascii=False))

if __name__=='__main__':main()
