"""Record the actual page-by-page review of the internal methods layout proof.

This task-specific record must not be reused to approve another rendering.
It does not certify that a complete manuscript or ecological result exists.
"""
from pathlib import Path
import datetime, hashlib, json

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / '02_过程文件/manuscript/method_preview'
EXPECTED_DOCX = 'd03d07c078a395edafc5c0145d607e35920da4e4a421e9c762afc36ce978b1d0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    docx = FOLDER / 'intro_methods_preview.docx'
    assert sha(docx) == EXPECTED_DOCX, 'Review applies only to the viewed version.'
    native = json.loads((FOLDER / 'native/native_render.json').read_text(encoding='utf-8-sig'))
    assert native['pages'] == 9 and native['native_equations'] == 6
    pages = sorted((FOLDER / 'pages_v2').glob('page-*.png'))
    assert len(pages) == 9
    receipt = {
        'status': 'INTERNAL_METHODS_LAYOUT_VISUAL_PASS',
        'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'docx_sha256': EXPECTED_DOCX,
        'native_engine_path': native['engine_path'],
        'native_pages': 9, 'native_editable_equations': 6,
        'reviewers': {'pages_1_to_4': 'root assistant, actual page images',
                      'pages_5_to_9': 'parameters219 assistant, actual page images'},
        'checks': [
            'No blue title border; black academic typography',
            'Six-indicator table fits one page with the intended column widths',
            'All six native equations readable; no clipped text or table cells',
            'Figures 1, 2 and 6 legible at actual manuscript width',
            'References retain complete entries across page boundaries',
        ],
        'layout_notes': [
            'Figure 2 is followed by unused space because the next full-size figure cannot fit; final paper must place figures next to their discussion.',
            'Two natural reference line wraps are slightly awkward but have no missing or obscured text.',
        ],
        'pages': [{'file': p.name, 'sha256': sha(p)} for p in pages],
        'complete_paper': False,
        'result_or_conclusion_readiness': 'BLOCKED_ORIGINAL_EOG_INPUTS_MISSING',
        'original_user_documents_modified': False,
    }
    target = FOLDER / 'visual_QA.json'
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'status': receipt['status'], 'pages': 9, 'complete_paper': False}))


if __name__ == '__main__':
    main()
