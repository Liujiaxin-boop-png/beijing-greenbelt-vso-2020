"""Verify all regional model and Beijing-wide windows through GDAL, independently of the uploader's LZW decoder."""
from pathlib import Path
import json,hashlib,os,ctypes,msvcrt,shutil
import numpy as np,rasterio,tifffile
from clcd_native import root,work,wide,original_model,localfull
q=work/'qa';q.mkdir(exist_ok=True)
api=ctypes.WinDLL('kernel32',use_last_error=True)
ctl=api.DeviceIoControl;ctl.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32),ctypes.c_void_p];ctl.restype=ctypes.c_int
all_q=[]
for year in range(2015,2026):
 report=json.loads((root/f'CLCD_{year}_source.json').read_text(encoding='utf8'));tmp=q/f'QA_national_{year}_sparse.tif'
 if year==2020:nation=localfull
 else:
  with tmp.open('wb') as fw:
   h=msvcrt.get_osfhandle(fw.fileno());b=ctypes.c_uint32()
   assert ctl(h,0x000900C4,None,0,None,0,ctypes.byref(b),None),ctypes.get_last_error()
   fw.truncate(report['national_file_bytes'])
   for ran in report['response_ranges']:
    a,z=ran['range'];val=(work/'ranges'/str(year)/f'{a}-{z}.bin').read_bytes();assert hashlib.sha256(val).hexdigest()==ran['sha256']
    fw.seek(a);fw.write(val)
  nation=tmp
 with rasterio.open(nation) as f,rasterio.open(report['raw']) as raw,rasterio.open(report['model']) as model:
  national=f.read(1,window=wide);aa=raw.read(1);bb=model.read(1)
  assert np.array_equal(national,aa) and np.array_equal(f.read(1,window=original_model),bb)
  all_q.append(dict(year=year,n_wide_pixels=aa.size,n_model_pixels=bb.size,wide_mismatches=0,model_mismatches=0,n_model_nodata=int(np.count_nonzero(bb==0)),model_sha256=hashlib.file_digest(open(report['model'],'rb'),'sha256').hexdigest(),wide_sha256=hashlib.file_digest(open(report['raw'],'rb'),'sha256').hexdigest()))
 if year!=2020:tmp.unlink()
 print(year,'PASS NATIONAL GDAL PIXEL EQUALITY',flush=True)
(work/'independent_gdal_QA.json').write_text(json.dumps(all_q,indent=2),encoding='utf8')
for f in [work/'independent_gdal_QA.json',work/'province_checks/beijing_province_check_2015.json',work/'province_checks/beijing_province_check_2025.json',work/'model/NASADEM_source_and_methods.json',Path(r'D:\ER219_work\indicator_rebuild_20261107\official_sources_data\CLCD18180184.json')]:
 shutil.copy2(f,root/f.name)
