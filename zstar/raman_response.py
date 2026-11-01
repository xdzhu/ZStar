"""Symmetry reconstruction of electronic-response displacement derivatives."""
from __future__ import annotations

import numpy as np


def reconstruct_raman_derivatives(natoms, observations, operations):
    """Fit G[atom, dielectric row, dielectric column, displacement] in 1/A.

    Symmetry expands measured displacement orbits; no acoustic sum-rule
    projection is imposed. All observations use actual written displacements.
    """
    derivative = np.zeros((natoms, 3, 3, 3))
    counts = np.zeros(natoms)
    reports = []
    if not observations or not operations:
        raise ValueError('Raman reconstruction requires observations and symmetry operations')
    for atom in sorted({int(s['atom']) for s in observations}):
        if not 0 <= atom < natoms:
            raise ValueError('Atom index outside the structure')
        x, y = [], []
        for s in (s for s in observations if s['atom'] == atom):
            u, d = np.asarray(s['displacement_A']), np.asarray(s['delta_epsilon'])
            if u.shape != (3,) or d.shape != (3, 3) or np.linalg.norm(u) < 1e-10:
                raise ValueError('Invalid displacement or response shape')
            if not np.all(np.isfinite(u)) or not np.all(np.isfinite(d)):
                raise ValueError('Nonfinite observation')
            for r, p in operations:
                if p[atom] == atom:
                    x.append(r @ u)
                    y.append((r @ d @ r.T).ravel())
        if not x:
            raise ValueError(f'Atom {atom}: no site-preserving symmetry operation')
        x, y = np.asarray(x), np.asarray(y)
        coefficients, _, rank, singular = np.linalg.lstsq(x, y, rcond=1e-10)
        if rank != 3:
            raise ValueError(f'Atom {atom}: displacement orbit rank {rank}/3; prepare a complete ensemble')
        tensor = coefficients.T.reshape(3, 3, 3)
        reports.append(dict(atom=atom, rank=int(rank), condition=float(singular[0]/singular[-1]),
                            max_epsilon_residual=float(np.max(abs(x@coefficients-y)))))
        for r, p in operations:
            derivative[p[atom]] += np.einsum('ia,jb,kc,abc->ijk', r, r, r, tensor)
            counts[p[atom]] += 1
    if np.any(counts == 0):
        raise ValueError('Incomplete inequivalent-atom coverage')
    derivative /= counts[:, None, None, None]
    return derivative, dict(site_fits=reports,
        translation_sum_max_per_A=float(np.max(abs(derivative.sum(axis=0)))),
        symmetry_ab_max_per_A=float(np.max(abs(derivative-derivative.swapaxes(1, 2)))),
        symmetry_reconstruction_applied=True, acoustic_sum_rule_projected=False)


def project_raman_modes(derivative, eigenvectors, masses):
    from .spectra import _mode_phase_real
    derivative = np.asarray(derivative, dtype=float)
    masses = np.asarray(masses, dtype=float)
    if derivative.shape != (len(masses), 3, 3, 3) or np.any(masses <= 0):
        raise ValueError('Raman derivative dimensions or masses are invalid')
    if not np.isfinite(derivative).all() or not np.isfinite(masses).all():
        raise ValueError('Raman derivatives and masses must be finite')
    vectors = _mode_phase_real(eigenvectors) / np.sqrt(masses)[None, :, None]
    return np.einsum('nabc,mnc->mab', derivative, vectors)


def internal_mode_indices(modes, dimension):
    """Select stable modes using the same conservative Gamma-mode audit."""
    from .spectra import assess_gamma_modes, rigid_motion_bases, validate_gamma_stability

    rows = assess_gamma_modes(modes, dimensionality=dimension)
    validate_gamma_stability(modes, dimensionality=dimension)
    mixed = [row['mode'] for row in rows if row['classification'] == 'mixed']
    if mixed:
        raise ValueError(f'Ambiguous rigid/vibrational mode mixing in modes {mixed}; '
                         'inspect the equilibrium structure and Hessian')
    translations, rotations = rigid_motion_bases(modes, dimensionality=dimension)
    rigid = [row for row in rows if row['classification'] in
             ('translation', 'rotation', 'axial-rotation-candidate')]
    if len(rigid) != translations.shape[1] + rotations.shape[1]:
        raise ValueError('Ambiguous rigid/vibrational mode count; inspect the equilibrium structure and Hessian')
    if any(row['classification'] == 'axial-rotation-candidate'
           and row['frequency_cm-1'] > 20 for row in rigid):
        raise ValueError('1D axial rotation candidate is far from zero frequency; inspect the Hessian')
    selected = np.asarray([row['mode'] - 1 for row in rows if row not in rigid], dtype=int)
    if not len(selected) or np.any(modes.frequencies_cm1[selected] <= 0):
        raise ValueError('Unstable internal vibrations; no stable harmonic spectrum can be reported')
    return selected, dict(rigid_mode_numbers=[row['mode'] for row in rigid],
                         rigid_frequencies_cm1=[row['frequency_cm-1'] for row in rigid],
                         rigid_overlaps=[row['translation_overlap'] + row['rotation_overlap'] for row in rows],
                         one_dimensional_axial_candidates=[row['mode'] for row in rigid
                             if row['classification'] == 'axial-rotation-candidate'],
                         note='1D positive near-zero axial candidates are excluded assuming an isolated wire; '
                              'negative candidates require review and are not automatically exempt.')
