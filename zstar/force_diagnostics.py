"""Diagnostics for raw and projected Gamma force-constant matrices."""

from __future__ import annotations

import numpy as np

from .spectra import GammaModes, rigid_motion_bases


def gamma_force_diagnostics(modes: GammaModes, raw, projected=None, *, dimensionality: int) -> dict:
    """Compare Hessian constraints and rigid/internal couplings without projecting.

    The tensors use force-atom, displaced-atom, force-axis, displacement-axis
    ordering and have units eV/angstrom^2. The projected tensor is optional.
    Rotations are diagnostic only, particularly for a 1D periodic cell.
    """
    masses = np.asarray(modes.masses_amu, dtype=float)
    n = len(masses)
    raw = np.asarray(raw, dtype=float)
    projected = None if projected is None else np.asarray(projected, dtype=float)
    if raw.shape != (n, n, 3, 3) or (projected is not None and projected.shape != raw.shape):
        raise ValueError('Gamma force constants must have shape (natom,natom,3,3)')
    if not np.all(np.isfinite(raw)) or (projected is not None and not np.all(np.isfinite(projected))):
        raise ValueError('Gamma force constants must be finite')
    translations, rotations = rigid_motion_bases(modes, dimensionality=dimensionality)
    rigid = np.column_stack((translations, rotations))
    # The SVD supplies an orthonormal complementary internal subspace.
    left, _, _ = np.linalg.svd(rigid, full_matrices=True)
    internal = left[:, rigid.shape[1]:]
    weights = np.repeat(1.0 / np.sqrt(masses), 3)

    def metrics(values):
        hessian = values.transpose(0, 2, 1, 3).reshape(3 * n, 3 * n)
        symmetric = (hessian + hessian.T) / 2
        dynamical = weights[:, None] * symmetric * weights[None, :]
        rigid_block = rigid.T @ dynamical @ rigid
        coupling = rigid.T @ dynamical @ internal
        internal_block = internal.T @ dynamical @ internal
        return {
            'reciprocity_max_eV_A2': float(np.max(np.abs(hessian - hessian.T))),
            'translation_force_residual_max_eV_A2': float(np.max(np.abs(values.sum(axis=1)))),
            'total_force_derivative_max_eV_A2': float(np.max(np.abs(values.sum(axis=0)))),
            'rigid_block_frobenius': float(np.linalg.norm(rigid_block)),
            'rigid_internal_coupling_frobenius': float(np.linalg.norm(coupling)),
            'internal_block_min_eigenvalue': (float(np.linalg.eigvalsh(internal_block)[0])
                                               if internal_block.size else None),
        }

    raw_h = raw.transpose(0, 2, 1, 3).reshape(3 * n, 3 * n)
    projected_h = (None if projected is None else
                   projected.transpose(0, 2, 1, 3).reshape(3 * n, 3 * n))
    return {
        'schema': 'zstar-gamma-force-diagnostics', 'version': 1,
        'dimensionality': dimensionality,
        'rigid_basis': {'translations': translations.shape[1], 'rotations': rotations.shape[1],
                        'rotation_scope': '1D axial candidate' if dimensionality == 1 else
                                          'molecular' if dimensionality == 0 else 'not assessed'},
        'mass_weighted_units': 'eV/(angstrom^2 amu)',
        'raw': metrics(raw), 'projected': None if projected is None else metrics(projected),
        'projection_relative_frobenius': (None if projected_h is None else
                                          float(np.linalg.norm(projected_h - raw_h)
                                                / max(np.linalg.norm(raw_h), 1e-30))),
        'interpretation': ('Internal-block eigenvalues and rigid/internal couplings are diagnostics; '
                           'they do not alone establish full-Hessian or all-wavevector stability.'),
    }
