"""Check the recorded Windows ASCII junctions; create missing ones only on request.

This utility never deletes, replaces, moves or overwrites an existing path.
The default mode is read-only. No scientific computation is invoked.
"""
from pathlib import Path
import argparse
import base64
import json
import os
import subprocess

CODE = Path(__file__).resolve().parent
PROJECT = CODE.parent
FOLDERS = {
    'ER219_raw': '01_原始数据',
    'ER219_work': '02_过程文件',
    'ER219_results': '03_结果文件',
    'ER219_figures': '04_图件',
    'ER219_code': '05_代码',
}


def inspect(alias, target):
    if os.path.lexists(alias):
        if not os.path.isjunction(alias):
            return {'alias': str(alias), 'target': str(target), 'status': 'CONFLICT_NOT_JUNCTION'}
        actual = alias.resolve()
        if actual != target.resolve():
            return {'alias': str(alias), 'target': str(target), 'actual': str(actual),
                    'status': 'CONFLICT_WRONG_TARGET'}
        if not target.is_dir():
            return {'alias': str(alias), 'target': str(target), 'status': 'CONFLICT_MISSING_TARGET'}
        return {'alias': str(alias), 'target': str(target), 'status': 'PASS'}
    return {'alias': str(alias), 'target': str(target), 'status': 'MISSING_JUNCTION'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Read-only check (default).')
    mode.add_argument('--create', action='store_true', help='Create only absent directories/junctions.')
    args = parser.parse_args()
    if os.name != 'nt' or not hasattr(os.path, 'isjunction'):
        raise SystemExit('This recorded workflow requires Windows and Python >= 3.12.')
    if CODE != (PROJECT / '05_代码').resolve():
        raise SystemExit('Clone this repository as <project>/05_代码 before running setup.')
    if not Path('D:/').is_dir():
        raise SystemExit('The recorded native paths require drive D:. No drive is created or remapped.')
    pairs = [(Path('D:/') / name, PROJECT / folder) for name, folder in FOLDERS.items()]
    # Inspect EVERY existing alias before any mutation, including broken junctions.
    rows = [inspect(a, t) for a, t in pairs]
    conflicts = [x for x in rows if x['status'].startswith('CONFLICT')]
    if conflicts:
        print(json.dumps({'status': 'STOP_CONFLICT', 'changes': [], 'checks': rows}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    created = []
    if args.create:
        for alias, target in pairs:
            if not os.path.lexists(alias):
                target.mkdir(parents=True, exist_ok=True)
                # Literal quoted paths in a native PowerShell creation command.
                quote = lambda p: "'" + str(p).replace("'", "''") + "'"
                script = ('New-Item -ItemType Junction -Path ' + quote(alias)
                          + ' -Target ' + quote(target) + ' -ErrorAction Stop | Out-Null')
                encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
                subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                                '-EncodedCommand', encoded], check=True)
                created.append(str(alias))
        rows = [inspect(a, t) for a, t in pairs]
    passed = all(x['status'] == 'PASS' for x in rows)
    print(json.dumps({'status': 'PASS' if passed else 'SETUP_REQUIRED',
                      'read_only': not args.create, 'created': created,
                      'project': str(PROJECT), 'checks': rows}, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
