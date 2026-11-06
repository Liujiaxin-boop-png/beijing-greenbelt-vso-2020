"""Apply reviewed wording clarifications to the working manuscript source only.

The approved proposal and calculated parameters are not modified. Original
working text is archived before the edit; this is not a complete-paper claim.
"""
from pathlib import Path
import datetime, hashlib, json, re

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '02_过程文件/manuscript'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source = WORK / 'manuscript_content.json'
    patch = json.loads((WORK / '219_method_clarity_patch_20261106.json').read_text(encoding='utf8'))
    assert sha(source) == patch['target_sha256_at_preparation']
    original = source.read_bytes()
    content = json.loads(original)
    assert content['status'] == 'DRAFT_RESULTS_PENDING' and len(content['references']) == 30
    backup = WORK / 'archive/manuscript_content_before_clarity_20261106.json'
    backup.parent.mkdir(exist_ok=True)
    if backup.exists():
        assert backup.read_bytes() == original
    else:
        backup.write_bytes(original)
    for item in patch['operations']:
        if item['json_path'].startswith('blocks['):
            index = int(re.search(r'\[(\d+)\]', item['json_path']).group(1))
            old = content['blocks'][index]['text']
            assert old.count(item['old']) == 1
            new = item['new']
            if item['id'] == 'C04a_cost_tool_citation':
                new = new.replace('[29]', '[29,31]')
            elif item['id'] == 'C04b_euclidean_tool_citation':
                new = new.replace('[29]', '[32]')
            content['blocks'][index]['text'] = old.replace(item['old'], new)
        else:
            assert item['id'] == 'C04c_reference29' and content['references'][28] == item['old']
            # Cite each distinct official page under its actual title.
            content['references'][28] = 'Esri. Cost Distance (Spatial Analyst)—ArcGIS Pro 3.1[EB/OL]. [2026-11-06]. https://pro.arcgis.com/en/pro-app/3.1/tool-reference/spatial-analyst/cost-distance.htm.'
    content['references'].extend([
        'Esri. Cost Allocation (Spatial Analyst)—ArcGIS Pro 3.1[EB/OL]. [2026-11-06]. https://pro.arcgis.com/en/pro-app/3.1/tool-reference/spatial-analyst/cost-allocation.htm.',
        'Esri. Euclidean Distance (Spatial Analyst)—ArcGIS Pro 3.1[EB/OL]. [2026-11-06]. https://pro.arcgis.com/en/pro-app/3.1/tool-reference/spatial-analyst/euclidean-distance.htm.',
    ])
    source.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf8')
    receipt = {'status': 'WORKING_PROSE_CLARIFIED_NO_METHOD_CHANGE',
               'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source_before_sha256': hashlib.sha256(original).hexdigest(),
               'source_after_sha256': sha(source), 'operations': 6,
               'distinct_official_sources': [29, 31, 32],
               'approved_proposal_changed': False, 'calculations_changed': False,
               'results_created': False, 'complete_paper': False}
    (WORK / 'method_clarity_applied_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
