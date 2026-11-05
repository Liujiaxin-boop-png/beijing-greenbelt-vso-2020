"""Run official FRAGSTATS 4.2 class CLUMPY with an auditable model.

This wrapper edits a *copy* of the author's tutorial SQLite model. All metric
calculations are performed by frg_cmd.exe, not by this wrapper. Input grids use
positive class codes, background 999, and NoData 9999; no artificial border.
Use relative ASCII-only batch paths because GDAL 1.9 has fragile Unicode I/O.
"""
from pathlib import Path
import csv
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(os.environ.get('ER219_FRAGSTATS_HOME',str(ROOT / '02_过程文件' / '计算审计' / 'FRAGSTATS4.2')))
MODEL = WORK / 'tutorial' / 'Tutorial_3' / 'fragmodel.fca'
EXE = WORK / 'portable' / 'frg_cmd.exe'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_model(path, neighborhood=8):
    """Only select class CLUMPY and support-area diagnostics; no imputation."""
    path = Path(path)
    shutil.copyfile(MODEL, path)
    with sqlite3.connect(path) as con:
        con.execute('DELETE FROM frg_landscape_layers')
        con.execute('UPDATE frg_table_metrics SET value=0')
        con.execute("UPDATE frg_table_metrics SET value=1 WHERE metric_name IN ('cCLUMPY','cCA','cPLAND','cNP','lTA')")
        con.execute('UPDATE frg_table_options SET value=0')
        con.execute("UPDATE frg_table_options SET value=1 WHERE option_name IN ('DO_NSTD_CLASS_LEVEL_STATS','DO_NSTD_LANDS_LEVEL_STATS','AUTO_SAVE_RESULTS')")
        con.execute("UPDATE frg_table_numerics SET value=? WHERE numeric_name='NEIGHBORHOOD_RULE'", (neighborhood,))
        con.execute("UPDATE frg_table_strings SET value=''")
    return path


def run_ascii_grids(grids, work, cell_size=30.0, neighborhood=8, timeout=120):
    """grids maps an ASCII identifier to a rectangular sequence of row values."""
    work = Path(work).resolve()
    work.mkdir(parents=True,exist_ok=True)
    model = prepare_model(work/'clumpy.fca',neighborhood)
    inputs = []
    lines = []
    for name, arr in grids.items():
        if not name.isascii() or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
            raise ValueError('Use a simple ASCII grid identifier')
        rows, cols = len(arr), len(arr[0])
        if not all(len(row)==cols for row in arr):
            raise ValueError('Nonrectangular array')
        grid = work/(name+'.asc')
        grid.write_text('\n'.join(' '.join(str(int(v)) for v in row) for row in arr)+'\n',encoding='ascii')
        lines.append(f'{grid.name}, {cell_size}, 999, {rows}, {cols}, 1, 9999, IDF_ASCII')
        inputs.append({'name':name,'rows':rows,'cols':cols,'sha256':sha256(grid)})
    (work/'inputs.fbt').write_text('\n'.join(lines)+'\n',encoding='ascii')
    command=[str(EXE),'/m','clumpy.fca','/b','inputs.fbt','/o','./clumpy_results']
    cp=subprocess.run(command,cwd=work,capture_output=True,timeout=timeout)
    log=cp.stdout.decode('utf-8','replace')+'\n'+cp.stderr.decode('utf-8','replace')
    (work/'frg_command.log').write_text(log,encoding='utf-8')
    result={'exit_code':cp.returncode,'exe_sha256':sha256(EXE),'model_sha256':sha256(model),
            'official_template_sha256':sha256(MODEL),'inputs':inputs,
            'command':command,'cwd':str(work),'four_sided_adjacencies':True,
            'landscape_border':False,'neighborhood_patch_rule':neighborhood,
            'background_code':999,'nodata_code':9999,'calculation_engine':'FRAGSTATS v4.2.1.612',
            'rows':[]}
    output = work/'clumpy_results.class'
    if output.exists():
        with output.open(encoding='utf-8-sig',errors='replace',newline='') as f:
            reader=csv.DictReader(f,skipinitialspace=True)
            result['rows']=[{k.strip():v.strip() for k,v in row.items()} for row in reader]
    (work/'run_receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if cp.returncode or not result['rows']:
        raise RuntimeError(log[-4000:])
    return result


def synthetic_check():
    grids={
        'checker':[[1 if (r+c)%2==0 else 2 for c in range(6)] for r in range(6)],
        'block':[[1 if c<3 else 2 for c in range(6)] for r in range(6)],
        'one':[[1 if r==2 and c==2 else 2 for c in range(6)] for r in range(6)],
        'pure':[[1]*6 for _ in range(6)],
        'absent':[[2]*6 for _ in range(6)],
        'internal_background':[[999 if r==2 and c==2 else (1 if c<3 else 2) for c in range(6)] for r in range(6)],
    }
    result=run_ascii_grids(grids,WORK/'synthetic_check')
    result['synthetic_only']=True
    result['not_research_observations']=True
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    synthetic_check()
