"""Audited full IR/Raman preparation for the unpassivated 1D case campaign."""

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import numpy as np

from zstar import spectra, workflow
from zstar.pyatb_precision import precision_command

ABACUS = '/home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus'


def rigid_mode_audit(modes):
    """Identify translations and axial rigid rotation from mass-weighted overlaps."""
    positions = modes.positions_fractional @ modes.lattice_angstrom
    positions -= np.average(positions, axis=0, weights=modes.masses_amu)
    weight = np.sqrt(modes.masses_amu)[:, None]
    translations = [np.broadcast_to(axis, positions.shape) * weight for axis in np.eye(3)]
    rotation = np.cross(np.array([0., 0., 1.]), positions) * weight
    basis = np.array([x.ravel() for x in translations + [rotation]]).T
    if np.linalg.matrix_rank(basis) != 4:
        raise ValueError('The selected tube/chain must have four independent rigid motions')
    q, _ = np.linalg.qr(basis)
    eigenvectors = modes.eigenvectors.reshape(len(modes.frequencies_cm1), -1)
    overlap = np.sum(abs(eigenvectors.conj() @ q) ** 2, axis=1)
    return [dict(mode=i + 1, frequency_cm1=float(f), rigid_overlap=float(p),
                 classified_rigid=bool(p > .8))
            for i, (f, p) in enumerate(zip(modes.frequencies_cm1, overlap))]


def prepare(root, parts):
    if parts < 1:
        raise ValueError('parts must be positive')
    response = root / 'unified'
    modes = spectra.load_gamma_modes(response / 'qpoints.yaml')
    audit = rigid_mode_audit(modes)
    (root / 'rigid-mode-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    rigid = [row for row in audit if row['classified_rigid']]
    if len(rigid) != 4 or any(abs(row['frequency_cm1']) > 20 for row in rigid):
        raise ValueError('Rigid-motion mixing/frequencies need review before excluding modes')
    selected = [row['mode'] for row in audit if not row['classified_rigid']]
    if any(row['frequency_cm1'] <= 0 for row in audit if not row['classified_rigid']):
        raise ValueError('Nonrigid mode is not stable; do not calculate a misleading spectrum')
    born = spectra.read_born_data(response / 'BEC.dat', natoms=len(modes.masses_amu),
                                   dielectric_path=response / 'BORN')
    ir = spectra.calculate_ir_spectrum(modes, born, dimensionality=1, mode_numbers=selected,
                                       broadening_cm1=8, points=3001)
    spectra.write_ir_outputs(root / 'ir', ir)
    output = root / 'raman'
    if output.exists():
        raise FileExistsError(f'Inspect existing Raman inputs before preparing: {output}')
    reference = response / '0.no-move'
    files = [reference / 'INPUT-scf', reference / 'KPT']
    files += sorted(reference.glob('*.upf')) + sorted(reference.glob('*.orb'))
    manifest = spectra.prepare_raman_displacements(
        response / 'STRU', modes, output, amplitude=.02,
        mode_numbers=selected, copy_files=files)
    manifest['reference_dir'] = str(reference.resolve())
    manifest['rigid_motion_selection'] = str((root / 'rigid-mode-audit.json').resolve())
    (output / 'raman_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for index in range(parts):
        folder = output / f'part-{index + 1}'
        folder.mkdir()
        partition = {**manifest, 'modes': manifest['modes'][index::parts]}
        if not partition['modes']:
            raise ValueError('More worker partitions than optical modes')
        (folder / 'raman_manifest.json').write_text(json.dumps(partition, indent=2) + '\n')
    print(json.dumps(dict(optical_modes=len(selected), partitions=parts,
                         scf_stages=2 * len(selected), ir='calculated', raman='prepared')))


def run(root, part):
    folder = root / 'raman' / f'part-{part}'
    lock = folder / 'worker.lock'
    with lock.open('x') as handle:
        handle.write(f'{socket.gethostname()} {os.getpid()}\n')
    state = dict(host=socket.gethostname(), pid=os.getpid(), status='running')
    state_file = folder / 'worker.json'
    state_file.write_text(json.dumps(state) + '\n')
    original = workflow._run_shell
    abacus = f'mpirun -np 1 {ABACUS}'

    def timed(command, **kwargs):
        pyatb = '-m zstar.pyatb_precision' in command
        kwargs['env'] = {**kwargs['env'], 'OMP_NUM_THREADS': '1' if pyatb else '40',
                         'MKL_NUM_THREADS': '1' if pyatb else '40', 'OPENBLAS_NUM_THREADS': '1'}
        record = dict(command=command, cwd=str(kwargs['cwd']), host=socket.gethostname(),
                      mpi=40 if pyatb else 1, omp=1 if pyatb else 40,
                      kind='ABACUS' if command == abacus else 'PYATB' if pyatb else 'preparation')
        start = time.monotonic()
        try:
            result = original(command, **kwargs)
            record['success'] = True
            return result
        except Exception as exc:
            record.update(success=False, error=str(exc))
            raise
        finally:
            record['wall_seconds'] = time.monotonic() - start
            record['allocated_core_hours'] = record['wall_seconds'] * 40 / 3600
            with (folder / 'component_times.jsonl').open('a') as stream:
                stream.write(json.dumps(record) + '\n')

    workflow._run_shell = timed
    binary = Path(sys.executable).parent
    try:
        workflow.run_raman_workflow(
            folder, reference_dir=root / 'unified/0.no-move', abacus_command=abacus,
            pyatb_input=str(binary / 'pyatb_input'), pyatb_executable=str(binary / 'pyatb'),
            pyatb_command=precision_command(f'mpirun -np 40 {binary / "pyatb"}'),
            dimensionality=1, omp_threads=40, mp_density=.08)
        state['status'] = 'completed-awaiting-tensor-audit'
    except Exception as exc:
        state.update(status='failed', error=str(exc))
        raise
    finally:
        workflow._run_shell = original
        state_file.write_text(json.dumps(state, indent=2) + '\n')
        lock.unlink()


def collect(root):
    folder = root / 'raman'
    stages = workflow.discover_raman_stages(folder)
    if not all(workflow.scf_is_complete(s.path) and workflow.dielectric_is_complete(s.path)
               for s in stages):
        raise ValueError('Raman response stages are incomplete')
    modes = spectra.load_gamma_modes(root / 'unified/qpoints.yaml')
    numbers, tensors, kind = spectra.collect_raman_tensors(
        folder, dimensionality=1, cell_cross_section_angstrom2=modes.area_angstrom2)
    result = spectra.calculate_raman_spectrum(modes, numbers, tensors, tensor_kind=kind,
                                              temperature_K=298, laser_nm=532,
                                              broadening_cm1=8, points=3001)
    spectra.write_raman_outputs(root / 'raman_spectrum', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'launch', 'collect'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parts', type=int, default=2)
    parser.add_argument('--part', type=int, default=1)
    args = parser.parse_args()
    args.root = args.root.resolve()
    if args.action == 'prepare':
        prepare(args.root, args.parts)
    elif args.action == 'run':
        run(args.root, args.part)
    elif args.action == 'collect':
        collect(args.root)
    else:
        folder = args.root / 'raman' / f'part-{args.part}'
        with (folder / 'launch.json').open('x') as marker:
            with (folder / 'driver.log').open('ab') as log:
                command = [sys.executable, '-u', str(Path(__file__).resolve()), 'run',
                           '--root', str(args.root), '--part', str(args.part)]
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
            json.dump(dict(host=socket.gethostname(), pid=process.pid, command=command), marker)
        print((folder / 'launch.json').read_text())
