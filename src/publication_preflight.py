"""Check the exact Git-visible text files before publishing research code.

This is a limited additional pattern/format check, not a guarantee that an
arbitrary repository is free of all sensitive material. Never print matches.
"""
from pathlib import Path
import datetime, hashlib, json, re, subprocess

CODE = Path(__file__).resolve().parents[1]
ROOT = CODE.parent
GIT = r'C:\Program Files\Git\cmd\git.exe'
PATTERNS = {
    'github_classic': r'gh[pousr]_[A-Za-z0-9]{20,}',
    'github_finegrained': r'github_pat_[A-Za-z0-9_]{40,}',
    'api_secret': r'sk-[A-Za-z0-9_-]{32,}',
    'private_key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
}
ALLOWED = {'.py', '.ps1', '.md', '.json', '.txt', '.yaml', '.yml', '.csv'}


def main():
    raw = subprocess.check_output([GIT, '-C', str(CODE), 'ls-files', '-z',
                                   '--cached', '--others', '--exclude-standard'])
    names = sorted(set(x.decode('utf8') for x in raw.split(b'\0') if x))
    files = []; failures = []
    for name in names:
        path = CODE / name
        if not path.is_file():
            failures.append({'file': name, 'reason': 'Missing Git-visible file'})
            continue
        if path.suffix.lower() not in ALLOWED and path.name not in {'.gitignore', '.gitattributes'}:
            failures.append({'file': name, 'reason': 'Unexpected file type'})
            continue
        data = path.read_bytes()
        if len(data) > 1024 * 1024:
            failures.append({'file': name, 'reason': 'Unexpected large text file'})
        text = data.decode('utf-8-sig')
        for label, pattern in PATTERNS.items():
            if re.search(pattern, text):
                failures.append({'file': name, 'reason': label})
        if path.suffix == '.py':
            compile(text, str(path), 'exec')
        elif path.suffix == '.json':
            json.loads(text)
        files.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest()})
    subprocess.run([GIT, '-C', str(CODE), 'diff', '--check'], check=True)
    report = {
        'status': 'PASS' if not failures else 'FAIL',
        'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'files_scanned': len(files), 'files': files, 'failures': failures,
        'note': 'Limited text/code pattern check; raw data, reference PDFs, local runtime overrides and accounts remain outside Git.',
    }
    target = ROOT / '02_过程文件/code_publication_preflight.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'status': report['status'], 'files_scanned': len(files),
                      'failures': failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
