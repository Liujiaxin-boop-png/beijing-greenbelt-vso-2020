# 北京二道绿隔及周边地区 2020 年生态韧性评价

本仓库保存 2026 年 11 月 6 日确认的开题报告所对应的计算代码。
研究采用脆弱性—敏感性—自组织框架，每个维度两项指标：生境质量、年度夜间灯光、聚集度、最小累积阻力、源汇平均距离和生态空间相对面积。

## 执行状态

正在执行。已完成原生 HQ、CLUMPY、MSPA、欧氏距离、灰绿配置及热环境分析；15 个 MCR 情景、181 组原生计算全部完成，9 组源地阈值单调性检查通过，结果已按哈希核验后归档。MCR 格网汇总为 172185 条记录，六指标基础表为 68874 条记录。真实 EOG 2020 年度亮度与原始有效观测次数尚未取得，基础表保留 NTL 缺失，综合指数因此尚未计算。
尚未生成或声称完成新的六指标综合评价结果。旧仓库中的抵抗力—恢复力—适应力结果不属于本次分析。

## 方法与目录

- 2020 年；1 km 正方形格网；500 m 格网对照。
- 林灌、草地、水体湿地分别评价；同类生境的六指标共同有效范围内进行极差标准化、熵权和线性聚合。
- 原生 InVEST Habitat Quality、FRAGSTATS CLUMPY、ArcGIS Cost Distance 和 Euclidean Distance。
- 对照土地覆盖产品、源地与阻力参数、格网尺度、去项和重新估权；同期 Landsat 地表温度用于灰绿配置的热环境补充检查。
- 原始数据、过程文件、结果文件、图件和本仓库分别存放。大体积数据、期刊全文、个人账户信息不上传仓库。

脚本在 `src/`，执行入口是 `pipeline.py`。以下说明针对本研究实际使用的 Windows 环境；尚未验证 Linux、macOS 或其他 GIS 版本的等价性。命令、软件回执和结果验收共同记录复现状态，脚本存在不等于实验完成。

## 公开代码与本地数据的关系

本仓库只提供代码和非敏感参数，不包含研究边界、原始影像、软件安装包、过程数据库、结果数据或期刊全文。下载仓库后仍需合法取得下表数据。自有研究边界并非二道绿隔官方规划边界，不能用另一套行政范围替换后声称复现相同结果。

将仓库克隆为 `<项目目录>/05_代码`，其同级目录如下：

```text
项目目录/
  01_原始数据/
  02_过程文件/
  03_结果文件/
  04_图件/
  05_代码/                 # 本仓库
```

原生程序采用短英文路径避免旧版 GIS 的中文路径问题。运行普通 Python 3.12：

```powershell
python .\setup_local_paths.py --check
# 只在新电脑尚未建立映射时执行；已有映射指错会停止，不会覆盖：
python .\setup_local_paths.py --create
```

该工具检查或创建 `D:\ER219_raw`、`D:\ER219_work`、`D:\ER219_results`、`D:\ER219_figures`、`D:\ER219_code` 五个目录联接，分别指向上列五个目录。当前实现要求存在 D 盘；不能只修改工作目录就绕过这些固定原生路径。`--check` 默认只读，不执行研究阶段。

## 原始输入清单

表内路径均相对 `01_原始数据`。下载源、版本、原始文件名、下载时间和校验值应随数据保存；不在 Git 中存储登录信息或临时签名链接。

