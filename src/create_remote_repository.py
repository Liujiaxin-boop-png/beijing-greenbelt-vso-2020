"""Create the explicitly requested GitHub repository via the standard helper.

No credential is logged or written to disk. This uses only github.com's own
configured Git credential helper, with interactive prompts disabled.
"""
from pathlib import Path
import os, subprocess, json
import requests

ROOT=Path(__file__).resolve().parents[2]
NAME='beijing-greenbelt-vso-2020'
OWNER='Liujiaxin-boop-png'

def main():
    env=os.environ.copy();env.update(GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never')
    cp=subprocess.run([r'C:\Program Files\Git\cmd\git.exe','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,env=env,timeout=25)
    if cp.returncode:
        print(json.dumps({'status':'NO_NONINTERACTIVE_GITHUB_CREDENTIAL','remote_created':False}));return
    values=dict(line.split('=',1) for line in cp.stdout.splitlines() if '=' in line)
    secret=values.get('password')
    if not secret:
        print(json.dumps({'status':'NO_NONINTERACTIVE_GITHUB_CREDENTIAL','remote_created':False}));return
    session=requests.Session();session.headers.update({'Authorization':'Bearer '+secret,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    identity=session.get('https://api.github.com/user',timeout=30)
    if identity.status_code!=200 or identity.json().get('login')!=OWNER:
        print(json.dumps({'status':'GITHUB_IDENTITY_NOT_MATCHED','remote_created':False}));return
    existing=session.get(f'https://api.github.com/repos/{OWNER}/{NAME}',timeout=30)
    if existing.status_code==200:
        payload=existing.json();status='ALREADY_EXISTS'
    elif existing.status_code==404:
        r=session.post('https://api.github.com/user/repos',json={'name':NAME,'description':'2020 Beijing greenbelt ecological resilience: vulnerability, sensitivity and self-organization; reproducible analysis code.','private':False,'auto_init':True},timeout=40)
        if r.status_code!=201:
            print(json.dumps({'status':'CREATE_FAILED','http_status':r.status_code,'remote_created':False}));return
        payload=r.json();status='CREATED'
    else:
        print(json.dumps({'status':'LOOKUP_FAILED','http_status':existing.status_code,'remote_created':False}));return
    receipt={'status':status,'repository':payload['full_name'],'url':payload['html_url'],'clone_url':payload['clone_url'],'visibility':payload['visibility'],'credential_saved':False}
    (ROOT/'02_过程文件/GitHub仓库创建回执.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(receipt))

if __name__=='__main__':main()
