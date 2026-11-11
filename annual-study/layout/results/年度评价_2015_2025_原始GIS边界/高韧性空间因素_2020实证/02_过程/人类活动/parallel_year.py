from pathlib import Path
import requests,concurrent.futures,time,json,sys,rasterio as rio,threading,numpy as np
from rasterio.merge import merge
from contextlib import ExitStack
D=Path(__file__).resolve().parent/'raw'
YY=sys.argv[1:]
def dl(t):
 y,j,i=t; P=D/'tiles_small'/y; P.mkdir(exist_ok=True,parents=True);f=P/f'{j}_{i}.tif'
 if f.exists():return f
 xmin=116.05+.085*i-.003;xmax=116.05+.085*(i+1)+.003;ymin=39.66+.07*j-.003;ymax=39.66+.07*(j+1)+.003
 body={'geojson':{'type':'Polygon','coordinates':[[[xmin,ymin],[xmax,ymin],[xmax,ymax],[xmin,ymax],[xmin,ymin]]]},'year':int(y),'resolution':'100m'}
 for att in range(18):
  try:
   sess=requests.Session(); sess.trust_env=False
   if att%3==2:sess.proxies={'https':'http://127.0.0.1:7897','http':'http://127.0.0.1:7897'}
   r=sess.post('https://api.worldpop.org/v3/raster',json=body,timeout=(12,35),stream=True)
   if r.status_code==429:
    print('rate limit',r.text[:180],r.headers.get('Retry-After'),flush=True);time.sleep(min(35,int(r.headers.get('Retry-After','10'))));continue
   if r.status_code!=200:raise ValueError(str(r.status_code)+r.text[:250])
   data=r.content
   if data[:2] not in (b'II',b'MM'):raise ValueError(str(r.status_code)+repr(data[:120]))
   f.write_bytes(data);f.with_suffix('.json').write_text(json.dumps({'source':r.url,'body':body,'headers':dict(r.headers)},ensure_ascii=False),encoding='utf8')
   print('tile',y,j,i,len(data),flush=True);return f
  except Exception as e: print('tile error',y,j,i,att,repr(e)[-170:],flush=True);time.sleep(min(12,2+att))
 raise RuntimeError('Could not get tile '+str(t))
def get(y):
 import grid_population_light as h
 tiles=[(y,j,i) for i in range(8) for j in range(8) if ((h.LON.max(1)>116.05+.085*i-.002)&(h.LON.min(1)<116.05+.085*(i+1)+.002)&(h.LAT.max(1)>39.66+.07*j-.002)&(h.LAT.min(1)<39.66+.07*(j+1)+.002)).any()]
 with concurrent.futures.ThreadPoolExecutor(2) as e: fs=list(e.map(dl,tiles))
 with ExitStack() as stack:
  ds=[stack.enter_context(rio.open(f)) for f in fs]
  assert len({a.crs.to_epsg() for a in ds})==1 and all(np.allclose(a.res,ds[0].res) for a in ds)
  a,t=merge(ds,method='first');b,t2=merge(ds,method='last')
  assert np.array_equal(a,b),'overlap mismatch'
  prof=ds[0].profile.copy();prof.update(count=1,width=a.shape[2],height=a.shape[1],transform=t,compress='deflate')
  f=D/f'worldpop_api_beijing_{y}.tif'
  if f.exists():print('existing alternate single bbox',flush=True);return
  with rio.open(f,'w',**prof) as out:out.write(a);out.update_tags(source='WorldPop official API v3 raster, 100m tiled with overlapping halos; equal overlap checked')
  print('mosaic',y,f,flush=True)
for y in YY:
 if not (D/f'worldpop_api_beijing_{y}.tif').exists(): get(y)
 import grid_population_light as g
 g.calc(int(y),'pop')
 import subprocess; subprocess.run([sys.executable,str(D.parent/'build_panel.py')],check=True)
