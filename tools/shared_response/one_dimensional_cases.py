"""Reproducible unpassivated 1D seeds and isolated relaxation workers."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

import numpy as np
from ase import Atoms
from ase.build import nanotube
from ase.io import write
from ase.neighborlist import neighbor_list
from phonopy.interface.abacus import read_abacus_output

from zstar.shared_response import read_structure, write_structure

ABACUS = '/home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus'


def center_transverse(atoms):
    """Unwrap at the largest vacuum gap, then center the bounding box in xy."""
    cell = np.asarray(atoms.cell)
    if not np.allclose(cell, np.diag(np.diag(cell)), atol=1e-9):
        raise ValueError('A positive orthogonal cell with periodic z is required')
    if np.any(np.diag(cell) <= 0):
        raise ValueError('Cell lengths must be positive')
    scaled = np.asarray(atoms.scaled_positions).copy()
    for axis in (0, 1):
        positions = scaled[:, axis] % 1.0
        ordered = np.sort(positions)
        gaps = np.diff(np.r_[ordered, ordered[0] + 1])
        start = ordered[(int(np.argmax(gaps)) + 1) % len(ordered)]
        unwrapped = (positions - start) % 1.0
        scaled[:, axis] = unwrapped + .5 - (unwrapped.min() + unwrapped.max()) / 2
    atoms.scaled_positions = scaled
    return atoms


def prepare_bn(root, repo, n):
    case = root / f'BN_{n}_0'
    seed = case / 'seed'
    if seed.exists():
        raise FileExistsError(seed)
    seed.mkdir(parents=True)
    tube = nanotube(n, 0, length=1, bond=1.45)
    radius = np.max(np.linalg.norm(tube.positions[:, :2], axis=1))
    tube.set_cell([2 * radius + 20, 2 * radius + 20, tube.cell[2, 2]])
    tube.pbc = [False, False, True]
    left, right = neighbor_list('ij', tube, 1.8)
    graph = [[] for _ in tube]
    for i, j in zip(left, right):
        graph[i].append(j)
    if any(len(neighbors) != 3 for neighbors in graph):
        raise ValueError('BN tube must have three neighbours per atom without H')
    labels = np.full(len(tube), -1)
    labels[0] = 0
    stack = [0]
    while stack:
        i = stack.pop()
        for j in graph[i]:
            if labels[j] == -1:
                labels[j] = 1 - labels[i]
                stack.append(j)
            elif labels[j] == labels[i]:
                raise ValueError('Tube graph is not bipartite')
    if np.any(labels < 0):
        raise ValueError('Disconnected tube')
    tube.set_chemical_symbols(['B' if x == 0 else 'N' for x in labels])
    tube = tube[np.argsort(labels, kind='stable')]
    tube.positions[:, :2] += np.diag(tube.cell)[:2] / 2
    tube.wrap()
    asset_root = repo / 'examples/2D_Slab/hBN/run/assets'
    shutil.copytree(asset_root, seed / 'assets')
    lines = ['ATOMIC_SPECIES', 'B 10.81 B.upf', 'N 14.007 N.upf',
             '', 'NUMERICAL_ORBITAL', 'B_gga_10au_100Ry_2s2p1d.orb',
             'N_gga_10au_100Ry_2s2p1d.orb', '', 'LATTICE_CONSTANT',
             '1.8897261246257702', '', 'LATTICE_VECTORS']
    lines += [' '.join(f'{x:.16g}' for x in row) for row in tube.cell]
    lines += ['', 'ATOMIC_POSITIONS', 'Direct']
    for symbol in ('B', 'N'):
        indices = [i for i, s in enumerate(tube.symbols) if s == symbol]
        lines += [symbol, '0', str(len(indices))]
        lines += [' '.join(f'{x:.16g}' for x in tube.get_scaled_positions()[i]) + ' m 1 1 1'
                  for i in indices]
    (seed / 'STRU').write_text('\n'.join(lines) + '\n')
    atoms = center_transverse(read_structure(seed / 'STRU'))
    write_structure(seed / 'STRU', seed / 'STRU', atoms)
    write(seed / 'structure.vasp', Atoms(symbols=atoms.symbols, cell=atoms.cell,
                                       scaled_positions=atoms.scaled_positions, pbc=True),
          format='vasp', direct=True)
    parameters = dict(suffix='BNNT', calculation='cell-relax', basis_type='lcao',
                      ks_solver='genelpa', dft_functional='pbe', ntype=2,
                      nspin=1, ecutwfc=100, scf_thr='1e-8', scf_nmax=200,
                      smearing_method='fixed', symmetry=1, gamma_only=0,
                      pseudo_dir='./assets', orbital_dir='./assets',
                      cal_force=1, cal_stress=1, fixed_axes='ab',
                      force_thr_ev=.003, stress_thr=.05, relax_nmax=100,
                      out_chg=0, out_mat_hs2=0, out_mat_r=0)
    (seed / 'INPUT').write_text('INPUT_PARAMETERS\n' + ''.join(
        f'{key:<24}{value}\n' for key, value in parameters.items()))
    (seed / 'KPT').write_text('K_POINTS\n0\nGamma\n1 1 12 0 0 0\n')
    info = dict(case=case.name, atoms=len(tube), composition=tube.get_chemical_formula(),
                generator='ASE nanotube plus checked bipartite B/N assignment',
                transverse_vacuum_A=20, axial_period_A=float(tube.cell[2, 2]),
                centered_xy=True, hydrogen_passivation=False, xc='PBE',
                reference_xc_matched=False, status='prepared-not-calculated')
    (case / 'preparation.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info))


def prepare_sb(root):
    source = root / 'reference/Sb2S3/B3LYP-D3/structure/sb2s3_fc_b3lyp-d3_opt2.f34'
    lines = source.read_text().splitlines()
    if int(lines[0].split()[0]) != 1:
        raise ValueError('Expected an explicitly one-dimensional CRYSTAL model')
    lattice = np.array([[float(v) for v in line.split()] for line in lines[1:4]])
    if not np.allclose(lattice, np.diag(np.diag(lattice))):
        raise ValueError('Expected the reference chain to be aligned with x')
    # CRYSTAL fort.34 stores four lines per symmetry operation, then all atoms.
    offset = 5 + 4 * int(lines[4].split()[0])
    count = int(lines[offset])
    records = [line.split() for line in lines[offset + 1:offset + count + 1]]
    numbers = [int(row[0]) % 100 for row in records]
    if sorted(numbers) != [16] * 6 + [51] * 4:
        raise ValueError('Expected the ten-atom Sb4S6 full chain')
    positions = np.array([[float(v) for v in row[1:4]] for row in records])
    # Proper cyclic rotation: new components are (old y, old z, old x).
    positions = positions[:, [1, 2, 0]]
    widths = np.ptp(positions[:, :2], axis=0)
    cell = np.diag([widths[0] + 20, widths[1] + 20, lattice[0, 0]])
    positions[:, :2] += np.diag(cell)[:2] / 2
    atoms = Atoms(numbers=numbers, positions=positions, cell=cell, pbc=[False, False, True])
    atoms = atoms[np.argsort(atoms.numbers, kind='stable')]
    atoms.wrap()
    seed = root / 'Sb2S3' / 'seed'
    seed.mkdir(parents=True, exist_ok=False)
    shutil.copytree(root / 'sb-assets', seed / 'assets')
    header = ['ATOMIC_SPECIES', 'S 32.06 S_ONCV_PBE-1.0.upf',
              'Sb 121.76 Sb_ONCV_PBE-1.0.upf', '', 'NUMERICAL_ORBITAL',
              'S_gga_9au_100Ry_2s2p1d.orb', 'Sb_gga_9au_100Ry_2s2p2d1f.orb',
              '', 'LATTICE_CONSTANT', '1.8897261246257702', '', 'LATTICE_VECTORS']
    header += [' '.join(f'{v:.16g}' for v in row) for row in cell]
    header += ['', 'ATOMIC_POSITIONS', 'Direct']
    for symbol in ('S', 'Sb'):
        indices = [i for i, s in enumerate(atoms.symbols) if s == symbol]
        header += [symbol, '0', str(len(indices))]
        header += [' '.join(f'{v:.16g}' for v in atoms.get_scaled_positions()[i]) + ' m 1 1 1'
                   for i in indices]
    (seed / 'STRU').write_text('\n'.join(header) + '\n')
    centered = center_transverse(read_structure(seed / 'STRU'))
    write_structure(seed / 'STRU', seed / 'STRU', centered)
    write(seed / 'structure.vasp', Atoms(symbols=centered.symbols, cell=centered.cell,
                                       scaled_positions=centered.scaled_positions, pbc=True),
          format='vasp', direct=True)
    from zstar.workflow import _set_abacus_parameter
    text = (root / 'BN_6_0/seed/INPUT').read_text()
    text = _set_abacus_parameter(text, 'suffix', 'Sb2S3')
    text = _set_abacus_parameter(text, 'vdw_method', 'd3_bj')
    (seed / 'INPUT').write_text(text)
    shutil.copy2(root / 'BN_6_0/seed/KPT', seed / 'KPT')
    (seed.parent / 'preparation.json').write_text(json.dumps(dict(
        atoms=count, composition='Sb4S6', source_doi='10.17632/6tntvw37tr.1',
        source_file=str(source), source_xc='B3LYP-D3(BJ)', calculation_xc='PBE-D3(BJ)',
        reference_xc_matched=False, source_to_zstar_axes=[1, 2, 0], centered_xy=True,
        hydrogen_passivation=False, status='prepared-not-calculated'), indent=2) + '\n')
    print(seed)


def relax(root, case):
    directory = root / case / 'relaxation'
    directory.mkdir()
    for source in (root / case / 'seed').iterdir():
        target = directory / source.name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    env = {**os.environ, 'OMP_NUM_THREADS': '40', 'MKL_NUM_THREADS': '40',
           'OPENBLAS_NUM_THREADS': '1', 'I_MPI_PIN_DOMAIN': 'omp'}
    begin = time.monotonic()
    state = dict(case=case, host=socket.gethostname(), pid=os.getpid(),
                 mpi=1, omp=40, status='running', stage='axial-cell-and-ions-relaxation')
    state_file = directory / 'worker.json'
    state_file.write_text(json.dumps(state, indent=2) + '\n')
    try:
        with (directory / 'abacus.log').open('w') as stream:
            subprocess.run(['mpirun', '-np', '1', ABACUS], cwd=directory, env=env,
                           stdout=stream, stderr=subprocess.STDOUT, check=True)
        logs = list(directory.glob('OUT.*/running_cell-relax.log'))
        if len(logs) != 1:
            raise ValueError('Missing unique cell-relax log')
        text = logs[0].read_text()
        forces = np.asarray(read_abacus_output(str(logs[0])))
        maximum = float(np.max(np.linalg.norm(forces, axis=1)))
        state['maximum_force_eV_A'] = maximum
        if maximum > .005 or not re.search(r'^\s*Relaxation is converged!\s*$', text, re.MULTILINE):
            raise ValueError('Relaxation convergence requires further inspection')
        state['status'] = 'finished-awaiting-stress-and-geometry-audit'
    except Exception as exc:
        state.update(status='failed', error=str(exc))
        raise
    finally:
        state['wall_seconds'] = time.monotonic() - begin
        state['allocated_core_hours'] = state['wall_seconds'] * 40 / 3600
        state_file.write_text(json.dumps(state, indent=2) + '\n')


def audit_relaxation(root, case):
    directory = root / case / 'relaxation'
    state = json.loads((directory / 'worker.json').read_text())
    if state['status'] != 'finished-awaiting-stress-and-geometry-audit':
        raise ValueError(f'Relaxation has not finished successfully: {state["status"]}')
    log, = directory.glob('OUT.*/running_cell-relax.log')
    final, = directory.glob('OUT.*/STRU_ION_D')
    forces = np.asarray(read_abacus_output(str(log)))
    maximum = float(np.max(np.linalg.norm(forces, axis=1)))
    lines = log.read_text().splitlines()
    if not any(line.strip() == 'Relaxation is converged!' for line in lines):
        raise ValueError('No explicit geometry optimization convergence marker')
    index = max(i for i, line in enumerate(lines) if 'TOTAL-STRESS (KBAR)' in line)
    numeric = []
    for line in lines[index + 1:index + 9]:
        fields = line.split()
        if len(fields) == 3:
            try:
                numeric.append([float(x) for x in fields])
            except ValueError:
                pass
    stress = np.asarray(numeric[:3])
    if stress.shape != (3, 3) or not np.all(np.isfinite(stress)):
        raise ValueError('Could not read a finite final stress tensor')
    if maximum > .005 or abs(stress[2, 2]) > .05:
        raise ValueError(f'Unconverged force/stress: {maximum}, {stress[2, 2]}')
    atoms = read_structure(final)
    original = read_structure(root / case / 'seed/STRU')
    if not np.allclose(atoms.cell[:2], original.cell[:2], atol=1e-7, rtol=0):
        raise ValueError('Transverse vacuum lattice changed during relaxation')
    if not np.allclose(atoms.cell, np.diag(np.diag(atoms.cell)), atol=1e-8):
        raise ValueError('Final cell is no longer orthogonal')
    if atoms.symbols != original.symbols:
        raise ValueError('Relaxation changed atom ordering')
    audit = dict(maximum_force_eV_A=maximum, final_stress_kbar=stress.tolist(),
                 axial_period_A=float(atoms.cell[2, 2]), source_final_structure=str(final),
                 relaxation_core_hours=state['allocated_core_hours'], status='accepted')
    return atoms, final, audit


def prepare_response(root, case):
    from zstar.shared_abacus import prepare_shared_abacus
    from zstar.workflow import _set_abacus_parameter

    atoms, final, audit = audit_relaxation(root, case)
    seed = root / case / 'response-seed'
    seed.mkdir(exist_ok=False)
    write_structure(final, seed / 'STRU', center_transverse(atoms))
    for source in (root / case / 'seed/assets').iterdir():
        shutil.copy2(source, seed / source.name)
    shutil.copy2(root / case / 'seed/KPT', seed / 'KPT')
    text = (root / case / 'seed/INPUT').read_text()
    for key, value in dict(calculation='scf', cal_force=1, cal_stress=0,
                           pseudo_dir='.', orbital_dir='.', out_chg=1,
                           out_mat_hs2=1, out_mat_r=1, init_chg='auto').items():
        text = _set_abacus_parameter(text, key, str(value))
    if case == 'Sb2S3':
        for key, value in dict(vdw_cutoff_type='radius', vdw_cutoff_radius=18,
                               vdw_radius_unit='A', vdw_cn_thr=15,
                               vdw_cn_thr_unit='A').items():
            text = _set_abacus_parameter(text, key, str(value))
        audit['response_dispersion'] = dict(method='PBE-D3(BJ)', pair_cutoff_A=18,
                                            coordination_cutoff_A=15,
                                            note='Final reference forces require rechecking after cutoff change')
    text = re.sub(r'^\s*(fixed_axes|relax_nmax|force_thr_ev|stress_thr)\s+.*\n',
                  '', text, flags=re.MULTILINE)
    (seed / 'INPUT').write_text(text)
    manifest = prepare_shared_abacus(seed / 'STRU', root=root / case / 'unified',
                                     scf_input=seed / 'INPUT', dimension=1,
                                     symprec=1e-5, method='auto')
    audit['displacement_stages'] = len(manifest['stages'])
    (root / case / 'relaxation-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit))


def run_response(root, case, ensemble='unified'):
    from zstar import workflow
    from zstar.pyatb_precision import precision_command
    from zstar.shared_abacus import collect_shared_abacus

    if ensemble not in ('unified', 'cartesian'):
        raise ValueError('Unknown response ensemble')
    output = root / case / ensemble
    binary = Path(sys.executable).parent
    command = f'mpirun -np 1 {ABACUS}'
    original = workflow._run_shell
    lock = output / '.response-worker.lock'
    with lock.open('x') as handle:
        handle.write(f'{socket.gethostname()} {os.getpid()}\n')
    state = dict(host=socket.gethostname(), pid=os.getpid(), status='running')

    def timed(cmd, **kwargs):
        pyatb = '-m zstar.pyatb_precision' in cmd
        kwargs['env'] = {**kwargs['env'], 'OMP_NUM_THREADS': '1' if pyatb else '40',
                         'MKL_NUM_THREADS': '1' if pyatb else '40',
                         'OPENBLAS_NUM_THREADS': '1', 'I_MPI_PIN_DOMAIN': 'omp'}
        entry = dict(command=cmd, cwd=str(kwargs['cwd']), host=socket.gethostname(),
                     mpi=40 if pyatb else 1, omp=1 if pyatb else 40,
                     kind='ABACUS' if cmd == command else 'PYATB' if pyatb else 'preparation')
        start = time.monotonic()
        try:
            result = original(cmd, **kwargs)
            entry['success'] = True
            return result
        except Exception as exc:
            entry.update(success=False, error=str(exc))
            raise
        finally:
            entry['wall_seconds'] = time.monotonic() - start
            entry['allocated_core_hours'] = entry['wall_seconds'] * 40 / 3600
            with (output / 'component_times.jsonl').open('a') as handle:
                handle.write(json.dumps(entry) + '\n')
            print(json.dumps(entry), flush=True)

    workflow._run_shell = timed
    (output / 'worker.json').write_text(json.dumps(state) + '\n')
    try:
        settings = dict(abacus_command=command, pyatb_input=str(binary / 'pyatb_input'),
            pyatb_executable=str(binary / 'pyatb'),
            pyatb_command=precision_command(f'mpirun -np 40 {binary / "pyatb"}'),
            omp_threads=40, dimensionality=1, mp_density=.08)
        workflow.run_serial_workflow(output, stop_after=1, **settings)
        log, = (output / '0.no-move').glob('OUT.*/running_scf.log')
        maximum = float(np.max(np.linalg.norm(np.asarray(read_abacus_output(str(log))), axis=1)))
        (output / 'reference-force-audit.json').write_text(json.dumps({
            'maximum_force_eV_A': maximum, 'threshold_eV_A': .005,
            'accepted': maximum <= .005}, indent=2) + '\n')
        if maximum > .005:
            raise ValueError(f'Final response reference force is too large: {maximum} eV/A')
        workflow.run_serial_workflow(output, **settings)
        collect_shared_abacus(output)
        state['status'] = 'finished-awaiting-response-and-mode-audit'
    except Exception as exc:
        state.update(status='failed', error=str(exc))
        raise
    finally:
        (output / 'worker.json').write_text(json.dumps(state, indent=2) + '\n')
        workflow._run_shell = original
        lock.unlink()


def d3_check(root, case):
    """Compare pair-cutoff radii on identical geometry, including image-free radii."""
    from zstar.workflow import _set_abacus_parameter

    if case != 'Sb2S3':
        raise ValueError('D3 audit is scoped to the Sb2S3 PBE-D3(BJ) case')
    parent = root / case / 'd3-check'
    parent.mkdir(exist_ok=False)
    for radius in (16, 18, 50.271835):
        folder = parent / f'radius-{radius:g}A'
        shutil.copytree(root / case / 'seed', folder)
        text = (folder / 'INPUT').read_text()
        for key, value in dict(calculation='scf', vdw_cutoff_type='radius',
                               vdw_cutoff_radius=radius, vdw_radius_unit='A',
                               vdw_cn_thr=15, vdw_cn_thr_unit='A').items():
            text = _set_abacus_parameter(text, key, str(value))
        (folder / 'INPUT').write_text(text)
        started = time.monotonic()
        state = dict(status='running', host=socket.gethostname(), radius_A=radius,
                     pid=os.getpid(), mpi=1, omp=40)
        (folder / 'timing.json').write_text(json.dumps(state) + '\n')
        try:
            env = {**os.environ, 'OMP_NUM_THREADS': '40', 'MKL_NUM_THREADS': '40',
                   'OPENBLAS_NUM_THREADS': '1', 'I_MPI_PIN_DOMAIN': 'omp'}
            with (folder / 'abacus.log').open('w') as log:
                subprocess.run(['mpirun', '-np', '1', ABACUS], cwd=folder, env=env,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            state['status'] = 'finished-awaiting-audit'
        except Exception as exc:
            state.update(status='failed', error=str(exc))
            raise
        finally:
            state['wall_seconds'] = time.monotonic() - started
            state['allocated_core_hours'] = state['wall_seconds'] * 40 / 3600
            (folder / 'timing.json').write_text(json.dumps(state, indent=2) + '\n')


def reference_check(root, case):
    from zstar.workflow import _set_abacus_parameter

    parent = root / case / 'reference-check'
    parent.mkdir(exist_ok=False)
    source = root / case / 'response-seed'
    for name in ('k24', 'vacuum-plus10A'):
        folder = parent / name
        shutil.copytree(source, folder)
        if name == 'k24':
            (folder / 'KPT').write_text('K_POINTS\n0\nGamma\n1 1 24 0 0 0\n')
        else:
            atoms = read_structure(folder / 'STRU')
            positions = atoms.positions.copy()
            cell = atoms.cell.copy()
            cell[0, 0] += 10
            cell[1, 1] += 10
            atoms.cell = cell
            atoms.scaled_positions = positions @ np.linalg.inv(cell)
            write_structure(folder / 'STRU', folder / 'STRU', center_transverse(atoms))
        text = (folder / 'INPUT').read_text()
        for key, value in dict(cal_stress=1, out_chg=0, out_mat_hs2=0, out_mat_r=0).items():
            text = _set_abacus_parameter(text, key, str(value))
        (folder / 'INPUT').write_text(text)
        env = {**os.environ, 'OMP_NUM_THREADS': '40', 'MKL_NUM_THREADS': '40',
               'OPENBLAS_NUM_THREADS': '1', 'I_MPI_PIN_DOMAIN': 'omp'}
        start = time.monotonic()
        state = dict(host=socket.gethostname(), pid=os.getpid(), status='running',
                     check=name, mpi=1, omp=40)
        (folder / 'timing.json').write_text(json.dumps(state) + '\n')
        try:
            with (folder / 'abacus.log').open('w') as log:
                subprocess.run(['mpirun', '-np', '1', ABACUS], cwd=folder, env=env,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            state['status'] = 'finished-awaiting-audit'
        except Exception as exc:
            state.update(status='failed', error=str(exc))
            raise
        finally:
            state['wall_seconds'] = time.monotonic() - start
            state['allocated_core_hours'] = state['wall_seconds'] * 40 / 3600
            (folder / 'timing.json').write_text(json.dumps(state, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'prepare-sb', 'relax', 'launch',
                                          'prepare-response', 'response', 'launch-response',
                                          'd3-check', 'launch-d3-check',
                                          'reference-check', 'launch-reference-check'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--case')
    args = parser.parse_args()
    if args.action == 'prepare':
        for n in (6, 9):
            prepare_bn(args.root, args.repo, n)
    elif args.action == 'prepare-sb':
        prepare_sb(args.root)
    elif args.action == 'relax':
        relax(args.root, args.case)
    elif args.action == 'prepare-response':
        prepare_response(args.root, args.case)
    elif args.action == 'response':
        run_response(args.root, args.case)
    elif args.action == 'd3-check':
        d3_check(args.root, args.case)
    elif args.action == 'reference-check':
        reference_check(args.root, args.case)
    else:
        response = args.action == 'launch-response'
        stage = args.action.removeprefix('launch-') if args.action != 'launch' else 'relax'
        marker = args.root / args.case / ('launch.json' if stage == 'relax' else stage + '-launch.json')
        with marker.open('x') as handle:
            with (marker.parent / (stage + '.log' if stage != 'relax' else 'worker.log')).open('ab') as log:
                command = [sys.executable, '-u', str(Path(__file__).resolve()),
                           stage, '--root', str(args.root), '--case', args.case]
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                           stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
            json.dump(dict(host=socket.gethostname(), pid=process.pid, command=command), handle)
        print(marker.read_text())
