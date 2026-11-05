"""219: run official JRC MSPA 2.4; verify Core coding; preserve native outputs.
No existing research input is changed. Synthetic checks precede six real runs.
Core codes17/117 are from MSPA Guide p6; input0 missing,1 background,2 foreground.
"""
from pathlib import Path
import argparse, json, hashlib, shutil, subprocess, time
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import binary_erosion, distance_transform_edt

PROJECT=Path(__file__).resolve().parents[2]
AUDIT=PROJECT/'02_过程文件'/'参数文献核验'
OUT=PROJECT/'02_过程文件'/'mspa'
SOFT=PROJECT/'01_原始数据'/'软件原始安装包'/'JRC_MSPA_2_4'
CORE_CODES=[17,117]
ALLOWED_CODES=[0,1,3,5,9,17,33,35,37,65,67,69,100,101,103,105,109,117,129,133,135,137,165,167,169,220]
PARAMS=['-eew','1','-graphfg','8','-internal','1','-transition','1']

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def save_json(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

def setup():
 SOFT.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 src=AUDIT/'MSPA核心核验'
 for n in ['mspa_win64.exe','readme.txt','GTB_commit.json','jeolib-miallib_commit.json']:
  if (src/n).exists():shutil.copy2(src/n,SOFT/n)
 for n in ['MSPA_Guide_official.pdf','SoilleVogt2022_MSPA.pdf','GTB_fsp.c','miallib_mspa.c']:
   # Evidence copies are optional; the verified native binary is mandatory.
   # A code-only reproduction need not possess a journal PDF to run MSPA.
   if (AUDIT/'sources'/n).is_file():shutil.copy2(AUDIT/'sources'/n,SOFT/n)
 save_json(SOFT/'source_manifest.json',{'download_date':'2026-11-06','binary_version':'2.4 October2026','binary_url':'https://raw.githubusercontent.com/ec-jrc/GTB/main/MSPAstandalone/mspa_win64.exe','official_entry':'https://forest.jrc.ec.europa.eu/en/activities/lpa/mspa/','guide_url':'https://ies-ows.jrc.ec.europa.eu/gtb/GTB/MSPA_Guide.pdf','GTB_source_commit':'8ea668f26e8355a8f8566f9e209d833130bc3984','miallib_source_commit':'d581cc66f27a03bfbbbceaf5c25f099b7100b791','binary_sha256':sha(SOFT/'mspa_win64.exe')})
 return SOFT/'mspa_win64.exe'

def native_run(exe,work):
 cmd=[str(exe),'-i','input_mspa.tif','-o','native_mspa.tif']+PARAMS
 start=time.time();r=subprocess.run(cmd,cwd=str(work),capture_output=True,text=True,errors='replace')
 (work/'native_stdout.log').write_text(r.stdout,encoding='utf-8');(work/'native_stderr.log').write_text(r.stderr,encoding='utf-8')
 rec={'command':cmd,'cwd':str(work),'exit_code':r.returncode,'elapsed_seconds':time.time()-start}
 save_json(work/'command_receipt.json',rec)
 if r.returncode!=0 or not (work/'native_mspa.tif').exists():raise RuntimeError('MSPA failed: '+str(work))
 return rec

def synthetic(exe):
 w=OUT/'synthetic_core_check';w.mkdir(exist_ok=True)
 a=np.ones((65,65),dtype=np.uint8);a[4:61,4:61]=2;a[15:50,15:50]=1;a[25:40,25:40]=2;a[7,7]=1;a[8:11,53:56]=0
 profile={'driver':'GTiff','height':65,'width':65,'count':1,'dtype':'uint8','crs':'EPSG:32650','transform':from_origin(400000,4500000,30,30),'nodata':0,'compress':'none'}
 with rasterio.open(w/'input_mspa.tif','w',**profile) as d:d.write(a,1)
 rec=native_run(exe,w)
 with rasterio.open(w/'native_mspa.tif') as d:y=d.read(1);crs=str(d.crs);transform=list(d.transform)
 core=np.isin(y,CORE_CODES);eroded=binary_erosion(a==2,structure=np.ones((3,3),bool),border_value=0)
 # Restrict shape-equivalence check to windows containing no true NoData.
 valid=binary_erosion(a!=0,structure=np.ones((5,5),bool),border_value=0)
 edt=distance_transform_edt(a==2)
 rec.update({'core_code_reference':'officialMSPAGuidep6','actual_codes':np.unique(y).tolist(),'core17_count':int(np.count_nonzero(y==17)),'core117_count':int(np.count_nonzero(y==117)),'missing129_count':int(np.count_nonzero(y==129)),'input_missing0_count':int(np.count_nonzero(a==0)),'mismatch_core_vs3x3_valid_interior':int(np.count_nonzero((core!=eroded)&valid)),'mismatch_core_vsEDTgt1_valid_interior':int(np.count_nonzero((core!=(edt>1))&valid)),'mismatch_core_vsEDTgt1_98_valid_interior':int(np.count_nonzero((core!=(edt>1.98))&valid)),'native_crs':crs,'native_transform':transform,'input_crs':'EPSG:32650','input_transform':list(profile['transform'])})
 rec['PASS']=rec['core17_count']>0 and rec['core117_count']>0 and rec['missing129_count']==rec['input_missing0_count'] and rec['mismatch_core_vs3x3_valid_interior']==0 and rec['mismatch_core_vsEDTgt1_valid_interior']>0
 save_json(w/'synthetic_QA.json',rec)
 if not rec['PASS']:raise RuntimeError('SyntheticCoreQAfailed')
 print('SYNTHETIC_PASS '+json.dumps(rec,ensure_ascii=False),flush=True)
 return rec

def one(exe,source,product,group,codes):
 w=OUT/(product+'_'+group);w.mkdir(exist_ok=True)
 with rasterio.open(source) as s:
  a=s.read(1);valid=s.read_masks(1)>0;profile=s.profile.copy();src_crs=s.crs;src_tr=s.transform;source_shape=s.shape;bounds=list(s.bounds)
 if not valid.any():raise ValueError('No valid source pixels')
 if not set(np.unique(a[valid])).issubset({1,2,3,4,5,6,7,8,9}):raise ValueError('Unexpected sourcecode')
 x=np.zeros(a.shape,dtype=np.uint8);x[valid]=1;x[valid&np.isin(a,codes)]=2
 profile.pop('blockxsize',None)
 profile.update(driver='GTiff',dtype='uint8',count=1,nodata=0,compress='none',tiled=False,blockysize=1)
 # Native input is clean singleband8bit, no overviews.
 with rasterio.open(w/'input_mspa.tif','w',**profile) as d:d.write(x,1)
 rec=native_run(exe,w)
 with rasterio.open(w/'native_mspa.tif') as n:
  y=n.read(1);native_crs=n.crs;native_tr=n.transform;native_shape=n.shape;native_nodata=n.nodata
 if y.shape!=x.shape:raise RuntimeError('Native dimensions changed')
 unknown=sorted(set(np.unique(y))-set(ALLOWED_CODES))
 if unknown:raise RuntimeError('Unknown native classcodes'+str(unknown))
 if np.any((y==129)!=~valid):raise RuntimeError('Native missingdatamask altered')
 c=np.zeros(y.shape,dtype=np.uint8);c[np.isin(y,CORE_CODES)]=1;c[~valid]=255
 if np.any((c==1)&(x!=2)):raise RuntimeError('Core outsideforeground')
 native_georef_matches=native_crs==src_crs and native_tr==src_tr
 cp=profile.copy();cp.update(nodata=255,compress='lzw')
 with rasterio.open(w/'core_mask_georef.tif','w',**cp) as d:
  d.write(c,1);d.update_tags(core_codes='17,117',method='official_JRC_MSPA2.4',effective_edge_width='1',foreground_connectivity='8',georeference_provenance='native_preserved' if native_georef_matches else 'copied_from_exact_same_shape_input')
 # Always preserve raw native file; separate georeferenced fullclass copy if needed.
 if not native_georef_matches:
  pp=profile.copy();pp.update(nodata=129,compress='lzw')
  with rasterio.open(w/'mspa_classes_georef.tif','w',**pp) as d:d.write(y,1);d.update_tags(georeference_provenance='copied_from_exact_same_shape_input')
 v,n=np.unique(y,return_counts=True);counts={str(int(k)):int(z) for k,z in zip(v,n)}
 frame=np.zeros(y.shape,bool);frame[0,:]=frame[-1,:]=True;frame[:,0]=frame[:,-1]=True
 rec.update({'source':str(source),'source_sha256':sha(source),'input_sha256':sha(w/'input_mspa.tif'),'native_sha256':sha(w/'native_mspa.tif'),'core_sha256':sha(w/'core_mask_georef.tif'),'product':product,'group':group,'foreground_classcodes':codes,'input_coding':{'0':'trueNoData','1':'other_valid_landcover_background','2':'focalforeground'},'core_codes':CORE_CODES,'core_code_reference':'officialMSPAGuidep6','native_class_counts':counts,'core_pixels':int(np.count_nonzero(c==1)),'foreground_pixels':int(np.count_nonzero(x==2)),'native_core_on_outer_frame':int(np.count_nonzero((c==1)&frame)),'foreground_on_outer_frame':int(np.count_nonzero((x==2)&frame)),'missing_pixels':int(np.count_nonzero(~valid)),'source_shape':source_shape,'source_crs':str(src_crs),'source_crs_wkt':src_crs.to_wkt() if src_crs else None,'source_transform':list(src_tr),'source_bounds':bounds,'native_crs':str(native_crs),'native_transform':list(native_tr),'native_nodata':native_nodata,'native_georeference_preserved':native_georef_matches,'georeferenced_core':str(w/'core_mask_georef.tif'),'native_output_preserved':True,'QA_PASS':True})
 save_json(w/'run_receipt.json',rec);print('RUN_COMPLETE '+product+' '+group+' core='+str(rec['core_pixels'])+' native_georef='+str(native_georef_matches),flush=True)
 return rec

def verify_real_runs():
 p=OUT/'219_MSPA_six_runs_manifest.json';m=json.loads(p.read_text(encoding='utf-8'));qa=[]
 fgcodes=[1,3,5,9,17,33,35,37,65,67,69,101,103,105,109,117,133,135,137,165,167,169]
 for rec in m['completed_runs']:
  w=Path(rec['cwd'])
  with rasterio.open(w/'input_mspa.tif') as d:x=d.read(1);crs=d.crs;tr=d.transform
  with rasterio.open(w/'native_mspa.tif') as d:y=d.read(1)
  with rasterio.open(w/'core_mask_georef.tif') as d:c=d.read(1);dcrs=d.crs;dtr=d.transform
  valid=binary_erosion(x!=0,structure=np.ones((5,5),bool),border_value=0)
  eroded=binary_erosion(x==2,structure=np.ones((3,3),bool),border_value=0)
  q={'product':rec['product'],'group':rec['group'],'foreground_reconstruction_mismatch':int(np.count_nonzero(np.isin(y,fgcodes)!=(x==2))),'core_vs3x3_validinterior_mismatch':int(np.count_nonzero((np.isin(y,CORE_CODES)!=eroded)&valid)),'derived_core_matches_native_exactly':bool(np.array_equal(c==1,np.isin(y,CORE_CODES))),'derived_crs_equals_input':dcrs==crs,'derived_transform_equals_input':dtr==tr,'derived_missing_equals_input':bool(np.array_equal(c==255,x==0))}
  q['PASS']=q['foreground_reconstruction_mismatch']==0 and q['core_vs3x3_validinterior_mismatch']==0 and all(q[k] for k in ['derived_core_matches_native_exactly','derived_crs_equals_input','derived_transform_equals_input','derived_missing_equals_input'])
  rec['full_pixel_QA']=q;save_json(w/'run_receipt.json',rec);qa.append(q)
 m['full_pixel_QA_PASS']=all(q['PASS'] for q in qa);m['spatial_scope']='completeworkingbackground_notstudyclippedresults';save_json(p,m);save_json(OUT/'219_MSPA_full_pixel_QA.json',qa)
 if not m['full_pixel_QA_PASS']:raise RuntimeError('FullpixelQAfailed')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--synthetic-only',action='store_true');args=ap.parse_args()
 exe=setup();test=synthetic(exe)
 if args.synthetic_only:return
 runs=[]
 for product,source in [('clcd2020',Path(r'D:\ER219_work\spatial\clcd2020.tif')),('worldcover2020',Path(r'D:\ER219_work\spatial\worldcover2020_common30m.tif'))]:
  for group,codes in [('forest_shrub',[2,3]),('grassland',[4]),('water_wetland',[5,9])]:
   runs.append(one(exe,source,product,group,codes));save_json(OUT/'219_MSPA_six_runs_manifest.json',{'synthetic_pass':test['PASS'],'completed_runs':runs,'all_six_complete':len(runs)==6})
 verify_real_runs()
 print('ALL_SIX_COMPLETE',flush=True)
if __name__=='__main__':main()
