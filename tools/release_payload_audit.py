"""Check delivery boundaries without extracting archived calculation data."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zipfile


def forbidden(name):
    parts = PurePosixPath(name.replace('\\', '/')).parts
    return ('nbse2' in name.lower() or 'POTCAR' in parts or
            any(p in {'.pypirc', 'id_rsa', 'id_ed25519', '.env'} for p in parts))


def members(path):
    if path.suffix in {'.zip', '.whl'}:
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    with tarfile.open(path) as archive:
        entries = archive.getmembers()
        if any(e.issym() or e.islnk() for e in entries):
            raise ValueError(f'Archive contains links: {path}')
        return [e.name for e in entries]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--dist', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    names = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=a.repo).decode().split('\0')
    files = [a.repo / n for n in set(names) if n and (a.repo / n).is_file()]
    for f in files:
        if forbidden(f.relative_to(a.repo).as_posix()) or f.is_symlink():
            raise ValueError(f'Forbidden repository payload: {f}')
        if f.stat().st_size >= 100 * 1024**2:
            raise ValueError(f'GitHub file-size limit: {f}')
    archives = [f for f in files if f.suffix == '.zip' or
                f.name.endswith(('.tar.gz', '.tgz', '.tar.xz'))]
    checked = []
    for f in archives:
        entries = members(f)
        bad = [n for n in entries if forbidden(n)]
        if bad:
            raise ValueError(f'Forbidden archive payload in {f}: {bad}')
        checked.append({'path': str(f.relative_to(a.repo)), 'members': len(entries)})
    distributions = []
    for f in sorted(a.dist.iterdir()):
        if not f.name.endswith(('.whl', '.tar.gz')):
            continue
        entries = members(f)
        bad = [n for n in entries if forbidden(n) or
               {'examples', 'dist', '.git'}.intersection(PurePosixPath(n).parts)]
        if bad:
            raise ValueError(f'Forbidden distribution payload in {f}: {bad}')
        distributions.append({'file': f.name, 'bytes': f.stat().st_size,
                              'sha256': hashlib.sha256(f.read_bytes()).hexdigest(),
                              'members': len(entries)})
    assert len(distributions) == 2, distributions
    report = {'repository_files': len(files), 'checked_archives': checked,
              'distributions': distributions, 'status': 'passed',
              'scope': 'Path, link, archive membership and package-boundary checks; not a license opinion.'}
    a.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'files': len(files), 'archives': len(archives),
                      'distributions': distributions}))


if __name__ == '__main__':
    main()
