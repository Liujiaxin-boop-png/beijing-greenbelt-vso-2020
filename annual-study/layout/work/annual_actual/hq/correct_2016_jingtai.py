from pathlib import Path
import json,shutil,os,subprocess
import geopandas as gpd, numpy as np, rasterio, shapely
from shapely.geometry import box
from annual_hq import ROOT,YEAR_DIR,REF,write,native,dump,sha,H
from make_road_masks import ARCPY
V=ROOT/'vectors';w=ROOT/'correction_2016';w.mkdir(exist_ok=True)
proof=w/'2016_correction.json'
if proof.exists():
 a=json.loads(proof.read_text(encoding='utf8'));assert sha(ROOT/'results/HQI_2016.tif')==a['corrected_hq_sha256'];print('ALREADY_DONE');raise SystemExit
adm=ROOT.parent/'boundary'/'beijing_greenbelt_full.gpkg'
boundary=ROOT.parent/'boundary'/'plan_30m_centres.tif'
gf=gpd.read_file(V/'OSM_major_2017.gpkg')
source=gf[(gf.highway=='motorway')&(gf.ref=='G3')&(gf['name']=='京台高速')].copy()
plan=gpd.read_file(adm).to_crs(gf.crs).geometry.union_all()
# Five and a half kilometres covers the 3-km road threat radius and the extent of 1-km edge cells plus the map uncertainty.
support=plan.buffer(5500)
snap=source.geometry.intersection(support)
keep=source[snap.length>0].copy();keep['geometry']=snap[snap.length>0]
ll=keep.to_crs(4326).total_bounds
assert ll[0]>116.4 and ll[2]<116.61 and ll[1]>39.55 and ll[3]<39.785,ll
path=w/'documented_open_2016_Jingtai_in_plan_influence.gpkg'
if not path.exists():keep.to_file(path,driver='GPKG')
sp=w/'jingtai.shp';raw=w/'jingtai_native.tif'
if not sp.exists():
 a=keep[['geometry']].copy();a['roadval']=np.ones(len(a),np.int32);a.to_file(sp,driver='ESRI Shapefile')
if not raw.exists():
 proc=subprocess.run([str(ARCPY),str(Path(__file__).with_name('rasterize_arcmap.py')),str(sp),str(REF),str(raw)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(w/'rasterlog.txt').write_bytes(proc.stdout);assert proc.returncode==0,proc.stdout[-1200:]
with rasterio.open(raw) as r,rasterio.open(ROOT/'road'/'roads_2016.tif') as b:
 fixed=r.read(1,masked=True).filled(0)==1;old=b.read(1)==1;prof=b.profile
 assert fixed.shape==old.shape and abs(r.transform.c-b.transform.c)<1e-7
 combined=(old|fixed).astype(np.uint8);adds=int((fixed & ~old).sum())
road=w/'roads_2016_open_confirmed.tif'
write(road,combined,prof,255,dict(method='2016 OSM snapshot union first post-opening G3 mainline within 5500m formal plan. Documented 2016-12 opening by Beijing Municipal Commission of Transport.'))
kw=ROOT/'full_scope_frozen_k.json';prev=json.loads(kw.read_text(encoding='utf8'));k=prev['k']
lc=YEAR_DIR/'CLCD_2016.tif';ws=ROOT/'native'/'2016_Jingtai_open'
dat=native(2016,lc,road,ws,k)
of=ROOT/'results'/'HQI_2016.tif';od=ROOT/'degradation'/'D_2016.tif';orec=od.with_suffix('.json')
for f in [of,od,orec,kw]:shutil.copy2(f,w/(f.stem+'_raw_OSM'+f.suffix))
with rasterio.open(ws/'quality_c.tif') as r,rasterio.open(ws/'deg_sum_c.tif') as s,rasterio.open(lc) as l,rasterio.open(boundary) as m,rasterio.open(of) as o:
 q=r.read(1);d=s.read(1);territory=m.read(1)==1;c=l.read(1);good=(q!=r.nodata)&np.isfinite(H[c]);focal=territory & np.isin(c,[2,3,4,5,9]) & good
 hq=np.where(good,q,-9999).astype(np.float32);dd=np.where(good,d,-9999).astype(np.float32)
 maxD=float(d[focal].max());Dall=dict(prev['Dmax_by_year']);Dall['2016']=maxD
 assert max(Dall.values())/2==k
 err=float(np.max(np.abs(q[good].astype(float)-H[c[good]]*k**2.5/(d[good].astype(float)**2.5+k**2.5))));assert err<1e-6
 shift=hq[focal]-o.read(1)[focal];counts=int((np.abs(shift)>1.e-7).sum());med=float(shift.mean());maxabs=float(np.abs(shift).max())
 profile=r.profile.copy()
write(of,hq,profile,-9999,dict(year='2016',common_k=str(k),stage='native InVEST model includes documented December 2016 Beijing G3 mainline opening'))
write(od,dd,profile,-9999,dict(year='2016',common_k=str(k),stage='native InVEST model includes documented December 2016 Beijing G3 mainline opening'))
rr=json.loads(orec.read_text(encoding='utf8'));rr.update(source_native=str(ws/'deg_sum_c.tif'),native_stack_sha256=sha(dat),road_sha256=sha(road),road_path=str(road),D_sha256=sha(od),quality_formula_max_abs_error=err,correction_note=str(proof))
dump(orec,rr)
prev['Dmax_by_year']=Dall;prev['documented_road_correction_2016']=str(proof);dump(kw,prev)
rec=dict(official_opening_url='https://jtw.beijing.gov.cn/xxgk/ndzdgz/201912/t20191210_1018028.html',official_opening_date='2016-12-09',verify_date='https://jtgl.beijing.gov.cn/jgj/94220/mrcxts/493986/index.html',independent_route_audit=str(ROOT/'官方通车与快照局部空间核验.csv'),geometry_source='2017-12-31 OSM ways explicitly tagged highway=motorway, ref=G3 and name=京台高速, clipped to planning boundary +5500m. New opening confirmed on this section. Links and other roads outside the calibrated route stay as observed.',road_geometry_length_projected_km=float(keep.length.sum()/1000),clipped_wgs84_bbox=ll.tolist(),added_road_pixels=adds,full_plan_habitat_pixels=len(shift),impact_abs_gt_1e_minus7_pixel_count=counts,mean_habitat_delta=med,max_abs_habitat_delta=maxabs,Dmax_plan_hab=maxD,common_k=k,corrected_hq_sha256=sha(of),corrected_d_sha256=sha(od),formula_maxabs_error=err)
dump(proof,rec);print(json.dumps(rec,ensure_ascii=False,indent=2))
