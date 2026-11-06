from pathlib import Path
import urllib.request, hashlib, json, shutil
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sources = [
 ('Chen2024_Beijing_STOTEN_accepted.pdf','https://eprints.whiterose.ac.uk/id/eprint/204646/1/Manuscript%20final%20%28002%29%20Chen%20et%20al.pdf'),
 ('Na2024_Beijing_MSPA_MCR.html','https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2024.1325880/full'),
 ('Chen2016_Beijing_HQ.html','https://xbna.pku.edu.cn/html/2016-3-553.htm'),
 ('FRAGSTATS_CLUMPY_official.html','https://fragstats.org/index.php/fragstats-metrics/patch-based-metrics/aggregation-metrics/c4-clumpiness-index'),
 ('FRAGSTATS_CLUMPY_formula.jpg','https://fragstats.org/images/doc_images/clumpy_c.jpg'),
 ('ArcMap10_8_CostDistance.html','https://desktop.arcgis.com/en/arcmap/latest/tools/spatial-analyst-toolbox/cost-distance.htm'),
 ('InVEST_HQ_official_current.html','https://storage.googleapis.com/releases.naturalcapitalproject.org/invest-userguide/latest/en/habitat_quality.html'),
 ('InVEST3_20_2_habitat_quality.py','https://raw.githubusercontent.com/natcap/invest/3.20.2/src/natcap/invest/habitat_quality/habitat_quality.py'),
]
dest=BASE/'sources'; dest.mkdir(parents=True,exist_ok=True)
manifest=[]
for name,url in sources:
    row={'name':name,'url':url,'downloaded_utc':datetime.now(timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Research archival verification'}),timeout=60) as r:
            content=r.read()
            row.update(status_code=r.status,final_url=r.url,content_type=r.headers.get('Content-Type'))
        if row['status_code']==200:
            p=dest/name;p.write_bytes(content)
            row.update(path=str(p.relative_to(BASE)),bytes=len(content),sha256=hashlib.sha256(content).hexdigest())
    except Exception as e:row['error']=repr(e)
    manifest.append(row)
    print(name,row.get('status_code'),row.get('bytes'),flush=True)

localroot=ROOT/'生态韧性新研究'/'数据下载_20261020'/'09_InVEST输入与参数'/'01_原文证据'
for name in ['S04_table2_as_published.csv','S04_table3_as_published.csv']:
    p=localroot/name
    if p.exists():
        target=dest/name;shutil.copy2(p,target)
        manifest.append({'name':name,'local_source':str(p),'path':str(target.relative_to(BASE)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'role':'previous transcription rechecked against current publisher HTML'})
(BASE/'219_parameter_source_archive_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
