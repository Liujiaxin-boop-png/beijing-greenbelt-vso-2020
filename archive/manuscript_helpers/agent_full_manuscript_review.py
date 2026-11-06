"""Independent reader review; creates suggestions only."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib

M=Path(r'D:\ER219_work\manuscript')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=M/'完整论文_审阅文本.txt'
main=M/'manuscript_content.json'
issues=[
 {'id':'P01','severity':'较高：结果解释必须修正','location':'4.3末段；摘要及结论第（2）点的对应解释',
  'anchor':'这既说明最低等级清单随评价设定改变，也说明完整比较的覆盖范围有限',
  'problem':'七方案完整域内持续最低格网为0，并不对三类生境都提供清单变化的证据。草地完整域的18格在基线中已经没有最低等级格网；其0值不能解释为最低清单不稳定。',
  'evidence':{'source':'03_结果文件/evaluation/spatial_stability.csv，筛选complete_comparison_set=True后按baseline_class计数',
              'forest_shrub':{'complete_n':137,'baseline_low_n':14,'continuous_low_n':0},
              'grassland':{'complete_n':18,'baseline_low_n':0,'continuous_low_n':0},
              'water_wetland':{'complete_n':89,'baseline_low_n':14,'continuous_low_n':0}},
  'action':'补充完整比较域中基线最低等级的数量；将草地界定为低值持续性尚缺完整比较证据。其他缺方案格网仍单列，不叫不稳定。',
  'suggested_text':'林灌和水体湿地完整比较域各含14个基线最低等级格网，均未在全部方案下保持最低等级；草地完整比较域不含基线最低等级格网，因而不能据此检验草地低值的持续性。完整对照覆盖有限，其余格网记为对照不足，不判为稳定或不稳定。'},
 {'id':'P02','severity':'中等：方法解释补充一句','location':'表1注释或3.2末尾',
  'anchor':'三类生境分别评价',
  'problem':'读者可能以为六项指标全部是各类生境独立计算的专属属性。实际上HQ、CLUMPY、MCR针对目标生境，而NTL、SSI、E/(E+C)来自共同方格景观；E包含全部四类生态空间。各类归一化不同并不能使共同原始数据成为不同生态过程的独立观测。',
  'evidence':{'source':'表1、six_indicator_records.csv及已冻结218口径；未改变指标'},
  'action':'用一句话区分生境专属指标与方格共同环境指标，配合现有不跨生境比较声明。',
  'suggested_text':'HQ、CLUMPY和MCR按目标生境计算；NTL、SSI与E/(E+C)表征方格共同的活动压力和灰绿格局，在各类生境有效样本内分别标准化。'},
 {'id':'P03','severity':'中等：删除未经检验的空间关系','location':'4.1第二段',
  'anchor':'两镇均存在高低得分相邻或混合的状况',
  'problem':'均值和镇内标准差只能支持内部离散程度，不能单独证明高低格网相邻；现有文字没有给出邻接判别或局部空间统计。',
  'evidence':{'source':'township_results.csv只提供均值/标准差/覆盖；本审阅不把视觉印象当邻接检验'},
  'action':'直接写内部差异，不新增空间统计，也无需改方法。',
  'suggested_text':'两镇有效格网的得分差异较大，单一镇域均值会遮蔽局部差异。'},
 {'id':'P04','severity':'中等：限定敏感性结论的比较范围','location':'4.3首句及结论第（2）点',
  'anchor':'土地覆盖底图和生态空间口径对评分的影响最为突出',
  'problem':'“最为突出”容易覆盖逐项删除等全部检验；水体湿地删除E的MAE为0.379，高于WorldCover的0.339。此外各对照的共同有效域不同，结论应限定于本轮主数据与参数对照、各自配对范围。',
  'evidence':{'source':'paired_sensitivity.csv：water_wetland/omit_E_fraction=0.379309；worldcover=0.338528；各方案paired_area_m2不同'},
  'action':'保留有用的规划发现，去掉全局比较措辞并点明配对域。',
  'suggested_text':'在各方案与基线的共同有效域内，土地覆盖产品与生态空间口径对照产生的得分差，明显大于本轮源地阈值与道路阻力对照。'},
 {'id':'P05','severity':'中等：规划贡献用语收紧','location':'引言第三段末句',
  'anchor':'为绿隔生境维护、连接改善及修复方案比选提供依据',
  'problem':'现有对照是数据和计算设定变化，并未模拟具体修复备选方案及成效。“方案比选”容易让读者以为已比较规划干预方案。后文前期筛查定位更准确。',
  'evidence':{'source':'3.4列出的六项主对照均非工程干预方案'},
  'action':'与摘要及讨论的前期筛查定位一致，不承诺未完成的干预效果分析。',
  'suggested_text':'为绿隔生境维护、斑块联系检查及修复前现状核查提供依据。'},
 {'id':'P06','severity':'中等：参数文献适配解释','location':'3.4源阈值句；附表S3',
  'anchor':'源地阈值另取≥35 ha与>100 ha[2,24,27]',
  'problem':'35 ha引文是城市绿地面积与鸟类多样性的跨研究量级先例，并非本地MSPA核心连通块阈值；100 ha来自原框架源地尺度。直接并列容易读成两者都已对北京核心源地校准。',
  'evidence':{'source':'R27全文第10页及219_reference_inventory_verified.json；R02源地面积阈值说明'},
  'action':'正文一句或附表注交代阈值对照的原始对象和用途；数值与运行不改。',
  'suggested_text':'35 ha参照城市鸟类研究的绿地面积量级[27]，>100 ha参照原框架源地尺度[2]，二者仅用于检查源地规模设定的敏感性。'},
 {'id':'P07','severity':'轻微：引用精确性','location':'引言第二段关于数量—配置共享信息的句子',
  'anchor':'综合得分可能重复表达同一空间特征[5–6]',
  'problem':'[5]直接讨论景观指标表现与面积混杂；[6]主要提供CLUMPY在红树林研究中的应用先例，不是综合指数重复计量的直接依据。',
  'evidence':{'source':'R05指标评价论文；R06官方全文Methods/Biophysical variables/Habitat fragmentation及已核证据表'},
  'action':'这句话只引[5]；[6]保留在聚集度指标采用先例处即可。','suggested_text':'部分景观指标同时包含生境数量和配置的信息，综合得分可能重复表达同一空间特征[5]。'},
 {'id':'P08','severity':'轻微：面向规划读者的首次术语解释','location':'摘要“源汇距离”和结论第（3）点',
  'anchor':'源汇距离和生态空间比例与夏季地表温度分别呈正、负相关',
  'problem':'摘要中“源汇”尚未定义，规划实务读者可能误解为生态源地之间的距离，与MCR混淆。',
  'action':'摘要首次出现改为建设空间至最近生态空间的平均距离，正文继续沿用已定义SSI。',
  'suggested_text':'建设空间至最近生态空间的平均距离与夏季地表温度呈正相关，生态空间比例与其呈负相关。'},
 {'id':'P09','severity':'可选：标题边界一致','location':'题目',
  'anchor':'北京二道绿隔生态韧性评价与管护启示',
  'problem':'正文清楚说明包含二道绿隔周边，且非官方规划全域；标题可同样保留“及周边”以减少独立检索时的范围误读。',
  'action':'若字数允许，加入及周边；正文现有范围说明保留。','suggested_text':'北京二道绿隔及周边生态韧性评价'},
]
report={'created_utc':datetime.now(timezone.utc).isoformat(),
 'status':'READ_ONLY_PLANNING_AND_SCIENTIFIC_WORDING_REVIEW',
 'source':{'text':str(source),'text_sha256':sha(source),'main_json':str(main),'main_json_sha256_at_review':sha(main)},
 'scope':'全文逻辑、规划用途、科学推论边界与关键引用匹配；不重复独立全量数值QA，不修改主稿。',
 'overall':'全文已经形成面向读者的论文逻辑，主线清晰，规划用途落实到格网初筛、分项核查和乡镇管护，未见需要重构既定六指标方法的问题。P01应在定稿前修正；P02—P06以短句收紧或说明即可，不需增加实验。',
 'strengths':['引言三段分别交代现实问题、文献路径与应用缺口、本文回应，逻辑较前期清楚。',
              '不把熵权称为因果贡献，不跨三类生境排列综合值，主动报告有效域。',
              '结果有具体乡镇、实际覆盖与内部差异，讨论能对应生境维护、联系核查和灰绿配置。',
              '明确2020年历史基线、35乡镇部分范围、官方规划边界差别；没有把单期评价写成政策净效应。',
              '正文使用研究叙述而非进度汇报语气，既定计算已完成与科学解释边界区分清楚。'],
 'issues':issues,
 'verified_no_change_needed':[{'item':'Feng出版年','decision':'继续引用2024年，不改成2025。',
    'official_url':'https://www.sciencedirect.com/science/article/pii/S2210670724007571',
    'evidence':'出版社页标明Volume116,1December2024,105933；此前本地PDF与Crossref已一致。'},
    {'item':'CLCD数据版本','decision':'Zenodo8176941、版本1.0.2与实际原始文件对应；正文正确。'},
    {'item':'软件方法','decision':'3.1.6实际Pro版本及29—31官方工具引用准确；新32jenkspy0.4.1与最终分类回执一致。'},
    {'item':'NTL零值','decision':'正文“有效观测支持下的产品零值”合适；附表进一步说明包含背景处理零。'},
    {'item':'三类生境比较','decision':'现有分别归一、赋权、分级且不横向排名的声明应保留。'}],
 'main_file_modified':False,'calculations_rerun':False,
 'not_assessed':'未据此宣称期刊分区/高被引/会议仍可投稿；视觉版式由另一轮原生渲染审查。'}
j=M/'219_全文独立规划审阅.json';t=M/'219_全文独立规划审阅.txt'
j.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['全文独立科学表述与规划读者审阅',report['overall'],'']
for x in issues:
 lines += [x['id']+'｜'+x['severity'], '位置：'+x['location'], '问题：'+x['problem'], '建议：'+x['action'], '可替换文字：'+x['suggested_text'],'']
lines+=['已核且无需更改：Feng卷年2024；CLCD实际8176941版本1.0.2；Pro3.1.6官方引用；NTL产品零值语义；三类生境独立评价边界。','本审阅不修改主稿，不重算生产数据。']
t.write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'json':str(j),'text':str(t),'issues':len(issues),'major':'P01'},ensure_ascii=False))
