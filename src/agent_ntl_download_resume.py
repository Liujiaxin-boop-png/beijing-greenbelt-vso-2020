"""Resumable EOG 2020 v2.1 downloads using ONLY officially authorized API access.

Free website accounts must download through the browser. Since 2026-06-01 EOG
restricts OpenID programmatic access to paid subscribers. This program never
extracts browser cookies, reads a credential file, or stores authentication.
"""
from pathlib import Path
import argparse,datetime,getpass,gzip,hashlib,json,re,sys,time
from urllib.parse import urlparse
import requests

ROOT=Path(__file__).resolve().parents[2]
TOKEN_URL="https://eogauth.mines.edu/realms/eog/protocol/openid-connect/token"
PAT=re.compile(r"^VNL_v21_npp_2020_global_vcmslcfg_c[0-9]{12}\.(average_masked|cf_cvg)\.dat\.tif\.gz$")
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf8")
def read(path): return json.loads(path.read_text(encoding="utf8"))
def file_sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b""): h.update(chunk)
 return h.hexdigest()
def validate_url(url,product):
 u=urlparse(url)
 if u.scheme!="https" or u.netloc!="eogdata.mines.edu" or u.query or u.fragment:
  raise ValueError("Use an unmodified HTTPS EOG data URL, without credentials, query string or fragment.")
 if not u.path.startswith("/nighttime_light/annual/v21/2020/"):
  raise ValueError("Only the frozen 2020 annual v2.1 directory is accepted.")
 name=u.path.rsplit("/",1)[-1]; m=PAT.fullmatch(name)
 if not m or m.group(1)!=product: raise ValueError("Filename must identify original average_masked or cf_cvg for 2020 v2.1.")
 return name
def gzip_crc(path):
 with gzip.open(path,"rb") as f:
  for _ in iter(lambda:f.read(8*1024*1024),b""): pass
def finalize(part,dest,state,side,expected_sha):
 gzip_crc(part)  # reads all compressed members and verifies CRC/trailer
 digest=file_sha(part)
 if expected_sha and digest.lower()!=expected_sha.lower(): raise RuntimeError("Publisher SHA256 mismatch; partial file preserved.")
 if dest.exists(): raise RuntimeError("Destination already exists; no overwrite performed.")
 part.replace(dest)
 state.update(status="COMPLETE",bytes=dest.stat().st_size,sha256=digest,gzip_crc="passed",completed_utc=now())
 save(side,state)
 print(dest.name+": complete; SHA256 "+digest,flush=True)

class Auth:
 def __init__(self,mode,entitled):
  self.mode=mode; self.token=None; self.expiry=0; self.params=None
  self.session=requests.Session(); self.session.trust_env=False
  if mode!="none" and not entitled:
   raise ValueError("Programmatic bearer/OAuth mode requires --confirm-programmatic-entitlement.")
  if mode=="bearer":
   self.token=getpass.getpass("Authorized EOG access token (hidden, memory only): ").strip()
   if not self.token: raise ValueError("Empty token.")
  if mode=="oauth":
   self.params={"client_id":getpass.getpass("EOG-issued client ID (hidden): ").strip(),
    "client_secret":getpass.getpass("EOG-issued client secret (hidden): "),
    "username":getpass.getpass("EOG username (hidden): "),
    "password":getpass.getpass("EOG password (hidden): "),"grant_type":"password"}
   if not all(self.params.values()): raise ValueError("Empty OAuth input.")
 def headers(self):
  if self.mode=="oauth" and time.monotonic()>=self.expiry:
   r=self.session.post(TOKEN_URL,data=self.params,timeout=(30,60),allow_redirects=False)
   if r.status_code!=200: raise RuntimeError("Official token endpoint denied request: HTTP "+str(r.status_code)+". No authentication response body recorded.")
   j=r.json(); self.token=j.get("access_token")
   if not self.token: raise RuntimeError("Official response has no access token.")
   self.expiry=time.monotonic()+max(1,float(j.get("expires_in",300))-30)
  return {"Authorization":"Bearer "+self.token} if self.token else {}
 def close(self):
  self.session.close()
  if self.params:
   for key in list(self.params): self.params[key]=None
  self.params=None; self.token=None  # no disk/credential-store persistence; Python cannot guarantee secure heap erasure

