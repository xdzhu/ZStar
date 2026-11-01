"""Geometry-gated, degeneracy-aware Gamma mode comparison."""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from .spectra import GammaModes


def _groups(frequencies: np.ndarray, tolerance: float) -> list[np.ndarray]:
    order = np.argsort(frequencies, kind='stable')
    groups = [[int(order[0])]]
    for index in order[1:]:
        # Compare to the first member, avoiding arbitrarily long chained groups.
        if frequencies[index] - frequencies[groups[-1][0]] <= tolerance:
            groups[-1].append(int(index))
        else:
            groups.append([int(index)])
    return [np.asarray(group, dtype=int) for group in groups]


def compare_gamma_modes(reference: GammaModes, candidate: GammaModes, *, dimensionality: int,
                        geometry_tolerance_A: float = 1e-4,
                        degeneracy_tolerance_cm1: float = 1.0) -> dict:
    """Match mode subspaces after verifying the structures are the same.

    Structures must use the same Cartesian frame and atom order. A global
    translation is allowed. Frequencies remain unshifted; overlap is not a
    validation of electronic response or vibrational intensities.
    """
    if dimensionality not in (0, 1, 2, 3):
        raise ValueError('dimensionality must be 0, 1, 2, or 3')
    for name, value in (('geometry_tolerance_A', geometry_tolerance_A),
                        ('degeneracy_tolerance_cm1', degeneracy_tolerance_cm1)):
        if not np.isfinite(value) or value < 0:
            raise ValueError(f'{name} must be finite and nonnegative')
    if reference.symbols != candidate.symbols or len(reference.symbols) == 0:
        raise ValueError('Mode sources have different atom ordering or species')
    n = len(reference.symbols)
    if (np.asarray(reference.masses_amu).shape != (n,) or
            np.asarray(candidate.masses_amu).shape != (n,) or
            not np.allclose(reference.masses_amu, candidate.masses_amu, atol=1e-4, rtol=0)):
        raise ValueError('Mode sources have different masses')
    cell = np.asarray(reference.lattice_angstrom, dtype=float)
    other_cell = np.asarray(candidate.lattice_angstrom, dtype=float)
    if (cell.shape != (3, 3) or other_cell.shape != (3, 3) or
            not np.all(np.isfinite(cell)) or not np.all(np.isfinite(other_cell)) or
            not np.allclose(cell, other_cell, atol=geometry_tolerance_A, rtol=0)):
        raise ValueError('Mode sources have different cells or Cartesian frames')
    ref_positions = np.asarray(reference.positions_fractional, dtype=float)
    other_positions = np.asarray(candidate.positions_fractional, dtype=float)
    if (ref_positions.shape != (n, 3) or other_positions.shape != (n, 3) or
            not np.all(np.isfinite(ref_positions)) or not np.all(np.isfinite(other_positions))):
        raise ValueError('Mode sources have invalid positions')
    delta = other_positions - ref_positions
    periodic_axes = {0: (), 1: (2,), 2: (0, 1), 3: (0, 1, 2)}[dimensionality]
    # Resolve wrapping relative to the first atom before removing a common shift.
    if periodic_axes:
        delta[:, periodic_axes] -= np.rint(delta[:, periodic_axes] - delta[0, periodic_axes])
        delta[:, periodic_axes] -= np.rint(np.mean(delta[:, periodic_axes], axis=0))
    shifts = delta @ cell
    global_shift = np.mean(shifts, axis=0)
    geometry_error = float(np.max(np.linalg.norm(shifts - global_shift, axis=1)))
    if geometry_error > geometry_tolerance_A:
        raise ValueError(f'Mode sources are not the same geometry after translation: {geometry_error:.6g} A')

    frequencies = [np.asarray(item.frequencies_cm1, dtype=float) for item in (reference, candidate)]
    vectors = [np.array(item.eigenvectors, dtype=complex, copy=True).reshape(-1, 3 * n)
               for item in (reference, candidate)]
    for frequency, vector in zip(frequencies, vectors):
        if (frequency.shape != (3 * n,) or vector.shape != (3 * n, 3 * n) or
                not np.all(np.isfinite(frequency)) or not np.all(np.isfinite(vector))):
            raise ValueError('Expected a complete finite Gamma eigensystem with 3N modes')
        norms = np.linalg.norm(vector, axis=1)
        if np.any(norms < 1e-12):
            raise ValueError('Mode eigenvectors must have nonzero norms')
        vector /= norms[:, None]
        if not np.allclose(vector.conj() @ vector.T, np.eye(3 * n), atol=1e-5, rtol=0):
            raise ValueError('Mode eigenvectors must form an orthonormal mass-weighted basis')

    groups_a = _groups(frequencies[0], degeneracy_tolerance_cm1)
    groups_b = _groups(frequencies[1], degeneracy_tolerance_cm1)
    overlap = np.abs(vectors[0].conj() @ vectors[1].T) ** 2
    scores = np.asarray([[overlap[np.ix_(a, b)].sum() / max(len(a), len(b)) for b in groups_b]
                         for a in groups_a])
    rows, cols = linear_sum_assignment(-scores)
    matches = []
    for row, col in zip(rows, cols):
        a, b = groups_a[row], groups_b[col]
        singular = np.linalg.svd(vectors[0][a].conj() @ vectors[1][b].T, compute_uv=False)
        matches.append({
            'reference_modes': (a + 1).tolist(), 'candidate_modes': (b + 1).tolist(),
            'reference_frequencies_cm-1': frequencies[0][a].tolist(),
            'candidate_frequencies_cm-1': frequencies[1][b].tolist(),
            'dimension_match': len(a) == len(b),
            'subspace_overlap_score': float(np.clip(scores[row, col], 0, 1)),
            'principal_overlaps': np.clip(singular ** 2, 0, 1).tolist(),
        })
    matched_a, matched_b = set(rows.tolist()), set(cols.tolist())
    return {
        'schema': 'zstar-gamma-mode-comparison', 'version': 1, 'dimensionality': dimensionality,
        'geometry_max_residual_A': geometry_error, 'common_translation_A': global_shift.tolist(),
        'geometry_tolerance_A': float(geometry_tolerance_A),
        'degeneracy_tolerance_cm-1': float(degeneracy_tolerance_cm1),
        'matches': matches,
        'unmatched_reference_groups': [(groups_a[i] + 1).tolist() for i in range(len(groups_a)) if i not in matched_a],
        'unmatched_candidate_groups': [(groups_b[i] + 1).tolist() for i in range(len(groups_b)) if i not in matched_b],
        'limitations': ('Same-frame geometry and mass checks do not make different electronic methods equivalent. '
                        'Subspace overlaps do not validate intensities or full Brillouin-zone stability.'),
    }
