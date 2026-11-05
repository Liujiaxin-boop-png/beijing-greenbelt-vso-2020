"""Assemble evidence-backed prose already available; keep the paper incomplete.

This preparatory file lives in process storage. It must be completed from real
six-indicator results and independently reviewed before Word layout is allowed.
"""
from pathlib import Path
import json,re,hashlib

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/manuscript'

def main():
    intro=json.loads((WORK/'agent_intro_and_evidence.json').read_text(encoding='utf8'))
    methodfile=WORK/'219_研究区域数据与方法正文_草稿.txt'
    blocks=[{'type':'heading','level':1,'text':'1 引言'}]
    blocks += [{'type':'paragraph','text':p['text']} for p in intro['intro_draft']]
    for para in methodfile.read_text(encoding='utf8').split('\n\n'):
        para=para.strip()
        if not para:continue
        lines=para.splitlines()
        if re.match(r'^\d(?:\.\d)*\s',lines[0]):
            heading=lines.pop(0);level=2 if re.match(r'^\d\.\d',heading) else 1
            blocks.append({'type':'heading','level':level,'text':heading})
        if lines:blocks.append({'type':'paragraph','text':'\n'.join(lines)})
    indicator_table={'type':'table','caption':'表1 三维生态韧性评价指标','headers':['维度','指标','方向','表征内容与测算','依据'],'widths_mm':[19,28,10,69,20],
      'rows':[
        ['脆弱性','生境质量 HQ','+','目标生境内部的InVEST质量均值，表征现有生态基础。','[2,10,23]'],
        ['脆弱性','夜间灯光 NTL','−','年度夜间辐亮度的原生像元面积加权均值，表征夜间活动压力。','[9,17]'],
        ['敏感性','聚集度 CLUMPY','+','FRAGSTATS类级同类像元聚集指标，表征局部连片条件。','[5,6,11]'],
        ['敏感性','最小累积阻力 MCR','−','到其他同类源斑块的最低累积成本，表征跨斑块联系条件。','[2,24,25,29]'],
        ['自组织','源汇平均距离 SSI','−','建设空间至最近生态空间的面积加权距离，表征灰绿邻近关系。','[2]'],
        ['自组织','生态空间面积比例','+','E/(E+C)，表征生态空间相对建设空间的数量配置。','[4]']],
      'notes':['注：方向以生态韧性评价值为参照。E为林灌、草地、水体和湿地，C为不透水面；三类生境分别评价。三维得分均同向化为高值有利。']}
    # Keep tables and source notes separately until narrative ordering is reviewed.
    refs=(ROOT/'01_原始数据/参考文献/参考文献表_推荐引用.txt').read_text(encoding='utf8')
    refs=[re.sub(r'^\[\d+\]\s*','',x.strip()) for x in refs.split('\n\n') if x.strip()]
    refs=[x.replace(' 本轮运行版本3.20.2另在软件表记录。','').replace(' 权重、聚合及敏感性子页分别标注2020-12-01更新；附存OECD/EU/JRC 2008手册不冒充2025网页。','') for x in refs]
    content={'status':'DRAFT_RESULTS_PENDING','title':'北京二道绿隔生态韧性评价与管护启示','subtitle':'——基于2020年景观条件的三维评价','abstract':'','keywords':['生态韧性','城乡交错区','景观评价','二道绿隔','乡镇管护'],
      'blocks':blocks,'prepared_tables':[indicator_table],
      'prepared_observed_thermal_result':'2020年8月3日，在同时含有建设和生态空间的1268个有效格网中，源汇平均距离与地表温度呈正相关，生态空间面积比例与地表温度呈负相关，Spearman相关系数分别为0.506和−0.574。四片区的关联方向一致，前者相关系数为0.411—0.686，后者为−0.749—−0.535（图6）。这表明灰绿空间的邻近关系与数量配置均具有热环境解释意义。',
      'thermal_evidence':['03_结果文件/thermal_association/graygreen_LST_spearman_descriptive.csv','02_过程文件/thermal_association/association_receipt.json'],
      'required_before_ready':['Real EOG2020 average_masked and original cf_cvg successfully aggregated.','All 15 native MCR scenarios and grid aggregation complete.','Actual six-indicator evaluation, paired sensitivities, classification and township statistics.','Independent final_scientific_QA.json PASS.','Result maps exported, reopened in native QGIS and visually reviewed.','Write abstract, results, discussion and conclusions from actual evidence; review claims and citation numbering.'],
      'scientific_qa_receipt':'02_过程文件/evaluation/final_scientific_QA.json','results_are_actual_2020_six_indicator_run':False,'references':refs,
      'source_hashes':{'methods_draft':hashlib.sha256(methodfile.read_bytes()).hexdigest(),'intro_evidence':hashlib.sha256((WORK/'agent_intro_and_evidence.json').read_bytes()).hexdigest()},
      'note':'This is process material, not a completed manuscript or a substitute for absent results.'}
    dest=WORK/'manuscript_content.json'
    assert not dest.exists(),'Do not overwrite edited manuscript content.'
    dest.write_text(json.dumps(content,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'status':content['status'],'path':str(dest),'paragraph_blocks':len(blocks),'references':len(refs),'word_created':False},ensure_ascii=False))

if __name__=='__main__':main()
