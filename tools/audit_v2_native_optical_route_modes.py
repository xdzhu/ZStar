"""Research-only optical attribution of archived response-route differences.

No calculator execution, tensor replacement, acceptance change or mass weighting.
Eigenvalues below are Cartesian force-constant curvatures, NOT phonon frequencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np

from zstar.shared_response import SharedResponse, project_response
from zstar.bec_database import read_born
from zstar.v2.units import convert_values


def block_response(vectors, curvatures, born_flat, xi, volume_angstrom3):
    """One optical spectral block: e in C/m², elastic correction in GPa.

    vectors: Cartesian displacement columns, orthonormal (dimensionless).
    curvatures: eV/Å²; born_flat: [polarization,atom-displacement], in e.
    xi: dF/d engineering strain, eV/Å; positive stable optical curvatures.
    """
    q, k = np.asarray(vectors), np.asarray(curvatures)
    z, x = np.asarray(born_flat), np.asarray(xi)
    if (q.ndim != 2 or k.shape != (q.shape[1],) or
            z.shape != (3, q.shape[0]) or x.shape != (q.shape[0], 6)):
        raise ValueError('Expected full 3D BEC, displacement and six-strain axes')
    if not all(np.all(np.isfinite(a)) for a in (q, k, z, x)):
        raise ValueError('Nonfinite response data')
    if not np.isfinite(volume_angstrom3) or volume_angstrom3 <= 0 or np.any(k <= 0):
        raise ValueError('Positive volume and stable optical curvatures required')
    if not np.allclose(q.T @ q, np.eye(q.shape[1]), atol=1e-10, rtol=0):
        raise ValueError('Optical vectors must be orthonormal')
    # Xi=-Gamma. Retain each curvature, never replace a near-degenerate block
    # with its mean. Exact degeneracies are reported as basis-invariant sums.
    amplitude = q.T @ x
    displacement_angstrom = q @ (amplitude / k[:, None])
    dipole_C_m = convert_values(z @ displacement_angstrom, 'e*angstrom', 'C*m')
    volume_m3 = volume_angstrom3 * float(convert_values(1., 'angstrom', 'm'))**3
    e_C_m2 = dipole_C_m / volume_m3
    c_GPa = -convert_values(amplitude.T @ (amplitude / k[:, None]) / volume_angstrom3,
                           'eV/angstrom^3', 'GPa')
    return e_C_m2, c_GPa


def exact_d_parts(delta_e_C_m2, delta_c_GPa, d_a_pm_V, c_b_GPa):
    """Finite-change attribution, not first-order/statistical propagation."""
    if np.min(np.linalg.eigvalsh(c_b_GPa)) <= 0:
        raise ValueError('Stable final elastic tensor required')
    electric = 1000 * np.linalg.solve(c_b_GPa.T, delta_e_C_m2.T).T
    mechanical = -np.linalg.solve(c_b_GPa.T, (d_a_pm_V @ delta_c_GPa).T).T
    return electric, mechanical


def _load(path):
    if path.stat().st_size > 5_000_000:
        raise ValueError(f'JSON exceeds bounded audit intake: {path.name}')
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f'Nonfinite JSON constant: {value}')

    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_pairs,
                      parse_constant=invalid_constant)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_record(record, root, degeneracy_atol=1e-8):
    from phonopy.file_IO import parse_FORCE_CONSTANTS

    for source, expected in record['source_sha256'].items():
        if _sha(Path(source)) != expected:
            raise ValueError(f'Frozen source hash mismatch: {source}')
    native = _load(root / 'vasp_native_response.json')['tensors']
    atoms = record['atom_order']
    n = len(atoms)
    if not 2 <= n <= 20:
        raise ValueError('Audit requires 2–20 explicit ordered atoms')
    if (root / 'vasp_bec.json').exists():
        full = _load(root / 'vasp_bec.json')
        if full['sum_scope'] != 'all_atoms' or full['tensor_convention'] != 'rows=atomic displacement/force; columns=polarization/electric field':
            raise ValueError('Unrecognized native all-atom BEC axes')
        if ([a['label'] for a in full['atoms']] != atoms or
                [a['index'] for a in full['atoms']] != list(range(1, n+1))):
            raise ValueError('All-atom BEC species/index mismatch')
        born = np.asarray([a['tensor'] for a in full['atoms']]).transpose(0, 2, 1)
    else:
        # Frozen prior audit establishes atom order; do not expand compact BORN
        # by duplicating representatives. Shape must be explicitly all-atom.
        _, born = read_born(root / 'BORN')
    fc_path = root / 'FORCE_CONSTANTS'
    if fc_path.stat().st_size > 1_000_000:
        raise ValueError('Force constants exceed bounded intake')
    fc = parse_FORCE_CONSTANTS(filename=str(fc_path))
    if (born.shape != (n, 3, 3) or fc.shape != (n, n, 3, 3) or
            not np.all(np.isfinite(born)) or not np.all(np.isfinite(fc))):
        raise ValueError('Full all-atom BEC/IFC shape mismatch')
    shared = project_response(SharedResponse(born, fc, {}))
    phi = shared.force_constants.transpose(0, 2, 1, 3).reshape(3*n, 3*n)
    z = shared.born.transpose(1, 0, 2).reshape(3, 3*n)
    t = np.tile(np.eye(3), (n, 1)) / np.sqrt(n)
    optical = np.linalg.qr(t, mode='complete')[0][:, 3:]
    eigenvalues, eigenvectors = np.linalg.eigh(optical.T @ phi @ optical)
    if np.min(eigenvalues) <= 0:
        raise ValueError('Unstable/zero optical mode, no stable attribution')
    np.testing.assert_allclose(eigenvalues, record['Phi_optical_eigenvalues_eV_A2'], atol=1e-10)
    q = optical @ eigenvectors
    xa = np.asarray(native['internal_strain_eV_per_A']).reshape(3*n, 6)
    xb = np.asarray(native['internal_strain_from_strained_cells_eV_per_A']).reshape(3*n, 6)
    a, b = (record['routes'][key] for key in ('displaced_atoms', 'strained_cells'))
    da = np.asarray(a['d_diagnostic_pm_V'])
    cb = np.asarray(b['C_total_diagnostic_GPa'])
    volume = record['volume_angstrom3']
    # This numerical spectral grouping is NOT the spglib/Phonopy symprec.
    groups = []
    start = 0
    while start < len(eigenvalues):
        stop = start + 1
        while stop < len(eigenvalues) and eigenvalues[stop]-eigenvalues[start] <= degeneracy_atol:
            stop += 1
        groups.append((start, stop))
        start = stop
    blocks, ea_sum, eb_sum, ca_sum, cb_sum = [], np.zeros((3, 6)), np.zeros((3, 6)), np.zeros((6, 6)), np.zeros((6, 6))
    for start, stop in groups:
        ea, ca = block_response(q[:, start:stop], eigenvalues[start:stop], z, xa, volume)
        eb, cbi = block_response(q[:, start:stop], eigenvalues[start:stop], z, xb, volume)
        de, dc = eb-ea, cbi-ca
        ed, cd = exact_d_parts(de, dc, da, cb)
        ea_sum += ea
        eb_sum += eb
        ca_sum += ca
        cb_sum += cbi
        blocks.append({'optical_indices_one_based': list(range(start+1, stop+1)),
                       'curvatures_eV_A2': eigenvalues[start:stop].tolist(),
                       'e_ionic_a_C_m2': ea.tolist(), 'e_ionic_b_C_m2': eb.tolist(),
                       'C_ionic_a_GPa': ca.tolist(), 'C_ionic_b_GPa': cbi.tolist(),
                       'delta_e_C_m2': de.tolist(), 'delta_C_GPa': dc.tolist(),
                       'd_difference_electric_pm_V': ed.tolist(),
                       'd_difference_mechanical_pm_V': cd.tolist(),
                       'd_difference_pm_V': (ed+cd).tolist(),
                       'd33_difference_pm_V': float((ed+cd)[2, 2]),
                       'd33_electric_pm_V': float(ed[2, 2]),
                       'd33_mechanical_pm_V': float(cd[2, 2])})
    for total, expected in ((ea_sum, a['e_ionic_C_m2']), (eb_sum, b['e_ionic_C_m2']),
                            (ca_sum, a['C_ionic_GPa']), (cb_sum, b['C_ionic_GPa'])):
        np.testing.assert_allclose(total, expected, atol=1e-9, rtol=1e-10)
    delta_d = np.asarray(b['d_diagnostic_pm_V'])-da
    summed = sum(np.asarray(block['d_difference_pm_V']) for block in blocks)
    np.testing.assert_allclose(summed, delta_d, atol=1e-8, rtol=1e-9)
    return {'case': record['case'], 'volume_angstrom3': volume,
            'source_sha256': record['source_sha256'], 'shared_projection': shared.diagnostics,
            'optical_dimension': 3*n-3, 'blocks': blocks,
            'd_difference_pm_V': delta_d.tolist(),
            'block_sum_closure_max_pm_V': float(np.max(np.abs(summed-delta_d)))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New exclusive output')
    args = parser.parse_args()
    archive = args.archive
    selections = [('native_ionic_contribution_reconstruction_audit.json', None),
                  ('PTO_native_ionic_contribution_reconstruction_audit.json', 'PTO_VASP'),
                  ('PZT_native_ionic_contribution_reconstruction_audit.json', 'PZT_VASP')]
    reports, hashes = [], {}
    for name, case_root in selections:
        path = archive / name
        hashes[name] = _sha(path)
        for record in _load(path)['calculations']:
            if case_root:
                root = archive / case_root
            else:
                root = next(Path(p).parent for p in record['source_sha256'] if p.endswith('vasp_native_response.json'))
            reports.append(audit_record(record, root))
    result = {'schema': 'v2-native-optical-route-mode-attribution-research-v1',
              'algorithm_sha256': _sha(Path(__file__)), 'parent_audit_sha256': hashes,
              'units': {'curvature': 'eV/angstrom^2', 'e': 'C/m^2', 'C': 'GPa', 'd': 'pm/V'},
              'coordinates': 'Original Cartesian; full 3D periodic bulk; atom order unchanged',
              'strain': 'engineering [xx,yy,zz,2yz,2xz,2xy]',
              'boundary_conditions': 'fixed electric field; relaxed ions; diagnostic copies only',
              'identity': 'delta_d_block=1000 delta_e_block S_b - d_a delta_C_block S_b',
              'spectral_grouping_atol_eV_A2': 1e-8,
              'limitations': ['Unweighted Cartesian optical curvatures are not phonon frequencies.',
                              'Exact-degenerate block sums are invariant; individual degenerate vectors are not observables.',
                              'Near degeneracies retain their own eigenvalues; no spectral averaging.',
                              'Attribution of existing routes is not a unique DFT error cause, independent validation or uncertainty.'],
              'standard_uncertainty': None, 'native_acceptance_changed': False,
              'new_DFT_calculations': 0,
              'packages': {p: version(p) for p in ('numpy', 'phonopy')}, 'calculations': reports}
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    for report in reports:
        top = max(report['blocks'], key=lambda block: abs(block['d33_difference_pm_V']))
        print(json.dumps({'case': report['case'], 'd33_difference_pm_V': report['d_difference_pm_V'][2][2],
                          'largest_signed_block': {k: top[k] for k in ('optical_indices_one_based', 'curvatures_eV_A2',
                          'd33_difference_pm_V', 'd33_electric_pm_V', 'd33_mechanical_pm_V')},
                          'closure_max_pm_V': report['block_sum_closure_max_pm_V']}))


if __name__ == '__main__':
    main()
