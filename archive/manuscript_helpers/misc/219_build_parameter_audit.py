from pathlib import Path
import json, csv, hashlib, shutil

B=Path(__file__).resolve().parent
R=B.parents[2]
def dump(name,data): (B/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
refs=[
 {'id':'FENG2024','authors':'Feng X; Zeng F; Loo B P Y; Zhong Y','year':2024,'title':'The evolution of urban ecological resilience: An evaluation framework based on vulnerability, sensitivity and self-organization','journal':'Sustainable Cities and Society','volume':'116','article':'105933','doi':'10.1016/j.scs.2024.105933','source':'user-provided full PDF','pages_checked':[7,8,9],'role':'VSO framework, HQ/MCR/SSI precedent, entropy weighted sum'},
 {'id':'CHEN2016','authors':'陈妍; 乔飞; 江磊','year':2016,'title':'基于InVEST模型的土地利用格局变化对区域尺度生境质量的评估研究——以北京为例','journal':'北京大学学报(自然科学版)','volume':'52','issue':'3','pages':'553-562','doi':'10.13209/j.0479-8023.2016.057','url':'https://xbna.pku.edu.cn/html/2016-3-553.htm','locator':'2.2; 表2; 表3','role':'Beijing-specific HQ threat and sensitivity parameters'},
 {'id':'CHEN2024','authors':'Chen R; Carruthers-Jones J; Carver S; Wu J','year':2024,'title':'Constructing urban ecological corridors to reflect local species diversity and conservation objectives','journal':'Science of The Total Environment','volume':'907','article':'167987','doi':'10.1016/j.scitotenv.2023.167987','url':'https://eprints.whiterose.ac.uk/id/eprint/204646/','locator':'accepted manuscript printed pp11-13; PDF pp12-14; Table1','role':'Beijing small urban habitat core and land/road resistance candidates; NOT identical greenbelt six-index model'},
 {'id':'NA2024','authors':'Na Y; Hong Z; Ren S; Huang K','year':2024,'title':'Optimizing the construction of ecological networks in Beijing using a morphological spatial pattern analysis—minimal cumulative resistance model','journal':'Frontiers in Environmental Science','volume':'12','article':'1325880','doi':'10.3389/fenvs.2024.1325880','url':'https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2024.1325880/full','locator':'2.4 resistance surface; 4 Discussion','role':'complete Beijing landclass resistance candidate and edge-width precedent'},
 {'id':'FRAGSTATS','url':'https://fragstats.org/index.php/fragstats-metrics/patch-based-metrics/aggregation-metrics/c4-clumpiness-index','locator':'C4 definition and comments; formula image','role':'authoritative CLUMPY algorithm and boundary treatment'},
 {'id':'INVEST3202','url':'https://raw.githubusercontent.com/natcap/invest/3.20.2/src/natcap/invest/habitat_quality/habitat_quality.py','locator':'MODEL_SPEC max_dist units; execute; distance_decay','role':'exact engine parameters and units'},
 {'id':'ARCMAP108','url':'https://desktop.arcgis.com/en/arcmap/latest/tools/spatial-analyst-toolbox/cost-distance.htm','locator':'Usage; Syntax','role':'positive resistance, source NoData, cost distance semantics'},
]

hq_rows=[
 {'lucode':1,'name':'cropland','habitat':0.4,'built':0.5,'road':0.1,'mapping':'CLCD农田整体对应北京2016旱地；水田不可识别，地方转译'},
 {'lucode':2,'name':'forest','habitat':1,'built':1,'road':0.6,'mapping':'有林地'},
 {'lucode':3,'name':'shrub','habitat':1,'built':0.6,'road':0.2,'mapping':'灌木林地'},
 {'lucode':4,'name':'grassland','habitat':0.75,'built':0.65,'road':0.25,'mapping':'未区分覆盖度，主方案取原表中覆盖度；低/高覆盖度作参数对照'},
 {'lucode':5,'name':'water','habitat':1,'built':0.9,'road':0.5,'mapping':'原表水库湖泊；原表河渠0.85/0.45为参数对照'},
 {'lucode':7,'name':'barren','habitat':0,'built':0,'road':0,'mapping':'原表裸地H=0；敏感度原为不适用，模型输入0仅因Q恒0'},
 {'lucode':8,'name':'impervious','habitat':0,'built':0,'road':0,'mapping':'以不透水面代理建设，不区分城乡；H=0'},
 {'lucode':9,'name':'wetland','habitat':0.6,'built':0.95,'road':0.55,'mapping':'CLCD湿地对应原表滩地是代理，不是天然等价'},
]
for row in hq_rows:row.update(source='CHEN2016',locator='表3',status='CANDIDATE_TRANSFER_NOT_LOCAL_BIOLOGICAL_CALIBRATION')
fields=list(hq_rows[0])
with (B/'219_HQ_candidate_sensitivity.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fields);w.writeheader();w.writerows(hq_rows)
with (B/'219_HQ_candidate_threats.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,['threat','max_dist_m','weight','decay','source','mapping']);w.writeheader();w.writerows([
 {'threat':'built','max_dist_m':10000,'weight':1,'decay':'linear','source':'CHEN2016 表2; 2.2式2','mapping':'CLCD全部不透水面使用原表城镇类参数，城乡合并为本研究适配'},
 {'threat':'road','max_dist_m':3000,'weight':1,'decay':'linear','source':'CHEN2016 表2; 2.2式2','mapping':'原文主要交通干道；本项目固定OSM主干道路等级，不包括所有小路'},
 ])

mcr_ch=[{'landcover':n,'water':a,'waterfront':b,'forest':c} for n,a,b,c in [
 ('cropland',20,20,20),('forest',3,2,1),('grassland',3,3,3),('shrub',3,3,2),('wetland',1,1,3),('water',2,2,3),('impervious',50,50,50)]]
road=[{'distance_upper_m':20,'resistance_addend_candidate':30},{'distance_upper_m':50,'resistance_addend_candidate':5},{'distance_upper_m':100,'resistance_addend_candidate':3},{'distance_upper_m':200,'resistance_addend_candidate':1},{'distance_lower_exclusive_m':200,'resistance_addend_candidate':0}]
na=[{'landcover':n,'resistance':v} for n,v in [('forest',1),('grassland',2),('shrub',2),('wetland',3),('cropland',3),('water',4),('barren',4),('impervious',5)]]

audit={
 'date':'2026-11-06','status':'EVIDENCE_AND_IMPLEMENTATION_CANDIDATES_NOT_RESULTS','framework_locked':'218 VSO six indicators; 2020; 1000m square primary/500m comparison; entropy linear aggregation',
 'sources':refs,
 'HQ':{
  'engine':'native InVEST; pin exact installed version; 3.20.2 source verified',
  'formula':'Q=H*(1-D^z/(D^z+k^z)); z=2.5',
  'Feng_printed_formula_caution':'Feng p7 Eq2 denominator prints k^2, whereas official engine uses k^z; use native engine and official version equation',
  'threats_candidate_csv':'219_HQ_candidate_threats.csv','sensitivity_candidate_csv':'219_HQ_candidate_sensitivity.csv',
  'not_included_from_CHEN2016':'Original also models cropland and rural threats. 218 specifies built/roads; do not silently add the other threats, or label current two-threat run a reproduction of all CHEN2016 threats.',
  'NTL':'not included in HQ',
  'max_dist_units_for_3_20_2':'metres; source code lines101-109; values10000 and3000',
  'k_rule_candidate':{'pilot_k':0.05,'pilot_role':'produce D, which is independent of k','final_rule':'k=0.5*max(D) over baseline 2020 study-domain valid 30m pixel centres; freeze before final HQ scenario runs','source':'CHEN2016 2.2 Eq3 explanation; InVEST official guidance','old_k_must_not_be_reused_as_current':0.39925000071525574,'why':'old k computed on old raster/reference support; new equal-area grid must derive its own reference D'},
  'accessibility':'omit access vector -> beta=1; do not invent protected-area attenuation',
  'required_before_run':['all actual lulc values have parameters; CLCD6 snow omitted only after full model background absence confirmed','full buffer at least max threat extent plus raster footprint, output only study-domain','H group predefined not selected by HQ score'],
  'support':'Model inputs can be prepared now; adapted type correspondence must be frozen and disclosed',
 },
 'MCR':{
  'Feng_source_selection':{'source':'FENG2024 p7-8','method':'MSPA blue-green core','area_km2_strictly_greater_than':1,'reported_PC_greater_than':0.5,'unreported':['PC vs dPC precise implementation','dispersal distance/probability relation','resistance numeric class values/weights','MSPA edge width','grid aggregation of pairwise source costs']},
  'candidate_source_for_greenbelt':{'source':'CHEN2024 printed p11/PDFp12 lines189-195','core_edge_width_pixels':1,'patch_neighbourhood':8,'minimum_core_area_ha_inclusive':10,'geographic_fit':'Beijing inside fifth ring, fine fragmented urban habitats; closer scale precedent than entire-Nanchang1km2','adaptation':'original cores derived from species MaxEnt habitats; current cores from predefined landclasses. No bird observations or MaxEnt claimed. Threshold is an adopted screening assumption, not empirically optimal in second greenbelt.','source_sensitivity':'Compare10ha baseline candidate with Feng area>100ha, preserving same-type and parent patch rules; cannot add unreported PC screening.'},
  'resistance_candidates':{
   'CHEN2024':{'locator':'printed Table1 pp12-13 / PDF pp13-14','landcover_rows':mcr_ch,'road_distance_rows':road,'not_covered':['barren','snow','a grassland-specialist resistance column'],'full_model_other_factors':['population density','building density and height','NDVI','green view index'],'adaptation':'218 only landclass+roads, so any two-layer construction is a simplified parameter scenario rather than a reproduction of the original full resistance. Group columns denote bird guilds, not water flow or ecosystem material flux.','numeric_road_intervals':'table labels endpoints; implementation must predeclare <=20,(20,50],(50,100],(100,200],>200 m, an interval convention rather than a quoted original inequality'},
   'NA2024':{'locator':'2.4 textual paragraph after Table1; Discussion edge width','landcover_rows':na,'original_four_factor_weights':{'landuse':0.3,'elevation':0.15,'slope':0.15,'NDVI':0.4},'caution':'Targets predominantly terrestrial animals/birds; water high resistance does not fit aquatic transfer. Original did not model roads, so road component must cite a different source. Do not add NDVI to218.'}
  },
  'implementation_lock':[
   'Use positive unit-distance cost; do not 0-1 rescale minimum cost to0; additive zero road pressure is allowed because total landclass cost stays>0.',
   'Source raster cells outside source must be NoData, not0 (ArcMap treats0 as valid source).',
   'ParentPatchID computed on complete background before grid clipping; all core fragments of same parent excluded when evaluating that parent.',
   'For each focal same-type patch: cost to other qualified same-type core source; exclude same parent; record destination source and Euclidean distance; aggregate using intersecting focal habitat area.',
   'No other same-type source, disconnected paths, incomplete background -> distinct not-applicable codes; never fabricate0.',
   'Keep HQ and NTL out of resistance and source selection.',
   'NASADEM can contextualize terrain and describe sources. 218 calculation text only commits landclass and road resistance; extra terrain resistance needs separately documented scenario and a source, not an unannounced baseline change.'
  ],
  'ready_status':'Geometry and core-source generation ready after explicit source threshold freeze. Main resistance mapping remains a transparent implementation decision; no single retrieved paper fully supplies the exact three ecological groups and both input layers without adaptation.'
 },
 'CLUMPY':{
  'source':'FRAGSTATS C4 official, inspected formula JPG',
  'formula':'G_i=g_ii/sum_k(g_ik); if G_i>=P_i OR P_i>=0.5 then (G_i-P_i)/(1-P_i), else (G_i-P_i)/P_i.',
  'range':[-1,1],
  'critical_algorithm':'Official current formula does not contain min-perimeter correction; do not swap AI or a differently implemented CLUMPY formula without comparison.',
  'adjacency':'Side-by-side cell joins, double-count internal adjacencies. Patch connectedness8/4 is distinct from four-side join counting.',
  'boundary':'Background edges count in total focal adjacency; with no landscape border the outside landscape boundary counts as background; with supplied border boundary joins count once. P_i includes internal background area.',
  'proposed_execution':'FRAGSTATS class-level native algorithm per square, same no-external-border/background convention and cell size for all grids; primary patch adjacency8, documented.',
  'special_cases':'Absent class is undefined; single-class window or very small class must retain actual engine output/status. Do not replace all NA by0 or1. Native output should be checked with hand-constructed tiny rasters.',
  'grid30m_issue':'1000m is not divisible by30m. Keep exact 1km vector boundary; raster cells assigned to each square by centre for CLUMPY (33/34 cells per side). Report count and physical raster-support width; use exact pixel intersection weighting for continuous/area indicators separately.',
  'ready_status':'Ready once native FRAGSTATS run settings and synthetic fixture output confirmed.'
 },
 'aggregation':{
  'source':'FENG2024 p9 4.2.2 specifies entropy plus weighted sum but not detailed implementation; JRC existing report source12 supports sensitivity checks',
  'indicators':['HQ_H+','NTL-','CLUMPY+','MCR-','SSIg-','E_div_EplusC+'],
  'entropy_formula':{'p_ij':'z_ij/sum_i(z_ij)','e_j':'-sum_i(p_ij*ln(p_ij))/ln(n)','d_j':'1-e_j','w_j':'d_j/sum_j(d_j)','ER':'sum_j(w_j*z_ij)'},
  'zero_term':'0*ln0=0 by continuous limit; do not add arbitrary epsilon.',
  'constant_indicator':'max=min => no discrimination; d=0 diagnostic, record explicitly. If all d=0 or n<2 stop composite, not invent weights.',
  'within_type':'All six complete on same ecological group common-valid domain; no cross-type score comparison without common scientific interpretation.',
  'dimension_score':'Within each dimension divide weighted two-indicator sum by its two-weight sum; dimension weights equal their sum. ER then equals sum of dimension score times dimension weight.',
  'sensitivity_reference_candidate':'Predeclare scenario set; after raw indicator calculations use pooled min/max of fixed scenarios on shared-valid support as a single fixed reference. Estimate baseline weights on baseline observations only; keep reference/weights fixed for data/parameter/scale comparisons; separately re-estimate entropy weights on scenario observations with the SAME nonnegative reference.',
  'why_reference_needs_freeze':'Baseline-only extrema may make scenario standardized values negative; negative values cannot be used as entropy proportions. Do not silently clip. Pooled reference is one transparent completion of218 unified-reference rule, not a quoted Feng specification.',
  'drop_one':'Hold baseline z; remove one w then renormalize remaining weights to1; do not recompute the other five weights for this test.',
  'ready_status':'Formulas ready; actual weights only after real complete data; no weights prefilled.'
 },
 'review_boundary':'This evidence audit does not certify local biological validity, generate empirical results, or claim any new source is verified CAS Q1. New references provide parameter precedent, with original context recorded.',
}
dump('219_parameter_evidence_and_candidates.json',audit)
dump('219_source_references.json',refs)
for name in ['S04_table2_as_published.csv','S04_table3_as_published.csv']:
 src=R/'生态韧性新研究'/'数据下载_20261020'/'09_InVEST输入与参数'/'01_原文证据'/name
 if src.exists():shutil.copy2(src,B/'sources'/name)
src=R/'计算生态韧性参考文献2026.11.5'/'1-s2.0-S2210670724007571-main (1).pdf'
if src.exists():shutil.copy2(src,B/'sources'/'Feng2024_user_supplied.pdf')
print(json.dumps({'files':[p.name for p in B.iterdir() if p.is_file()],'source_count':len(refs)},ensure_ascii=False))
