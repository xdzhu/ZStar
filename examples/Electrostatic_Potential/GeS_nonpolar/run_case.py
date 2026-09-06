"""Reproduce the fixed-ion GeS control without altering retained evidence."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from zstar.configuration import launcher_command, resolve_parallelism


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calculate', action='store_true', help='Run a fresh ABACUS SCF first.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--work', type=Path, help='New scratch folder; existing folders are refused.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    work = (args.work or root / 'work').resolve()
    command = launcher_command('abacus', root=root)
    mpi, omp = resolve_parallelism(root)
    print(f'Work: {work}\nSCF: {command} (MPI={mpi}, OMP={omp})')
    print('Mode: ' + ('fresh fixed-ion SCF' if args.calculate else 'retained cube, no DFT'))
    if args.dry_run:
        return
    work.mkdir(parents=True, exist_ok=False)
    if args.calculate:
        for path in (root / 'run').iterdir():
            if path.is_file():
                shutil.copy2(path, work / path.name)
        for path in (root / 'run/assets').iterdir():
            shutil.copy2(path, work / path.name)
        env = {**os.environ, 'OMP_NUM_THREADS': str(omp), 'MKL_NUM_THREADS': str(omp)}
        with (work / 'abacus.out').open('w') as log:
            subprocess.run(command, shell=True, cwd=work, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        log = work / 'OUT.ABACUS/running_scf.log'
        if 'charge density convergence is achieved' not in log.read_text():
            raise RuntimeError('SCF convergence was not confirmed; do not use its potential.')
        cube = work / 'OUT.ABACUS/ElecStaticPot.cube'
    else:
        cube = work / 'ElecStaticPot.cube'
        with gzip.open(root / 'results/ElecStaticPot.cube.gz', 'rb') as src, cube.open('wb') as dst:
            shutil.copyfileobj(src, dst)
        expected = json.loads((root / 'results/evidence.json').read_text())['cube_sha256']
        if hashlib.sha256(cube.read_bytes()).hexdigest() != expected:
            raise ValueError('Retained cube digest mismatch')
    before = hashlib.sha256(cube.read_bytes()).hexdigest()
    subprocess.run([sys.executable, '-m', 'zstar', 'pot', '--cube', str(cube),
        '--axes', 'z', '--plane', 'xy', '--plane-average', '--tile', '3', '3',
        '--direction', 'a', '--direction', 'b', '--direction-method', 'linear',
        '--direction-samples', '64', '64', '--direction-smooth', '.15', '--mirror-test',
        '--outdir', str(work / 'potential')], check=True)
    if hashlib.sha256(cube.read_bytes()).hexdigest() != before:
        raise RuntimeError('Input cube changed during analysis')


if __name__ == '__main__':
    main()
