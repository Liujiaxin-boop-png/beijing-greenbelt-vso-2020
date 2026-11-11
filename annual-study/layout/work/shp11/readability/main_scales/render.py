from pathlib import Path
import sys,shutil,json,subprocess
w=Path(__file__).resolve().parent
root=w.parent/'arcmap_delivery'
base=Path('D:/ER219_work/shp11/maps')
maker='D:/ER219_code/arcmap_hi_20261106/run_native.ps1'
ps_base=Path(maker).read_text('utf-8-sig')
runner=w/'run.ps1'
runner.write_text("param([string]$Mxd,[string]$Config,[string]$Audit)\n"+ps_base.split("$ErrorActionPreference",1)[1].rsplit("Add-Type",1)[0].join(["$ErrorActionPreference",""])+"Add-Type -Path (Join-Path $PSScriptRoot 'MainScale.cs') -ReferencedAssemblies $assemblyRefs\n[MainScale]::Run($Mxd,$Config,$Audit)\n",encoding='utf-8-sig')
ps=['C:/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File']
for k in sys.argv[1:]:
    cfg=json.loads((base/f'fig{k}.json').read_text('utf8'));dest=root/('图'+k);src=Path(cfg['output_mxd']);out=dest/src.name
    cfg['export_stem']=str(w/f'fig{k}')
    if k=='3':
        cfg['scales'][0]['shift_x_cm']=-.35
        cfg['scales'][0]['x']-=.35
    cfg_path=w/f'fig{k}.json';cfg_path.write_text(json.dumps(cfg,ensure_ascii=False),'utf8')
    shutil.copyfile(src,out)
    subprocess.run(ps+[str(runner),'-Mxd',str(out),'-Config',str(cfg_path),'-Audit',str(w/f'edit{k}.json')],check=True)
    subprocess.run(ps+[maker,'-InputMxd',str(out),'-Config',str(cfg_path),'-ExportOnly'],check=True)
    for ext in ['.png','.pdf']:shutil.copyfile(w/('fig'+k+ext),out.with_suffix(ext))
    print('Exported',k,flush=True)

