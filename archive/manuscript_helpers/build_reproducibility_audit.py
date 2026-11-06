"""Read-only scientific-code audit; writes only this manuscript audit package."""
from pathlib import Path
import ast, datetime, hashlib, json, subprocess, sys

CODE=Path('D:/ER219_code').resolve()
PROJECT=CODE.parent
OUT=PROJECT/'02_过程文件/manuscript'
def row(id,severity,status,where,issue,repair):
    return dict(id=id,severity=severity,status=status,location=where,issue=issue,minimal_repair=repair)

findings=[
row('R01','high','FIXED_SETUP_AND_DOCUMENTED',['setup_local_paths.py','README.md','src/prepare_spatial.py:53-58','src/prepare_distance_inputs.py:16-21','src/prepare_mcr.py:23,83'],
'研究过程依赖 D:/ER219_* 目录联接；代码下载原先没有映射创建或检查入口。',
'已新增默认只读的五联接检查，--create仅创建缺失项；已有路径非联接或指向不同即停止，绝不删除或覆盖。README限定D盘Windows环境。'),
row('R02','high','FIXED_PATHS_NOT_EXECUTED',['src/acquisition/219_download_support.py:5','src/acquisition/219_download_worldcover.py:5','src/acquisition/219_finalize_data_audit.py:7','src/acquisition/219_inventory_stage.py:7-8'],
'辅助脚本移动到src/acquisition后父目录层级未同步：三个ROOT落到代码仓库，inventory还重复拼正式研究名。',
'三个ROOT改为parents[3]；inventory OUT=parents[3]、ROOT=OUT.parent。只编译和静态路径核验，不下载、不搬运、不重写既有审计。'),
row('R03','high','FIXED_OPTIONAL_EVIDENCE_COPY',['src/agent_mspa.py:28-36'],
'MSPA setup强制复制非Git过程目录内的4份文档；已具备原生EXE的新机器仍会因缺论文PDF而失败。',
'仅将4份证据复制改为存在时复制，原生二进制仍必需；所有数值参数、主输入、原生执行及输出逻辑保持原样。'),
row('R04','high','DOCUMENTED_MANUAL_PREREQUISITE',['src/agent_fragstats_clumpy.py:17-20,27-30','README.md'],
'FRAGSTATS原生程序与官方SQLite模板保存在过程目录，pipeline未创建，不能只提供frg_cmd.exe。',
'README列出固定作者提交、完整便携包、Tutorial.zip及精确目录，提供ER219_FRAGSTATS_HOME选择；不在生产执行中更换程序。'),
row('R05','high','OPEN_DOCUMENTED_LAYOUT_LIMIT',['pipeline.py:11-20','src/prepare_spatial.py:70','src/prepare_hq.py:68','src/run_hq.py:9-10'],
'local_runtime只替换三个Python入口；InVEST和GDAL路径仍固定，异机不同安装位置不会自动适配。',
'本次诚实记录受支持安装布局和逐项核查；下一次非生产期可统一到运行配置，测试后再宣称可移植。当前不改生产入口。'),
row('R06','high','OPEN_DOCUMENTED_RAW_WINDOW_REQUIREMENT',['src/prepare_spatial.py:26','src/acquisition/219_inventory_stage.py:38-40','src/agent_thermal_prepare.py:23-25,39'],
'主流程依赖已有CLCD无损背景窗口及已选Landsat原生窗口；下载全国CLCD/整景Landsat并不自动生成这些输入。',
'README补CLCD原始版本、精确shape/transform/hash及像元核对规则；保留Landsat场景/窗口元数据。后续补从完整原件生成固定窗口的小型入口，不能按任意新范围裁切。'),
row('R07','high','DOCUMENTED_NO_INPUT_SUBSTITUTION',['pipeline.py:25','src/agent_ntl_aggregate.py:71-95','README.md'],
'NTL真实输入与ntl_inputs.json不在公开仓库。没有这两项不能完成六指标评价。',
'README提供不含秘密的配置结构、同发布批次平均亮度/观测次数要求、官方来源和真实核验条件；已有脚本缺失即停止，不用替代值。'),
row('R08','medium','DOCUMENTED_MANUAL_STAGES',['pipeline.py:18-29','src/agent_thermal_prepare.py','src/agent_thermal_association.py:14-16','README.md'],
'热环境准备、分析、验证与图件尚未纳入pipeline；主入口顺序不能单独重建全文所有内容。',
'README列出热环境独立执行顺序和HQ/距离/aggregate_basics依赖，说明无需NTL。后续可加命名阶段，当前不修改运行流程。'),
row('R09','medium','DOCUMENTED_HISTORY_VS_RUNTIME',['config/approved_protocol.json:software_contract','src/bootstrap_project.py:18-27,39','src/acquisition/219_finalize_data_audit.py:27'],
'批准方案记录ArcMap10.8、历史bootstrap依赖旧开题路径、数据审计含采集时软件状态；这些不等于实际可运行环境。',
'不改批准记录；README区分原计划与实际Pro3.1.6，标历史搬运/审计脚本为归档用途，以本轮原生receipt为准。'),
row('R10','medium','OPEN_PACKAGE_LOCK',['README.md','pipeline.py:11-15'],
'公开仓库无普通Python完整依赖锁文件；Pro/QGIS环境也需要各自安装与许可。',
'README列基本依赖和独立环境。建议最终交付导出普通Python版本锁和原生软件哈希/版本清单；不向厂商GIS环境盲目pip升级。'),
row('R11','medium','DOCUMENTED_PRIVATE_BOUNDARY',['src/prepare_spatial.py:27-34','README.md'],
'案例边界没有公共下载地址且不是官方规划边界；只有代码不能复现同一35乡镇样本。',
'README说明必须取得相同边界及sidecar/Name字段/38图形35乡镇；最终数据可访问声明需说明合法获取方式，不能暗自换范围。'),
row('R12','low','OPEN_PRESENTATION_PORTABILITY',['src/qgis_study_map.py','src/qgis_method_diagram.py','src/agent_thermal_qgis_figure6.py','README.md'],
'制图依赖Windows微软雅黑字体和D盘导出目录。',
'README限定Windows现有字体与目录；若替换字体，需重新原生渲染核查，不影响已冻结数值。')]

