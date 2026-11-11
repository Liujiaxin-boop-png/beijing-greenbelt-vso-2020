from pathlib import Path
import re,json,hashlib
from PIL import Image,ImageDraw
from pypdf import PdfReader
w=Path(__file__).parent
frames=json.loads((w/'frames.json').read_text('utf8'))
audit={}
gallery=Image.new('RGB',(880,7*165),'white')
for ii,k in enumerate(['A2','A3','A4','A5','A6','A8','A9']):
 cfg=json.loads((w/(k+'.json')).read_text('utf8')); desired=cfg['scale']['km']
 rr=frames[k];rows=rr['delivered']['frames'];orig=rr['original']['frames']
 actual_r=json.loads((w/(k+'.export_receipt.json')).read_text('utf8'))
 p=next((w.parent/'arcmap_delivery'/('图'+k)).glob('*.pdf'))
 pdf=PdfReader(p);assert len(pdf.pages)==1
 page=pdf.pages[0];strm=page.get_contents().get_data().decode('latin1')
 num=r'([-.\d]+)'
 matches=re.findall(r'(?m)^'+num+' '+num+' m '+num+' '+num+' l S\s*$',strm[-10000:])
 lines=[tuple(map(float,pt)) for pt in matches[-3:]];assert len(lines)==3
 (a,b,c,d),(e,f,g,h),(x,y,X,Y)=lines
 assert a==c and e==g and b<d and f<h and abs(b-f)<.01 and abs(y-Y)<.01 and abs(a-x)<.01 and abs(e-X)<.01
 svg=(w/('export'+k+'.svg')).read_bytes().decode('cp936',errors='replace')
 last=svg[svg.rfind('stroke-linejoin="round" d='):]
 texts=re.findall(r'<text\b[^>]*>(.*?)</text>',last,flags=re.S)
 labels=[''.join(re.findall(r'>([^<>]*)</tspan>',t)).strip() for t in texts]
 assert sorted(labels)==sorted(['0','%g'%(desired/2),'%g'%desired,'km']),(k,labels)
 map_ratios=[(r['extent'][2]-r['extent'][0])/r['w'] for r in rows]
 exp=[desired*1000/q*72/2.54 for q in map_ratios]
 actual=X-x;err=max(abs(v-actual) for v in exp)*cfg['dpi']/72
 assert err <1.5,(k,err,actual,exp)
 assert max(map_ratios)/min(map_ratios)-1<1e-7,(k,map_ratios)
 assert rr['delivered']['relative'] and rr['delivered']['broken']==0 and all(r['local'] and not r['broken'] for r in rows)
 for r,o in zip(rows,orig):
  assert r['name']==o['name'] and abs(r['w']-o['w'])<1e-8 and abs(r['h']-o['h'])<1e-8
  assert max(abs(a-b) for a,b in zip(r['extent'],o['extent']))<1e-5
 im=Image.open(p.with_suffix('.png')).convert('RGB')
 assert list(im.size)==actual_r['pixels']
 pw=float(page.mediabox.width);ph=float(page.mediabox.height)
 box=(round((x-10)/pw*im.width),round((ph-y-19)/ph*im.height),round((X+27)/pw*im.width),min(im.height,round((ph-y+5)/ph*im.height)))
 crop=im.crop(box);crop.thumbnail((720,152)); gallery.paste(crop,(130,ii*165+5)); dr=ImageDraw.Draw(gallery);dr.text((25,ii*165+60),k,fill='black',font_size=30)
 audit[k]=dict(panel_count=len(rows),local_layers=sum(len(r['sources']) for r in rows),native_dynamic_bars=1,labels=labels,stroke_pt_requested=.7,cap_height_pt=d-b,ground_km=desired,vector_bar_pt=actual,expected_pt=exp,max_residual_export_px=err,physical_meters_per_page_cm=map_ratios,scale_reported_by_arcpy=[r['scale'] for r in rows],width_and_projected_extents_match_original=True,broken_links=0)
 print(k,len(rows),round(actual,3),round(exp[0],3),round(err,3),labels,flush=True)
gallery.save(w/'scale_crops.png')
(w/'appendix_qa.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
