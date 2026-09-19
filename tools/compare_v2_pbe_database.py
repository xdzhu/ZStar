#!/usr/bin/env python3
"""Extract verified PBE database tensors and compare accepted native AlN data.

Research post-processing only. Never run DFT, infer missing tensors or rotate
unmatched phases by guessing. Retain the unprojected native tensor, including
the small symmetry-forbidden numerical components.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zstar.structure_io import read_structure
from zstar.v2.mechanical import rotate_elastic_tensor, rotate_piezoelectric_tensor, stress_representation

DATABASE_SHA256 = 'dc9d04836f7f91ecb4ef6dc23e42468571be857f0fccafdfb51a5a40f19db898'
TARGETS = {'AlN': ('mp-661', 186), 'GaN': ('mp-804', 186),
           'ZnO': ('mp-2133', 186), 'PTO': ('mp-20459', 99)}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def space_group_number(value):
    """Read collector Hermann-Mauguin symbols without guessing from material."""
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        if 1 <= int(value) <= 230:
            return int(value)
        raise ValueError(f'Invalid space group number: {value}')
    import spglib
    symbol = str(value).replace(' ', '')
    numbers = {int(group.number) for hall in range(1, 531)
               if (group := spglib.get_spacegroup_type(hall)) is not None
               and group.international_short.replace(' ', '') == symbol}
    if len(numbers) != 1:
        raise ValueError(f'Unknown/ambiguous collected space group: {value}')
    return numbers.pop()


def extract_database(path):
    if sha256(path) != DATABASE_SHA256:
        raise ValueError('Database SHA256 differs from official matminer metadata')
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        data = json.load(stream)
    if len(data['data']) != 941:
        raise ValueError('Incomplete database: expected 941 records')
    wanted = {mpid for mpid, _ in TARGETS.values()}
    selected = {}
    for row in data['data']:
        record = dict(zip(data['columns'], row))
        if record['material_id'] not in wanted:
            continue
        material = next(name for name, (mpid, _) in TARGETS.items() if mpid == record['material_id'])
        if int(record['space_group']) != TARGETS[material][1]:
            raise ValueError(f'Database phase mismatch: {material}')
        if material in selected:
            raise ValueError(f'Duplicate database identifier: {material}')
        tensor = np.asarray(record['piezoelectric_tensor']['data'], dtype=float)
        if tensor.shape != (3, 6) or not np.all(np.isfinite(tensor)):
            raise ValueError(f'Invalid full e tensor: {material}')
        selected[material] = {
            'material_id': record['material_id'], 'formula': record['formula'],
            'space_group': int(record['space_group']), 'point_group': record['point_group'],
            'e_C_m2': tensor.tolist(), 'structure': record['structure'],
            'unit': 'C/m^2', 'tensor_kind': 'proper', 'ion_relaxation': 'relaxed-ion',
            'coordinate_system': 'IEEE standard', 'voigt': ['xx','yy','zz','yz','xz','xy'],
            'backend': 'VASP PAW', 'functional': 'PBE',
            'paper_doi': '10.1038/sdata.2015.53',
        }
    if set(selected) != set(TARGETS):
        raise ValueError(f'Missing target database records: {set(TARGETS)-set(selected)}')
    return selected


def tensor_comparison(calculated, reference):
    calculated = np.asarray(calculated, dtype=float)
    reference = np.asarray(reference, dtype=float)
    if calculated.shape != (3, 6) or reference.shape != (3, 6):
        raise ValueError('Full piezoelectric tensors must be 3 x 6')
    if not np.all(np.isfinite(calculated)) or not np.all(np.isfinite(reference)):
        raise ValueError('Tensor values must be finite')
    difference = calculated - reference
    rows = []
    for i in range(3):
        for j in range(6):
            ref, value = float(reference[i,j]), float(calculated[i,j])
            rows.append({'component': f'e{i+1}{j+1}', 'zstar_C_m2': value,
                         'database_C_m2': ref, 'signed_difference_C_m2': float(difference[i,j]),
                         'absolute_relative_difference_percent': None if abs(ref) <= 1e-12 else 100 * abs(value-ref)/abs(ref)})
    reference_norm = float(np.linalg.norm(reference))
    zero_mask = abs(reference) <= 1e-12
    return {'components': rows, 'max_absolute_difference_C_m2': float(np.max(np.abs(difference))),
            'frobenius_relative_difference_percent': None if reference_norm == 0 else 100 * float(np.linalg.norm(difference)/reference_norm),
            'zero_reference_max_absolute_C_m2': float(np.max(np.abs(calculated[zero_mask]))) if np.any(zero_mask) else None}


def compare_completed_result(spec, references):
    """Compare an actual collected result, preserving failed scientific gates.

    The manifest must cite the explicit axes/domain audit. Never silently flip
    the sign to improve agreement or mix an old PBEsol result into this campaign.
    """
    material, backend = spec['material'], spec['backend']
    path = Path(spec['result'])
    result = json.loads(path.read_text(encoding='utf-8'))
    provenance = json.loads(Path(spec['continuation']).read_text(encoding='utf-8'))
    functional = result.get('functional', provenance.get('functional',''))
    if str(functional).lower() != 'pbe':
        raise ValueError(f'Not a PBE calculation: {path}')
    if spec.get('coordinate_and_domain_verified') is not True or not spec.get('coordinate_audit_evidence'):
        raise ValueError('Explicit coordinate/domain audit evidence required; no guessed sign flips')
    issues = []
    if backend == 'vasp':
        if result.get('backend') != 'vasp' or result.get('dimensionality') != 3 or result.get('normalization') != 'bulk':
            raise ValueError('Not a native VASP bulk result')
        gate = provenance.get('reference_gate',{})
        if not all(key in gate for key in ('space_group','force_max_eV_A','stress_max_kbar','gap_eV')):
            raise ValueError('Missing reference optimization/insulating acceptance evidence')
        gate_values = [gate['force_max_eV_A'],gate['stress_max_kbar'],gate['gap_eV']]
        if not np.all(np.isfinite(gate_values)) or gate['force_max_eV_A'] > 1e-4 or gate['stress_max_kbar'] > .5 or gate['gap_eV'] < .01:
            issues.append('Reference force/stress/insulating gate failed')
        group = gate['space_group']
        tensors = result['tensors']
        e = tensors['piezoelectric_total_C_m2']
        c = tensors.get('elastic_relaxed_GPa')
        d = tensors.get('piezoelectric_d_pm_V')
        diagnostics = result['diagnostics']
        if diagnostics.get('d_rejected_reason'):
            issues.append('Native d gate: '+str(diagnostics['d_rejected_reason']))
        if diagnostics.get('electromechanical_warning'):
            issues.append(str(diagnostics['electromechanical_warning']))
        if diagnostics.get('ir_rejected_reason'):
            issues.append('Harmonic stability warning: '+str(diagnostics['ir_rejected_reason']))
    elif backend == 'vasp-central-strain':
        if result.get('schema') != 'zstar-v2-VASP-independent-central-strain-result/1':
            raise ValueError('Not an independent VASP central-strain result')
        if not str(result.get('backend', '')).startswith('VASP'):
            raise ValueError('Independent central-strain result is not from VASP')
        if result.get('dimensionality') != 3 or result.get('periodic_axes') != ['x', 'y', 'z']:
            raise ValueError('Not a three-dimensional periodic central-strain result')
        finite_difference = result.get('finite_difference', {})
        if (finite_difference.get('method') != 'central'
                or finite_difference.get('amplitude') != .005
                or finite_difference.get('order') != 'O(h^2)'):
            raise ValueError('Central-strain result does not use the frozen +/-0.5% protocol')
        if result.get('stage_count') != 13 or result.get('relaxation_stage_count') != 13:
            issues.append('Independent central-strain result does not contain all 13 geometries')
        if result.get('native_d_gate_changed') is not False or result.get('native_result_replaced') is not False:
            raise ValueError('Independent strain validation must not replace or relax the native d gate')
        group = space_group_number(result.get('space_group'))
        e = result.get('piezoelectric_proper_C_per_m2')
        c = result.get('elastic_GPa')
        d = result.get('piezoelectric_d_pm_per_V')
        stage_checks = result.get('stage_checks', {})
        if len(stage_checks) != 13:
            issues.append('Missing one or more independent strain-stage checks')
        else:
            for label, check in stage_checks.items():
                if check.get('electronic_converged') is not True:
                    issues.append(f'{label}: electronic convergence gate failed')
                force = check.get('force_max_eV_per_A')
                gap = check.get('gap_eV')
                if force is None or not np.isfinite(force) or force > 1e-4:
                    issues.append(f'{label}: force gate failed')
                if gap is None or not np.isfinite(gap) or gap < .01:
                    issues.append(f'{label}: insulating gate failed')
        reference_record = result.get('reference', {})
        reference_check = reference_record.get('checks', {})
        if reference_check.get('space_group') != group:
            issues.append('Reference space group differs from fitted response group')
        reference_stress = np.asarray(reference_record.get('stress_raw_kbar', []), dtype=float)
        if (reference_stress.shape != (3, 3) or not np.all(np.isfinite(reference_stress))
                or np.max(np.abs(reference_stress)) > .5):
            issues.append('Reference stress gate failed')
        fits = result.get('fit_diagnostics', {})
        for key in ('piezoelectric_raw', 'elastic'):
            fit = fits.get(key, {})
            if (fit.get('complete') is not True or fit.get('input_rank') != 6
                    or fit.get('fit_rank') != fit.get('allowed_rank')):
                issues.append(f'Missing/incomplete finite-difference rank: {key}')
        symmetry_checks = result.get('symmetry_diagnostics', {})
        for key in ('piezoelectric_proper', 'elastic'):
            residual = symmetry_checks.get(key, {}).get('projection_residual_relative')
            if residual is None or not np.isfinite(residual) or residual > 1e-3:
                issues.append(f'Missing/failed {key} symmetry projection')
        stability = result.get('mechanical_stability', {})
        if stability.get('stable_within_tolerance') is not True:
            issues.append('Mechanical stability not passed')
        branch_residuals = np.asarray(result.get('branch_residuals', []), dtype=float)
        if branch_residuals.shape != (13,) or not np.all(np.isfinite(branch_residuals)):
            issues.append('Missing/nonfinite polarization branch diagnostics')
        diagnostics = {
            'fit_diagnostics': fits,
            'symmetry_diagnostics': symmetry_checks,
            'mechanical_stability': stability,
            'branch_residuals': branch_residuals.tolist(),
            'route': 'independent relaxed-ion central strain; not native displaced-atoms d',
        }
    elif backend == 'abacus':
        if result.get('dimensionality',{}).get('value') != 3:
            raise ValueError('Not an ABACUS bulk result')
        group = space_group_number(result.get('observed_reference_space_group'))
        if group != provenance.get('space_group'):
            raise ValueError('Collected reference space group differs from continuation gate')
        e = result['piezoelectric_proper_C_per_m2']
        c = result.get('elastic_GPa')
        d = result.get('piezoelectric_d_pm_per_V')
        diagnostics = result.get('symmetry_response_audit', {})
        if diagnostics.get('status') != 'available':
            issues.append('Reference/intended symmetry agreement not established')
        for key in ('piezoelectric_proper','elastic'):
            audit = diagnostics.get('quantities',{}).get(key,{})
            if not str(audit.get('status','')).startswith('consistent'):
                issues.append(f'Missing/failed {key} symmetry audit')
        if result.get('mechanical_stable_positive_definite') is not True:
            issues.append('Mechanical stability not passed')
        for key in ('piezoelectric_proper_diagnostics', 'elastic_diagnostics'):
            fit = result.get(key, {})
            if (fit.get('complete') is not True or fit.get('input_rank') != 6
                    or fit.get('fit_rank') != fit.get('allowed_rank')):
                issues.append(f'Missing/incomplete finite-difference rank: {key}')
        force = result.get('reference_force_max_eV_per_angstrom')
        if force is None or not np.isfinite(force) or force > 1e-4:
            issues.append('Missing/failed reference force gate')
        gaps = result.get('stage_band_gaps_eV',{})
        if not gaps or any(g.get('insulating') is not True for g in gaps.values()):
            issues.append('Missing/failed stage insulating gates')
    else:
        raise ValueError(f'Unknown backend: {backend}')
    reference = references.get(material)
    if reference is not None and group != reference['space_group']:
        raise ValueError(f'Phase mismatch: {material}, space group {group}')
    e = np.asarray(e, dtype=float)
    if e.shape != (3,6) or not np.all(np.isfinite(e)):
        raise ValueError('Incomplete/nonfinite full e tensor')
    native_e = e.copy()
    frame_rotation = spec.get('frame_rotation_old_to_new')
    if frame_rotation is not None:
        matrix = np.asarray(frame_rotation, dtype=float)
        e = rotate_piezoelectric_tensor(e, matrix)
        if c is not None:
            c = rotate_elastic_tensor(c, matrix)
        if d is not None:
            # d maps ordinary stress Voigt, not engineering strain Voigt.
            d = matrix@np.asarray(d,dtype=float)@np.linalg.inv(stress_representation(matrix))
    closure = None
    if c is None or d is None:
        issues.append('Complete C/d unavailable; e alone is not full e/C/d acceptance')
    else:
        c, d = np.asarray(c,dtype=float), np.asarray(d,dtype=float)
        if c.shape != (6,6) or d.shape != (3,6) or not np.all(np.isfinite(c)) or not np.all(np.isfinite(d)):
            raise ValueError('Incomplete/nonfinite C or d')
        if np.min(np.linalg.eigvalsh((c+c.T)/2)) <= 0:
            issues.append('Elastic tensor is not positive definite')
        if np.max(np.abs(c-c.T)) > 1e-3*max(1.,float(np.max(np.abs(c)))):
            issues.append('Elastic major symmetry failed')
        closure = float(np.max(np.abs(d@c/1000-e)))
        if closure > 1e-8:
            issues.append('d/e/C algebraic closure failed')
    return {'material':material,'backend':backend,'functional':'PBE','space_group':group,
            'source':str(path),'source_sha256':sha256(path),'continuation':provenance,
            'coordinate_audit_evidence':spec['coordinate_audit_evidence'],
            'frame_rotation_old_to_new':frame_rotation,
            'e_C_m2_original_frame':native_e.tolist(),
            'e_C_m2':e.tolist(),'C_GPa':None if c is None else np.asarray(c).tolist(),
            'd_pm_V':None if d is None else np.asarray(d).tolist(),
            'd33_pm_V':None if d is None else float(np.asarray(d)[2,2]),
            'd33_database_value':None,'d33_database_difference_percent':None,
            'd_e_C_closure_max_C_m2':closure,'quality_issues':issues,'quality_diagnostics':diagnostics,
            'status':'scientific_gate_pending' if issues else 'internally_consistent_external_difference_reported',
            'comparison':None if reference is None else tensor_comparison(e,reference['e_C_m2']),
            'database_note':'No matching ordered PZT model entry' if reference is None else reference['material_id']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--native-case', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--additional-calculations', type=Path,
                        help='JSON list of actual result sources and explicit coordinate/domain audits')
    args = parser.parse_args()
    selected = extract_database(args.database)
    validation_path = args.native_case / 'results/validation.json'
    validation = json.loads(validation_path.read_text())
    if validation.get('passed') is not True or validation['checks'].get('elastic: reliable derived d emitted') is not True:
        raise ValueError('Native AlN acceptance or derived-d quality gate did not pass')
    native_path = args.native_case / 'results/elastic/vasp_native_response.json'
    native = json.loads(native_path.read_text())
    if native['dimensionality'] != 3 or native['normalization'] != 'bulk':
        raise ValueError('Not an accepted bulk response')
    # The case and IEEE reference both use +a along x, +c along z. No hidden
    # domain sign flip, symmetry projection or improper-to-proper correction.
    geometry_path = args.native_case / 'results/AlN_relaxed.vasp'
    cell = read_structure(geometry_path).lattice_angstrom
    if cell[0,0] <= 0 or cell[2,2] <= 0 or np.max(np.abs([cell[0,1],cell[0,2],cell[2,0],cell[2,1]])) > 1e-6:
        raise ValueError('Native AlN axes not aligned with IEEE reference; explicit rotation required')
    e = np.asarray(native['tensors']['piezoelectric_total_C_m2'])
    c = np.asarray(native['tensors']['elastic_relaxed_GPa'])
    d = np.asarray(native['tensors']['piezoelectric_d_pm_V'])
    closure = np.max(np.abs(d @ c / 1000 - e))
    if closure > 1e-8 or np.min(np.linalg.eigvalsh((c+c.T)/2)) <= 0:
        raise ValueError('Native d/e/C closure or mechanical stability failed')
    comparison = tensor_comparison(e, selected['AlN']['e_C_m2'])
    record = {'database_url': 'https://ndownloader.figshare.com/files/13220621',
              'database_sha256': DATABASE_SHA256, 'database_records_expected': 941,
              'database_records_retrieved': 941, 'same_phase_records_selected': 4,
              'access_date': '2026-09-18', 'reference_tensors': selected,
              'native_AlN': {'e_C_m2': e.tolist(), 'C_GPa': c.tolist(), 'd_pm_V': d.tolist(),
                             'd33_pm_V': float(d[2,2]), 'native_sha256': sha256(native_path),
                             'validation_sha256': sha256(validation_path), 'source': str(native_path),
                             'source_branch': 'codex/vasp-native-response', 'commit': 'bbaf059a',
                             'd_e_C_closure_max_C_m2': float(closure),
                             'quality_diagnostics': native['diagnostics'], 'comparison': comparison},
              'limitations': ['No accepted new PBE e/C/d results for the other campaign cases.',
                              'Database contains e, not directly reported d33 or C.',
                              'Native AlN has ENCUT=600 eV, database 1000 eV; same functional is not identical inputs.',
                              'PZT ordered model has no matching entry in this dataset.',
                              'Do not fill missing calculated tensors with PBEsol values.']}
    args.output.mkdir(parents=True, exist_ok=True)
    if args.additional_calculations:
        specifications = json.loads(args.additional_calculations.read_text(encoding='utf-8'))
        record['additional_calculations'] = [compare_completed_result(spec, selected) for spec in specifications]
        record['limitations'][0] = (
            'Some collected campaign results may remain scientific_gate_pending; inspect each quality_issues list.')
    (args.output / 'comparison.json').write_text(json.dumps(record, indent=2) + '\n')
    with (args.output / 'AlN_full_tensor_comparison.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparison['components'][0]))
        writer.writeheader(); writer.writerows(comparison['components'])
    for calculation in record.get('additional_calculations', []):
        if calculation['comparison'] is None:
            continue
        filename = f"{calculation['material']}_{calculation['backend'].upper()}_full_tensor_comparison.csv"
        rows = calculation['comparison']['components']
        with (args.output/filename).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    print(json.dumps({'output': str(args.output), 'AlN': comparison, 'd33_pm_V': float(d[2,2])}))


if __name__ == '__main__':
    main()
