from pathlib import Path
import pandas as pd
p=Path('D:/ER219_work/shp11/towns')
s=Path('D:/ER219_work/towndisc11/source/attribute.py').read_text('utf8')
s=s.replace("A/'towns/pieces_full.csv'","OUT/'pieces_full.csv'").replace("'D:/ER219_work/townmaps11/evidence/patch_grid_contributions.csv'","OUT/'patch_grid_contributions.csv'").replace("k=json.loads((A/'hq/full_scope_frozen_k.json').read_text())['k']","k=json.loads((OUT.parent/'core/domain.json').read_text('utf8'))['new_hq_k']").replace("for code,t in zip('ABCD',[30,33,7,78]):","case_towns=pd.read_csv(OUT/'四类入选镇街指标与增减地段强度.csv')\nfor code,t in zip(case_towns.base_type,case_towns.town_seq):")
(p/'hq_inputs.py').write_text(s,'utf8')
s=Path('D:/ER219_work/towndisc11/evidence/mcr_grid.py').read_text('utf8')
s=s.replace("g=pd.read_csv('D:/ER219_work/six_final11/annual/ALLDIST/六项格网十年变化.csv')","g=gp.read_file(w.parent/'core/annual_grid_500.gpkg',layer='grid500',ignore_geometry=True)\nprevious=Path('D:/ER219_work/towndisc11/evidence')").replace("w/'mcr_resistance","previous/'mcr_resistance")
(p/'mcr_decomposition.py').write_text(s,'utf8')