inputs=[
{'id':'boundary','required':'core','path':'01_原始数据/研究范围/研究范围0328.shp + sidecars','version':'user-supplied same geometry;38 features/35 Name','usage':'scope/fishnet/town intersections','public_code_includes':False},
{'id':'clcd','required':'core','path':'01_原始数据/CLCD2020/CLCD_v01_2020_albert.tif; CLCD_2020_v102_native_background17km.tif','version':'Zenodo8176941 v1.0.2 / 2020','usage':'native land-cover/HQ/MSPA/MCR/CLUMPY/SSI/area','public_code_includes':False,'source':'https://zenodo.org/records/8176941','original_md5':'1274285bb18f9b1d443a3cc906b1310c'},
{'id':'worldcover','required':'sensitivity','path':'01_原始数据/WorldCover2020官方整幅/*N39E114_Map.tif;*N39E117_Map.tif','version':'2020v100','usage':'second-product comparison','public_code_includes':False,'source':'https://esa-worldcover.org/en/data-access'},
{'id':'roads','required':'core','path':'01_原始数据/OSM2020原始道路成员/gis_osm_roads_free_1.shp + sidecars','version':'Geofabrik2020-01-01','usage':'HQ threat / MCR road distance','public_code_includes':False,'source':'https://download.geofabrik.de/asia/china-200101-free.shp.zip'},
{'id':'ntl','required':'core','path':'same-release VNL2020v21 average_masked + cf_cvg; process/aggregation/ntl_inputs.json','version':'VNL_v21_npp_2020_global_vcmslcfg_cYYYYMMDDHHMM','usage':'annual human-activity pressure','public_code_includes':False,'status':'INPUT_ACQUISITION_AND_NATIVE_QA_MUST_BE_CONFIRMED_BY_ACTUAL_RECEIPT','source':'https://eogdata.mines.edu/products/vnl/'},
{'id':'landsat','required':'approved thermal supplement','path':'01_原始数据/Landsat8_2020已有原生窗口; Landsat8_2020补充质量层','version':'C2L2 three frozen 2020 scenes; original DN/QA/MTL/STAC','usage':'gray-green thermal supplement','public_code_includes':False},
{'id':'nasadem','required':'not required for six indicators','version':'v001 primarily2000SRTM','usage':'context only; not added to resistance'},
{'id':'software','required':'native algorithms','path':'official native installations;FRAGSTATS tutorial model;MSPA exe','usage':'native software execution','public_code_includes':False}]

stages=[
('spatial',['boundary','CLCD native window','WorldCover two tiles','GDAL','Pro']),
('hq',['spatial','OSM roads','InVEST','config/hq_sensitivity.csv']),
('euclidean',['spatial','hq road raster','Pro']),
('clumpy',['spatial','FRAGSTATS exe dependencies','official fragmodel.fca']),
('mspa',['spatial','MSPA2.4 native executable']),
('mcr',['spatial','euclidean','mspa','config/mcr_parameters.json','Pro Spatial Analyst']),
('ntl',['spatial','actual EOG pair','ntl_inputs.json']),
('aggregate',['hq','euclidean','clumpy','mcr','ntl']),
('arithmetic_qa',['aggregate grid definitions']),
('evaluate',['six-indicator complete records','arithmetic_qa','QGIS classification']),
('context_maps',['spatial','QGIS']),
('thermal_prepare_validate',['spatial','Landsat native windows/quality layers']),
('thermal_association_validate',['thermal_prepare_validate','aggregate_basics output']),
('thermal_figure_validate',['thermal_association_validate','QGIS','Windows font'])]

owned=['README.md','setup_local_paths.py','src/agent_mspa.py',
       'src/acquisition/219_download_support.py','src/acquisition/219_download_worldcover.py',
       'src/acquisition/219_finalize_data_audit.py','src/acquisition/219_inventory_stage.py']
