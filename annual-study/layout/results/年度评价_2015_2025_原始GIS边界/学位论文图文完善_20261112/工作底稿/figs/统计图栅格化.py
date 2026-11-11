from pathlib import Path
from PIL import Image,ImageChops,ImageOps
import pypdfium2 as pdfium
import json
out=Path(__file__).resolve().parent
report=[]
for key in ['A_转折与地段','B_水面产品对照','C_植被分组与覆盖']:
    with pdfium.PdfDocument(out/(key+'.pdf')) as pdf:
        assert len(pdf)==1
        page=pdf[0];bmp=page.render(scale=5); im=bmp.to_pil().convert('RGB')
        mask=ImageChops.difference(im,Image.new('RGB',im.size,'white')).convert('L').point(lambda v:255 if v>22 else 0)
        bb=mask.getbbox()
        if bb is None: raise ValueError(key)
        im=ImageOps.expand(im.crop(bb),border=34,fill='white')
        im.save(out/(key+'.png'),dpi=(360,360),optimize=True)
        print(key,im.size)
        thumb=im.copy();thumb.thumbnail((1300,650));thumb.save(out/(key+'预览.jpg'),quality=90)
        report.append({'figure':key,'image_px':im.size,'dpi':360,'source_pdf_pages':len(pdf)})
        page.close()
(out/'图像核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

