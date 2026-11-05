"""Replace inline formula notation with editable equation blocks; no method change."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]

def main():
    path=ROOT/'02_过程文件/manuscript/manuscript_content.json'
    c=json.loads(path.read_text(encoding='utf8'))
    assert c['status']=='DRAFT_RESULTS_PENDING'
    if any(b.get('formula_id') for b in c['blocks']):print('ALREADY_STRUCTURED');return
    out=[]
    for b in c['blocks']:
        text=b.get('text','')
        if b['type']=='paragraph' and text.startswith('评价从脆弱性'):
            b['text']='评价从脆弱性、敏感性和自组织三个维度展开[2]。三者分别对应生态系统受扰时容易受损的条件、景观联系对扰动的响应条件，以及生态空间维持内部调节的条件。每个维度选取两项指标，先独立计算，再同向化综合（表1）。'
        if b['type']=='paragraph' and text.startswith('（1）生境质量。'):
            b['text']=text.replace('模型按Q=H[1−D^2.5/(D^2.5+k^2.5)]计算','模型按式（1）计算')
            out.extend([b,{'type':'equation','formula_id':'HQ','number':1}]);continue
        if b['type']=='paragraph' and text.startswith('在各类生境内，用基线'):
            out.append({'type':'paragraph','text':'在各类生境内，用基线及预设对照实际参与评分的观测值共同确定极差端点，统一标准化参照。正向指标按式（2）计算，负向指标取1−z。以基准有效格网计算熵权[2]，按式（3）—（5）估计指标权重，再按式（6）线性合成生态韧性指数。恒定指标的信息离散度取0。'})
            for n,key in enumerate(['standardize','proportion','entropy','weight','ER'],2):out.append({'type':'equation','formula_id':key,'number':n})
            out.append({'type':'paragraph','text':'式中，i表示格网，j表示指标，n为该类生境的基准有效格网数，z为同向标准化值，p为计算熵值的指标占比，e为熵值，w为权重。权重反映样本中的信息离散程度。三维得分分别按维度内权重归一后计算，均以高值为有利。'})
            out.append({'type':'paragraph','text':'综合指数保留连续值，并参照自然断点五级显示方法[18]，使用QGIS 3.28.2对各类基线分别拟合一次阈值，所有对照沿用。乡镇统计同时报告有效覆盖比例、面积加权均值、内部标准差及最低等级格网覆盖面积，将综合水平与具体短板位置对应。维度得分较低的项目用于定位相对短板，并结合单项图解释。'})
            continue
        out.append(b)
    c['blocks']=out;c['typesetting_revision']='Editable OMML equations; compact duplicated dimension prose; formulas, coefficients and scoring unchanged.'
    path.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf8');print('SIX_EDITABLE_EQUATION_BLOCKS_PREPARED')

if __name__=='__main__':main()
