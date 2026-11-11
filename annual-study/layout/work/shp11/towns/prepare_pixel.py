from pathlib import Path
p=Path('D:/ER219_work/shp11/towns')
old=Path('D:/ER219_work/towndisc11/evidence')
s=(old/'pixel_habitat.py').read_text('utf8').replace("'D:/ER219_work/townmaps11/evidence/case_hotspots.gpkg'","out/'case_hotspots.gpkg'").replace("json.loads((base/'hq/full_scope_frozen_k.json').read_text())['k']","json.loads((out.parent/'core/domain.json').read_text('utf8'))['new_hq_k']")
(p/'pixel_habitat.py').write_text(s,'utf8')
s=(old/'mcr_inputs.py').read_text('utf8')
s=s.replace("v01,v10=pool.map(hybrid,[(2015,2025),(2025,2015)])","v01,v10=[Path('D:/ER219_work/towndisc11/evidence')/f'mcr_resistance{c}_source{s}/surface_dpc.f32' for c,s in [(2015,2025),(2025,2015)]]").replace("'D:/ER219_work/townmaps11/evidence/case_hotspots.gpkg'","w/'case_hotspots.gpkg'")
(p/'pixel_mcr.py').write_text(s,'utf8')
