"""Measure independent force-only SCFs without modifying joint-response archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import numpy as np

from zstar import workflow
from zstar.shared_abacus import read_forces


BASE = Path('/home/zhuxd/abacus/agent-runs')
ROOT = BASE / '20260904-independent-force-benchmark'
OLD = BASE / '20260904-shared-response-benchmark'
EIGHT = BASE / '20260904-eight-system-efficiency'
MOL = BASE / '20260904-molecular-relaxed-efficiency'
SOURCES = {
    'SiC': OLD / 'sic/shared', 't_HfO2': OLD / 'hfo2/shared',
    'alpha_In2Se3': OLD / 'in2se3/shared',
    'hBN': EIGHT / 'hBN/unified', 'MoS2': EIGHT / 'MoS2/unified',
    'H2O': MOL / 'H2O/unified', 'CH4': MOL / 'CH4/unified',
}
ABACUS = '/home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus'


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def prepare(case):
    source = SOURCES[case]
    metadata = json.loads((source / 'shared_response.json').read_text())
    output = ROOT / case
    output.mkdir(parents=True, exist_ok=False)
    adjustments = {'calculation': 'scf', 'cal_force': '1', 'cal_stress': '0',
                   'init_chg': 'auto', 'out_chg': '0', 'out_mat_hs2': '0',
                   'out_mat_r': '0', 'pseudo_dir': '.', 'orbital_dir': '.'}
    hashes = {}
    for item in metadata['stages']:
        name = item['name']
        src, dst = source / name, output / name
        dst.mkdir()
        # Copy only hashed input assets, never density or Hamiltonian outputs.
        for relative in metadata['input_hashes']:
            path = Path(relative)
            if path.parts[0] != name or len(path.parts) != 2:
                continue
            filename = path.name
            if filename == 'INPUT-scf':
                continue
            original = src / filename
            if not original.is_file():
                raise FileNotFoundError(original)
            shutil.copy2(original, dst / filename)
        text = (src / 'INPUT-scf').read_text()
        for key, value in adjustments.items():
            text = workflow._set_abacus_parameter(text, key, value)
        (dst / 'INPUT').write_text(text)
        for path in dst.iterdir():
            hashes[str(path.relative_to(output))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for filename in ('STRU', 'phonopy_disp.yaml'):
        shutil.copy2(source / filename, output / filename)
    save(output / 'plan.json', {
        'case': case, 'source': str(source), 'stages': metadata['stages'],
        'input_changes': adjustments, 'input_sha256': hashes,
        'reference': 'Retained Cartesian reference; no additional reference SCF is counted.',
        'scope': 'Independent force-only SCFs from atomic charge; no PYATB or matrix export.',
        'cost_combination': 'Add measured force cost to retained Cartesian BEC route. '
                            'That BEC route already requested forces; its cost is not adjusted.',
    })
    print(json.dumps({'case': case, 'prepared': len(metadata['stages'])}))


def run(case):
    output = ROOT / case
    plan = json.loads((output / 'plan.json').read_text())
    lock = output / '.worker.lock'
    with lock.open('x') as handle:
        handle.write(f'{socket.gethostname()} {os.getpid()}\n')
    worker = {'host': socket.gethostname(), 'pid': os.getpid(), 'status': 'running'}
    save(output / 'worker.json', worker)
    forces, differences = [], []
    try:
        for item in plan['stages']:
            stage = output / item['name']
            marker = stage / 'completed.json'
            if not marker.exists():
                from zstar.abacus_assets import prepare_stru_assets
                source_stage = Path(plan['source']) / item['name']
                assets = prepare_stru_assets(stage / 'STRU', pp_dir=source_stage,
                    orb_dir=source_stage, output_dir=stage / '.zstar-assets')
                if assets.changed:
                    shutil.copy2(assets.path, stage / 'STRU')
                for asset in assets.assets:
                    destination = stage / asset.name
                    if asset.resolve() != destination.resolve():
                        shutil.copy2(asset, destination)
                for path in stage.iterdir():
                    if path.is_file() and (path.name in ('STRU', 'INPUT', 'KPT')
                                          or path.suffix.lower() in ('.upf', '.orb')):
                        plan['input_sha256'][str(path.relative_to(output))] = hashlib.sha256(path.read_bytes()).hexdigest()
                save(output / 'plan.json', plan)
                record = {'host': socket.gethostname(), 'stage': item['name'],
                          'mpi': 1, 'omp': 40, 'allocated_cores': 40,
                          'kind': 'independent_force_scf', 'success': False}
                start = time.monotonic()
                try:
                    workflow._run_shell(f'mpirun -np 1 {ABACUS}', cwd=stage,
                        env={**os.environ, 'OMP_NUM_THREADS': '40', 'MKL_NUM_THREADS': '40',
                             'OPENBLAS_NUM_THREADS': '1', 'I_MPI_PIN_DOMAIN': 'omp'},
                        log_path=stage / 'driver.log', dry_run=False)
                    if not workflow.scf_is_complete(stage):
                        raise RuntimeError(f'Unconverged SCF: {stage}')
                    read_forces(stage)
                    record['success'] = True
                finally:
                    record['wall_seconds'] = time.monotonic() - start
                    record['core_hours'] = record['wall_seconds'] * 40 / 3600
                    with (output / 'component_times.jsonl').open('a') as handle:
                        handle.write(json.dumps(record) + '\n')
                    print(json.dumps(record), flush=True)
                save(marker, record)
            force = read_forces(stage)
            forces.append(force)
            old = read_forces(Path(plan['source']) / item['name'])
            differences.append(float(np.max(np.abs(force - old))))
        save(output / 'forces.json', np.asarray(forces).tolist())
        records = [json.loads((output / item['name'] / 'completed.json').read_text())
                   for item in plan['stages']]
        save(output / 'completed.json', {
            'case': case, 'host': socket.gethostname(), 'SCFs': len(forces),
            'independent_force_core_hours': sum(r['core_hours'] for r in records),
            'max_force_difference_from_unified_eV_A': max(differences),
            'status': 'completed',
        })
        worker['status'] = 'completed'
    except Exception as exc:
        worker.update(status='failed', error=repr(exc))
        raise
    finally:
        save(output / 'worker.json', worker)
        lock.unlink()


def launch(cases):
    marker = ROOT / ('launch-' + '-'.join(cases) + '.json')
    if marker.exists():
        raise FileExistsError(marker)
    env = {**os.environ, 'PYTHONPATH': str(EIGHT / 'upload')}
    with marker.with_suffix('.log').open('ab') as log:
        process = subprocess.Popen([sys.executable, '-u', __file__, 'run', *cases],
            env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True)
    save(marker, {'pid': process.pid, 'host': socket.gethostname(), 'cases': cases})
    print(marker.read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'launch'])
    parser.add_argument('cases', nargs='+', choices=list(SOURCES))
    args = parser.parse_args()
    if args.action == 'launch':
        launch(args.cases)
    else:
        for case in args.cases:
            (prepare if args.action == 'prepare' else run)(case)
