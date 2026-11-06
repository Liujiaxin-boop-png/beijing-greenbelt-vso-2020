"""Read-only comparison of original and native projected reporting supports."""
from pathlib import Path
import geopandas as gpd,pandas as pd,json
ROOT=Path(__file__).resolve().parents[2];SP=ROOT/'02_过程文件/spatial'
grid=gpd.read_file(SP/'analysis.gdb',layer='grid_1000').set_index('Grid_ID')
town=gpd.read_file(SP/'analysis.gdb',layer='towns').set_index('Name')
pieces=gpd.read_file(SP/'analysis.gdb',layer='town_grid_1000')
native=gpd.read_file(SP/'analysis.gdb',layer='study_scope').geometry.iloc[0]
original=gpd.read_file(SP/'scope.gpkg',layer='study_scope').geometry.iloc[0]
rows=[]
for p in pieces.itertuples():
    square=grid.loc[p.Grid_ID].geometry
    nt=square.intersection(native);ot=square.intersection(original)
    exact=square.intersection(town.loc[p.Name].geometry)
    rows.append({'grid_id':p.Grid_ID,'town':p.Name,'native_piece_m2':p.geometry.area,'native_scope_in_grid_m2':nt.area,'original_scope_in_grid_m2':ot.area,
      'native_piece_minus_native_scope_m2':p.geometry.area-nt.area,'native_piece_minus_original_scope_m2':p.geometry.area-ot.area,
      'piece_vs_exact_native_town_area_delta_m2':p.geometry.area-exact.area,'piece_vs_exact_native_town_symdiff_m2':p.geometry.symmetric_difference(exact).area,
      'piece_vs_exact_native_town_hausdorff_m':p.geometry.hausdorff_distance(exact),
      'native_vs_original_scope_in_grid_symdiff_m2':nt.symmetric_difference(ot).area})
frame=pd.DataFrame(rows);work=ROOT/'02_过程文件/evaluation';frame.to_csv(work/'town_geometry_diagnosis.csv',index=False,encoding='utf-8-sig')
record={'rows':len(rows),'native_vs_original_scope_global_area_difference_m2':native.area-original.area,'native_vs_original_scope_global_symmetric_difference_m2':native.symmetric_difference(original).area,'native_vs_original_scope_global_Hausdorff_m':native.hausdorff_distance(original),'maxima':{c:float(frame[c].max()) for c in frame.columns if c not in ['grid_id','town']},'largest_original_scope_discrepancies':frame.nlargest(5,'native_piece_minus_original_scope_m2').to_dict('records')}
(work/'town_geometry_diagnosis.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(record,ensure_ascii=False))
