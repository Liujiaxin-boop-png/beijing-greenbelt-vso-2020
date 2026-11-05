"""Run the pinned native InVEST executable and audit actual raster outputs."""
from pathlib import Path
import json,subprocess,hashlib,time
import numpy as np
import rasterio

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'02_过程文件/hq';O=ROOT/'03_结果文件/hq';O.mkdir(exist_ok=True)
EXE=Path('D:/Apps/InVEST-3.20.2/invest.exe')
ALIAS=Path('D:/ER219_work/hq')

def dump(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def native(args,stack_path,log_path):
    stack={'invest_version':'3.20.2','model_id':'habitat_quality','model_name':'natcap.invest.habitat_quality.habitat_quality','args':args}
    dump(stack_path,stack)
    t=time.monotonic()
    with log_path.open('wb') as f:
        cp=subprocess.run([str(EXE),'run','habitat_quality','-d',str(stack_path),'--no-report'],stdout=f,stderr=subprocess.STDOUT)
    if cp.returncode:raise RuntimeError(log_path.read_text(errors='replace')[-5000:])
    return time.monotonic()-t

def main():
    pilot=P/'pilot_clcd/deg_sum_c.tif'
    with rasterio.open(pilot) as s:d=s.read(1);meta=s.profile;nodata=s.nodata
    with rasterio.open(ROOT/'02_过程文件/spatial/reporting_mask.tif') as s:
        mask=s.read(1)==1
        assert s.shape==d.shape and s.transform==meta['transform'] and s.crs==meta['crs']
    ref=mask & np.isfinite(d) & (d!=nodata)
    maximum=float(d[ref].max());k=maximum*.5
    assert 0<k<1
    freeze={'status':'FROZEN_FROM_NATIVE_BASELINE_DEGRADATION_BEFORE_FINAL_RUNS','Dmax':maximum,'k':k,
            'formula':'k=0.5*Dmax','reference_cells':int(ref.sum()),'reference':'2020 CLCD, study-scope pixel centres, valid native degradation',
            'same_k_for_all_products':True,'pilot_quality_is_not_final':True}
    target=P/'k_frozen.json'
    if target.exists():assert json.loads(target.read_text(encoding='utf8'))==freeze
    else:dump(target,freeze)
    params=np.genfromtxt(P/'sensitivity.csv',delimiter=',',names=True,dtype=None,encoding='ascii')
    H={int(row['lucode']):float(row['habitat']) for row in params}
    results=[]
    for product,landfile in [('clcd','clcd2020.tif'),('wc','worldcover2020_common30m.tif')]:
        print('NATIVE_HQ_START '+product,flush=True)
        stack=json.loads((P/(product+'_pilot.json')).read_text(encoding='utf8'))
        args=stack['args'];args['half_saturation_constant']=k;args['workspace_dir']=str(ALIAS/('final_'+product))
        elapsed=native(args,P/(product+'_final.json'),P/(product+'_final_stdout.log'))
        run=P/('final_'+product)
        with rasterio.open(run/'quality_c.tif') as s:q=s.read(1);qm=s.profile
        with rasterio.open(run/'deg_sum_c.tif') as s:dd=s.read(1)
        with rasterio.open(ROOT/'02_过程文件/spatial'/landfile) as s:a=s.read(1)
        assert q.shape==d.shape and qm['crs']==meta['crs'] and qm['transform']==meta['transform']
        h=np.zeros(a.shape,np.float32)
        for code,value in H.items():h[a==code]=value
        valid=(q!=qm['nodata']) & np.isfinite(q)
        assert np.all((q[valid]>=0)&(q[valid]<=1))
        expected=h*(1-(dd.astype(np.float64)**2.5)/(dd.astype(np.float64)**2.5+k**2.5))
        error=float(np.max(np.abs(q[valid]-expected[valid])))
        assert error<5e-7,error
        if product=='clcd':assert np.array_equal(dd,d),'Changing k altered D unexpectedly'
        # Separate result rasters from intermediate native workspaces.
        out=O/(product+'_HQ2020.tif')
        pp=qm.copy();pp.update(compress='deflate',tiled=True,blockxsize=256,blockysize=256)
        with rasterio.open(out,'w',**pp) as dst:
            dst.write(q,1);dst.update_tags(engine='native InVEST 3.20.2',k=str(k),source_native=str(run/'quality_c.tif'),
                                          interpretation='modeled habitat quality; aggregate within predefined focal habitat')
        results.append({'product':product,'seconds':elapsed,'output':str(out.relative_to(ROOT)),'native_workspace':str(run.relative_to(ROOT)),
                        'valid_cells':int(valid.sum()),'Q_min':float(q[valid].min()),'Q_max':float(q[valid].max()),
                        'formula_max_abs_error':error,'official_engine_exit_code':0})
        dump(O/'native_hq_execution.json',{'status':'RUNNING' if len(results)<2 else 'NATIVE_HQ_TWO_PRODUCTS_COMPLETED',
            'k':freeze,'engine':'official InVEST 3.20.2 executable','outputs':results})
        print(json.dumps(results[-1]),flush=True)

if __name__=='__main__':main()
