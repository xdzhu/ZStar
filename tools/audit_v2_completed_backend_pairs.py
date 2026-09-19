"""Compare completed bulk backend tensors; diagnostic native d never promotes a gate."""
from __future__ import annotations

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.audit_v2_pbe_reference_pairing import digest, strict_json
from zstar.v2.mechanical import rotate_elastic_tensor, rotate_piezoelectric_tensor, stress_representation


def tensors(e, c, d=None):
    e, c = np.asarray(e, dtype=float), np.asarray(c, dtype=float)
    if e.shape != (3, 6) or c.shape != (6, 6) or not all(np.all(np.isfinite(x)) for x in (e, c)):
        raise ValueError('Complete finite 3D e/C tensors required')
    if np.max(np.abs(c-c.T)) > 1e-8 or np.min(np.linalg.eigvalsh(c)) <= 0:
        raise ValueError('Major-symmetric positive definite C required; no silent projection')
    algebraic = np.linalg.solve(c.T, e.T).T * 1000
    if d is not None:
        d = np.asarray(d, dtype=float)
        if d.shape != (3, 6) or not np.all(np.isfinite(d)) or np.max(np.abs(d@c/1000-e)) > 1e-8:
            raise ValueError('Declared d does not close with full e/C')
    return e, c, algebraic if d is None else d


def difference(calculated, comparator, unit, shape, absolute, relative):
    a, b = np.asarray(calculated, dtype=float), np.asarray(comparator, dtype=float)
    if a.shape != shape or b.shape != shape or not all(np.all(np.isfinite(x)) for x in (a, b)):
        raise ValueError('Incorrect complete tensor shape/nonfinite input')
    delta = a-b
    norm = np.linalg.norm(b)
    limits = np.maximum(absolute, relative*np.abs(b))
    row, column = np.unravel_index(np.argmax(np.abs(delta)), shape)
    return {'unit': unit, 'calculated': a.tolist(), 'comparator': b.tolist(),
            'signed_difference': delta.tolist(), 'max_absolute_difference': float(np.max(np.abs(delta))),
            'largest_difference_index_zero_based': [int(row), int(column)],
            'frobenius_relative_difference_percent': None if norm == 0 else float(100*np.linalg.norm(delta)/norm),
            'informative_stability_floor': absolute, 'informative_stability_relative': relative,
            'components_exceeding_informative_stability_target': int(np.count_nonzero(np.abs(delta)>limits)),
            'target_application': 'Descriptive screen only: different backends/geometries are not amplitude convergence tests',
            'standard_uncertainty': None}


