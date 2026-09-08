"""Exercise each indexed example's documented dry run without starting DFT."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def audit(repo, output, shell='bash'):
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join((str(Path(sys.executable).resolve().parent),
                                  env.get('PATH', '')))
    records = []
    for case in json.loads((repo/'examples/manifest.json').read_text())['cases']:
        folder = repo/'examples'/case['path']
        started = time.monotonic()
        try:
            run = subprocess.run([shell, 'run.sh', '--dry-run'], cwd=folder,
                                 capture_output=True, text=True, timeout=120,
                                 env=env)
            row = dict(case=case['path'], returncode=run.returncode,
                       stdout=run.stdout, stderr=run.stderr)
        except subprocess.TimeoutExpired as exc:
            row = dict(case=case['path'], returncode=-1, error=str(exc))
        row['elapsed_s'] = time.monotonic()-started
        records.append(row)
        output.write_text(json.dumps(records, indent=2))
        print(case['path'], row['returncode'], flush=True)
    failed = [r['case'] for r in records if r['returncode']]
    if failed:
        raise RuntimeError(f'Example dry runs failed: {failed}')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--shell', default='bash', help='Bash executable (use Git Bash on Windows).')
    args = p.parse_args()
    audit(args.repo.resolve(), args.output.resolve(), args.shell)
