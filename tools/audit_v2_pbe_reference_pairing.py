"""Audit archived PBE e/C pairing; cross-archive d is not a reported DB value."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
from importlib.metadata import version
import itertools
import json
from pathlib import Path
import sys
import warnings

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zstar.v2.units import convert_values

TARGETS = {'AlN': 'mp-661', 'GaN': 'mp-804', 'ZnO': 'mp-2133', 'PTO': 'mp-20459'}
HASHES = {
    'elastic_tensor_2015': '8c3b342f75da7e7baa1b769b59554485fd647f4cb1da9318d0d1ba3b3b838183',
    'piezoelectric_tensor': 'dc9d04836f7f91ecb4ef6dc23e42468571be857f0fccafdfb51a5a40f19db898',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def reject(value):
        raise ValueError('Nonfinite JSON constant')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


def read_table(path, name, expected_count, metadata):
    if not 0 < path.stat().st_size <= 2_000_000 or digest(path) != HASHES[name]:
        raise ValueError('Unexpected archived dataset size/hash')
    if metadata[name]['hash'] != HASHES[name] or metadata[name]['num_entries'] != expected_count:
        raise ValueError('Official metadata hash/count mismatch')
    with gzip.open(path, 'rb') as stream:
        raw = stream.read(50_000_001)
    if len(raw) > 50_000_000:
        raise ValueError('Decompressed dataset exceeds bound')
    table = strict_json(raw)
    columns = table['columns']
    if (len(columns) != len(set(columns)) or len(table['data']) != expected_count or
            len(table['index']) != expected_count):
        raise ValueError('Incomplete/ambiguous dataset')
    rows = {}
    for values in table['data']:
        if len(values) != len(columns):
            raise ValueError('Dataset row width mismatch')
        row = dict(zip(columns, values))
        key = row['material_id']
        if key in rows:
            raise ValueError('Duplicate material identifier')
        rows[key] = row
    return rows


def intake_structure(payload):
    # Explicit constructor, not a general MSON object-graph decoder.
    from pymatgen.core import Structure
    sites = payload['sites']
    if not 2 <= len(sites) <= 8:
        raise ValueError('Only bounded ordered bulk reference structures supported')
    for site in sites:
        species = site['species']
        if len(species) != 1 or species[0]['occu'] != 1 or 'oxidation_state' in species[0]:
            raise ValueError('Disorder/oxidation decoration requires a separate audit')
    structure = Structure.from_dict(payload)
    if (not structure.is_ordered or tuple(structure.lattice.pbc) != (True, True, True) or
            not np.isfinite(structure.volume) or structure.volume <= 0 or
            not np.all(np.isfinite(structure.frac_coords))):
        raise ValueError('Expected finite ordered 3D periodic structure')
    distances = structure.distance_matrix.copy()
    np.fill_diagonal(distances, np.inf)
    if distances.min() < .5:
        raise ValueError('Unphysical site proximity')
    return structure


def geometry_difference(piezo, elastic):
    if len(piezo) != len(elastic) or piezo.composition != elastic.composition:
        raise ValueError('Reference stoichiometry/site count mismatch')
    lp, lc = piezo.lattice.matrix, elastic.lattice.matrix
    directions_p = lp / np.linalg.norm(lp, axis=1)[:, None]
    directions_c = lc / np.linalg.norm(lc, axis=1)[:, None]
    direction_difference = float(np.max(np.abs(directions_p-directions_c)))
    # Both archives serialize POSCAR-derived matrices to six decimal places.
    # This is a basis-direction diagnostic, not an atom/symmetry tolerance.
    same_basis = bool(direction_difference < 1e-6)
    report = {
        'piezo_volume_angstrom3': float(piezo.volume),
        'elastic_volume_angstrom3': float(elastic.volume),
        'elastic_minus_piezo_volume_percent': float(100*(elastic.volume/piezo.volume-1)),
        'elastic_minus_piezo_lattice_lengths_percent': (100*(np.asarray(elastic.lattice.abc)/piezo.lattice.abc-1)).tolist(),
        'same_fractional_basis_directions': same_basis,
        'basis_direction_max_difference_dimensionless': direction_difference,
        'basis_direction_tolerance_dimensionless': 1e-6,
        'lattice_matrix_max_difference_angstrom': float(np.max(np.abs(lp-lc))),
        'internal_comparison': None,
        'same_geometry_at_serialization_precision': False,
        'serialization_identity_tolerance_angstrom': 1e-6,
        'identity_tolerance_note': 'File-geometry equality diagnostic, not a production acceptance or spglib tolerance',
    }
    if not same_basis:
        return report
    report['internal_comparison'] = internal_coordinate_difference(piezo, elastic, 1)
    report['inversion_related_internal_comparison'] = internal_coordinate_difference(piezo, elastic, -1)
    report['inversion_note'] = 'Diagnostic structural inversion only. Rank-four C is inversion-even; retain published e and its domain/sign unchanged.'
    report['same_geometry_at_serialization_precision'] = bool(
        report['lattice_matrix_max_difference_angstrom'] <= 1e-6 and
        report['internal_comparison']['max_difference_angstrom'] <= 1e-6)
    return report


def internal_coordinate_difference(piezo, elastic, inversion_sign):
    labels_p = [str(s.specie) for s in piezo]
    labels_c = [str(s.specie) for s in elastic]
    best = None
    for permutation in itertools.permutations(range(len(elastic))):
        if [labels_c[i] for i in permutation] != labels_p:
            continue
        target = inversion_sign*elastic.frac_coords[list(permutation)]
        shift = target[0]-piezo.frac_coords[0]
        # Exact periodic metric in the piezo lattice; do not round each
        # fractional component as a triclinic minimum-image approximation.
        distances = np.diag(piezo.lattice.get_all_distances(piezo.frac_coords+shift, target))
        score = (float(np.max(distances)), float(np.linalg.norm(distances)))
        if best is None or score < best[0]:
            best = (score, permutation, shift, distances)
    if best is None:
        raise ValueError('No species-preserving site correspondence')
    return {
        'metric': 'Compare piezo_fractional+shift against sign*elastic_fractional in the piezo lattice; exclude lattice dilation',
        'elastic_fractional_inversion_sign': inversion_sign,
        'max_difference_angstrom': best[0][0],
        'per_site_difference_angstrom': best[3].tolist(),
        'piezo_to_elastic_site_indices_zero_based': list(best[1]),
        'common_origin_shift_fractional': best[2].tolist(),
    }


def cross_archive_d(e_c_m2, c_gpa):
    e, c = np.asarray(e_c_m2, dtype=float), np.asarray(c_gpa, dtype=float)
    if e.shape != (3, 6) or c.shape != (6, 6) or not all(np.all(np.isfinite(a)) for a in (e, c)):
        raise ValueError('Finite full 3D e/C matrices required')
    if np.max(np.abs(c-c.T)) > 1e-8 or np.min(np.linalg.eigvalsh(c)) <= 0:
        raise ValueError('Reference C must be major-symmetric and positive definite; no silent projection')
    c_pa = convert_values(c, 'GPa', 'Pa')
    d_c_n = np.linalg.solve(c_pa.T, e.T).T
    return {
        'value': (d_c_n*1e12).tolist(), 'unit': 'pm/V (= pC/N)',
        'relation': 'd_cross_archive = e_piezo_archive @ inverse(C_E_elastic_archive)',
        'coordinate_system': 'Published IEEE; common hexagonal c axis assumed, not arbitrary POSCAR arrays',
        'voigt': ['xx', 'yy', 'zz', 'yz', 'xz', 'xy'],
        'input_strain': 'engineering shear', 'input_stress': 'tensorial shear',
        'ion_relaxation': 'relaxed-ion', 'electrical_boundary': 'fixed E',
        'backend': 'VASP PAW', 'functional': 'PBE',
        'source_kind': 'derived cross-archive comparator, not a database-reported d tensor',
        'same_calculation_paired_reference': False, 'standard_uncertainty': None,
        'roundtrip_max_C_m2': float(np.max(np.abs(d_c_n@c_pa-e))),
        'condition_number_C': float(np.linalg.cond(c_pa)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--piezo', type=Path, required=True)
    parser.add_argument('--elastic', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--comparison', type=Path,
                        help='Existing frozen e/C/d comparison; retain its acceptance statuses')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.metadata.stat().st_size > 200_000:
        raise ValueError('New output and bounded official metadata required')
    metadata = strict_json(args.metadata.read_bytes())
    e_rows = read_table(args.piezo, 'piezoelectric_tensor', 941, metadata)
    c_rows = read_table(args.elastic, 'elastic_tensor_2015', 1181, metadata)
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    result = {
        'schema': 'zstar-v2-research-cross-archive-reference/1',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'algorithm_sha256': digest(__file__),
        'versions': {name: version(name) for name in ('pymatgen', 'spglib', 'numpy')},
        'sources': {name: {'sha256': HASHES[name], 'url': metadata[name]['url'],
                           'expected_count': count, 'retrieved_count': count}
                    for name, count in [('piezoelectric_tensor', 941), ('elastic_tensor_2015', 1181)]},
        'official_metadata': {'url': 'https://raw.githubusercontent.com/hackingmaterials/matminer/main/src/matminer/datasets/dataset_metadata.json',
                              'sha256': digest(args.metadata), 'access_date': '2026-09-19'},
        'network': 'No API/DFT calls by this collector; two pre-existing frozen local caches',
        'cases': {},
        'limitations': ['Different archived response geometries, k densities and ENCUT may affect derived d.',
                        'No formal acceptance threshold or native d gate is changed.',
                        'Difference from this comparator is not independent accuracy or a confidence interval.'],
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for name, identifier in TARGETS.items():
            ep = e_rows[identifier]
            ec = c_rows.get(identifier)
            case = {'material_id': identifier, 'elastic_match_count': int(ec is not None),
                    'database_reported_d': None, 'cross_archive_d': None}
            if ec is not None:
                sp, sc = intake_structure(ep['structure']), intake_structure(ec['structure'])
                groups = [SpacegroupAnalyzer(s, symprec=1e-3, angle_tolerance=5).get_space_group_number()
                          for s in (sp, sc)]
                if groups != [186, 186] or [int(ep['space_group']), int(ec['space_group'])] != groups:
                    raise ValueError('This cross-archive contraction only audits matching hexagonal cases')
                for structure in (sp, sc):
                    cell = structure.lattice.matrix
                    if cell[0, 0] <= 0 or cell[2, 2] <= 0 or np.max(np.abs([*cell[0, 1:], *cell[2, :2]])) > 1e-6:
                        raise ValueError('Common +a/+c hexagonal archive axes not established')
                case.update({
                    'space_groups': groups, 'symprec_angstrom': 1e-3, 'angle_tolerance_degree': 5,
                    'geometry': geometry_difference(sp, sc),
                    'piezo_structure': sp.as_dict(), 'elastic_structure': sc.as_dict(),
                    'elastic_reference': {'value': ec['elastic_tensor']['data'], 'unit': 'GPa',
                                          'coordinate_system': 'IEEE', 'ion_relaxation': 'relaxed-ion'},
                    'piezo_reference': {'value': ep['piezoelectric_tensor']['data'], 'unit': 'C/m^2',
                                        'coordinate_system': 'IEEE', 'kind': 'proper', 'ion_relaxation': 'relaxed-ion'},
                    'elastic_kpoint_density_pra': ec['kpoint_density'],
                    'published_settings_note': 'Piezo paper: ENCUT1000 eV/2000 pra; elastic paper: ENCUT700 eV. Per-record actual inputs/PAW hashes unavailable.',
                    'cross_archive_d': cross_archive_d(ep['piezoelectric_tensor']['data'], ec['elastic_tensor']['data']),
                })
            else:
                case['limitation'] = 'No matching material ID in all 1181 archived elastic entries; do not infer C/d'
            result['cases'][name] = case
    result['parser_and_symmetry_warnings'] = [str(w.message) for w in caught]
    if args.comparison:
        if args.comparison.stat().st_size > 5_000_000:
            raise ValueError('Existing comparison exceeds intake bound')
        comparison = strict_json(args.comparison.read_bytes())
        records = comparison['additional_calculations'] + [
            dict(comparison['native_AlN'], material='AlN', backend='vasp',
                 status='previously_accepted_native_AlN', quality_issues=[])]
        result['calculation_comparison_source_sha256'] = digest(args.comparison)
        result['calculation_comparisons'] = []
        for record in records:
            reference = result['cases'][record['material']]
            if reference['cross_archive_d'] is None:
                continue
            c = np.asarray(record['C_GPa'], dtype=float)
            cref = np.asarray(reference['elastic_reference']['value'], dtype=float)
            if c.shape != (6, 6) or not np.all(np.isfinite(c)):
                raise ValueError('Complete finite calculated C required')
            d33 = record['d33_pm_V']
            ref33 = reference['cross_archive_d']['value'][2][2]
            result['calculation_comparisons'].append({
                'material': record['material'], 'backend': record['backend'],
                'original_acceptance_status': record['status'],
                'original_quality_issues': record['quality_issues'],
                'C_GPa': c.tolist(), 'C_minus_reference_GPa': (c-cref).tolist(),
                'C_full_voigt_frobenius_relative_difference_percent': float(100*np.linalg.norm(c-cref)/np.linalg.norm(cref)),
                'C_max_absolute_difference_GPa': float(np.max(np.abs(c-cref))),
                'calculated_d33_pm_V': d33, 'cross_archive_reference_d33_pm_V': ref33,
                'd33_signed_relative_difference_percent': None if d33 is None else float(100*(d33-ref33)/abs(ref33)),
                'comparison_note': 'Qualified cross-archive reference, not DB-reported d; null native d stays null',
            })
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({name: {'volume_difference_percent': case.get('geometry', {}).get('elastic_minus_piezo_volume_percent'),
                             'd33_cross_archive_pm_V': None if case['cross_archive_d'] is None else case['cross_archive_d']['value'][2][2]}
                      for name, case in result['cases'].items()}))


if __name__ == '__main__':
    main()
