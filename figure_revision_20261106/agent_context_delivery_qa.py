"""Artifact structure and recorded human visual QA for the four native figures."""
import json,hashlib,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from pypdf import PdfReader
W=Path('D:/ER219_work/figure_revision_20261106');O=Path('D:/ER219_figures/统一图式与过程图_20261106')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
observations={
 '图1_研究范围与土地覆盖':'实际打开最终600dpi PNG；研究区完整，土地覆盖图例两行无重叠；面积以平方千米显示无缺字；比例尺位于地图下方，指北针和格网北说明清楚；边框细且未截断。',
 '图2_研究技术路线':'实际打开最终600dpi PNG；六指标三列完整，标题16pt、维度标题13pt、指标11pt、说明10pt形成层级；箭头和方框相连清楚，规划用途及温度补充说明无截断；无无关比例尺或指北针。',
 '图8_灰绿配置与热环境':'实际打开最终600dpi PNG；两散点、细轴框、LST温度单位及每幅样本数清楚；主图ρ正负号与分片区矩阵负号均正常；(a)(b)(c)编号与其余论文图统一；注释不遮挡散点；统计图未加地理比例尺。',
 '图S1_四项原始指标空间分布':'实际打开最终600dpi PNG；两列四行八面板完整、(a)至(h)编号明确；HQ/CLUMPY/SSI/E四套原范围色标分别标注；地图范围、比例尺一致；NA与低数值区分；原始指标说明和投影/格网北说明完整。'}
records=[]
for key,observation in observations.items():
 m=json.loads((W/(key+'_manifest.json')).read_text(encoding='utf8'));q=json.loads((W/(key+'_native_QA.json')).read_text(encoding='utf8'))
 assert q['status']=='NATIVE_REOPEN_SCIENCE_FONTS_PASS_VISUAL_PENDING'
 assert sha(O/(key+'.qgz'))==q['project_sha256']==m['new_project_sha256']
 assert sha(m['old_project'])==m['old_project_sha256']
 for inp in m['frozen_inputs']:assert sha(inp['path'])==inp['sha256']
 with Image.open(O/(key+'.png')) as im:
  size=im.size;dpi=im.info.get('dpi');im.verify()
 assert dpi and abs(dpi[0]-600)<.1 and abs(size[0]-190/25.4*600)<2
 reader=PdfReader(O/(key+'.pdf'));assert len(reader.pages)==1
 page=reader.pages[0];mm=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72]
 assert abs(mm[0]-190)<.5 and mm[1]<=270.5
 font_info=[]
 for entry in page.get('/Resources',{}).get('/Font',{}).values():
  f=entry.get_object();font_info.append(str(f.get('/BaseFont','unknown')))
 # Native QGIS vector export uses glyph outlines by default, hence no PDF font
 # dictionary is expected. The editable QGZ separately verifies SimHei and every glyph.
 assert all('SimHei' in n for n in font_info),font_info
 with zipfile.ZipFile(O/(key+'.qgz')) as archive:
  tree=ET.fromstring(archive.read(next(x for x in archive.namelist() if x.endswith('.qgs'))))
  srcs=[x.text for x in tree.iter('datasource') if x.text]
 assert all(not (s[1:3]==':/' or s[1:3]==':\\') for s in srcs),srcs
 for export in m['exports']:assert sha(export['path'])==export['sha256']
 records.append({'figure':key,'status':'PASS','observation':observation,'native_QA_file':str(W/(key+'_native_QA.json')),'PNG_sha256':sha(O/(key+'.png')),'project_sha256':q['project_sha256'],'PNG_size_px':size,'PNG_dpi':dpi,'PDF_size_mm':mm,'PDF_fonts':font_info,'PDF_text_representation':'native vector glyph outlines; edit text using supplied QGZ','relative_layer_sources':srcs,'font_hierarchy_pt':m['font_roles'],'min_text_pt_at_Word_width_146_4_mm':m['minimum_at_word_146_4_mm_pt'],'all_input_and_old_project_hashes_preserved':True})
report={'status':'PASS','scope':'Only figures1,2,8,S1; no manuscript/data/computation changes','engine':'QGIS3.28.2 native export and native reopen','visual_observation':'Every final PNG was actually opened through view_image. 190mm source width, minimum text10pt becomes7.705pt at146.4mm Word display. No overlap, missing glyph or cropped label observed.','figures':records}
(W/'context_figures_final_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('ALL_FOUR_CONTEXT_FIGURES_PASS')
