"""Collect exact reviewed artifacts; do not submit or invent author metadata."""
from pathlib import Path
import json, hashlib, shutil, csv

ROOT=Path(__file__).resolve().parents[2]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    c=json.loads((ROOT/'02_过程文件/manuscript/manuscript_content.json').read_text(encoding='utf8'))
    qa=json.loads((ROOT/'02_过程文件/manuscript/final_delivery_QA.json').read_text(encoding='utf8'))
    assert qa['status']=='PASS'
    source=ROOT/'03_结果文件/论文'/c['filename'];assert sha(source)==qa['docx_sha256']
    out=ROOT/'03_结果文件/投稿文件';out.mkdir(exist_ok=True)
    mapping=[(source,out/source.name)]
    for block in c['blocks']:
        if block['type']=='figure':
            p=ROOT/block['path'];mapping.append((p,out/'正文图件'/p.name))
    for p in (ROOT/'03_结果文件/论文补充材料').iterdir():
        if p.is_file():mapping.append((p,out/'方法参数补充材料'/p.name))
    ledger=[]
    for src,dst in mapping:
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():assert sha(dst)==sha(src),'Never overwrite an altered submission copy.'
        else:shutil.copy2(src,dst)
        assert sha(src)==sha(dst)
        ledger.append({'source':str(src.relative_to(ROOT)).replace('\\','/'),'copy':str(dst.relative_to(ROOT)).replace('\\','/'),'sha256':sha(dst)})
    (out/'文件使用说明.txt').write_text(
        '本目录汇集已核验的匿名论文、6幅正文图及方法参数补充材料。\n'
        '本地副本与论文、图件、参数目录内容完全一致，SHA-256见复制核验清单。\n'
        '可编辑地图工程仍在04_图件，统计与分析数据仍在03_结果文件各子目录。\n'
        '作者、单位、基金等个人和机构信息未代填；匿名稿无作者标识。\n'
        '本目录是文件整理，不代表已经投稿或录用。2026年规划年会常规征稿已结束。\n',encoding='utf8')
    with (out/'复制核验清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['source','copy','sha256']);w.writeheader();w.writerows(ledger)
    record={'status':'PASS','copies':ledger,'submission_performed':False}
    (ROOT/'02_过程文件/delivery/submission_package_QA.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'status':'PASS','matching_copies':len(ledger),'package':str(out)},ensure_ascii=False))

if __name__=='__main__':main()
