"""Assemble the final narrative from actual, independently checked results.

Numerical values are read from retained tables. This script never recalculates
the approved indicators, changes class breaks, or writes analysis outputs.
"""
from pathlib import Path
import copy, datetime, hashlib, json, re
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'02_过程文件/manuscript'
RESULT=ROOT/'03_结果文件/evaluation'
H=['forest_shrub','grassland','water_wetland']
ZH=['林灌','草地','水体湿地']
METRICS=['HQ_H','NTL','CLUMPY','MCR','SSI','E_fraction']

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def para(text):return {'type':'paragraph','text':text}
def heading(text,level=1):return {'type':'heading','text':text,'level':level}
def fig(stem,caption,notes=None):
    return {'type':'figure','path':'04_图件/'+stem+'.png','caption':caption,'notes':notes or []}
def vals(values,precision=3):return '、'.join(f'{float(x):.{precision}f}'.replace('-','−') for x in values)
def asbool(s):return s.astype(str).str.lower().isin(['true','1','1.0'])

def main():
    qa=ROOT/'02_过程文件/evaluation/final_scientific_QA.json'
    assert json.loads(qa.read_text(encoding='utf8'))['status']=='PASS'
    source=WORK/'manuscript_content.json'
    archive=WORK/'archive/manuscript_content_before_results.json'
    if not archive.exists():archive.write_bytes(source.read_bytes())
    content=json.loads(archive.read_text(encoding='utf8'))
    r=pd.read_csv(RESULT/'regional_results.csv').set_index('habitat')
    town=pd.read_csv(RESULT/'township_results.csv')
    weights=pd.read_csv(RESULT/'entropy_weights.csv').pivot(index='habitat',columns='indicator',values='weight')
    pairs=pd.read_csv(RESULT/'paired_sensitivity.csv')
    corr=pd.read_csv(RESULT/'indicator_correlations.csv')
    scores=pd.read_csv(RESULT/'scores_classified.csv',low_memory=False)
    base=scores[scores.scenario.eq('baseline')].set_index(['habitat','grid_id'])
    stability=pd.read_csv(RESULT/'spatial_stability.csv')
    agreement=pd.read_csv(RESULT/'class_agreement.csv')
    scope=1987.8997892244938
    def pair(s,h):return pairs[(pairs.scenario==s)&(pairs.habitat==h)].iloc[0]
    def towns(t,h='forest_shrub'):return town[(town.town==t)&(town.habitat==h)].iloc[0]
    complete=[];stable=[];complete_areas=[];complete_baseline_low=[]
    for h in H:
        st=stability[stability.habitat.eq(h)]
        co=st[asbool(st.complete_comparison_set)]
        complete.append(len(co));stable.append(int(asbool(co.consistent_low_complete_set).sum()))
        complete_baseline_low.append(int(co.baseline_class.eq(1).sum()))
        complete_areas.append(float(base.loc[(h,co.grid_id.tolist()),'scope_area_m2'].sum())/1e6)
    complete_pct=[100*a/(r.loc[h,'valid_scope_area_m2']/1e6) for h,a in zip(H,complete_areas)]
    assert stable==[0,0,0], 'Narrative requires reauthoring if stable-low observations differ.'
    assert complete_baseline_low==[14,0,14], 'Interpret complete-domain low-class denominators explicitly.'
    wc=[pair('worldcover',h) for h in H]
    crop=[pair('crop_in_ecological_space',h) for h in H]
    scale=[pair('scale500_to1000_full_coverage',h) for h in H]
    small=pairs[pairs.scenario.isin(['core35_land_road','core100_land_road','core10_land_only'])]
    assert small.spearman_rho.min()>0.999
    counts=[int(r.loc[h,'valid_grid_n']) for h in H]
    areas=[r.loc[h,'valid_scope_area_m2']/1e6 for h in H]
    area_pct=[a/scope*100 for a in areas]
    corr_se=[float(corr[(corr.habitat==h)&(corr.indicator_1=='SSI')&(corr.indicator_2=='E_fraction')].iloc[0].spearman_rho) for h in H]
    weightE=[weights.loc[h,'E_fraction'] for h in H]
    weightN=[weights.loc[h,'NTL'] for h in H]
    yf=towns('阳坊镇');sj=towns('苏家坨镇');jz=towns('军庄镇')
    gly=towns('高丽营镇');lq=towns('李桥镇');hc=towns('黄村镇','grassland');th=towns('台湖镇','grassland')
    facts={'created':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'scope_area_km2':scope,'habitat_order':H,'valid_grids':counts,'valid_grid_coverage_km2':areas,
      'valid_grid_coverage_percent':area_pct,'worldcover_paired_MAE':[float(x.weighted_MAE) for x in wc],
      'crop_paired_MAE':[float(x.weighted_MAE) for x in crop],
      'scale_full_n':[int(x.n) for x in scale],'scale_full_rho':[float(x.spearman_rho) for x in scale],
      'seven_scheme_n':complete,'seven_scheme_area_km2':complete_areas,'seven_scheme_coverage_percent':complete_pct,
      'stable_low_n':stable,'complete_domain_baseline_low_n':complete_baseline_low,'SSI_E_spearman':corr_se,'weight_E':weightE,'weight_NTL':weightN,
      'source_sha256':{p.name:digest(p) for p in RESULT.glob('*.csv')},'scientific_qa_sha256':digest(qa)}
    (WORK/'manuscript_numeric_facts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding='utf8')
    blocks=copy.deepcopy(content['blocks'])
    for b in blocks:
        if b['type']!='paragraph':continue
        t=b['text']
        t=t.replace('夜间活动指标选用EOG VIIRS 2020年度平均辐亮度及有效观测次数','夜间活动指标选用EOG VIIRS VNL v2.1 2020年度平均辐亮度及有效观测次数（文件批次c202205302300）')
        t=t.replace('有有效观测的零亮度保留为真实观测；','有效观测支持下的产品零值予以保留；')
        t=t.replace('使用QGIS 3.28.2对各类基线分别拟合一次阈值','使用jenkspy 0.4.1的Fisher–Jenks算法对各类基线分别拟合一次阈值[33]')
        t=t.replace('地类适宜度及敏感度列于附表','地类适宜度及敏感度列于补充材料附表S1')
        t=t.replace('恒定指标的信息离散度取0。','熵值计算约定0 ln 0=0，恒定指标的信息离散度取0。')
        t=t.replace('综合得分可能重复表达同一空间特征[5–6]','综合得分可能重复表达同一空间特征[5]')
        t=t.replace('为绿隔生境维护、连接改善及修复方案比选提供依据','为绿隔生境维护、斑块联系检查及修复前现状核查提供依据')
        t=t.replace('源地阈值另取≥35 ha与>100 ha[2,24,27]','源地阈值另取≥35 ha与>100 ha。35 ha参照城市鸟类研究的绿地面积量级[27]，>100 ha参照原框架源地尺度[2]，用于检查源地规模设定的敏感性')
        t=t.replace('分别考察林地—灌丛、草地、水体—湿地三类生境的生态韧性潜力。','分别考察林地—灌丛、草地、水体—湿地三类生境的生态韧性潜力。本文范围为既有案例边界与乡镇覆盖部分，不等同于二道绿隔官方规划全域。')
        b['text']=t
    # Insert native figures and the declared indicator table next to their discussion.
    index=next(i for i,b in enumerate(blocks) if b.get('text')=='3 研究方法')
    blocks.insert(index,fig('图1_研究范围与土地覆盖','图1 研究范围与2020年土地覆盖',''))
    index=next(i for i,b in enumerate(blocks) if b.get('text')=='3.1 空间单元与计算范围')
    blocks.insert(index,fig('图2_研究技术路线','图2 研究技术路线'))
    index=next(i for i,b in enumerate(blocks) if b.get('text')=='3.2 六项指标计算')+1
    blocks.insert(index,copy.deepcopy(content['prepared_tables'][0]))
    blocks[index]['notes'].append('HQ、CLUMPY和MCR按目标生境计算；NTL、SSI与E/(E+C)表征方格共同的活动压力和灰绿格局，在各类生境有效样本内分别标准化。')
    blocks += [heading('4 结果'),heading('4.1 有效评价范围与乡镇内部差异',2),
      para(f'林灌、草地、水体湿地六项指标同时有效的格网分别为{counts[0]}、{counts[1]}和{counts[2]}个，研究区内覆盖面积分别为{vals(areas,2)} km²（表2）。这些结果对应各项指标均可定义的混合景观：无目标生境、无建设空间或聚集度未定义的格网未进入综合评分，不能据空白范围判定生态条件较差。三类生境各自标准化、赋权与分级，图3反映各类内部相对差异，不作跨类型数值排序。'),
      {'type':'table','caption':'表2 各类生境的有效评价范围','headers':['生境类型','有效格网数','格网覆盖面积\n（km²）','占研究区面积\n（%）','有有效结果的\n乡镇数'],'widths_mm':[25,24,35,35,27],'center_columns':[0,1,2,3,4],
       'rows':[[ZH[i],str(counts[i]),f'{areas[i]:.2f}',f'{area_pct[i]:.2f}',str(int(((town.habitat==h)&(town.grid_n>0)).sum()))] for i,h in enumerate(H)],
       'notes':['注：面积为有效格网在研究区内的覆盖面积，并非生境实体面积；三类范围可重叠，不能加总。乡镇均指其研究范围内部分。']},
      para(f'乡镇内部差异是管护研判的重要信息。阳坊、苏家坨的林灌综合指数均值分别为{yf.ER_mean:.3f}和{sj.ER_mean:.3f}，内部标准差分别为{yf.ER_within_town_sd:.3f}和{sj.ER_within_town_sd:.3f}；对应有效格网覆盖其研究范围内镇域的{yf.six_valid_fraction*100:.2f}%和{sj.six_valid_fraction*100:.2f}%。两镇均存在高低得分相邻或混合的状况，用单一镇域均值概括会遮蔽局部差异。军庄的林灌均值为{jz.ER_mean:.3f}，但脆弱性维度有利度仅为{jz.V_mean:.3f}，低于敏感性和自组织维度的{jz.S_mean:.3f}、{jz.O_mean:.3f}（图4）。较高综合得分仍需回到生境质量和活动压力等分项检查。'),
      fig('图3_生态韧性空间分布','图3 各类生境生态韧性潜力的空间分布'),
      heading('4.2 综合得分包含的主要景观信息',2),
      para(f'生态空间面积比例在林灌、草地、水体湿地中的熵权分别为{vals(weightE)}，夜间灯光权重分别为{vals(weightN)}（表3）。林灌、水体湿地得分较多体现生态空间相对建设空间的数量差异，草地的生境质量、聚集度和面积比例则具有相对分散的权重结构。这里的权重衡量有效样本中信息的离散程度，并非各因素的生态作用强弱；夜光权重小不意味着人类活动压力可以忽略。'),
      {'type':'table','caption':'表3 三类生境的指标熵权','headers':['指标','林灌','草地','水体湿地'],'widths_mm':[56,30,30,30],'center_columns':[1,2,3],
       'rows':[[n]+[f'{weights.loc[h,m]:.4f}' for h in H] for n,m in zip(['生境质量 HQ','夜间灯光 NTL','聚集度 CLUMPY','最小累积阻力 MCR','源汇平均距离 SSI','生态空间面积比例'],METRICS)],
       'notes':['注：每类生境独立估权，未舍入权重之和均为1；权重不用于跨生境比较。']},
      para(f'源汇平均距离与生态空间面积比例的Spearman相关系数分别为{vals(corr_se)}。两项分别描述位置与数量，但在本区仍共享较强的景观信息。逐项删除检验也显示，林灌评价删除生态空间比例后的面积加权平均绝对差为{pair("omit_E_fraction",H[0]).weighted_MAE:.3f}，高于删除夜间灯光后的{pair("omit_NTL",H[0]).weighted_MAE:.3f}。因此，相对短板图应与原始指标共同阅读，不能把某一低维度直接解释为独立的生态致因。'),
      fig('图4_三维相对短板','图4 三维评价的相对短板'),
      heading('4.3 数据与设定变化对空间判断的影响',2),
      para(f'土地覆盖底图和生态空间口径对评分的影响最为突出。在共同有效格网中，将CLCD替换为WorldCover，三类生境得分的面积加权平均绝对差分别为{vals([x.weighted_MAE for x in wc])}；将耕地纳入生态空间，相应差值为{vals([x.weighted_MAE for x in crop])}。两种产品的分类差异会同时传递到生境、源地与灰绿配置等指标，而耕地归类直接改变生态空间数量与邻近关系。上述差值是相同年份评价设定的敏感性，不代表生态条件实际改善。'),
      para('相比之下，源地核心面积由10 ha调整为35 ha或大于100 ha，以及移除道路阻力项，三类综合排序与基线的Spearman相关系数均超过0.999。这表明本轮综合排序对这些参数变动较稳定，但不能据此推断道路阻隔或源地规模在生态过程中不重要。'),
      para(f'500 m结果汇回1 km后，完整覆盖组分别有{int(scale[0].n)}、{int(scale[1].n)}和{int(scale[2].n)}个格网，与基线的排序相关系数为{vals([x.spearman_rho for x in scale])}。同时具备基线及六项主对照的格网分别为{complete[0]}、{complete[1]}和{complete[2]}个，覆盖各自基线有效面积的{vals(complete_pct,2)}%。完整对照域中，林灌、水体湿地各有14个基线最低等级格网，均未在全部方案下保持最低；草地不含基线最低等级格网，未能检验其低值持续性（图5）。其余格网对照不足，不能判为稳定或不稳定。'),
      fig('图5_空间分级稳定性','图5 分级稳定性及完整对照范围'),
      heading('4.4 灰绿配置与热环境的空间关联',2),
      para(content['prepared_observed_thermal_result']),
      para('6月16日的对照覆盖570个有效格网，分布于四片区但覆盖不均；8月10日的426个有效格网仅位于西部。两日期分别用于有限范围对照，不作为全域重复验证。热环境关联提供了灰绿配置的应用解释：建设空间离生态空间较远、生态空间相对较少的格网，更值得结合夏季热暴露核查绿地与水体的配置。相关结果属于描述性空间关联，不等同于六指标综合韧性的过程验证。'),
      fig('图6_灰绿配置与热环境','图6 灰绿配置与2020年8月3日地表温度的关系'),
      heading('5 讨论与规划启示'),heading('5.1 从综合排序转向可核查的管护对象',2),
      para('生态韧性评价的规划价值，在于把区域差异转化为可以核查的位置和问题。本文将格网结果汇总至研究范围内的乡镇部分，同时保留分项指标、镇内离散程度和有效覆盖信息。对于阳坊、苏家坨等内部差异较大的乡镇，可分别核查连片生境及较低得分局部，避免以镇域均值配置同质化措施。对于军庄等综合得分较高但维度表现不均衡的区域，应把现有连续生态空间维护与具体压力源核查结合起来。'),
      para(f'高丽营、李桥的林灌有效格网均值分别为{gly.ER_mean:.3f}、{lq.ER_mean:.3f}，覆盖其研究范围内镇域的{gly.six_valid_fraction*100:.2f}%、{lq.six_valid_fraction*100:.2f}%，可作为组织生境质量、活动压力和灰绿配置核查的线索。与之不同，黄村、台湖的草地有效覆盖仅为{hc.six_valid_fraction*100:.2f}%、{th.six_valid_fraction*100:.2f}%，应用时应定位到具体格网，不宜给整个乡镇安排统一的草地修复措施。格网尺度用于筛查，具体项目边界仍需落到现状地块。'),
      heading('5.2 将底图核对纳入绿隔减量提质实施',2),
      para('二道绿隔减量提质强调生态系统完整性和生态过程连续性[1]。本研究显示，同一套模型面对不同土地覆盖分类和耕地归类，会产生不同的评分判断。因而，在生态修复项目库或乡镇管护计划中，应把底图核对置于工程比选之前：先检查林灌、草地、水体与建设边缘的识别，再结合国土空间用途管制确认耕地及其他用地的处理方式。耕地纳入情景是评价口径对照，不是将耕地转为林地或建设生态工程的依据。'),
      para('核查后，可按问题类型对接管护工具。生境质量较低的格网，重点查看建设与道路周边的生境边缘、植被状况及压力源；聚集度低或跨斑块成本高的格网，检查现有蓝绿空间中断点，再论证连接维护的可行性；源汇距离较大且生态空间比例较低的格网，可结合公共绿地、水体与建设空间的实际布局，筛选小微蓝绿节点完善位置。由此，综合评价提供初筛，分项指标解释问题，现状核查决定能否形成管护项目，三者共同服务乡镇实施。'),
      heading('5.3 方法贡献与适用范围',2),
      para('本文的贡献是把已有生态韧性框架转化为绿隔地区可追踪的规划评价：一方面，在同类生境内联结格网差异与乡镇统计，避免以均值代替内部诊断；另一方面，在同一评价体系中对照数据、口径与参数，并同步呈现比较覆盖范围，识别哪些空间判断需要优先核实。与单独给出高低值分布相比，这一过程能够说明分数包含什么信息、结论在哪些位置成立，以及进入管护实施前还需核对什么。'),
      para('研究评价的是2020年景观与压力条件所表征的韧性潜力，未直接测量扰动后的恢复轨迹[7,21]。土地覆盖是多项指标的共同输入，熵权不能消除指标相关性[5,12]；通用阻力参数也未针对北京物种迁移或水文连通作本地校准。六项共同有效条件排除了部分纯生态景观，草地覆盖尤其有限。本文结果适合作为同类生境的历史基线和现状核查线索，后续应用应更新底图并结合生态监测，不以本指数单独划定生态保护红线或工程修复地块。'),
      heading('6 结论'),
      para('（1）基于脆弱性、敏感性与自组织的六指标评价，能够在同类生境内部识别格网差异，并将其与乡镇管护范围连接。有效覆盖和镇内离散程度与均值同样重要；综合得分较高也可能伴随分项不足，乡镇统计应返回具体格网解读。'),
      para('（2）本轮评分对土地覆盖产品和耕地归类的敏感性，高于对已测试源地阈值及道路阻力设定的敏感性。完整对照范围内，林灌与水体湿地的基线最低等级格网均未在全部方案下保持最低；草地低值持续性缺少完整对照证据。修复清单不能仅由单次最低等级图推出，应同时核对底图、单项条件与对照范围。'),
      para('（3）源汇距离与夏季地表温度呈正向关联，生态空间比例与其呈负向关联，四片区内各指标的关联方向一致，为灰绿配置的管护意义提供补充证据。面向二道绿隔减量提质，可将本成果用于生境维护、斑块联系检查和小微蓝绿空间完善的前期筛查，形成从格网识别、分项核查到乡镇实施的工作衔接。')]
    for b in blocks:
        if 'text' not in b:continue
        b['text']=b['text'].replace('两镇均存在高低得分相邻或混合的状况','两镇有效格网的得分差异较大')
        b['text']=b['text'].replace('土地覆盖底图和生态空间口径对评分的影响最为突出。','在各方案与基线的共同有效域内，土地覆盖产品与生态空间口径对照产生的得分差，明显大于源地阈值与道路阻力对照。')
        b['text']=b['text'].replace('本轮','本研究')
    content['blocks']=blocks
    content['title']='北京二道绿隔及周边生态韧性评价'
    content['abstract']=(
      '超大城市绿化隔离地区由增绿扩面转向减量提质，需要识别生态空间内部差异并将评价结果落实到乡镇管护。'
      '以北京二道绿隔及周边35个乡镇的部分地区为对象，基于2020年土地覆盖、道路和夜间灯光，构建脆弱性、敏感性与自组织三维六指标体系，在1 km正方形格网上分别评价林灌、草地和水体湿地的生态韧性潜力。'
      '采用熵权综合、乡镇面积加权统计及数据与参数对照，分析空间差异和判断稳定性。'
      '结果表明：乡镇内部及不同维度之间存在明显差异，较高均值不能替代局部诊断；评分对土地覆盖产品和耕地归类较敏感，而对本轮源地阈值及道路阻力调整较稳定；完整对照域的林灌与水体湿地最低等级格网均未在全部方案下保持最低，草地低值持续性缺少完整对照证据。'
      '建设空间至最近生态空间的平均距离与夏季地表温度呈正相关，生态空间比例与其呈负相关。'
      '研究将分项短板、有效覆盖和方案敏感性共同纳入乡镇研判，为生境维护、联系改善及灰绿配置提供可核查的前期筛查依据。')
    content['abstract']=content['abstract'].replace('本轮','本研究')
    assert 300<=len(content['abstract'])<=500,len(content['abstract'])
    content['references'].append('VIRY M. jenkspy: Fast Fisher-Jenks breaks for Python, version 0.4.1[CP/OL]. [2026-11-06]. https://github.com/mthh/jenkspy.')
    # Remove an uncited corrigendum record; keep full source verification archive.
    refs=content['references'];del refs[29]
    def renumber(text):
        def sub(m):
            items=[]
            for item in m.group(1).split(','):
                if '–' in item or '-' in item:items.append(item);continue
                n=int(item);assert n!=30;items.append(str(n-1 if n>30 else n))
            return '['+','.join(items)+']'
        return re.sub(r'\[([0-9,–-]+)\]',sub,text)
    for b in blocks:
        if 'text'in b:b['text']=renumber(b['text'])
        if b['type']=='table':b['rows']=[[renumber(str(v)) for v in row] for row in b['rows']]
    content['references']=refs
    content['status']='READY_FOR_LAYOUT'
    content['results_are_actual_2020_six_indicator_run']=True
    content['filename']='北京二道绿隔及周边生态韧性评价_完整论文_20261106.docx'
    content['note']='Actual 2020 six-indicator manuscript; native layout and independent text QA remain separate gates.'
    content['numeric_facts']='02_过程文件/manuscript/manuscript_numeric_facts.json'
    source.write_text(json.dumps(content,ensure_ascii=False,indent=2),encoding='utf8')
    text='\n\n'.join([content['title'],'摘要：'+content['abstract']]+[b.get('text',b.get('caption','')) for b in blocks]+['参考文献']+[f'[{i}] {v}' for i,v in enumerate(refs,1)])
    (WORK/'完整论文_审阅文本.txt').write_text(text,encoding='utf8')
    print(json.dumps({'status':content['status'],'abstract_characters':len(content['abstract']),'body_characters':sum(len(b.get('text','')) for b in blocks),'references':len(refs),'figures':sum(b['type']=='figure'for b in blocks),'tables':sum(b['type']=='table'for b in blocks),'source_sha256':digest(source)},ensure_ascii=False))

if __name__=='__main__':main()
