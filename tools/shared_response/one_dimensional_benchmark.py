"""Matched 1D Cartesian BEC and independent Gamma-force timing controls."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import one_dimensional_cases as production
import separate_force_benchmark as force
from zstar.shared_abacus import prepare_shared_abacus

SOURCE = Path('/home/zhuxd/abacus/agent-runs/20260905-one-dimensional')
ROOT = Path('/home/zhuxd/abacus/agent-runs/20260906-one-dimensional-benchmark')
CASES = ('BN_9_0', 'Sb2S3')


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def setup_force():
    force.ROOT = ROOT / 'independent_phonon'
    force.SOURCES = {case: SOURCE / case / 'unified' for case in CASES}


def prepare(case):
    destination = ROOT / case
    destination.mkdir(parents=True, exist_ok=False)
    seed = destination / 'seed'
    shutil.copytree(SOURCE / case / 'response-seed', seed)
    manifest = prepare_shared_abacus(seed / 'STRU', root=destination / 'cartesian',
        scf_input=seed / 'INPUT', dimension=1, symprec=1e-5,
        method='central', displacement_scheme='cartesian-control')
    old = json.loads((SOURCE / case / 'unified/shared_response.json').read_text())
    save(destination / 'plan.json', {
        'case': case, 'source': str(SOURCE / case), 'dimension': 1,
        'cartesian_displacements': len(manifest['stages']),
        'unified_displacements': len(old['stages']),
        'cartesian_BEC_SCFs': 1 + len(manifest['stages']),
        'independent_phonon_SCFs': len(old['stages']),
        'unified_BEC_and_phonon_SCFs': 1 + len(old['stages']),
        'reference_convention': 'One reference counted in Cartesian BEC; independent force route contains only displacements.',
        'control_caveat': 'Cartesian response runner also exports forces, as in earlier benchmark; no speculative timing subtraction.',
        'seed_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in seed.iterdir() if p.is_file()}})
    setup_force()
    force.prepare(case)


def run(case, route):
    if route == 'cartesian':
        production.run_response(ROOT, case, ensemble='cartesian')
    else:
        setup_force()
        force.run(case)


def launch(case, route):
    root = ROOT / case
    marker = root / f'{route}-launch.json'
    if marker.exists():
        raise FileExistsError(marker)
    env = {**os.environ, 'PYTHONPATH': str(SOURCE / 'upload'),
           'OMP_NUM_THREADS': '40', 'MKL_NUM_THREADS': '40',
           'OPENBLAS_NUM_THREADS': '1', 'I_MPI_PIN_DOMAIN': 'omp'}
    with marker.with_suffix('.log').open('xb') as log:
        process = subprocess.Popen([sys.executable, '-u', __file__, 'run', case, route],
            env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True)
    save(marker, {'host': socket.gethostname(), 'pid': process.pid,
                  'case': case, 'route': route})
    print(marker.read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'launch'])
    parser.add_argument('case', choices=CASES)
    parser.add_argument('route', choices=['cartesian', 'phonon'], nargs='?')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.case)
    elif args.route is None:
        parser.error('run/launch requires a route')
    else:
        (run if args.action == 'run' else launch)(args.case, args.route)
