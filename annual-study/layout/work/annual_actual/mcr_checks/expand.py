"""Endpoint background sensitivity, all sides +340 native pixels (=10.20km) and a complete recomputation."""
from pathlib import Path
import json,types,sys,subprocess,os,time
import numpy as np,pandas as pd,rasterio as rio
import threshold as th
D=th.D;A=th.A;orig=th.orig
yb=A/'years';sys.path.insert(0,str(yb))
import clcd_native as lc
def run(y):
 ws=D/str(y);full=ws/'expanded10200';full.mkdir(exist_ok=True,parents=True)
 base=A/'mcr'/str(y)
 out=ws/'MCR_expand10200.tif';land=full/f'CLCD_{y}_expand10200.tif'
 if (full/'qa.json').is_file() and out.exists():return
 with rio.open(yb/'model'/f'CLCD_{y}.tif') as ss,rio.open(lc.root/f'CLCD_{y}_Beijing_native.tif') as sw:
  native=sw.window(*ss.bounds).round_offsets().round_lengths();buf=340
  w=rio.windows.Window(native.col_off-buf,native.row_off-buf,native.width+2*buf,native.height+2*buf)
  assert w.col_off>=0 and w.row_off>=0 and w.col_off+w.width<=sw.width and w.row_off+w.height<=sw.height
  a=sw.read(1,window=w);print(y,a.shape, 'nodata',np.count_nonzero(a==0),flush=True)
  assert np.array_equal(a[buf:-buf,buf:-buf],ss.read(1))
  pr=ss.profile.copy();pr.update(width=int(w.width),height=int(w.height),transform=sw.window_transform(w))
  if not land.exists():
   with rio.open(land,'w',**pr) as ds:ds.write(a,1)
  basepr=ss.profile;del a
 if not (full/'cost.f32').exists():
  prep=(orig/'prepare.py').read_text(encoding='utf8').replace("D=Path(__file__).resolve().parent","D=annual_dir").replace("P=Path(r'D:\\ER219_work\\spatial\\clcd2020.tif')","P=annual_land")
  mod=types.ModuleType('prepare');mod.__dict__.update(__name__='__main__',__file__=str(orig/'prepare.py'),annual_dir=full,annual_land=land)
  exec(compile(prep,'prepare.py','exec'),mod.__dict__);sys.modules['prepare']=mod
  exec(compile((orig/'sources.py').read_text(encoding='utf8'),'sources.py','exec'),{'__name__':'__main__','__file__':str(orig/'sources.py')})
 surface=full/'surface_dpc.f32'
 if not surface.exists():
  subprocess.run([str(orig/'TwoSource.exe'),str(full),'dpc',str(pr['width']),str(pr['height']),'30'],check=True)
 m=np.memmap(surface,dtype='float32',mode='r',shape=(pr['height'],pr['width']))
 sub=m[buf:-buf,buf:-buf];assert sub.min()>=0
 prout=basepr.copy();prout.update(dtype='float32',nodata=-9999,compress='deflate',predictor=3)
 tmp=out.with_suffix('.partial.tif')
 with rio.open(tmp,'w',**prout) as ds:ds.write(sub,1)
 tmp.replace(out)
 s0=pd.read_csv(base/'source_dPC.csv');s1=pd.read_csv(full/'source_dPC.csv')
 with rio.open(base/'sources_area.tif') as s:low=s.read(1)
 with rio.open(full/'sources_area.tif') as s:high=s.read(1,window=rio.windows.Window(buf,buf,low.shape[1],low.shape[0]))
 tag=lambda x:set(x.loc[x.dPC_percent>.5,'source_id'].tolist())
 k0,k1=tag(s0),tag(s1)
 cross=[]
 for o in s0.source_id:
  hit,cnt=np.unique(high[low==o],return_counts=True)
  best=int(hit[np.argmax(cnt)]);overlap=float(cnt.max()/cnt.sum())
  cross.append(dict(original_id=int(o),best_expanded_id=best,pixel_overlap=overlap,base_selected=int(o) in k0,expanded_selected=best in k1,was_edge=bool(s0.loc[s0.source_id==o,'touches_background_edge'].iloc[0])))
 pd.DataFrame(cross).to_csv(full/'source_correspondence.csv',index=False,encoding='utf-8-sig')
 with rio.open(base/f'MCR_{y}.tif') as s:baseline=s.read(1)
 change=sub.astype('float64')-baseline
 qa=dict(year=y,extra_width_each_side_m=buf*30,base_cells=list(low.shape),expanded_cells=list(m.shape),n_original_candidates=len(s0),n_expanded_candidates=len(s1),n_original_sources=len(k0),n_expanded_sources=len(k1),original_selected_edge_ids=s0.loc[(s0.dPC_percent>.5)&(s0.touches_background_edge),'source_id'].tolist(),expanded_selected_edge_ids=s1.loc[(s1.dPC_percent>.5)&(s1.touches_background_edge),'source_id'].tolist(),original_selected_with_expanded_selected_correspondence=sum(t['base_selected'] and t['expanded_selected'] for t in cross),full_original_background_raw_MCR_MAD=float(np.abs(change).mean()),full_original_background_raw_MCR_median_delta=float(np.median(change)),note='Full original raster domain includes surrounding area; township and planning-area results must use the target polygon. Same-year recalculation increases background, recalculates MSPA source patch identity, graph, dPC and cost from all enlarged landscape, then crops the cost field to the exact previous grid.')
 (full/'qa.json').write_text(json.dumps(qa,indent=2),encoding='utf8');print(qa,flush=True)
if __name__=='__main__':
 for x in [2015,2025]:run(x)
