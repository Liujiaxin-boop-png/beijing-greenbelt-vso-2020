from pathlib import Path
import requests, rasterio as r,json
from rasterio.windows import Window
D=Path(__file__).resolve().parent
with r.open(D/'raw'/'worldpop_api_beijing_2020.tif') as ds:
 row,col=ds.index(116.32,39.96);w=Window(col,row,16,17);ll=ds.window_bounds(w);grid_sum=float(ds.read(1,window=w,masked=True).sum(dtype='float64'))
 left,bottom,right,top=ll
geom={'type':'Polygon','coordinates':[[[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]]}
for att in range(5):
 try:
  body={'geojson':geom,'year':2020};u='https://api.worldpop.org/v3/population'
  rr=requests.post(u,json=body,timeout=12);rr.raise_for_status();rec=rr.json()
  print('official area population',rec.get('total_population'),'local sum',grid_sum)
  (D/'WorldPop官方分区总数与裁片核对.json').write_text(json.dumps({'source':u,'request':body,'response':rec,'local_native_sum':grid_sum,'absolute_difference':abs(rec['total_population']-grid_sum),'note':'sanity check on native pixel-aligned 16×17 sample block'},indent=2,ensure_ascii=False),encoding='utf8');break
 except Exception as e: print(str(e)[-150:])
