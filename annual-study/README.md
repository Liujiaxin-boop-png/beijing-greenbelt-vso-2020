# 北京二道绿隔 2015—2025 年年度生态韧性研究代码

本目录补充仓库早期的 2020 年截面计算，收录年度论文实际使用的模型计算、格网汇总、机制检验、镇街分型和制图源程序。GIS、遥感产品、已完成的面板与未发表稿件由资料持有人另行提供。

## 三种起点

1. **复核发表用得分**。先取得同一次计算的 200 m、500 m 和 1 km 六指标表。在本目录执行以下命令。程序用 Python 3.12 标准库从三表的六列原值重建归一化、固定熵权和全部 500 m 格网年度得分，逐列与原表核对。输出须指向新的目录。

       python -B "entrypoints/新手辅助程序/rebuild_500m_panel.py" --source "D:/data/core" --out "D:/score_check_01"

2. **从遥感与道路重建指标**。运行 `python setup_study.py --workspace D:/greenbelt_lab`，把实际源代码按原工程层级部署到空目录。将许可数据、边界和本人工程归档复制进对应的数据目录。使用 Python 3.12 与 numpy、pandas、scipy、shapely、rasterio、geopandas、exactextract、pyogrio、tifffile、requests。InVEST 3.20.2 计算生境质量，道路栅格化使用 ArcPy，地图版式使用 ArcMap Desktop 10.8。软件安装目录可通过 `--software software-paths.json` 重映射，例如一个 JSON 对象把 `D:/Apps/InVEST-3.20.2/invest.exe` 映射到本机同版本程序。以下 PowerShell 示例在部署目录中运行，独立练习输出使用另一个新英文路径。年度模型入口含归档对照，需要既有案例的栅格与参数用于逐像元核验。

       Set-Location D:/greenbelt_lab
       python -B "entrypoints/基础实验/从原始数据重跑年度模型.py" prep --year 2020 --root D:/run_annual_01
       foreach ($yr in 2015..2025) { python -B "entrypoints/基础实验/从原始数据重跑年度模型.py" all --year $yr --root D:/run_annual_01; if ($LASTEXITCODE) { throw "year $yr failed" } }
       python -B "entrypoints/基础实验/从原始数据重跑年度模型.py" score --root D:/run_annual_01

   使用 .NET Framework C# 编译器，以 `csc /optimize+ /target:exe /out:Landscape.exe Landscape.cs` 和 `csc /optimize+ /target:exe /out:TwoSource.exe TwoSource.cs` 分别在下表的源码目录生成同名程序，向运行器提供年度像元统计及双源最短成本算法。需要重建原生道路/地类窗口时先参见 `work/annual_actual/years、hq` 下生产脚本。各入口对缺失的输入会终止，禁止将缺失填零。

3. **复算变化机制与政策对照**。进入部署目录，令 `$archive` 为持有的年度归档目录。运行 `python -B "entrypoints/新机制复现工具/隔离复算.py" --archive "$archive" --task D --dest D:/stage_01` 可从逐格年表复算两个转折。将任务改为 A、B、C 分别核对外部观测、土地转换与生境质量分解、镇街对照；Map 使用 ArcMap。可用 `--observations`、`--panel` 提供自算资料。`entrypoints/复算镇街分型与政策对照.py --help` 列出复算政策对照、分类和替代权重的参数。

## 主计算脚本

下列路径相对于部署目录，仓库里相应文件位于 `layout/`。

| 任务 | 源文件与依赖 |
|---|---|
| 固定研究边界、多尺度交叠、年度场 | work/shp11/core/domain.py；work/annual_actual/analysis/surfaces.py、Landscape.cs；work/annual_actual/hq/sensitivity_3threat.csv |
| 生态源地、阻力与敏感性 | work/feng_round2/source_mcr/prepare.py、sources.py、TwoSource.cs；work/annual_actual/mcr_checks/ |
| 六指标、固定熵权和格网年度表 | work/shp11/core/compute.py、compare_six.py、swap_slots.py、hq_attribution.py；work/shp11/method_clarify/entropy_reference_scale.py |
| 镇域相交、分型与四个镇街 | work/shp11/towns/territories.py、summarize_towns.py、classify.py、case_patch_evidence.py、hq_inputs.py |
| 年际机制 | results 下“机制验证_三阶段”的 A、B、C、D 四组；“高韧性空间因素_2020实证/02_过程”下的下载和逐格统计脚本 |
| ArcMap地图、历史版式 | work/shp11/maps/，work/cases_local_1111/maps/，work/shp11/readability/ 的主图及附图比例尺；code/arcmap_hi_20261106/run_native.ps1 和 NativeLayout.cs；案例工程与图层另需取得 |
| 三张示意图、三张数据图 | results 下“学位论文图文完善_20261112/工作底稿/diagrams.py、export_fig.ps1”和“figs/构建可编辑统计图.py、原生Excel导出.ps1、统计图栅格化.py”。数据图读取机制结果 CSV，Excel 原生导出；示意图生成可编辑 PPTX。两份本地标注文件见下文。 |

## 输入及软件条件

- 取得归档中同一版本的 CLCD 2015—2025 原生研究窗口、DEM、历史 OSM 主要道路、同一研究边界及镇界。边界为研究组自公开图重建的矢量。受控底图、原始观测及各年度的裁剪/投影记录须依照资料许可获取。研究边界输入置于 project/GIS数据/GIS数据/二道绿隔范围.shp，另保留同位置匹配的侧车文件和 0219/北京全域.shp。
- 植被数据为 Terra MOD13Q1.061；建成为 Esri Land Cover v003；夜光为 OpenGeoHub v0.4；人口为 WorldPop Global2 R2025A v1。年份可用范围、质量掩膜、原生像元和同域规则见对应抓取及逐格脚本。[CLCD](https://zenodo.org/records/18180184) · [MOD13Q1](https://doi.org/10.5067/MODIS/MOD13Q1.061) · [Esri Land Cover](https://livingatlas.arcgis.com/landcover/) · [夜光](https://zenodo.org/records/17294744) · [WorldPop](https://doi.org/10.5258/SOTON/WP00839)
- 复制已有 ArcMap 输出需要相对链接的 MXD 和本机许可；重制地图另外需要只读模板、图层 GDB 与布局配置，例如 context_fig1.json（input_template 指向可打开的 .mxd）、各图 fig*.json 与子图数据。安装脚本只写全新目录。运行旧生产脚本前应使用独立的数据副本。
- 六幅新图使用机制 CSV 以及留在项目资料包的 diagram_labels.local.json（放在 diagrams.py 旁）和 chart_checks.local.json（放在构建可编辑统计图.py 旁）。二者保存未发表的个案文字、数值或核对基准。使用者可在本地换成自己的对照值与图注，需要 Excel、PowerPoint、xlsxwriter、python-pptx、Pillow 和 pypdfium2。
- 索引全部源程序可运行 `python setup_study.py --list`。两个代码框架位于仓库同一分支，请按年度路径进入操作。