def download(entry,out,auth):
 url=entry["url"]; name=validate_url(url,entry["product"]); dest=out/name
 side=out/(name+".download.json"); part=out/(name+".part")
 if dest.exists():
  if not side.exists(): raise RuntimeError("Existing destination lacks matching provenance; retained without overwrite.")
  state=read(side)
  if state.get("url")!=url or state.get("status")!="COMPLETE" or state.get("sha256")!=file_sha(dest):
   raise RuntimeError("Existing-file provenance/hash check failed.")
  print(name+": existing complete file verified.",flush=True); return
 pos=part.stat().st_size if part.exists() else 0
 state=read(side) if side.exists() else {"url":url,"product":entry["product"],"filename":name,"started_utc":now(),"status":"PENDING"}
 if state.get("url")!=url: raise RuntimeError("Partial-file source URL differs from requested file.")
 if pos and not side.exists(): raise RuntimeError("Partial file has no matching provenance sidecar.")
 if pos:
  with part.open("rb") as f:
   if f.read(2)!=b"\x1f\x8b": raise RuntimeError("Existing partial file is not a gzip archive.")
  if state.get("total_bytes")==pos:
   finalize(part,dest,state,side,entry.get("expected_sha256")); return
 headers={"Accept-Encoding":"identity",**auth.headers()}
 if pos:
  validator=state.get("etag") or state.get("last_modified")
  if not validator: raise RuntimeError("Resume requires a server ETag or Last-Modified validator; partial file retained.")
  headers.update({"Range":f"bytes={pos}-","If-Range":validator})
 with auth.session.get(url,headers=headers,stream=True,timeout=(30,120),allow_redirects=False) as r:
  if r.status_code in [301,302,303,307,308,401,403]:
   raise RuntimeError("Authentication/redirect response HTTP "+str(r.status_code)+". Use normal browser login/download, or authorized EOG API credentials; no login bypass attempted.")
  if pos and r.status_code!=206: raise RuntimeError("Server did not return a safe partial response; retained existing partial file.")
  if not pos and r.status_code!=200: raise RuntimeError("Unexpected HTTP "+str(r.status_code))
  ct=r.headers.get("Content-Type","").lower()
  if "html" in ct or "json" in ct or "text/" in ct: raise RuntimeError("Received non-data response; nothing appended.")
  if pos:
   match=re.fullmatch(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)",r.headers.get("Content-Range",""))
   if not match or int(match.group(1))!=pos: raise RuntimeError("Invalid Content-Range; nothing appended.")
   total=int(match.group(3))
   if state.get("total_bytes") not in (None,total): raise RuntimeError("Remote size changed; partial file retained.")
   for key,header in [("etag","ETag"),("last_modified","Last-Modified")]:
    if state.get(key) and r.headers.get(header) and state[key]!=r.headers[header]:
     raise RuntimeError("Remote validator changed; partial file retained.")
  else:
   total=int(r.headers["Content-Length"]) if r.headers.get("Content-Length") else None
  stream=r.iter_content(chunk_size=1024*1024)
  first=next(stream,b"")
  if not pos and not first.startswith(b"\x1f\x8b"): raise RuntimeError("Response does not have gzip magic bytes; nothing saved.")
  state.update(status="DOWNLOADING",total_bytes=total,etag=r.headers.get("ETag") or state.get("etag"),
               last_modified=r.headers.get("Last-Modified") or state.get("last_modified"),last_attempt_utc=now())
  save(side,state)
  with part.open("ab" if pos else "wb") as f:
   f.write(first); last=time.monotonic()
   for block in stream:
    f.write(block)
    if time.monotonic()-last>20:
     print(name+": "+str(f.tell())+" bytes stored",flush=True); last=time.monotonic()
 if total is not None and part.stat().st_size!=total:
  raise RuntimeError("Incomplete byte count; run the same command to resume.")
 finalize(part,dest,state,side,entry.get("expected_sha256"))

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--manifest",type=Path,required=True)
 parser.add_argument("--auth",choices=["none","bearer","oauth"],default="none")
 parser.add_argument("--confirm-programmatic-entitlement",action="store_true")
 args=parser.parse_args()
 spec=read(args.manifest)
 if spec.get("official_directory_filenames_verified") is not True:
  raise ValueError("Confirm BOTH actual current filenames in the authorized official directory; template is not a verified request.")
 files=spec.get("files",[])
 if len(files)!=2 or {x["product"] for x in files}!={"average_masked","cf_cvg"}:
  raise ValueError("Exactly the two matching original products are required.")
 for e in files: validate_url(e["url"],e["product"])
 prefixes={e["url"].rsplit("/",1)[-1].split(".")[0] for e in files}
 if len(prefixes)!=1: raise ValueError("The paired files must have the same product/version/year/creation prefix.")
 out=ROOT/"01_原始数据/VIIRS2020"; out.mkdir(parents=True,exist_ok=True)
 auth=Auth(args.auth,args.confirm_programmatic_entitlement)
 try:
  for e in files: download(e,out,auth)
 finally: auth.close()
if __name__=="__main__":
 try: main()
 except (ValueError,RuntimeError,requests.RequestException,OSError,EOFError) as e:
  print("STOPPED: "+str(e),file=sys.stderr)
  sys.exit(2)
