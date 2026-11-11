import sys
from common import *
import subprocess,concurrent.futures,time
WORKER=str(Path('C:/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe'))
native='D:/ER219_code/arcmap_hi_20261106/run_native.ps1'
base=json.loads(Path('D:/ER219_code/arcmap_hi_20261106/context_fig1.json').read_text('utf-8-sig'))['input_template']
def launch(k):
 cfg=W/f'fig{k}.json';j=json.loads(cfg.read_text('utf8'));out=Path(j['output_mxd'])
 ps=[WORKER,'-NoProfile','-ExecutionPolicy','Bypass','-File',native]
 with (W/f'log{k}.txt').open('wb') as f:
  subprocess.run(ps+['-InputMxd',base,'-OutputMxd',str(out),'-Config',str(cfg)],check=True,stdout=f,stderr=subprocess.STDOUT)
  subprocess.run(ps+['-InputMxd',str(out),'-Config',str(cfg),'-ExportOnly'],check=True,stdout=f,stderr=subprocess.STDOUT)
 for ext in ('.png','.pdf'):
  src=Path(j['export_stem']+ext);assert src.stat().st_size>5000;shutil.copy2(src,out.with_suffix(ext))
 print('done',k,flush=True)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=1) as e:list(e.map(launch,sys.argv[1:]))
