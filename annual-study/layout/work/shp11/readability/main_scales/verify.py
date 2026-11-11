from pathlib import Path
import xml.etree.ElementTree as ET,json,re,math
from PIL import Image,ImageDraw
import numpy as np
w=Path(__file__).resolve().parent
base=Path('D:/ER219_work/shp11/maps')
fdir=w.parent/'arcmap_delivery'
spt=72/2.54
res={}; preview=[]
health=json.loads((w/'native_data_health.json').read_text('utf8'))
for k in ('1','3','7','8','9','10'):
    spec=json.loads((w/f'fig{k}.json').read_text('utf8'))
    audit=json.loads((w/f'fig{k}.export_receipt.json').read_text('utf8'))
    old=json.loads((base/f'fig{k}.export_receipt.json').read_text('utf8'))
    frames=health[k]['frames']
    for frame in frames:
        saved=next(m for m in old['maps'] if m['name']==frame['name'])
        assert all(abs(a-b)<.002 for a,b in zip(frame['extent'],saved['extent']))
    assert [e for e in audit['elements'] if e['type']!='scale']==[e for e in old['elements'] if e['type']!='scale']
    xml=ET.fromstring((w/f'fig{k}.svg').read_bytes().decode('utf8',errors='replace'));ns={'s':'http://www.w3.org/2000/svg'}; pagecm=audit['page_cm']
    paths=[]
    for path in xml.findall('.//s:path',ns):
        if path.get('stroke')!='#000000' or path.get('fill')!='none':continue
        m=re.fullmatch(r'\s*M([.\d-]+),([.\d-]+)L([.\d-]+),([.\d-]+)\s*',path.get('d',''))
        if m: paths.append(tuple(map(float,m.groups())))
    im=Image.open(w/f'fig{k}.png').convert('RGB'); factor=im.width/(pagecm[0]*spt); rows=[]
    diff=(np.asarray(im)!=np.asarray(Image.open(base/f'export{k}.png').convert('RGB'))).any(-1)
    for bar in spec['scales']:
        x0,y0=bar['x']*spt,(pagecm[1]-bar['y'])*spt
        mapdef=next(m for m in spec['maps'] if m['name']==bar['map'])
        def ground_per_cm(m):
            ex=next(z['extent'] for z in frames if z['name']==m['name'])
            return (ex[2]-ex[0])/m['w']
        metric=ground_per_cm(mapdef)
        if k!='1': assert max(abs(ground_per_cm(m)/metric-1) for m in spec['maps'])<.00002
        km=bar['divisions']*bar['division_km'];expected=km*1000/metric*spt
        cand=[p for p in paths if abs(p[1]-p[3])<.001 and abs(p[0]-x0)<12 and abs(p[1]-y0)<12 and p[2]>p[0]]
        assert cand,(k,x0,y0)
        px,py,ex,ey=min(cand,key=lambda p:abs(p[0]-x0)+abs(p[1]-y0))
        for xx in (px,ex):
            assert any(abs(a-xx)<.01 and abs(c-xx)<.01 and abs(b-py)<.01 and 4.15<b-d<4.85 for a,b,c,d in paths),(k,xx)
        assert not any(abs(a-(px+ex)/2)<.5 and abs(c-a)<.01 and abs(b-py)<.5 and abs(d-b)>1 for a,b,c,d in paths)
        ratio=(ex-px)/expected-1
        assert abs(ratio)<.016,(k,km,ratio)
        crops=(max(0,math.floor((px-4)*factor)),max(0,math.floor((py-19)*factor)),min(im.width,math.ceil((ex+25)*factor)),min(im.height,math.ceil((py+4.2)*factor)))
        crop=im.crop(crops);crop.thumbnail((480,110));preview.append((k+': '+str(km)+' km',crop))
        diff[max(0,int((py-25)*factor)):int((py+14)*factor),max(0,int((px-12)*factor)):int((ex+35)*factor)]=False
        rows.append(dict(name=bar['name'],map=bar['map'],scale_km=km,label_mid=km/2,expected_printed_pt=expected,measured_svg_pt=ex-px,difference_percent=ratio*100,no_middle_tick=True,identical_mapframe_scales=(k!='1')))
    unaltered=int(diff.sum());assert unaltered==0,(k,unaltered)
    res[k]=dict(scales=rows,png=str(next((fdir/('图'+k)).glob('*.png'))),broken=audit['broken_layers'],changed_pixels_outside_scales=unaltered)
out=Image.new('RGB',(900,len(preview)//2*145),'#EEEEEE');draw=ImageDraw.Draw(out)
for i,(lab,img) in enumerate(preview):
    xx=i%2*450;yy=i//2*145;draw.text((xx+10,yy+3),lab,fill='black');out.paste(img,(xx+10,yy+23))
out.save(w/'all_main_scales.png')
(w/'verification.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),'utf8')
print({k:[(a['scale_km'],round(a['difference_percent'],2)) for a in rr['scales']] for k,rr in res.items()})

