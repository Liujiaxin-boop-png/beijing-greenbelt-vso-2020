"""Install this source archive into a new local workspace; no datasets are downloaded."""
import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOLDERS = ('project', 'work', 'raw', 'results', 'figures', 'code')
def substitutions(root, exe):
    pairs = {f'D:/ER219_{name}': (root / name).as_posix() for name in FOLDERS}
    pairs['C:/ER219_user'] = Path.home().as_posix()
    pairs.update(exe)
    tokens = {}
    for old, new in pairs.items():
        for separator in ['/', '\\', '\\\\']:
            tokens[old.replace('/', separator)] = str(new).replace('\\','/')
    return sorted(tokens.items(), key=lambda item: -len(item[0]))
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list', action='store_true', help='list the source files without writing')
    p.add_argument('--workspace', type=Path, help='a new, non-existent practice directory')
    p.add_argument('--software', type=Path, help='optional JSON map from archived install paths to installed software')
    opt = p.parse_args()
    files = [path for parent in ['layout', 'entrypoints'] for path in (HERE/parent).rglob('*') if path.is_file() and '__pycache__' not in path.parts]
    if opt.list:
        for path in sorted(files):
            print(path.relative_to(HERE).as_posix())
        return
    if opt.workspace is None:
        p.error('use --list or --workspace')
    target = opt.workspace.resolve()
    if target.exists() or target.is_relative_to(HERE) or any(c in str(target) for c in "'\"\r\n"):
        p.error('supply a new directory outside the repository, without quote marks in the path')
    exe = json.loads(opt.software.read_text(encoding='utf-8-sig')) if opt.software else {}
    rules = substitutions(target, exe)
    target.mkdir(parents=True, exist_ok=False)
    for name in FOLDERS:
        (target/name).mkdir()
    for src in files:
        rel = src.relative_to(HERE)
        dst = target/(Path(*rel.parts[1:]) if rel.parts[0]=='layout' else rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding='utf-8-sig')
        for old, new in rules:
            text=text.replace(old,new)
        dst.write_text(text,encoding='utf-8-sig' if src.suffix.lower()=='.ps1' else 'utf-8')
    print(f'{len(files)} source files installed to {target}')
if __name__=='__main__':
    main()
