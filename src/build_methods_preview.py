"""Internal layout proof using only existing introduction and methods prose.

This is visibly labelled as a process proof, never a completed-paper output.
The scientific readiness gate in build_manuscript.main is not bypassed.
"""
from pathlib import Path
import copy,json,hashlib
from build_manuscript import layout_document,ROOT,WORK

def main():
    source=WORK/'manuscript_content.json';c=copy.deepcopy(json.loads(source.read_text(encoding='utf8')))
    assert c['status']=='DRAFT_RESULTS_PENDING'
    c['title']='生态韧性论文引言与方法排版校样'
    c['subtitle']='过程文件 结果与结论尚未完成'
    c['preview_note']='本校样仅检查已核验的引言、方法、指标表和已有图件的排版；不包含六指标综合评价结果，不作为完整论文交付。'
    blocks=[]
    for block in c['blocks']:
        if block['type']=='heading' and block['text']=='3.1 空间单元与计算范围':
            blocks.append(c['prepared_tables'][0])
        blocks.append(block)
    blocks += [
      {'type':'heading','level':1,'text':'附录 已完成图件的版面检查'},
      {'type':'figure','path':'04_图件/图1_研究范围与土地覆盖.png','caption':'图1 研究范围与2020年土地覆盖','notes':['研究范围为35个乡镇的覆盖部分；边界未替换为完整乡镇或二道绿隔官方规划范围。']},
      {'type':'figure','path':'04_图件/图2_研究技术路线.png','caption':'图2 研究技术路线','notes':['技术路线表示既定研究步骤，不表示全部阶段已完成。']},
      {'type':'figure','path':'04_图件/图6_灰绿配置与热环境.png','caption':'图6 灰绿配置与同期地表温度','notes':['2020年8月3日，每点为1个完整1 km格网；相关分析用于灰绿配置的热环境解释。']}]
    c['blocks']=blocks
    doc=layout_document(c)
    folder=WORK/'method_preview';folder.mkdir(exist_ok=True)
    target=folder/'intro_methods_preview.docx'
    doc.save(target)
    receipt={'status':'PROCESS_LAYOUT_PROOF_ONLY_NATIVE_REVIEW_PENDING','docx':str(target),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'docx_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'complete_paper':False,'new_result_or_conclusion_created':False}
    (folder/'build_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
