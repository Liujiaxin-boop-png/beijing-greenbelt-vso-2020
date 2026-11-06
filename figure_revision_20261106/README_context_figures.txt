图1、图2、图8、补充图S1的统一图式

绘图环境：本机 QGIS 3.28.2，SimHei/黑体（C:/Windows/Fonts/simhei.ttf）。
运行入口：F:/Program Files/QGIS 3.28.2/bin/python-qgis.bat
图宽统一190 mm；字号来自同目录 figure_style.json。600 dpi PNG、矢量PDF/SVG及可编辑QGZ另存到：
D:/ER219_figures/统一图式与过程图_20261106

重新生成：以QGIS原生Python执行 agent_context_figures.py。
原生复核：以QGIS原生Python执行 agent_context_verify.py。
交付结构复核：以本机Python3.12执行 agent_context_delivery_qa.py。
agent_context_final_labels.py 是本轮一次性分图括号修正的记录；正式生成器已包含括号格式，重做时无需再执行该一次性脚本。

QGZ图层为相对路径。打开工程后，在“项目→布局”中编辑标题、文字、图例、边框、比例尺和散点图元。
请与研究项目的02_过程文件、03_结果文件一并保留目录结构，勿只移动QGZ而丢失其数据源。
PDF/SVG使用原生矢量字形轮廓以防字体替换；需要更改文字时修改QGZ再导出。

科学内容保持：不修改空间数据、连续得分、分级、指标公式、相关系数和样本。
图8保留2×1268个真实点，不抖动、不新拟合、不增加显著性；原生QGS布局坐标以六位有效数字保存，重开最大0.0005 mm舍入误差，小于600dpi下0.012像素，源数据数值完全不变。
补充图S1保留8个原指标面板、各原范围色标和NA，独立核查8×2478个字段值。
核验文件：D:/ER219_work/figure_revision_20261106/context_figures_final_QA.json。

字体注意：SimHei不含上标²和数学负号U+2212。面积单位使用“平方千米”，负数用ASCII“-”；数值含义不变。
