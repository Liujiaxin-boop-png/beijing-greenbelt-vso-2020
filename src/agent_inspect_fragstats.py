"""Inspect the official FRAGSTATS tutorial model without changing it."""
from pathlib import Path
import sqlite3
import json

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '02_过程文件' / '计算审计' / 'FRAGSTATS4.2'
model = WORK / 'tutorial/Tutorial_3/fragmodel.fca'
con = sqlite3.connect(f'file:{model.as_posix()}?mode=ro', uri=True)
tables = con.execute("SELECT name,sql FROM sqlite_master WHERE type='table'").fetchall()
report = {}
for name, sql in tables:
    rows = con.execute('SELECT * FROM "' + name + '"').fetchall()
    report[name] = {'sql':sql,'rows':rows}
(WORK/'official_tutorial_model_schema.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for name, spec in report.items():
    print(name, len(spec['rows']), spec['sql'])
    if 'param' in name or 'metric' in name or name in ('frg_models','frg_scenarios'):
        print(json.dumps(spec['rows'],ensure_ascii=False,indent=2))
