"""Analytic response relations used before calculator-backed implementation."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from .units import ELEMENTARY_CHARGE


def _finite(value: np.ndarray | Iterable[float], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values")
    return array


def remove_acoustic_translation(
    displacements: np.ndarray | Iterable[object],
    *,
    weights: np.ndarray | Iterable[float] | None = None,
) -> np.ndarray:
    """Remove an explicitly requested rigid translation from atom displacements.

    The input may have shape ``(atom, 3)`` or ``(..., atom, 3)``.  With no
    weights the arithmetic mean displacement is removed; supplied positive
    weights can represent masses or another documented center-of-mass gauge.
    This helper is never applied implicitly by collectors or fits.
    """

    values = _finite(np.asarray(displacements, dtype=float), "displacements")
    if values.ndim < 2 or values.shape[-1] != 3 or values.shape[-2] == 0:
        raise ValueError("displacements must have shape (atom, 3) or (..., atom, 3)")
    natoms = values.shape[-2]
    if weights is None:
        weight_array = np.ones(natoms, dtype=float)
    else:
        weight_array = _finite(weights, "weights")
        if weight_array.shape != (natoms,) or np.any(weight_array <= 0.0):
            raise ValueError(f"weights must have shape ({natoms},) and be positive")
    total = float(np.sum(weight_array))
    center = np.sum(values * weight_array.reshape((1,) * (values.ndim - 2) + (natoms, 1)), axis=-2) / total
    return values - np.expand_dims(center, axis=-2)


def internal_strain_response(
    force_constants: np.ndarray,
    strain_force_coupling: np.ndarray,
    *,
    svd_rcond: float = 1.0e-10,
) -> np.ndarray:
    """Return ``Lambda = -Phi^+ Gamma`` after acoustic-mode projection."""

    phi = _finite(force_constants, "force_constants")
    gamma = _finite(strain_force_coupling, "strain_force_coupling")
    if phi.ndim != 2 or phi.shape[0] != phi.shape[1]:
        raise ValueError(f"force_constants must be square; got {phi.shape}")
    if gamma.ndim != 2 or gamma.shape[0] != phi.shape[0]:
        raise ValueError(f"strain_force_coupling must have shape ({phi.shape[0]}, nstrain); got {gamma.shape}")
    if not np.isfinite(svd_rcond) or svd_rcond < 0.0:
        raise ValueError("svd_rcond must be finite and non-negative")
    return -np.linalg.pinv(phi, rcond=float(svd_rcond)) @ gamma


def relaxed_piezoelectric(
    clamped_piezo: np.ndarray,
    born_effective_charges: np.ndarray,
    internal_strain: np.ndarray,
    volume: float,
    *,
    charge: float = ELEMENTARY_CHARGE,
) -> tuple[np.ndarray, np.ndarray]:
    """Combine clamped-ion and internal-strain piezoelectric contributions.

    ``born_effective_charges`` uses ``(atom, polarization, displacement)`` and
    ``internal_strain`` uses ``(atom, displacement, voigt)``.  ``volume`` is
    expressed in m^3 when the returned tensor is in C m^-2.
    """

    e0 = _finite(clamped_piezo, "clamped_piezo")
    born = _finite(born_effective_charges, "born_effective_charges")
    lam = _finite(internal_strain, "internal_strain")
    if e0.shape != (3, 6):
        raise ValueError(f"clamped_piezo must have shape (3, 6); got {e0.shape}")
    if born.ndim != 3 or born.shape[1:] != (3, 3):
        raise ValueError(f"born_effective_charges must have shape (natom, 3, 3); got {born.shape}")
    if lam.shape != (born.shape[0], 3, 6):
        raise ValueError(f"internal_strain must have shape ({born.shape[0]}, 3, 6); got {lam.shape}")
    if not np.isfinite(volume) or float(volume) <= 0.0:
        raise ValueError("volume must be finite and positive")
    if not np.isfinite(charge) or float(charge) <= 0.0:
        raise ValueError("charge must be finite and positive")
    contribution = float(charge) / float(volume) * np.einsum("iab,ibm->am", born, lam)
    return e0 + contribution, contribution


def relaxed_elastic(
    clamped_elastic: np.ndarray,
    force_constants: np.ndarray,
    strain_force_coupling: np.ndarray,
    volume: float,
    *,
    svd_rcond: float = 1.0e-10,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return relaxed-ion ``C``, ``Lambda`` and the internal correction."""

    c0 = _finite(clamped_elastic, "clamped_elastic")
    phi = _finite(force_constants, "force_constants")
    gamma = _finite(strain_force_coupling, "strain_force_coupling")
    if c0.shape != (6, 6):
        raise ValueError(f"clamped_elastic must have shape (6, 6); got {c0.shape}")
    if not np.isfinite(volume) or float(volume) <= 0.0:
        raise ValueError("volume must be finite and positive")
    lam = internal_strain_response(phi, gamma, svd_rcond=svd_rcond)
    correction = gamma.T @ (-lam) / float(volume)
    return c0 - correction, lam, correction
