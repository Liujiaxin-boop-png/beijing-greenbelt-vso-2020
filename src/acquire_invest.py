"""Acquire pinned official InVEST binary; never treat a partial file as complete."""
from pathlib import Path
import json, hashlib, requests, time, shutil
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'01_原始数据/软件原始安装包'
OUT.mkdir(exist_ok=True)
P=ROOT/'02_过程文件/软件运行环境';P.mkdir(exist_ok=True)
NAME='invest_3.20.2_workbench_win32_x64.exe'
URL='https://github.com/natcap/invest/releases/download/3.20.2/'+NAME
SIZE=383671376
EXPECTED='2be0ec5f3b331faec39dd62b8b7223c84d26972a28e5ae56530b29e2bceb4aaf'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    final=OUT/NAME;part=OUT/(NAME+'.partial')
    if final.exists():
        assert final.stat().st_size==SIZE and sha(final)==EXPECTED
        print('Already verified',flush=True);return
    old=ROOT.parent/'2020年论文成果/01_原始数据/生态韧性评价149_官方软件'/ (NAME+'.part')
    if not part.exists() and old.exists():shutil.copy2(old,part)
    start=part.stat().st_size if part.exists() else 0
    r=requests.get(URL,headers={'Range':f'bytes={start}-'},stream=True,timeout=(40,120))
    r.raise_for_status()
    if r.status_code==206:
        assert r.headers['Content-Range'].startswith(f'bytes {start}-')
        mode='ab'
    elif r.status_code==200:mode='wb';start=0
    else:raise RuntimeError(r.status_code)
    last=time.monotonic();n=start
    with part.open(mode) as f:
        for b in r.iter_content(1024*1024):
            if b:f.write(b);n+=len(b)
            if time.monotonic()-last>=10:
                print(json.dumps({'bytes':n,'total':SIZE,'fraction':round(n/SIZE,4)}),flush=True)
                (P/'invest_download_status.json').write_text(json.dumps({'bytes':n,'total':SIZE,'status':'DOWNLOADING'}),encoding='utf8')
                last=time.monotonic()
    assert part.stat().st_size==SIZE,(part.stat().st_size,SIZE)
    assert sha(part)==EXPECTED
    part.rename(final)
    (P/'invest_download_status.json').write_text(json.dumps({'file':str(final.relative_to(ROOT)),'bytes':SIZE,'sha256':EXPECTED,'source':URL,'status':'VERIFIED_OFFICIAL_INSTALLER_NOT_YET_EXECUTED'},indent=2),encoding='utf8')
    print('VERIFIED_OFFICIAL_INSTALLER',flush=True)

if __name__=='__main__':main()
