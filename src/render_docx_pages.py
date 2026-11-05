"""Use the bundled renderer with the actual native Word/WPS PDF on Windows.

The managed renderer is unmodified. This adapter is explicit because LibreOffice
is not installed on this host; PDFium renders the native PDF into page PNGs.
"""
from pathlib import Path
import argparse,importlib.util,sys,json
import pypdfium2 as pdfium

def main():
    p=argparse.ArgumentParser();p.add_argument('docx');p.add_argument('native_pdf');p.add_argument('output_dir');a=p.parse_args()
    skill=Path('C:/Users/LJX/.codex/plugins/cache/openai-primary-runtime/documents/26.1104.11149/skills/documents')
    spec=importlib.util.spec_from_file_location('bundled_render_docx',skill/'render_docx.py');rd=importlib.util.module_from_spec(spec);spec.loader.exec_module(rd)
    native=Path(a.native_pdf).resolve();assert native.is_file()
    rd.convert_to_pdf=lambda *args,**kw:(str(native),'Actual native Word/WPS PDF; explicit Windows adapter; source DOCX unchanged')
    def raster(pdf_path,dpi,fmt,thread_count,output_folder,paths_only,output_file):
        d=pdfium.PdfDocument(str(pdf_path));paths=[]
        for i in range(len(d)):
            dest=Path(output_folder)/f'page0001-{i+1:02d}.png'
            d[i].render(scale=dpi/72).to_pil().save(dest,dpi=(dpi,dpi));paths.append(str(dest))
        return paths
    rd.convert_from_path=raster
    sys.argv=['render_docx.py',a.docx,'--output_dir',a.output_dir,'--dpi','150','--emit_pdf'];rd.main()
    print(json.dumps({'engine':'bundled render_docx.py with task-local native-PDF/PDFium adapters','managed_renderer_modified':False,'native_pdf':str(native)}))

if __name__=='__main__':main()
