"""Compare tensor reconstruction before claiming spectroscopy speedups."""
import argparse
import json
from pathlib import Path
import numpy as np

from zstar import spectra
from zstar.shared_response import read_structure, make_phonopy, symmetry_operations, actual_displacement
from tools.spectroscopy_benchmark.atomic_raman import reconstruct, mode_derivatives
from tools.shared_response.molecular_validation import internal_basis
from tools.shared_response.one_dimensional_spectra import rigid_mode_audit


def load(root):
    manifest = json.loads((root/'shared_response.json').read_text())
    atoms = read_structure(root/'STRU')
    epsilon0 = np.asarray(json.loads((root/'0.no-move/completed.json').read_text())['epsilon'])
    observations = []
    costs = []
    for s in manifest['stages']:
        record = json.loads((root/s['name']/'completed.json').read_text())
        assert record['success'] and record['additional_DFT_calls'] == 0
        atom, vector = actual_displacement(atoms, read_structure(root/s['name']/'STRU'))
        assert atom == s['atom']
        np.testing.assert_allclose(vector, s['displacement_A'], atol=1e-9)
        observations.append(dict(atom=atom, displacement_A=vector,
                                 delta_epsilon=np.asarray(record['epsilon'])-epsilon0))
        costs.append(record['core_hours'])
    operations = symmetry_operations(make_phonopy(atoms, symprec=manifest['symprec_A']),
                                     dimension=manifest['dimension'])
    tensor, diagnostics = reconstruct(len(atoms), observations, operations)
    diagnostics['reference_symmetry_max'] = float(max(np.max(abs(r@epsilon0@r.T-epsilon0))
                                                    for r,_ in operations))
    diagnostics['optical_increment_core_h'] = sum(costs)
    diagnostics['precision_reference_core_h'] = json.loads((root/'0.no-move/completed.json').read_text())['core_hours']
    return manifest, atoms, tensor, diagnostics


def optical_indices(modes, dimension):
    if dimension == 1:
        return np.array([a['mode']-1 for a in rigid_mode_audit(modes) if not a['classified_rigid']])
    if dimension == 0:
        _, rigid = internal_basis(modes.positions_fractional@modes.lattice_angstrom, modes.masses_amu)
        overlap = np.sum(abs(modes.eigenvectors.reshape(len(modes.frequencies_cm1),-1)@rigid)**2,axis=1)
        if np.any((overlap >= .2) & (overlap <= .8)) or np.count_nonzero(overlap > .8) != rigid.shape[1]:
            raise ValueError('Ambiguous rigid/internal molecular mode separation')
        return np.flatnonzero(overlap < .2)
    return np.flatnonzero(modes.frequencies_cm1 > 20)


def collect(root, case):
    loaded = [load(root/case/s) for s in ('unified','cartesian')]
    manifest, atoms, unified, diag_u = loaded[0]
    _, atoms_c, cartesian, diag_c = loaded[1]
    np.testing.assert_allclose(atoms.cell, atoms_c.cell, atol=1e-8)
    np.testing.assert_allclose(atoms.positions, atoms_c.positions, atol=1e-8)
    dimension = manifest['dimension']
    modes = spectra.load_gamma_modes(root/case/'unified/qpoints.yaml')
    select = optical_indices(modes, dimension)
    if np.min(modes.frequencies_cm1[select]) <= 0:
        raise ValueError('Unstable internal mode')
    factor = {3:1, 2:modes.cell_height_angstrom,
              1:modes.area_angstrom2/(4*np.pi), 0:modes.volume_angstrom3/(4*np.pi)}[dimension]
    outputs = root/case/'analysis'
    outputs.mkdir(exist_ok=True)
    report = dict(case=case, dimension=dimension,
                  tensor_Frobenius_relative_difference=float(np.linalg.norm(unified-cartesian)/np.linalg.norm(cartesian)),
                  derivative_max_abs_difference_per_A=float(np.max(abs(unified-cartesian))),
                  unified=diag_u, cartesian=diag_c,
                  raw_tensors_used=True, additional_DFT_calls=0,
                  raman_comparison_basis='Both derivatives contracted with the same Unified eigenvectors; isolates response-fit error.',
                  normalization_factor=factor, optical_mode_numbers=(select+1).tolist())
    report['excluded_rigid_frequencies_cm1'] = np.delete(modes.frequencies_cm1, select).tolist()
    activities = []
    for scheme, derivative in [('unified',unified),('cartesian',cartesian)]:
        mode_tensors = mode_derivatives(derivative, modes.eigenvectors, modes.masses_amu)*factor
        np.save(outputs/f'{scheme}_atomic_derivatives.npy', derivative)
        np.save(outputs/f'{scheme}_all_mode_tensors.npy', mode_tensors)
        raman = spectra.calculate_raman_spectrum(modes, select+1, mode_tensors[select],
                    tensor_kind='Benchmark derivative; source dimensional convention retained',
                    temperature_K=298, laser_nm=532, broadening_cm1=8, points=3001,
                    allow_imaginary=dimension == 0)
        spectra.write_raman_outputs(outputs/scheme/'raman', raman)
        activities.append(raman)
    # The full-mode Cartesian tensor comparison is independent of degenerate eigenvector gauges.
    u = mode_derivatives(unified, modes.eigenvectors, modes.masses_amu)[select]
    c = mode_derivatives(cartesian, modes.eigenvectors, modes.masses_amu)[select]
    report['optical_mode_tensor_relative_difference'] = float(np.linalg.norm(u-c)/np.linalg.norm(c))
    (outputs/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--case', required=True)
    a = p.parse_args()
    print(json.dumps(collect(a.root,a.case),indent=2))
