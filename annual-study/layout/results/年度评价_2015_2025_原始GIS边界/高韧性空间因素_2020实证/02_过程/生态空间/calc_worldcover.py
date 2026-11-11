"""X1/study strata: native ESA WorldCover 2020 v100 pixels, overlap fraction times ellipsoidal pixel area, full 500 m squares. No source is overwritten."""
from pathlib import Path
import json, hashlib, numpy as np, pandas as pd, geopandas as gp, rasterio, shapely, exactextract as ex
HERE=Path(__file__).resolve().parent
GRID=next(Path(r'D:/ER219_results/年度评价_2015_2025_原始GIS边界/计算结果与核验/01_全区与格网').glob('annual_grid_500.gpkg'))
SRC=Path(r'D:/ER219_project/生态韧性新研究/数据下载_20261020/02_WorldCover地类核查/2020/WorldCover_2020_v100_study_envelope.tif')
codes={10:'tree',20:'shrub',30:'grass',40:'crop',50:'built',60:'bare',70:'snow',80:'water',90:'wetland',95:'mangrove',100:'moss'}
packed=HERE.parents[1]/'01_原始数据'/'ESA_WorldCover2020_v100'/SRC.name
if packed.exists():SRC=packed
grid=gp.read_file(GRID,layer='grid500')
assert grid.grid_id.is_unique and len(grid)==4478
def calc(geom,suffix):
    proj=geom.copy(); proj.geometry=proj.geometry.segmentize(25); proj=proj.to_crs(4326)
    results=[]
    with rasterio.open(SRC) as f:
        area_factor=(np.pi/180)**2*abs(f.transform.a*f.transform.e)*6378137**2*(1-0.0066943799901413165)
        b=f.bounds; assert ((proj.total_bounds>=np.array([b.left,b.bottom,-1e9,-1e9])) & (proj.total_bounds<=np.array([1e9,1e9,b.right,b.top]))).all()
        for i in range(0,len(proj),100):
            tab=ex.exact_extract(f,proj.iloc[i:i+100],['values','coverage','center_y'],include_cols=['grid_id'],output='pandas')
            for w in tab.itertuples(index=False):
                lat=np.deg2rad(w.center_y); weight=w.coverage*area_factor*np.cos(lat)/(1-0.0066943799901413165*np.sin(lat)**2)**2
                q=np.bincount(w.values.astype(int),weights=weight,minlength=101)
                total=q[list(codes)].sum()
                results.append({'grid_id':w.grid_id,**{k+suffix:q[j]/total if total else np.nan for j,k in codes.items()},'sample_m2'+suffix:total})
    return pd.DataFrame(results)
square=grid.copy();square.geometry=shapely.box(grid.ix*500,grid.iy*500,(grid.ix+1)*500,(grid.iy+1)*500)
out=grid.drop(columns='geometry').merge(calc(square,'_full'),on='grid_id',validate='one_to_one').merge(calc(grid,'_clip'),on='grid_id',validate='one_to_one')
for k in ['_full','_clip']:
    arr=np.vstack([out['tree'+k]+out['shrub'+k],out['crop'+k],out['water'+k]+out['wetland'+k],out['built'+k],out['grass'+k],out['bare'+k]])
    labels=np.array(['林灌','耕地','水体湿地','建设','草地','裸地'])
    out['largest_cover'+k]=labels[np.argmax(arr,axis=0)]
    out['cover50'+k]=np.where(np.max(arr,axis=0)>.5,out['largest_cover'+k],'混合')
out.to_csv(HERE/'worldcover500.csv',index=False,encoding='utf-8-sig',float_format='%.10g')
rat=out.sample_m2_full/250000
assert np.max(np.abs(rat-1))<.01
rec=dict(n=len(grid),area=grid.area.sum()/1e6,geom='500 m full square; clip is supplementary; both densified to 25m before transformation',src=str(SRC),url='https://esa-worldcover.org/en/data-access',class_codes=codes,sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),coverage_vs_nominal=rat.describe().to_dict(),coverage_vs_clipped=(out.sample_m2_clip/out.area).describe().to_dict(),cover50=out.cover50_full.value_counts().to_dict(),method='Native geographic pixels weighted by polygon coverage and local ellipsoidal pixel area; water=80, wetlands=90; built=50; >50% decides dominant cover, others mixed.',x1=out.built_full.describe().to_dict())
(HERE/'worldcover_sources.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(rec,ensure_ascii=False,indent=1))
