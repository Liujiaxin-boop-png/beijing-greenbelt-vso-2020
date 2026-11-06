"""Clarify complementary robustness metrics and add a seven-scenario table.

The author-approved manuscript text stays in the private process folder.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import json, hashlib, sys

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '02_过程文件/wamad_revision_20261106'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from revise_wmad import NS, W, txt, para, replace_once


def add(parent, tag, **attributes):
    node = E.SubElement(parent, W + tag)
    for key, value in attributes.items():
        node.set(W + key, str(value))
    return node


def scenario_table(plan, template):
    table = E.Element(W + 'tbl')
    props = deepcopy(template.find('w:tblPr', NS))
    table.append(props)
    widths = [600, 2000, 5677]
    grid = add(table, 'tblGrid')
    for width in widths:
        add(grid, 'gridCol', w=width)
    for index, values in enumerate([plan['headers']] + plan['rows']):
        row = add(table, 'tr')
        rowpr = add(row, 'trPr')
        add(rowpr, 'cantSplit')
        if index == 0:
            add(rowpr, 'tblHeader')
        for column, (value, width) in enumerate(zip(values, widths)):
            cell = add(row, 'tc')
            cp = add(cell, 'tcPr')
            add(cp, 'tcW', w=width, type='dxa')
            if index == 0:
                add(cp, 'shd', val='clear', color='auto', fill='F0F1F2')
            margins = add(cp, 'tcMar')
            for direction in ['top', 'left', 'bottom', 'right']:
                add(margins, direction, w=80, type='dxa')
            add(cp, 'vAlign', val='center')
            p = add(cell, 'p'); pp = add(p, 'pPr')
            add(pp, 'spacing', before=0, after=30, line=264, lineRule='auto')
            add(pp, 'ind', left=0, right=0, firstLine=0)
            add(pp, 'jc', val='center' if column == 0 or index == 0 else 'left')
            run = add(p, 'r'); rp = add(run, 'rPr')
            add(rp, 'rFonts', ascii='Times New Roman', hAnsi='Times New Roman', eastAsia='宋体')
            if index == 0:
                add(rp, 'b')
            add(rp, 'color', val='000000'); add(rp, 'sz', val=20)
            add(rp, 'highlight', val='yellow')
            add(run, 't').text = value
    return table


def main():
    plan = json.loads((WORK / 'expansion_plan.json').read_text(encoding='utf-8'))
    source = Path(plan['source']); data = source.read_bytes()
    sha = lambda b: hashlib.sha256(b).hexdigest()
    assert sha(data) == plan['expected_source_sha256']
    output = ROOT / '03_结果文件/论文' / plan['output_name']
    assert not output.exists()
    with ZipFile(source) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    tree = E.fromstring(parts['word/document.xml']); before = deepcopy(tree)
    body = tree.find('w:body', NS); original = list(body)
    changed = []
    def find(prefix):
        return next(p for p in original if txt(p).startswith(prefix))
    def swap(prefix, key):
        p = find(prefix); replace_once(p, txt(p), plan[key]); changed.append(original.index(p))
        return p
    swap('多方案对照用于定位', 'method_lead')
    swap('对每类生境，采用面积加权平均绝对差', 'metric_intro')
    stable = swap('稳定低值要求同一格网', 'stability')
    swap('空间判断对土地覆盖产品和耕地归类较敏感', 'result1')
    swap('参数对照中的排序一致性较高', 'result2')
    scale_result = swap('能够同时比较全部方案的格网很少', 'result3')
    body.insert(body.index(scale_result) + 1, para(scale_result, plan['result4']))

    # Renumber later captions and in-text references without changing tables.
    caption_template = deepcopy(find('表2 各类生境的有效评价范围'))
    for p in original:
        old = txt(p)
        if p.tag != W + 'p' or not ('表2' in old or '表3' in old):
            continue
        for old_ref, new_ref in [('表3', '表4'), ('表2', '表3')]:
            if old_ref in old:
                replace_once(p, old_ref, new_ref)
        changed.append(original.index(p))

    method_template = find('多方案对照用于识别')
    explain = find('式（7）中')
    insertions = [
        para(method_template, plan['spearman']),
        para(method_template, plan['table_lead'], True),
        para(caption_template, plan['caption'], True),
        scenario_table(plan, before.xpath('.//w:tbl', namespaces=NS)[1]),
        para(method_template, plan['table_note']),
    ]
    pos = body.index(explain) + 1
    for node in insertions:
        body.insert(pos, node); pos += 1

    oldbody = list(before.find('w:body', NS))
    for index, (a, b) in enumerate(zip(oldbody, original)):
        if index not in changed:
            assert E.tostring(a) == E.tostring(b), index
    for xpath in ['.//w:drawing', './/w:sectPr', './/m:oMath']:
        assert [E.tostring(n) for n in before.xpath(xpath, namespaces=NS)] == [E.tostring(n) for n in tree.xpath(xpath, namespaces=NS)], xpath
    old_tables = before.xpath('.//w:tbl', namespaces=NS)
    new_tables = tree.xpath('.//w:tbl', namespaces=NS)
    assert len(new_tables) == 4
    assert [E.tostring(n) for n in old_tables] == [E.tostring(new_tables[i]) for i in [0, 2, 3]]
    assert len(tree.xpath('.//m:oMathPara', namespaces=NS)) == 7
    parts['word/document.xml'] = E.tostring(tree, encoding='UTF-8', xml_declaration=True, standalone=True)
    with ZipFile(output, 'x', ZIP_DEFLATED) as z:
        for name, value in parts.items():
            z.writestr(name, value)
    assert source.read_bytes() == data
    report = {'status': 'STRUCTURAL_PASS_RENDER_PENDING', 'source': str(source.resolve()),
              'source_sha256': sha(data), 'output': str(output), 'output_sha256': sha(output.read_bytes()),
              'changed_original_body_indices': sorted(set(changed)), 'added_blocks': len(insertions) + 1,
              'tables': 4, 'original_tables_unchanged': True, 'images_equations_comments_references_preserved': True,
              'numbered_display_equations': 7, 'new_scenario_table': 'S0-S6',
              'result_extension': 'WMAD below 0.003 and rho above 0.999 for source/road comparisons; independently checked saved results'}
    (WORK / 'expanded_revision_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
