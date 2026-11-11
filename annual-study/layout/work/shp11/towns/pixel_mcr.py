"""Hold source patches or the resistance surface constant in two complementary endpoint runs."""
from pathlib import Path
import os,concurrent.futures,subprocess,sys
import numpy as np, pandas as pd,geopandas as gp,rasterio as rio
base=Path('D:/ER219_work/annual_actual'); w=Path(__file__).resolve().parent
sys.path.insert(0,str(base/'analysis/geo'))
from exactextract import exact_extract
model=Path('D:/ER219_work/feng_round2/source_mcr/TwoSource.exe')
root=base/'mcr'
def hybrid(t):
    c,s=t; folder=w/f'mcr_resistance{c}_source{s}';folder.mkdir(exist_ok=True)
    for src,dst in [(root/str(c)/'cost.f32',folder/'cost.f32'),(root/str(s)/'dpc.i32',folder/'dpc.i32')]:
        if not dst.exists():os.link(src,dst)
    if not (folder/'surface_dpc.f32').exists():subprocess.run([str(model),str(folder),'dpc','4033','4071','30'],check=True)
    return folder/'surface_dpc.f32'
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        v01,v10=[Path('D:/ER219_work/towndisc11/evidence')/f'mcr_resistance{c}_source{s}/surface_dpc.f32' for c,s in [(2015,2025),(2025,2015)]]
    arrays={}
    for i,j,v in [(0,0,root/'2015'/'surface_dpc.f32'),(1,1,root/'2025'/'surface_dpc.f32'),(0,1,v01),(1,0,v10)]:
        arrays[i,j]=np.memmap(v,dtype='float32',mode='r')
        assert len(arrays[i,j])==4071*4033
    patches=gp.read_file(w/'case_hotspots.gpkg',layer='patches')
    with rio.open(root/'2015'/'MCR_2015.tif') as ds:
        assert np.allclose(ds.read(1).ravel(),arrays[0,0])
        masks=exact_extract(ds,patches,['cell_id','coverage'],include_cols=['code'],output='pandas')
    recs=[]
    for it in masks.itertuples():
        ar=np.asarray(it.coverage,float)
        vals={k:np.average(v[np.asarray(it.cell_id,int)],weights=ar) for k,v in arrays.items()}
        d=vals[1,1]-vals[0,0]
        resistance=.5*((vals[1,0]-vals[0,0])+(vals[1,1]-vals[0,1]))
        source=.5*((vals[0,1]-vals[0,0])+(vals[1,1]-vals[1,0]))
        assert abs(d-resistance-source)<1e-8
        recs.append(dict(code=it.code,mcr2015=vals[0,0],mcr2025=vals[1,1],cost15sources25=vals[0,1],cost25sources15=vals[1,0],delta_MCR_raw=d,resistance= resistance,source=source))
    df=pd.DataFrame(recs)
    df.to_csv(w/'八片区MCR两项模型输入变化分解.csv',index=False,encoding='utf-8-sig')
    print(df.round(1).to_string(index=False))
