# 本轮文稿辅助脚本归档

本目录保留2020年生态韧性研究中使用的14个自编辅助脚本，包括文献整理、方法附录、结果解释和独立审阅。原文件仍留在项目的 `02_过程文件/manuscript` 与 `02_过程文件/参数文献核验`，此处副本与原件逐字节一致；具体SHA-256见 `archive_manifest.json`。

这些脚本是历史工作记录，不是主分析入口，也不按文件排列顺序执行。部分脚本含当时的草稿措辞、旧阶段状态或早期分级实现检查，不能代替最终论文与最终QA；正式计算入口和当前方法以仓库根目录README、`pipeline.py`及`src/`为准。

部分脚本依赖 `D:/ER219_*`、原工作区当前目录、历史材料目录或脚本原所在位置。直接从本归档目录运行可能找不到输入，或写回既有过程文件。它们未经迁移适配，不属于一键复现命令；如需重用，应先检查输入、输出路径和所需运行阶段。

| 脚本 | 历史用途 |
| --- | --- |
| agent_audit_evaluation.py | 评价代码的独立只读审查 |
| agent_fetch_selected_fulltexts.py | 已选来源的公开全文获取 |
| agent_finalize_evidence.py | 文献与方法证据整理 |
| agent_full_manuscript_review.py | 全文规划视角审阅建议 |
| agent_reference_archive.py | 参考文献归档与元数据整理 |
| agent_result_interpretation.py | 真实结果的规划解释辅助 |
| agent_update_method_appendix.py | 方法参数附录的版本化整理 |
| agent_write_intro_and_evidence.py | 引言草稿及引文依据整理 |
| agent_write_methods.py | 区域、数据和方法草稿整理 |
| build_reproducibility_audit.py | 代码和运行条件的复现性检查 |
| prepare_method_clarity_patch.py | 方法表述修订建议生成 |
| misc/build_venue_report.py | 投稿会议官方要求核对记录 |
| misc/219_archive_parameter_sources.py | 已选参数来源的公开材料归档 |
| misc/219_build_parameter_audit.py | 早期参数候选与适用条件审计 |

收录前进行了凭据模式扫描，以及URL、敏感关键词上下文和长文本用途检查，未发现token、cookie内容、账号密码或与本研究无关的私人文本；没有加入原始数据、期刊全文或第三方软件。未清理或修改代码内容，原有本地路径作为历史运行条件保留。

`misc/219_build_parameter_audit.py` 保留早期候选参数的核查过程，包含当时尚未冻结的方案；不能用其旧状态或候选值替换最终配置。`misc/build_venue_report.py` 的会议日期与格式记录是本轮查询快照，后续投稿需重新核对官方通知。
