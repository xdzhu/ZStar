#!/usr/bin/env python3
"""Bounded research continuation using existing ABACUS and native VASP APIs.

No public interface change, branch merge or automatic retry. Failed stages
retain inputs and outputs; resume requires a physically accepted stage.
"""
from __future__ import annotations

import argparse
import hashlib
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


def record(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def structure_gate(cell, positions, symbols, expected):
    import spglib
    from pymatgen.core import Element
    dataset = spglib.get_symmetry_dataset(
        (cell, positions, [Element(s).Z for s in symbols]), symprec=1e-3)
    if dataset is None or int(dataset.number) != expected:
        raise ValueError(f'Phase changed: expected space group {expected}, found {dataset}')
    return int(dataset.number)


def run_logged(command, stage, label, ranks):
    marker = stage / f'{label}_execution.json'
    if marker.exists():
        previous = json.loads(marker.read_text())
        if previous['returncode'] != 0:
            raise RuntimeError(f'Prior failed run retained at {stage}; no blind retry')
        return
    start = time.time()
    with (stage / f'{label}.log').open('w') as output:
        result = subprocess.run(command, cwd=stage, stdout=output, stderr=subprocess.STDOUT)
    record(marker, {'command': command, 'node': socket.gethostname(), 'mpi': ranks,
                    'omp': 1, 'returncode': result.returncode, 'start_unix': start,
                    'elapsed_seconds': time.time()-start,
                    'core_hours': (time.time()-start)*ranks/3600})
    if result.returncode:
        raise RuntimeError(f'{label} failed with {result.returncode}; logs retained at {stage}')


def abacus_gate(stage, expected, stress_required=False):
    from zstar.v2.abacus import collect_abacus_stage
    observed = collect_abacus_stage(stage)
    if observed['force_max_eV_per_angstrom'] > 1e-4:
        raise ValueError(f'Force gate failed at {stage}: {observed["force_max_eV_per_angstrom"]}')
    if stress_required and observed['stress_max_abs_kbar'] > .5:
        raise ValueError(f'Reference stress gate failed at {stage}')
    atoms = observed['relaxed_structure']
    if atoms is None:
        from zstar.shared_response import read_structure
        atoms = read_structure(stage / 'STRU')
    sg = structure_gate(atoms.cell, atoms.scaled_positions, atoms.symbols, expected)
    return observed, sg


def run_abacus(args):
    from zstar.v2.strain import prepare_abacus_fixed_cell_relaxation, prepare_abacus_strain_ensemble
    from zstar.v2.abacus import collect_abacus_stage
    node = socket.gethostname().split('.')[0]
    if node not in ('cu17', 'cu21', 'cu24', 'cu25', 'cu26') or args.ranks != 40:
        raise ValueError('235 requires an authorized cu17/cu21/cu24-cu26 node and 40 MPI x 1 OMP')
    # Check real processes, not user-owned PBS placeholders.
    if subprocess.run(['pgrep', '-x', 'abacus|vasp_std|pyatb'], capture_output=True).returncode == 0:
        raise RuntimeError('Calculator already active on node; refusing overlap')
    from contextlib import ExitStack
    import fcntl
    args.output.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        lock = stack.enter_context((args.output.parent / f'.piezo-{node}.lock').open('a'))
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        campaign = json.loads(args.manifest.read_text())
        for material in args.materials:
            root = args.output / material
            root.mkdir(exist_ok=True)
            try:
                spec = campaign['cases'][material]
                source = Path(spec['abacus_reference'])
                observed, sg = abacus_gate(source, spec['expected_space_group'], True)
                r2 = root / 'R2r'
                if not r2.exists():
                    prepare_abacus_fixed_cell_relaxation(
                        r2, structure=observed['relaxed_structure_path'],
                        input_template=source/'INPUT', kpt_template=source/'KPT',
                        pp_dir=source, orb_dir=source, profile='production', symprec=1e-3)
                print(f'START {material} R2r', flush=True)
                run_logged([args.mpi, '-np', '40', args.abacus], r2, 'fixed_cell', 40)
                r2_data, sg = abacus_gate(r2, spec['expected_space_group'], True)
                response = root / 'response'
                if not response.exists():
                    prepare_abacus_strain_ensemble(
                        response, structure=r2_data['relaxed_structure_path'],
                        input_template=r2/'INPUT', kpt_template=r2/'KPT', pp_dir=r2,
                        orb_dir=r2, ion_relaxation='relaxed-ion', profile='production',
                        amplitude=.005, symprec=.001, symmetry_reduce=False, method='central')
                valence = []
                for symbol in dict.fromkeys(r2_data['relaxed_structure'].symbols):
                    header = (r2/f'{symbol}.upf').read_text(errors='replace').split('</PP_HEADER>',1)[0]
                    match = re.search(r'z_valence\s*=\s*[\"\']([^\"\']+)', header)
                    if match is None:
                        raise ValueError(f'No pseudopotential valence for {symbol}')
                    number = float(match.group(1).replace('D','E').replace('d','e'))
                    if not number.is_integer():
                        raise ValueError(f'Nonintegral polarization valence for {symbol}: {number}')
                    valence.append(str(int(number)))
                provenance = {'functional': 'PBE', 'reference': str(source),
                              'reference_geometry_sha256': digest(Path(r2_data['relaxed_structure_path'])),
                              'space_group': sg, 'symprec_angstrom': .001,
                              'strain_amplitude': .005, 'method': 'central',
                              'valence_from_upf': valence, 'stage_count': 13,
                              'status': 'prepared_pending_calculation'}
                record(root/'continuation.json', provenance)
                env = dict(os.environ, ZSTAR_MPI_RANKS='40', ZSTAR_OMP_THREADS='1',
                           ZSTAR_MPI_LAUNCHER=args.mpi, ZSTAR_ABACUS=args.abacus,
                           ZSTAR_PYATB_ADAPTER=str(args.runtime/'zstar/pyatb_precision.py'),
                           ZSTAR_STAGE_IDS='reference')
                driver = args.runtime/'tools/v2_piezo_235_direct.sh'
                # One real reference SCF/PYATB smoke first. This also supplies
                # eigenvalues to test insulating character before all strains.
                print(f'START {material} reference SCF/PYATB', flush=True)
                subprocess.run(['bash', str(driver), str(response), *valence], env=env, check=True)
                ref = collect_abacus_stage(response/'reference')
                if ref['force_max_eV_per_angstrom'] > 1e-4 or not ref['band_gap'] or not ref['band_gap']['insulating']:
                    raise ValueError(f'Reference electronic/force gate failed: {material}')
                env.pop('ZSTAR_STAGE_IDS')
                print(f'START {material} 12 central strain stages', flush=True)
                subprocess.run(['bash', str(driver), str(response), *valence], env=env, check=True)
                subprocess.run([sys.executable, str(args.runtime/'tools/collect_v2_piezo_case.py'),
                                str(response), '--acoustic-gauge', 'equal-weight'], check=True)
                provenance['status'] = 'computed_pending_external_comparison'
                record(root/'continuation.json', provenance)
                print(f'END {material} ABACUS response collected', flush=True)
            except Exception as error:
                record(root/'failure.json', {'material': material, 'error': str(error),
                                            'status': 'failed_logs_retained_no_retry'})
                print(f'FAILED {material}: {error}', flush=True)


def vasp_gate(stage, expected):
    from pymatgen.io.vasp.outputs import Vasprun
    run = Vasprun(stage/'vasprun.xml', parse_dos=False, parse_eigen=True,
                  parse_projected_eigen=False, parse_potcar_file=False)
    if not run.converged_electronic or not run.converged_ionic:
        raise ValueError('VASP reference optimization not converged')
    forces = np.asarray(run.ionic_steps[-1]['forces'])
    force = float(np.max(np.linalg.norm(forces, axis=1)))
    stress = float(np.max(np.abs(run.ionic_steps[-1]['stress'])))
    gap = float(run.eigenvalue_band_properties[0])
    if force > 1e-4 or stress > .5 or gap < .01:
        raise ValueError(f'VASP reference gate: force={force}, stress={stress}, gap={gap}')
    atoms = run.final_structure
    sg = structure_gate(atoms.lattice.matrix, atoms.frac_coords,
                        [str(s) for s in atoms.species], expected)
    return {'force_max_eV_A': force, 'stress_max_kbar': stress, 'gap_eV': gap, 'space_group': sg}


def run_vasp(args):
    from zstar.vasp_bec import prepare_vasp_bec, run_vasp_bec, collect_vasp_bec
    from pymatgen.io.vasp.inputs import Incar
    if args.ranks != 32 or int(os.environ.get('SLURM_NTASKS', '0')) != 32:
        raise ValueError('HF execution requires a 32-task Slurm allocation')
    args.output.mkdir(parents=True, exist_ok=True)
    for material in args.materials:
        root = args.output/material
        root.mkdir(exist_ok=True)
        try:
            source = args.source/material
            metadata = json.loads((source/'source.json').read_text())
            for name, expected_hash in metadata['source_sha256'].items():
                if digest(source/name) != expected_hash:
                    raise ValueError(f'Continuation source hash changed: {source/name}')
            relax = root/'relax-continuation'
            if not relax.exists():
                relax.mkdir()
                for name in ('INCAR','KPOINTS','POTCAR'):
                    shutil.copy2(source/name, relax/name)
                shutil.copy2(source/'CONTCAR', relax/'POSCAR')
                incar = Incar.from_file(relax/'INCAR')
                # Restart the failed CG line search with a different optimizer;
                # do not change functional, cutoff, k mesh or force threshold.
                incar.update(IBRION=1, POTIM=.1, NFREE=5, NSW=100, ISYM=0, NCORE=4,
                             EDIFF=1e-8, EDIFFG=-1e-4, LWAVE=False, LCHARG=False)
                incar.pop('NPAR', None)
                incar.write_file(relax/'INCAR')
            print(f'START {material} VASP continuation', flush=True)
            run_logged([args.mpi, '-np','32', args.vasp], relax, 'relax', 32)
            accepted = vasp_gate(relax, metadata['expected_space_group'])
            inputs = root/'accepted-input'
            inputs.mkdir(exist_ok=True)
            for name in ('INCAR','KPOINTS','POTCAR'):
                shutil.copy2(relax/name, inputs/name)
            shutil.copy2(relax/'CONTCAR', inputs/'POSCAR')
            response = root/'native-elastic'
            if not response.exists():
                prepare_vasp_bec(inputs, response, elastic=True, dimensionality=3)
            print(f'START {material} native e/C/d', flush=True)
            start = time.time()
            states = run_vasp_bec(response, vasp_command=f'{args.mpi} -np 32 {args.vasp}', omp_threads=1)
            if len(states) != 2 or any(s.status != 'completed' for s in states):
                raise ValueError(f'Native stage failure: {states}')
            collect_vasp_bec(response)
            native = json.loads((response/'vasp_native_response.json').read_text())
            record(root/'continuation.json', {'functional':'PBE','reference_gate':accepted,
                      'mpi':32,'omp':1,'slurm_job_id':os.environ['SLURM_JOB_ID'],
                      'elapsed_native_seconds':time.time()-start,
                      'native_core_hours':(time.time()-start)*32/3600,
                      'source':metadata, 'native_priority':True,
                      'derived_d_available':'piezoelectric_d_pm_V' in native['tensors'],
                      'status':'computed_pending_external_comparison'})
            print(f'END {material} native response collected', flush=True)
        except Exception as error:
            record(root/'failure.json', {'material':material, 'error':str(error),
                                        'status':'failed_logs_retained_no_retry'})
            print(f'FAILED {material}: {error}', flush=True)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=('abacus','vasp'), required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--materials', nargs='+', required=True)
    parser.add_argument('--mpi', required=True)
    parser.add_argument('--abacus')
    parser.add_argument('--vasp')
    parser.add_argument('--ranks', type=int, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.runtime))
    os.environ.update(OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    (run_abacus if args.backend == 'abacus' else run_vasp)(args)


if __name__ == '__main__':
    main()
