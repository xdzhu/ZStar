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
    """Separate rigid motions by mass-weighted overlaps, not a frequency cutoff."""
    if dimension not in (0, 1, 2, 3):
        raise ValueError('dimensionality must be 0, 1, 2, or 3')
    positions = modes.positions_fractional @ modes.lattice_angstrom
    positions -= np.average(positions, axis=0, weights=modes.masses_amu)
    weight = np.sqrt(modes.masses_amu)[:, None]
    vectors = [np.broadcast_to(axis, positions.shape)*weight for axis in np.eye(3)]
    if dimension in (0, 1):
        axes = np.eye(3) if dimension == 0 else np.eye(3)[2:]
        vectors += [np.cross(axis, positions)*weight for axis in axes]
    rigid = np.array([v.ravel() for v in vectors]).T
    norms = np.linalg.norm(rigid, axis=0)
    rigid = rigid[:, norms > 1e-12]/norms[norms > 1e-12]
    u, singular, _ = np.linalg.svd(rigid, full_matrices=False)
    rank = np.count_nonzero(singular > singular[0]*1e-10)
    overlap = np.sum(abs(modes.eigenvectors.reshape(len(modes.frequencies_cm1), -1).conj()
                         @ u[:, :rank])**2, axis=1)
    if np.any((overlap >= .2) & (overlap <= .8)) or np.count_nonzero(overlap > .8) != rank:
        raise ValueError('Ambiguous rigid/vibrational mode mixing; inspect the equilibrium structure and Hessian')
    selected = np.flatnonzero(overlap < .2)
    if not len(selected) or np.any(modes.frequencies_cm1[selected] <= 0):
        raise ValueError('Unstable internal vibrations; no stable harmonic spectrum can be reported')
    return selected, dict(rigid_mode_numbers=(np.flatnonzero(overlap > .8)+1).tolist(),
                         rigid_frequencies_cm1=modes.frequencies_cm1[overlap > .8].tolist(),
                         rigid_overlaps=overlap.tolist())