for name in owned:
    if name.endswith('.py'):compile((CODE/name).read_text(encoding='utf8'),str(CODE/name),'exec')
# Pure AST check: no production module imported, no side effects or native execution.
ms=ast.parse((CODE/'src/agent_mspa.py').read_text(encoding='utf8'))
constants={}
for node in ms.body:
    if isinstance(node,ast.Assign):
        for t in node.targets:
            if isinstance(t,ast.Name) and t.id in ['CORE_CODES','PARAMS','ALLOWED_CODES']:
                constants[t.id]=ast.literal_eval(node.value)
assert constants['CORE_CODES']==[17,117]
assert constants['PARAMS']==['-eew','1','-graphfg','8','-internal','1','-transition','1']
for n in ['219_download_support.py','219_download_worldcover.py','219_finalize_data_audit.py']:
    p=CODE/'src/acquisition'/n
    assert 'ROOT=Path(__file__).resolve().parents[3]' in p.read_text(encoding='utf8')
    assert p.resolve().parents[3]==PROJECT
p=CODE/'src/acquisition/219_inventory_stage.py'
assert 'OUT = Path(__file__).resolve().parents[3]' in p.read_text(encoding='utf8')
assert 'ROOT = OUT.parent' in p.read_text(encoding='utf8')
cp=subprocess.run([sys.executable,str(CODE/'setup_local_paths.py'),'--check'],capture_output=True,text=True,encoding='utf8')
assert cp.returncode==0,cp.stderr
preflight=json.loads(cp.stdout)
assert preflight['read_only'] is True and preflight['created']==[]
(OUT/'reproducibility_preflight.json').write_text(json.dumps(preflight,ensure_ascii=False,indent=2),encoding='utf8')
snapshot={str(p.relative_to(CODE)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
          for p in [CODE/n for n in owned]+[CODE/'pipeline.py']}
report={'audit_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'scientific code, README, pipeline and config; no authentication/credential scan or online retrieval',
 'review_mode':'initial_readonly_then_parent_authorized_nonproduction_setup_fixes',
 'production_stages_executed':False,'production_mcr_files_changed':False,
 'status':'RECORDED_WINDOWS_LAYOUT_DOCUMENTED;PORTABILITY_GAPS_REMAIN',
 'findings':findings,'raw_inputs_not_in_public_git':inputs,
 'native_versions':{'ArcGISPro':'3.1.6 + licensed Spatial Analyst','InVEST':'3.20.2','FRAGSTATS':'4.2.1.612 + official tutorial SQLite','MSPA':'2.4 October2026','QGIS':'3.28.2 Firenze','Python':'3.12; package lock not yet distributed'},
 'dependencies':[{'stage':a,'requires':b,'pipeline_stage':not a.startswith('thermal')} for a,b in stages],
 'public_readme_requirements':['precise raw names/versions/source/checksums/licenses','case boundary access and support','full local folder and ASCII alias mapping','native installs/models/licenses','separate Python environments','NTL config schema and true acquisition status','stage ordering and receipts','manual thermal sequence','remaining portability limitations','no credentials, raw imagery, copyright PDFs or false completion'],
 'minimal_fixes_applied':owned,'not_changed':['six indicators','HQ/MSPA/MCR numeric parameters','native MCR scripts or queue','source inputs','completed results','approved proposal218'],
 'qa':{'syntax_compile_in_memory':'PASS','acquisition_root_static':'PASS','MSPA constants unchanged':'PASS','read_only_five_junction_check':'PASS','native_stages_rerun':False,'preflight':'reproducibility_preflight.json'},
 'post_fix_snapshot':snapshot}
(OUT/'reproducibility_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
lines=['复现材料独立审计（2026-11-06）','',
'结论：现有代码可依照已记录的 Windows 本机布局继续运行，但公开下载代码尚不等于取得全部输入和软件；不应声称一键跨平台复现。',
'审查后仅按主代理授权修复了非生产环境准备：4个acquisition根目录、MSPA可选文档复制、五个ASCII联接检查/创建工具及README。六项指标、数值参数、生产MCR脚本、队列和已有结果均未改动。','']
for f in findings:lines += [f"{f['id']} [{f['status']}] {f['issue']}",f"处理/最小建议：{f['minimal_repair']}",f"定位：{'; '.join(f['location'])}",'']
lines += ['验收：6个Python文件仅在内存compile，acquisition父目录静态检查通过，MSPA参数常量未变；setup_local_paths.py --check五个联接均PASS且created=[]。未启动任何生产阶段或联网获取数据。',
'剩余最少工作：最终交付补普通Python版本锁、原始数据清单/可访问说明与原生窗口生成记录；不同安装目录先统一运行配置后小型核验；真实NTL/MCR仍以最终运行receipt确认完成度。']
(OUT/'reproducibility_audit.txt').write_text('\n'.join(lines),encoding='utf8')
print(json.dumps({'status':'AUDIT_WRITTEN','findings':len(findings),'syntax_files':sum(n.endswith('.py') for n in owned),'preflight':preflight['status'],'changed':owned},ensure_ascii=False))
