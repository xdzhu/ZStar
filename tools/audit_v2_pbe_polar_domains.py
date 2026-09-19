#!/usr/bin/env python3
"""Read-only axes/domain audit for the four bulk PBE comparison cells.

This deliberately does not standardize cells or change tensor signs. It covers
the already aligned hexagonal/tetragonal cells, not arbitrary IEEE transforms.
"""
from __future__ import annotations

import argparse
from collections import Counter
from importlib.metadata import version
import json
from pathlib import Path
import sys

import numpy as np
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zstar.structure_io import read_abacus_stru
from tools.compare_v2_pbe_database import extract_database, sha256


def aligned_axes(structure):
    cell = np.asarray(structure.lattice.matrix)
    lengths = np.linalg.norm(cell, axis=1)
    axes = cell / lengths[:, None]
    if (not np.all(np.isfinite(cell)) or np.linalg.det(cell) <= 0
            or not np.allclose(axes[0], [1, 0, 0], atol=1e-7)
            or not np.allclose(axes[2], [0, 0, 1], atol=1e-7)
            or axes[1, 1] <= 0 or abs(axes[1, 2]) > 1e-7):
        raise ValueError('Cell is not aligned +a/+x, +c/+z: explicit tensor rotation required')


def translation_fit(calculated, reference, reflect_c=False):
    """Species-preserving periodic fit; cell strain is reported separately."""
    own_species = [site.specie.symbol for site in calculated]
    ref_species = [site.specie.symbol for site in reference]
    if Counter(own_species) != Counter(ref_species):
        raise ValueError('Composition/site counts differ; cannot assign a polar domain')
    own = calculated.frac_coords
    target = reference.frac_coords.copy()
    if reflect_c:
        target[:, 2] *= -1
    candidates = []
    for anchor in np.flatnonzero(np.asarray(ref_species) == own_species[0]):
        shift = own[0] - target[anchor]
        for _ in range(6):
            mapping = np.zeros(len(own), dtype=int)
            residual = np.zeros_like(own)
            for species in sorted(set(own_species)):
                oi = np.flatnonzero(np.asarray(own_species) == species)
                ri = np.flatnonzero(np.asarray(ref_species) == species)
                distances = reference.lattice.get_all_distances(own[oi], target[ri] + shift)
                rows, cols = linear_sum_assignment(distances ** 2)
                for row, col in zip(rows, cols):
                    i, j = oi[row], ri[col]
                    mapping[i] = j
                    _, image = reference.lattice.get_distance_and_image(own[i], target[j] + shift)
                    residual[i] = own[i] - (target[j] + shift + image)
            shift += residual.mean(axis=0)
        distances = reference.lattice.get_all_distances(own, target + shift)
        rms = float(np.sqrt(np.mean(distances[np.arange(len(own)), mapping] ** 2)))
        candidates.append({'rms_angstrom': rms, 'translation_fractional': np.mod(shift, 1).tolist(),
                           'calculated_to_reference_site': mapping.tolist()})
    return min(candidates, key=lambda item: item['rms_angstrom'])


def audit(calculated, reference, expected_sg, *, frame_rotation=None):
    frame = {}
    if frame_rotation is not None:
        matrix = np.asarray(frame_rotation, dtype=float)
        if (matrix.shape != (3,3) or not np.all(np.isfinite(matrix))
                or not np.allclose(matrix@matrix.T, np.eye(3), atol=1e-10, rtol=0)
                or not np.isclose(np.linalg.det(matrix), 1, atol=1e-10, rtol=0)):
            raise ValueError('Frame rotation must be proper orthogonal')
        cell = np.asarray(calculated.lattice.matrix)@matrix.T
        # Retain physical cell shear. Only the Cartesian representation changes.
        skew = float(np.max(np.abs(cell[[0,0,1,2,2],[1,2,2,0,1]])))
        if expected_sg not in (186,99) or skew > 1e-3 or np.any(np.diag(cell) <= 0):
            raise ValueError('Rotated axes exceed 1e-3 angstrom residual alignment limit')
        frame = {'frame_rotation_old_to_new':matrix.tolist(),
                 'axis_residual_max_angstrom':skew,
                 'axis_absolute_tolerance_angstrom':1e-3,
                 'structure_standardized':False,'cell_shear_removed':False,
                 'frame_definition':'+z along actual c; +x along a projected perpendicular to c'}
        calculated = Structure(cell, calculated.species, calculated.frac_coords,
                               coords_are_cartesian=False, validate_proximity=True)
    for structure in (calculated, reference):
        if not structure.is_ordered:
            raise ValueError('Disordered sites are outside this comparison audit')
        if structure is reference or frame_rotation is None:
            aligned_axes(structure)
    sg = [SpacegroupAnalyzer(s, symprec=1e-3, angle_tolerance=5).get_space_group_number()
          for s in (calculated, reference)]
    if sg != [expected_sg, expected_sg]:
        raise ValueError(f'Phase mismatch at symprec=1e-3 angstrom: {sg}')
    same = translation_fit(calculated, reference)
    opposite = translation_fit(calculated, reference, reflect_c=True)
    # A diagnostic inference, not a sign-selection rule. Never modify tensors.
    direct, reversed_rms = same['rms_angstrom'], opposite['rms_angstrom']
    domain = 'ambiguous'
    if direct < 0.1 and reversed_rms > 2 * max(direct, 0.01):
        domain = 'same_c_polar_domain'
    elif reversed_rms < 0.1 and direct > 2 * max(reversed_rms, 0.01):
        domain = 'opposite_c_polar_domain'
    return {'space_groups': sg, 'symprec_angstrom': 1e-3, 'angle_tolerance_degree': 5,
            'axes': '+a parallel +x; +c parallel +z; right-handed' if not frame
                    else '+c parallel +z; projected +a parallel +x; residual cell shear retained',
            'domain_inference': domain, 'same_domain_fit': same, 'opposite_domain_fit': opposite,
            'cell_lengths_difference_percent':
                (100 * (np.asarray(calculated.lattice.abc) / reference.lattice.abc - 1)).tolist(),
            'coordinate_and_domain_verified': domain == 'same_c_polar_domain',
            'tensor_sign_changed': False,
            'scope': 'Bulk SG186/99 only; RMS uses reference-cell metric, cell strain excluded',
            **frame}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--structure-directory', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    references = extract_database(args.database)
    results = {}
    for material, reference in references.items():
        path = Path(args.structure_directory) / (material.lower() + '-STRU')
        source = read_abacus_stru(path)
        structure = Structure(source.lattice_angstrom, source.symbols, source.positions_fractional,
                              coords_are_cartesian=False, validate_proximity=True)
        results[material] = {'source': str(path.resolve()), 'source_sha256': sha256(path),
                            'database_material_id': reference['material_id'],
                            **audit(structure, Structure.from_dict(reference['structure']), reference['space_group'])}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'pymatgen_version': version('pymatgen'),
                                 'database_sha256': sha256(args.database), 'materials': results},
                                indent=2) + '\n', encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
