from pathlib import Path
import subprocess,concurrent.futures,shutil,json,sys
w=Path(__file__).parent
ps=str(Path('C:/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe'))
src=next(Path.cwd().glob('生态韧性正式研究_*/04_图件/原始GIS边界*ArcMap10.8'))
def render(k):
 d=w.parent/'arcmap_delivery'/('图'+k)
 m=next(d.glob('*.mxd'))
 cfg=w/(k+'.json')
 cmd=[ps,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(w/'run.ps1'),'-InputMxd',str(m),'-Config',str(cfg)]
 if k!='A2':
  shutil.copy2(src/('图'+k)/m.name,m)
  with open(w/('log'+k+'.txt'),'wb') as f:
   subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
   subprocess.run(cmd+['-ExportOnly'],check=True,stdout=f,stderr=subprocess.STDOUT)
 rec=json.loads((w/(k+'.export_receipt.json')).read_text('utf8'))
 assert rec['broken_layers']==0 and rec['map_count']==len(rec['maps']) and len([a for a in rec['elements'] if a['type']=='scale'])==1
 for ext in ['png','pdf']:
  out=w/('export'+k+'.'+ext)
  assert out.stat().st_size>1000
  shutil.copy2(out,m.with_suffix('.'+ext))
 print('done',k,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 list(pool.map(render,sys.argv[1:]))