def compare_pair(abacus, native):
    ea, ca, da = tensors(abacus['e_C_m2'], abacus['C_GPa'], abacus['d_pm_V'])
    en, cn, dn = tensors(native['e_C_m2'], native['C_GPa'], native['d_pm_V'])
    return {'e': difference(ea, en, 'C/m^2', (3, 6), .02, .02),
            'C': difference(ca, cn, 'GPa', (6, 6), 2., .02),
            'd': difference(da, dn, 'pm/V (= pC/N)', (3, 6), .2, .03),
            'ABACUS_d33_pm_V': float(da[2, 2]), 'VASP_algebraic_d33_pm_V': float(dn[2, 2]),
            'd33_signed_difference_percent_ABACUS_minus_VASP': None if dn[2, 2] == 0 else float(100*(da[2, 2]-dn[2, 2])/abs(dn[2, 2])),
            'native_d_emitted_in_source': native['d_pm_V'] is not None,
            'native_source_status': native['status'], 'native_source_quality_issues': native['quality_issues'],
            'native_d_acceptance_changed': False,
            'VASP_d_classification': 'Previously accepted native d' if native['d_pm_V'] is not None else
                                     'Diagnostic algebra of serialized native e/C only; source d remains null'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path(__file__).resolve().parents[1]
    source = args.archive / 'comparison.json'
    if source.stat().st_size > 5_000_000:
        raise ValueError('Bounded comparison input required')
    comparison = strict_json(source.read_bytes())
    records = comparison['additional_calculations'] + [dict(comparison['native_AlN'], material='AlN', backend='vasp',
                 source_sha256=comparison['native_AlN']['native_sha256'],
                 status='previously_accepted_native_AlN', quality_issues=[], frame_rotation_old_to_new=None)]
    source_hashes = {str(source): digest(source)}
    for record in records:
        path = Path(record['source'])
        if digest(path) != record['source_sha256']:
            raise ValueError('Collected source changed after frozen comparison')
        source_hashes[str(path)] = digest(path)
    route_records = {}
    for name in ('native_ionic_contribution_reconstruction_audit.json', 'PTO_native_ionic_contribution_reconstruction_audit.json'):
        path = args.archive / name
        if path.stat().st_size > 5_000_000:
            raise ValueError('Bounded ionic reconstruction evidence required')
        evidence = strict_json(path.read_bytes())
        if evidence['native_acceptance_changed'] or evidence['model']['strain'] != 'engineering [xx,yy,zz,2yz,2xz,2xy]':
            raise ValueError('Unexpected reconstruction convention or promotion')
        source_hashes[str(path)] = digest(path)
        for record in evidence['calculations']:
            for label, expected in record['source_sha256'].items():
                parent = Path(label)
                if not parent.is_absolute():
                    parent = root / parent
                if digest(parent) != expected:
                    raise ValueError('Frozen reconstruction parent changed')
                source_hashes[str(parent)] = expected
            route_records[record['case']] = record
    results = {}
    for material, case in [('AlN', 'AlN_accepted'), ('GaN', 'GaN_primary'), ('ZnO', 'ZnO_primary'), ('PTO', 'PTO_primary')]:
        matching = [r for r in records if r['material'] == material]
        selected = {r['backend']: r for r in matching}
        if len(matching) != 2 or set(selected) != {'abacus', 'vasp'}:
            raise ValueError('Exactly one completed tensor source per material/backend required')
        abacus, native = selected['abacus'], selected['vasp']
        results[material] = compare_pair(abacus, native)
        results[material]['coordinate_audit_evidence'] = {backend: r.get('coordinate_audit_evidence', 'Previously accepted aligned AlN archive')
                                                       for backend, r in selected.items()}
        reconstruction = route_records[case]
        routes = {}
        for route_name, route in reconstruction['routes'].items():
            if route_name not in ('displaced_atoms', 'strained_cells'):
                continue
            e, c, d = tensors(route['e_total_diagnostic_C_m2'], route['C_total_diagnostic_GPa'], route['d_diagnostic_pm_V'])
            q = native.get('frame_rotation_old_to_new')
            if q is not None:
                q = np.asarray(q, dtype=float)
                e = rotate_piezoelectric_tensor(e, q)
                c = rotate_elastic_tensor(c, q)
                # d is dual to ordinary stress, not to engineering strain.
                d = q @ d @ np.linalg.inv(stress_representation(q))
            e, c, d = tensors(e, c, d)
            routes[route_name] = {'e_C_m2': e.tolist(), 'C_GPa': c.tolist(), 'd_pm_V': d.tolist()}
        a, b = routes['displaced_atoms'], routes['strained_cells']
        results[material]['same_source_native_route_sensitivity'] = {
            'e': difference(b['e_C_m2'], a['e_C_m2'], 'C/m^2', (3, 6), .02, .02),
            'C': difference(b['C_GPa'], a['C_GPa'], 'GPa', (6, 6), 2., .02),
            'd': difference(b['d_pm_V'], a['d_pm_V'], 'pm/V (= pC/N)', (3, 6), .2, .03),
            'limitations': 'Common projected Phi/Z; NOT an independent backend comparator or uncertainty estimate'}
        results[material]['native_serialized_vs_displaced_reconstruction'] = {
            key: difference(a[field], native[field] if native[field] is not None else tensors(native['e_C_m2'], native['C_GPa'])[2],
                            unit, shape, absolute, relative)
            for key, field, unit, shape, absolute, relative in
            [('e', 'e_C_m2', 'C/m^2', (3, 6), .02, .02), ('C', 'C_GPa', 'GPa', (6, 6), 2., .02),
             ('d', 'd_pm_V', 'pm/V (= pC/N)', (3, 6), .2, .03)]}
    result = {'schema': 'zstar-v2-completed-backend-pairs-research/1', 'algorithm_sha256': digest(__file__),
              'sources': source_hashes, 'versions': {name: version(name) for name in ('numpy', 'scipy')},
              'conventions': {'e': 'proper relaxed-ion, C/m^2', 'C': 'relaxed-ion C^E, GPa',
                              'd': '3x6 ordinary-stress map, pm/V (=pC/N)', 'strain': '[xx,yy,zz,2yz,2xz,2xy]',
                              'coordinate': 'Explicit previously audited +a/+c common frame, no sign selection'},
              'calculations': results, 'native_acceptance_changed': False, 'new_DFT_calculations': 0,
              'limitations': ['Different reference geometries, pseudopotentials/basis and strain steps (.5% versus1%).',
                              'Informative stability screens are not cross-backend acceptance thresholds.',
                              'Null source native d stays null; diagnostic algebra is not accepted d.',
                              'No statistical uncertainty/absolute accuracy proof from deterministic differences.']}
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({name: {k: row[k] for k in ('ABACUS_d33_pm_V', 'VASP_algebraic_d33_pm_V',
                     'd33_signed_difference_percent_ABACUS_minus_VASP', 'native_d_emitted_in_source')} for name, row in results.items()}))


if __name__ == '__main__':
    main()