| 输入及用途 | 必需文件/版本 | 获取与复现要求 |
| --- | --- | --- |
| 研究范围，格网与乡镇统计 | `研究范围/研究范围0328.shp` 及 `.shx/.dbf/.prj/.cpg` 等配套文件；38 个图形、`Name` 字段内 35 个乡镇 | 用户提供的同一边界；按原始编码读取，保留原件及哈希。缺少此边界不能复现同一案例。 |
| CLCD 主方案土地覆盖 | `CLCD2020/CLCD_v01_2020_albert.tif`；Zenodo 8176941，记录版本 1.0.2 | [原始发布记录](https://zenodo.org/records/8176941)。发布方 MD5 为 `1274285bb18f9b1d443a3cc906b1310c`；文件名 `v01` 不是记录版本号。 |
| CLCD 原生背景窗口 | `CLCD2020/CLCD_2020_v102_native_background17km.tif` | 从上述完整原件无损取原生窗口，不重采样。当前代码保留历史无损窗口而未自动从全国文件生成；新机器需按原始窗口元数据提取，见下文。 |
| WorldCover 数据源对照 | `WorldCover2020官方整幅/ESA_WorldCover_10m_2020_v100_N39E114_Map.tif` 及 `N39E117` 同名瓦片 | [官方数据入口](https://esa-worldcover.org/en/data-access)，2020 v100，CC BY 4.0；先拼接原生瓦片再以众数重采样，勿直接使用 2021 产品。 |
| 道路，HQ 胁迫及 MCR 道路阻力 | `OSM2020原始道路成员/gis_osm_roads_free_1.shp` 及配套文件，含 `fclass` | [Geofabrik 2020-01-01 原始压缩包](https://download.geofabrik.de/asia/china-200101-free.shp.zip)。这是年初快照，不能写成年末道路普查。 |
| 年度夜间灯光 | 同一 `VNL_v21_npp_2020_global_vcmslcfg_cYYYYMMDDHHMM` 发布批次的 `.average_masked.dat.tif` 和 `.cf_cvg.dat.tif` | [EOG 官方产品](https://eogdata.mines.edu/products/vnl/)。保留官方压缩原件、解压文件及不含认证信息的来源 URL。原始亮度和观测次数必须齐全；不得用虚拟值或另一年份代替。 |
| 地表温度补充检验 | `Landsat8_2020已有原生窗口/<场景ID>/` 的 ST_B10 DN、QA_PIXEL、QA_RADSAT、MTL；`Landsat8_2020补充质量层/<场景ID>/` 的 ST_QA、ST_EMIS 与 STAC | Landsat 8 Collection 2 Level 2 原生窗口；主景 `LC08_L2SP_123032_20200803_02_T1`，另两景 `LC08_L2SP_123032_20200616_02_T1`、`LC08_L2SP_124032_20200810_02_T1` 分别对照，不合成为年均温。 |

CLCD 背景窗口的固定定义：行数 4071，列数 4033，原生 Albers CRS 沿用完整文件，仿射变换前六项为 `[30, 0, 896665.2169543286, 0, -30, 4407871.5596752735]`。窗口 SHA-256 为 `a4a8b5f3dcdd123d187393edda2e61e4203334a48c327650d28f5c85b1cc8a4e`。重新编码 GeoTIFF 可能改变文件哈希；此时须同时核对 CRS、变换、像元形状、有效掩膜及全部像元值，不能仅以文件名一致判定同一输入。

NASADEM 为地形背景资料，主要观测来自 2000 年 SRTM；不进入本轮六项指标或 MCR 阻力。完整期刊 PDF、早期实验目录、社会韧性数据也不是六指标计算输入。

`src/acquisition/` 保存本轮下载/归档辅助脚本，路径已按当前子目录位置修正。其中 `219_inventory_stage.py` 是原工作区到新成果目录的历史搬运程序，依赖既有 `生态韧性新研究`、`GIS数据`、`2020年论文成果`，不是新机器通用下载器；没有这些历史目录时不要运行。`219_finalize_data_audit.py` 含采集时的软件状态记录，不是当前软件验收程序。当前下载辅助脚本不能独自重建所有 Landsat 原生窗口，须保留场景和窗口元数据。

## 软件环境与配置

| 环境 | 本轮版本及用途 | 准备要求 |
| --- | --- | --- |
| 普通 Python | 3.12；numpy、pandas、scipy、rasterio、geopandas、shapely >= 2、pyproj、requests | 与 ArcGIS/QGIS 自带 Python 分开。`requirements-analysis.txt` 固定本轮普通 Python 的直接分析依赖版本（不涵盖 Pro/QGIS 私有环境）；先检查依赖和小型数值核验，不能将普通 Python 的包安装命令直接施加到 GIS 自带环境。 |
| ArcGIS Pro | 3.1.6，Spatial Analyst；Fishnet、Cost Distance、Euclidean Distance | 须合法安装并具备相应许可；使用 Pro 的 `propy.bat`，不是普通 Python。开题记录中的 ArcMap 10.8 是原计划，当前原生运行版本以 Pro 回执为准。 |
| InVEST | 3.20.2，原生 Habitat Quality | 默认入口 `D:\Apps\InVEST-3.20.2\invest.exe`。`acquire_invest.py` 只校验下载官方安装包，并不完成安装。 |
| FRAGSTATS | 4.2.1.612，原生 class CLUMPY | 同时需要完整便携程序目录和官方 Tutorial_3 的 `fragmodel.fca`，详见下文；不是只复制一个 EXE。 |
| JRC MSPA | 2.4 October 2026，原生 Win64 | 放置 `01_原始数据/软件原始安装包/JRC_MSPA_2_4/mspa_win64.exe`。原始文档及源代码副本可选归档，不是执行的必要输入。 |
| QGIS | 3.28.2 Firenze；原生分级、可编辑工程及地图 | 默认 `F:\Program Files\QGIS 3.28.2`；`gdalbuildvrt.exe` 固定于该安装目录。地图使用 Windows 微软雅黑字体。 |

FRAGSTATS 使用[作者仓库固定提交](https://github.com/kmcgarigal/Fragstats/tree/91b03d143c4acc0e42304d2961253340720604a2)中的 `fragstats64.zip` 和 `Tutorial.zip`。解压后需满足：

```text
02_过程文件/计算审计/FRAGSTATS4.2/
  portable/frg_cmd.exe      # 保留同包 DLL 等依赖
  tutorial/Tutorial_3/fragmodel.fca
```

也可通过环境变量 `ER219_FRAGSTATS_HOME` 指定具有同样子目录结构的位置。代码修改的是模型副本，保留官方模板。MSPA 的固定源代码提交及二进制来源记在 `src/agent_mspa.py`；需沿用本轮归档二进制并核对软件回执，不能把 GitHub `main` 上日后更新的程序当作固定版本。

本机默认普通 Python、Pro 和 QGIS Python 入口写在 `pipeline.py`。可在仓库根部建立不提交的 `local_runtime.json`：

```json
{
  "python": "C:/your-python312/python.exe",
  "propy": "F:/Program Files/ArcGIS/Pro/bin/Python/Scripts/propy.bat",
  "qgis": "F:/Program Files/QGIS 3.28.2/bin/python-qgis.bat"
}
```

该文件目前只覆盖三个 Python 入口，不覆盖固定的 InVEST、GDAL 或 D 盘联接路径。若安装目录不同，须对这些入口作路径适配并再次核验；不得把修改软件路径误作已经验证计算等价性。

夜间灯光输入配置放在 `02_过程文件/aggregation/ntl_inputs.json`。以下仅是结构样例，必须换成实际同批次原件及官方 URL，核验后再将布尔值改为 `true`：

```json
{
  "official_source_files_verified": false,
  "release_prefix": "VNL_v21_npp_2020_global_vcmslcfg_cYYYYMMDDHHMM",
  "average_masked_tif": "01_原始数据/实际目录/实际原始文件.average_masked.dat.tif",
  "cf_cvg_tif": "01_原始数据/实际目录/实际原始文件.cf_cvg.dat.tif",
  "average_masked_source_url": "https://eogdata.mines.edu/nighttime_light/annual/v21/2020/实际原始文件.average_masked.dat.tif.gz",
  "cf_cvg_source_url": "https://eogdata.mines.edu/nighttime_light/annual/v21/2020/实际原始文件.cf_cvg.dat.tif.gz"
}
```

## 运行顺序、依赖与验收

先运行 `python pipeline.py --plan` 只读查看命令。各阶段需前序输入完整；入口目前不自动补齐下载、安装、许可或中间文件，失败即停止。不要在 MCR 队列运行时重跑空间准备、MSPA、MCR 输入准备或改变参数。

| 顺序/阶段 | 依赖 | 主要输出或验收 |
| --- | --- | --- |
| `--stage spatial` | 边界、CLCD 背景窗口、两块 WorldCover、GDAL、Pro | 统一背景栅格、研究范围、1 km/500 m 完整方格及相交权重基础 |
| `--stage hq` | spatial、道路、InVEST、`config/hq_sensitivity.csv` | 原生退化度试算确定半饱和常数，冻结同一 k，输出两产品 HQ |
| `--stage euclidean` | spatial、hq 生成的道路栅格、Pro | 同类生态空间及道路距离 |
| `--stage clumpy` | spatial、FRAGSTATS 模板与程序 | 各类生境两尺度原生 CLUMPY；N/A 状态原样保留 |
| `--stage mspa` | spatial、MSPA 原生程序 | 先合成核验，再保存六组原生核心图及全部像元核验 |
| `--stage mcr` | spatial、euclidean、mspa、Pro、`config/mcr_parameters.json` | 15 组原生任务、同母斑块排除核验、发布 MCR 结果；支持哈希一致的续跑 |
| `--stage ntl` | spatial、真实 EOG 同批次文件与输入配置 | 原生像元面积加权 NTL；数据缺失时停止，不生成占位指标 |
| `--stage aggregate` | hq、euclidean、clumpy、mcr、ntl | 单项汇总、三类生境六项记录、有效域状态；部分单项可先独立汇总，完整入口需全部齐备 |
| `--stage arithmetic_qa` | aggregate 生成的格网基础 | 标准化、去项、格网汇回等数学/面积守恒检查；不是生态过程验证 |
| `--stage evaluate` | 六项共同有效记录及核验通过 | 统一参考范围、熵权、固定五级 Jenks、成对敏感性和乡镇有效范围统计 |
| `--stage context_maps` | spatial 及所需背景图层 | 可编辑 QGIS 研究区/技术路线工程，原生导出与重开核验 |
| `--stage result_maps` | evaluate 全部完成 | 实际综合指数、短板与分级稳定性图；另需原生重开和目视审阅 |
| `--stage final_qa` | 全部真实评分、分级与乡镇报表 | 独立标量/分组复算、最优分级目标和空间支持检查；缺数据返回 BLOCKED |
| `--stage manifest` | 当前各阶段回执 | 更新本地 project.yaml 和阶段快照；不会把缺失数据标成完成 |

热环境补充分析可用 `--stage thermal` 和 `--stage thermal_figure` 执行；对应的独立脚本顺序为：普通 Python 执行 `src/agent_thermal_prepare.py`、`src/agent_thermal_validate.py`；在 HQ/欧氏距离和 `aggregate_basics.py` 已完成后执行 `src/agent_thermal_association.py`、`src/agent_thermal_association_validate.py`；再用 QGIS Python 执行 `src/agent_thermal_qgis_figure6.py` 与 `src/agent_thermal_qgis_figure6_validate.py`，实际逐图审阅通过后，普通 Python 执行 `src/agent_thermal_figure6_finalize.py` 固定本轮交付记录；新运行不能未经目视审阅直接沿用 PASS。热环境是灰绿配置补充分析，不用虚构 NTL 或未完成的综合指数填充。

每阶段查看 `02_过程文件` 中对应的 receipt/QA 文件，并核对 `03_结果文件`。`pipeline_runs` 中命令退出码为 0 只表示命令执行完毕；综合评价还要求真实输入、共同有效域、原生输出、数值检查和地图重开均有对应记录。无同类生境、无建设空间或原生指标未定义应保留独立状态，不能自动填成低分。

当前分发属于有原生运行记录的研究代码，尚不是一键跨平台软件。原始输入、各软件许可、路径和软件模板均需准备；未取得真实 NTL、MCR 或验收未结束时，不应宣称已经复现全文结果。数据及参考文献的再分发分别遵守其许可；本 README 不为第三方数据授予许可。

## 主要方法来源

- Feng et al. (2024), *Sustainable Cities and Society*, 105933. DOI: 10.1016/j.scs.2024.105933.
- Fan and Wei (2025), *Ecological Indicators*, 112980. DOI: 10.1016/j.ecolind.2024.112980.
- Wang, Blanchet and Koper (2014), *Methods in Ecology and Evolution*, 634–646. DOI: 10.1111/2041-210X.12198.
- InVEST 与 FRAGSTATS 官方模型文档及版本固定的原生软件。

文献参数、数据处理和本研究的适配分别记录。程序数值核验、参数敏感性和生态过程验证属于不同证据，不相互替代。

## 论文与补充图

`prepare_manuscript_content.py` 仅整理过程目录中的已核验引言、方法及真实热环境段落，不生成完整论文。`build_manuscript.py` 要求内容标记为 READY_FOR_LAYOUT、真实六指标数值验收为 PASS，才可创建新的匿名 Word 文件；原生 Office 渲染与逐页审阅仍须另行完成。文档环境使用 `requirements-manuscript.txt`，与分析/GIS 环境分开。

`build_methods_preview.py` 只在过程目录生成明确标记的引言与方法排版校样。当前校样经本机 WPS 原生只读打开和 PDF 渲染，共 9 页、6 个可编辑公式，已逐页检查；它不包含综合评价结果和结论，不能当作已完成论文。图 1、图 2 和图 6 已在 QGIS 原生布局中优化字体，并独立重开后检查。`render_docx_native.ps1` 保留用户已有窗口，不保存或关闭原文档；`render_docx_pages.py` 使用已有原生 PDF 为页图转换提供输入。

补充图 S1 的独立链为普通 Python 的 `agent_s1_prepare.py`，QGIS Python 的 `agent_s1_qgis_map.py`、`agent_s1_qgis_validate.py`；它展示 HQ、CLUMPY、SSI 与 E/(E+C) 原始值，不能当作六指标综合评价图。任何命名为 finalize 的交付脚本都须在实际目视审阅后运行，不能用脚本名称代替审阅。
