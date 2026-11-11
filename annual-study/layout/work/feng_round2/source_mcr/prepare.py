"""Build five-factor resistance and native mixed blue-green cores for 2020 trial."""
from pathlib import Path
import numpy as np, rasterio as rio, json, subprocess, time
from scipy import ndimage as nd
from rasterio.warp import reproject, Resampling
from rasterio.merge import merge
D=Path(__file__).resolve().parent
P=Path(r'D:\ER219_work\spatial\clcd2020.tif')
def note(t):print(t,flush=True)
def save(name,a,nod,profile):
    q=profile.copy()
    q.update(driver='GTiff',count=1,dtype=str(a.dtype),nodata=nod,compress='lzw')
    with rio.open(D/name,'w',**q) as dst:dst.write(a,1)
if __name__=='__main__':
    with rio.open(P) as src:
        a=src.read(1);valid=src.read_masks(1)>0;profile=src.profile.copy()
    note(str((a.shape,np.unique(a[valid]))))
    assert set(np.unique(a[valid]))<={1,2,3,4,5,7,8,9}
    fg=np.isin(a,[2,3,4,5,9])&valid
    m=D/'input_mspa.tif'
    if not (D/'native_mspa.tif').exists():
        q=profile.copy();q.pop('blockxsize',None);q.update(dtype='uint8',nodata=0,tiled=False,blockysize=1,compress='none')
        with rio.open(m,'w',**q) as dst:dst.write(np.where(valid,np.where(fg,2,1),0).astype('uint8'),1)
        exe=next(Path(r'D:\ER219_raw').rglob('mspa_win64.exe'))
        res=subprocess.run([str(exe),'-i',m.name,'-o','native_mspa.tif','-eew','1','-graphfg','8','-internal','1','-transition','1'],cwd=str(D),capture_output=True)
        (D/'mspa_console.txt').write_bytes(res.stdout+res.stderr)
        res.check_returncode()
    with rio.open(D/'native_mspa.tif') as s:core=np.isin(s.read(1),[17,117])
    assert not np.any(core & ~fg)
    corelabels,k=nd.label(core,np.ones((3,3))); counts=np.bincount(corelabels.ravel());keep=(counts*900>1e6);keep[0]=False
    index=np.cumsum(keep)*keep; ids=index[corelabels].astype('int32')
    save('sources_area.tif',ids,0,profile)
    note(f'n_sources={ids.max()}')
    demfiles=list(Path(r'D:\ER219_raw').rglob('NASADEM_HGT_*.tif'))
    demfiles=[f for f in demfiles if not 'window' in f.name and f.name.count('_')==2]
    note(str(demfiles))
    srcs=[rio.open(f) for f in demfiles]
    merged,tr=merge(srcs,nodata=-9999,dtype='float32')
    dem=np.full(a.shape,-9999,dtype='float32')
    reproject(merged[0],dem,src_transform=tr,src_crs=srcs[0].crs,src_nodata=-9999,dst_transform=profile['transform'],dst_crs=profile['crs'],dst_nodata=-9999,resampling=Resampling.bilinear)
    del merged
    for s in srcs:s.close()
    demmissing=dem==-9999
    if demmissing.any():
        inds=nd.distance_transform_edt(demmissing,return_distances=False,return_indices=True)
        demfilled=dem[tuple(inds)]
    else:demfilled=dem
    gy,gx=np.gradient(demfilled,30,30);slope=np.rad2deg(np.arctan(np.hypot(gx,gy)))
    valid_r=valid & ~demmissing
    # Central finite difference of fixed topography. Exclude pixels adjacent to missing DEM from slope calculation.
    valid_r &= ~nd.binary_dilation(demmissing,np.array([[0,1,0],[1,1,1],[0,1,0]]))
    # Read threshold breaks and partial factor weights from Ecological Indicators 2024 (tables 2–3).
    def val(x,br):return (2*np.searchsorted(br,x,side='right')+1).astype('float32')
    w=np.array([.0510,.1213,.3250,.0503,.0667]);w/=sum(w)
    impdist=nd.distance_transform_edt(a!=8,sampling=30).astype('float32')
    waterdist=nd.distance_transform_edt(a!=5,sampling=30).astype('float32')
    lc=np.array([0,5,1,1,1,3,0,7,9,3],dtype='float32')[a]
    cost=(w[0]*val(dem,[300,600,900,1200])+w[1]*val(slope,[3,8,15,25])+w[2]*lc+w[3]*val(waterdist,[1000,3000,5000,10000])+w[4]*(10-val(impdist,[300,500,1000,2000]))).astype('float32')
    cost[~valid_r]=-9999;save('cost5.tif',cost,-9999,profile)
    (D/'cost_receipt.json').write_text(json.dumps(dict(landcover=str(P),dem=[str(f) for f in demfiles],total=int(a.size),cost_valid=int(valid_r.sum()),src_area_filtered=int(ids.max()),cost_range=[float(cost[valid_r].min()),float(cost[valid_r].max())],weights=w.tolist(),source_ref='https://doi.org/10.1016/j.ecolind.2024.112382 tables 2-3; reweight 5 factors; bare=7 from Jin 2024; shrubs grouped with woodland and wetlands with water. No NTL correction.'),indent=2),encoding='utf8')
    note('completed')
