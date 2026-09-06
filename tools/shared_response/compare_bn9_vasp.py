"""Compare complete native VASP BN(9,0) tensors in the archived local tube frame."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from tools.shared_response.export_one_dimensional_bec import cylindrical_tensors
from zstar.structure_io import read_poscar
from zstar.vasp_bec import parse_vasp_outcar


def compare(case, native):
    state_file = native / '.zstar/vasp_bec_state.json'
    state = json.loads(state_file.read_text())
    if len(state['stages']) != 2 or any(s['status'] != 'completed' for s in state['stages']):
        raise ValueError('Both native VASP stages must be complete')
    if state['stages'][0]['gap_eV'] <= 0:
        raise ValueError('Independent reference must remain insulating')
    outcar = native / 'response/OUTCAR'
    text = outcar.read_text(errors='replace')
    if 'General timing and accounting' not in text:
        raise ValueError('Native response OUTCAR has no successful final timing section')
    eps, displacement_first = parse_vasp_outcar(outcar)
    source = case / 'results/response.json'
    record = json.loads(source.read_text())
    structure = record['structure']
    quantities = {q['name']:q for q in record['quantities']}
    q = quantities['born_effective_charge']
    if q['axes'] != ['atom', 'displacement', 'polarization']:
        raise ValueError('Unexpected ABACUS response axes')
    abacus = np.asarray(q['values']).transpose(0, 2, 1)
    vasp = displacement_first.transpose(0, 2, 1)
    geometry = read_poscar(native / 'response/POSCAR')
    cell = np.asarray(structure['cell_angstrom'])
    frac = np.asarray(structure['scaled_positions'])
    if tuple(structure['symbols']) != geometry.symbols or abacus.shape != vasp.shape:
        raise ValueError('Atom labels, order, or tensor shapes differ')
    cell_error = float(np.max(np.abs(cell - geometry.lattice_angstrom)))
    delta = frac - geometry.positions_fractional
    delta -= np.rint(delta)
    position_error = float(np.max(np.linalg.norm(delta @ cell, axis=1)))
    if max(cell_error, position_error) > 1e-7:
        raise ValueError('The comparison is not at identical geometry')
    labels = np.asarray(structure['symbols'])
    summaries = {}
    for name, tensors in [('ABACUS_PYATB', abacus), ('VASP_DFPT', vasp)]:
        local = cylindrical_tensors(frac @ cell, cell, tensors)
        summaries[name] = {
            'cartesian_ASR_max_e': float(np.max(np.abs(tensors.sum(axis=0)))),
            'species': {s: {'mean_rr_tt_zz_e': np.diagonal(local[labels == s], axis1=1, axis2=2).mean(axis=0).tolist(),
                            'range_rr_tt_zz_e': np.ptp(np.diagonal(local[labels == s], axis1=1, axis2=2), axis=0).tolist()}
                        for s in ('B', 'N')},
            'cartesian_polarization_first_e': tensors.tolist(),
        }
    elapsed = {}
    for stage in ('reference', 'response'):
        log = (native / stage / 'OUTCAR').read_text(errors='replace')
        values = re.findall(r'Elapsed time \(sec\):\s*([\d.]+)', log)
        if len(values) != 1:
            raise ValueError(f'Missing or ambiguous timing: {stage}')
        elapsed[stage] = float(values[0])
    fit = json.loads((case / 'results/response_fit.json').read_text())
    return {
        'case': 'BN(9,0)', 'functional': 'PBE', 'units': 'e',
        'geometry_max_difference_A': max(cell_error, position_error),
        'reference_gap_eV': state['stages'][0]['gap_eV'],
        'normalization': 'Atom-local radial/tangential/axial; no isolated-tube image correction.',
        'projection': 'ABACUS tensors retain the archived projection; native VASP values are unmodified.',
        'comparison_scope': 'Independent PAW/DFPT versus ONCV/LCAO finite-displacement responses; not a same-basis numerical error estimate.',
        'tensors': summaries, 'native_epsilon_supercell': eps.tolist(),
        'ABACUS_raw_diagnostics': {
            'born_asr_max_e': fit['diagnostics']['born_asr_max_e'],
            'projection_max_e': fit['projected_diagnostics']['born_projection_max_e'],
        },
        'native_timing': {'elapsed_seconds': elapsed, 'mpi_ranks': 40, 'omp_threads': 1,
                          'allocated_core_hours': sum(elapsed.values()) * 40 / 3600},
        'source_hashes': {'ABACUS_response.json': hashlib.sha256(source.read_bytes()).hexdigest(),
                          'VASP_OUTCAR': hashlib.sha256(outcar.read_bytes()).hexdigest(),
                          'VASP_POSCAR': hashlib.sha256((native/'response/POSCAR').read_bytes()).hexdigest()},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.case, args.native)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'tensors'}, indent=2))
    for name, result in report['tensors'].items():
        print(name, json.dumps(result['species']), 'ASR', result['cartesian_ASR_max_e'])
