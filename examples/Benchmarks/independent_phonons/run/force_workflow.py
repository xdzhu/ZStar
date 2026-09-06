"""Verify retained independent forces or repeat one case in a private work tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def verify():
    evidence = ROOT / 'results'
    manifest = json.loads((evidence / 'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        if hashlib.sha256((evidence / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Changed original evidence: {name}')
    summaries = json.loads((evidence / 'summary.json').read_text())
    for name, report in summaries.items():
        assert report['separate']['status'] == report['unified']['status'] == 'computed'
        assert report['timing']['status'] == 'completed'
        print(name, report['timing']['SCFs'], 'independent SCFs verified')
    print(f'PASS: {len(manifest["files"])} archived file hashes; no result files modified.')


def calculate(case, work, command, threads):
    from zstar.abacus_assets import prepare_stru_assets
    from zstar.shared_abacus import read_forces
    from zstar.workflow import scf_is_complete

    source = ROOT / 'results' / case
    plan = json.loads((source / 'plan.json').read_text())
    basis = ROOT.parent / case / 'run'
    work = work.resolve()
    if work == source.resolve() or source.resolve() in work.parents:
        raise ValueError('New calculations cannot overwrite archived results.')
    work.mkdir(parents=True, exist_ok=True)
    for item in plan['stages']:
        stage = work / item['name']
        if not stage.exists():
            stage.mkdir()
            for filename in ('INPUT', 'STRU', 'KPT'):
                shutil.copy2(source / item['name'] / filename, stage / filename)
            assets = prepare_stru_assets(stage / 'STRU', pp_dir=basis,
                orb_dir=basis, output_dir=stage / '.zstar-assets')
            if assets.changed:
                shutil.copy2(assets.path, stage / 'STRU')
            for asset in assets.assets:
                shutil.copy2(asset, stage / asset.name)
        if not scf_is_complete(stage):
            start = time.monotonic()
            with (stage / 'driver.log').open('ab') as log:
                subprocess.run(command, shell=True, cwd=stage, check=True,
                    env={**os.environ, 'OMP_NUM_THREADS': str(threads),
                         'MKL_NUM_THREADS': str(threads), 'OPENBLAS_NUM_THREADS': '1'},
                    stdout=log, stderr=subprocess.STDOUT)
            (stage / 'timing.json').write_text(json.dumps({
                'elapsed_seconds': time.monotonic()-start, 'command': command,
                'omp_threads': threads}) + '\n')
        if not scf_is_complete(stage):
            raise RuntimeError(f'SCF did not converge: {stage}')
        read_forces(stage)
        print(stage.name, 'completed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--calculate', choices=['SiC', 't_HfO2', 'alpha_In2Se3', 'hBN', 'MoS2', 'H2O', 'CH4'])
    parser.add_argument('--work', type=Path)
    parser.add_argument('--command', default='mpirun -np 1 abacus')
    parser.add_argument('--omp', type=int, default=40)
    args = parser.parse_args()
    if args.omp < 1:
        parser.error('--omp must be positive')
    verify()
    if args.calculate:
        calculate(args.calculate, args.work or ROOT / ('work-' + args.calculate), args.command, args.omp)
