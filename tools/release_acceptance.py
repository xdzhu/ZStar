"""Create a checkout-independent review snapshot and exercise installed ZStar."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def snapshot(repo, destination):
    if destination.exists():
        raise FileExistsError(destination)
    names = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=repo).decode().split('\0')
    folders = {'zstar', 'tests', 'tools', 'docs', 'examples', '.github'}
    files = {'pyproject.toml', 'MANIFEST.in', 'LICENSE', 'CHANGELOG.md',
             'CITATION.cff', 'README.md', 'README.zh-CN.md', 'README_PYPI.md',
             '.gitattributes', '.gitignore'}
    excluded = {'__pycache__', '.pytest_cache', 'work', 'node_modules'}
    records = {}
    for name in sorted(set(names)):
        if not name:
            continue
        relative = Path(name)
        if relative.parts[0] not in folders and name not in files:
            continue
        source = repo / relative
        if not source.is_file() or excluded.intersection(relative.parts):
            continue
        if source.is_symlink() or source.name == 'POTCAR' or 'nbse2' in name.lower():
            raise ValueError(f'Forbidden delivery input: {name}')
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        records[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (destination / 'snapshot-sha256.json').write_text(json.dumps(records, indent=2))
    return {'files': len(records), 'path': str(destination)}


def smoke(output):
    import zstar
    import importlib.metadata as metadata
    prefix = Path(sys.prefix).resolve()
    module = Path(zstar.__file__).resolve()
    if prefix not in module.parents:
        raise ValueError(f'Not testing installed package: {module}')
    output.mkdir(parents=True, exist_ok=True)
    commands = [['--version'], ['--help']]
    for family in ('bec', 'phonon', 'spectra'):
        commands += [[family, verb, '--help'] for verb in ('pre', 'run', 'stat', 'post', 'job')]
    commands += [['dielectric', verb, '--help'] for verb in ('static', 'freq', 'optics')]
    commands += [[family, '--help'] for family in
                 ('config', 'response', 'density', 'stru', 'data', 'skill', 'pot')]
    commands += [['backend', 'list', '--json'], ['skill', 'path'], ['config', 'show']]
    records = []
    for args in commands:
        result = subprocess.run([sys.executable, '-I', '-m', 'zstar', *args],
                                cwd=output, capture_output=True, text=True, encoding='utf-8')
        records.append({'args': args, 'returncode': result.returncode,
                        'stdout': result.stdout, 'stderr': result.stderr})
    report = {'python': sys.version, 'module': str(module), 'prefix': str(prefix),
              'packages': {d.metadata['Name']: d.version for d in metadata.distributions()},
              'commands': records}
    (output / 'installed-smoke.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    failed = [r['args'] for r in records if r['returncode']]
    if failed:
        raise RuntimeError(f'Failed CLI commands: {failed}')
    return {'commands': len(records), 'module': str(module)}


def installed_tests(repo, output, include_tools=False):
    import zstar
    import pytest
    module = Path(zstar.__file__).resolve()
    assert Path(sys.prefix).resolve() in module.parents, module
    # Repository-only validation helpers are not wheel modules. Import ZStar
    # first so adding those helpers cannot replace the installed package path.
    sys.path.insert(0, str(repo))
    output.mkdir(parents=True, exist_ok=True)
    targets = [str(repo/'tests')]
    if include_tools:
        targets.append(str(repo/'tools'))
    code = pytest.main([*targets, '--import-mode=importlib', '-q',
                        '--junitxml='+str(output/'tests.xml')])
    paths = {name: item.__file__ for name, item in sys.modules.items()
             if name.startswith('zstar.') and getattr(item, '__file__', None)}
    (output/'imported-modules.json').write_text(json.dumps(paths, indent=2))
    assert all(Path(sys.prefix).resolve() in Path(p).resolve().parents for p in paths.values())
    if code:
        raise RuntimeError(f'Installed package tests failed: {code}')
    return {'exitcode': int(code), 'installed_modules': len(paths)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['snapshot', 'smoke', 'tests'])
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--include-tools', action='store_true')
    args = parser.parse_args()
    operations = {'snapshot': lambda: snapshot(args.repo, args.output),
                  'smoke': lambda: smoke(args.output),
                  'tests': lambda: installed_tests(args.repo, args.output, args.include_tools)}
    print(json.dumps(operations[args.action](), indent=2))
