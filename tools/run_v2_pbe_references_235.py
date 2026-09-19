#!/usr/bin/env python3
"""Run prepared PBE reference jobs serially on one authorized, idle 235 node.

No tensor is promoted here. Inspect force, stress, symmetry and insulating
character before preparing the response ensembles. Failures retain all logs.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', required=True, type=Path)
parser.add_argument('--mpi', required=True)
parser.add_argument('--abacus', required=True)
parser.add_argument('--vasp', required=True)
args = parser.parse_args()
node = socket.gethostname().split('.')[0]
if node not in ('cu24', 'cu25', 'cu26'):
    raise SystemExit(f'Not an authorized compute node: {node}')
# One compute reservation per node, in addition to stage-directory guards.
lock = Path('/home/zhuxd/abacus/agent-runs') / f'.zstar-pbe-reference-{node}.lock'
lock.mkdir()  # Existing lock requires human inspection, never silent removal.
env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', I_MPI_FABRICS='shm')
manifest = json.loads((args.root / 'campaign.json').read_text())
results = []


def cpu_busy_fraction():
    def sample():
        values = [int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
        return sum(values), values[3] + values[4]
    total0, idle0 = sample()
    time.sleep(1)
    total1, idle1 = sample()
    return 1 - (idle1 - idle0) / max(total1 - total0, 1)


try:
    for material, case in manifest['cases'].items():
        for backend, binary in (('vasp', args.vasp), ('abacus', args.abacus)):
            # User-owned placeholder PBS processes do not imply node activity;
            # running calculator processes or substantial load do.
            active = subprocess.run(['pgrep', '-x', 'abacus|vasp_std|pyatb'], capture_output=True, text=True)
            if active.returncode == 0 or cpu_busy_fraction() > .15:
                raise RuntimeError(f'Node is occupied before {material}/{backend}; refusing overlap')
            stage = Path(case[f'{backend}_reference'])
            marker = stage / 'runtime_pbe_reference.json'
            if marker.exists():
                print(f'RETAIN_EXISTING_RUN {material} {backend}', flush=True)
                continue
            start = time.time()
            print(f'START {material} {backend} node={node} mpi=40 omp=1', flush=True)
            with (stage / 'reference_40mpi.log').open('w') as log:
                completed = subprocess.run([args.mpi, '-np', '40', binary], cwd=stage, env=env, stdout=log, stderr=subprocess.STDOUT)
            runtime = {'material': material, 'backend': backend, 'functional': 'PBE',
                       'node': node, 'mpi': 40, 'omp': 1, 'returncode': completed.returncode,
                       'start_unix': start, 'elapsed_seconds': time.time() - start,
                       'status': 'executed_pending_physical_validation',
                       'command': [args.mpi, '-np', '40', binary]}
            runtime['core_hours'] = runtime['elapsed_seconds'] * 40 / 3600
            marker.write_text(json.dumps(runtime, indent=2) + '\n')
            results.append(runtime)
            (args.root / 'reference_execution.json').write_text(json.dumps(results, indent=2) + '\n')
            print(f'END {material} {backend} rc={completed.returncode}', flush=True)
            if completed.returncode:
                print('FAILED_LOGS_PRESERVED; continuing other independent references', flush=True)
finally:
    lock.rmdir()
