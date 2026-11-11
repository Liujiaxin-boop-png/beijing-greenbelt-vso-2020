from common import *
import json
old=Path('D:/ER219_work/cases_local_1111/maps/prepare_maps.py').read_text('utf8')
old=old.replace("Path('D:/ER219_figures/四个典型镇街_镇内十年变化_ArcMap10.8').resolve()","Path(r'"+str(B)+"')").replace("Path('D:/ER219_work/six_final11/annual/ALLDIST/六项格网十年变化.csv')","Path(r'"+str(D/'六项格网十年变化.csv')+"')").replace("annual / 'boundary/planning_towns.gpkg'","Path(r'"+str(T/'planning_towns.gpkg')+"')").replace("annual / 'towns/pieces_full.csv'","Path(r'"+str(T/'pieces_full.csv')+"')").replace("D:/ER219_work/litlogic11/types/78镇街首末年分型与敏感性.csv",str(T/'82镇街首末年分型与敏感性.csv').replace('\\','/')).replace('D:/ER219_work/townmaps11/evidence/case_hotspots.csv',str(T/'case_hotspots.csv').replace('\\','/')).replace("8,'阳坊镇','阳坊镇'","8,'北臧村镇','北臧村镇'").replace("9,'长辛店镇','原长辛店镇'","9,'拱辰街道','拱辰街道'").replace("for f in ('ix','iy'):clipped[f]=clipped[f].astype('int32')","for f in ('ix','iy'):clipped[f]=clipped[f].astype('int32')")
# Old Python path literals absorb escapes on Windows; use POSIX path for all quoted text.
old=old.replace('ds = pieces.loc[pieces.town_seq.eq(row.town_seq)].merge','ds = pieces.drop(columns=[c for c in ("grid_id","area_km2") if c in pieces]).loc[pieces.town_seq.eq(row.town_seq)].merge')
env={'__name__':'__main__','__file__':str(W/'mapcases.py')};exec(compile(old,'case adapter','exec'),env)
for i in range(7,11):
 c=json.loads((W/f'case{i}.json').read_text('utf8'));config(str(i),c,Path(c['output_mxd']).stem)
