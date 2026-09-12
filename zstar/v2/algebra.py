"""Analytic response relations used before calculator-backed implementation."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from .units import ELEMENTARY_CHARGE, convert_values


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


def _acoustic_translation_basis(natoms: int) -> np.ndarray:
    """Return normalized rigid-translation vectors for ``natoms`` atoms."""

    if int(natoms) <= 0:
        raise ValueError("natoms must be positive")
    basis = np.zeros((3 * int(natoms), 3), dtype=float)
    scale = 1.0 / np.sqrt(float(natoms))
    for atom in range(int(natoms)):
        basis[3 * atom : 3 * atom + 3, :] = np.eye(3) * scale
    return basis


def acoustic_sum_rule_diagnostics(
    force_constants: np.ndarray,
    strain_force_coupling: np.ndarray,
    *,
    tolerance: float = 1.0e-10,
) -> dict[str, object]:
    """Diagnose translational compatibility of ``Phi`` and ``Gamma``.

    The three columns of the normalized basis are rigid translations of the
    whole cell.  A force-constant matrix must annihilate these vectors and a
    strain-force coupling must have zero net force for every strain.  No
    projection or repair is performed; callers can use ``check_acoustic`` in
    :func:`internal_strain_response` when an incompatible input should fail.
    """

    phi = _finite(force_constants, "force_constants")
    gamma = _finite(strain_force_coupling, "strain_force_coupling")
    if phi.ndim != 2 or phi.shape[0] != phi.shape[1]:
        raise ValueError(f"force_constants must be square; got {phi.shape}")
    if phi.shape[0] == 0 or phi.shape[0] % 3:
        raise ValueError(
            "force_constants dimension must be a positive multiple of 3 "
            f"(3*natom); got {phi.shape[0]}"
        )
    if gamma.ndim != 2 or gamma.shape[0] != phi.shape[0]:
        raise ValueError(f"strain_force_coupling must have shape ({phi.shape[0]}, nstrain); got {gamma.shape}")
    if not np.isfinite(tolerance) or float(tolerance) < 0.0:
        raise ValueError("tolerance must be finite and non-negative")

    translations = _acoustic_translation_basis(phi.shape[0] // 3)
    right_phi = phi @ translations
    left_phi = translations.T @ phi
    net_gamma = translations.T @ gamma
    phi_scale = max(float(np.linalg.norm(phi, ord=2)), 1.0)
    gamma_scale = max(float(np.linalg.norm(gamma, ord=2)), 1.0)
    phi_right_max = float(np.max(np.abs(right_phi)))
    phi_left_max = float(np.max(np.abs(left_phi)))
    gamma_max = float(np.max(np.abs(net_gamma))) if net_gamma.size else 0.0
    symmetry_max = float(np.max(np.abs(phi - phi.T)))
    phi_relative = max(phi_right_max, phi_left_max) / phi_scale
    gamma_relative = gamma_max / gamma_scale
    limit = float(tolerance)
    return {
        "natoms": int(phi.shape[0] // 3),
        "translation_basis": translations,
        "force_constants_translation_residual_max": max(phi_right_max, phi_left_max),
        "force_constants_translation_residual_relative": float(phi_relative),
        "strain_force_translation_residual_max": gamma_max,
        "strain_force_translation_residual_relative": float(gamma_relative),
        "force_constants_symmetry_residual_max": symmetry_max,
        "force_constants_scale": phi_scale,
        "strain_force_coupling_scale": gamma_scale,
        "tolerance": limit,
        "force_constants_compatible": bool(phi_relative <= limit),
        "strain_force_coupling_compatible": bool(gamma_relative <= limit),
        "compatible": bool(phi_relative <= limit and gamma_relative <= limit),
    }


def internal_strain_response(
    force_constants: np.ndarray,
    strain_force_coupling: np.ndarray,
    *,
    svd_rcond: float = 1.0e-10,
    check_acoustic: bool = False,
    acoustic_tolerance: float = 1.0e-10,
) -> np.ndarray:
    """Return the minimum-norm ``Lambda = -Phi^+ Gamma`` response.

    The Moore--Penrose inverse removes unresolved null-space components but
    does not repair a force-constant or strain-force matrix that violates the
    acoustic sum rule.  Set ``check_acoustic=True`` to reject such inputs with
    an actionable error; the default preserves the draft API's historical
    algebra-only behavior.
    """

    phi = _finite(force_constants, "force_constants")
    gamma = _finite(strain_force_coupling, "strain_force_coupling")
    if phi.ndim != 2 or phi.shape[0] != phi.shape[1]:
        raise ValueError(f"force_constants must be square; got {phi.shape}")
    if gamma.ndim != 2 or gamma.shape[0] != phi.shape[0]:
        raise ValueError(f"strain_force_coupling must have shape ({phi.shape[0]}, nstrain); got {gamma.shape}")
    if not np.isfinite(svd_rcond) or svd_rcond < 0.0:
        raise ValueError("svd_rcond must be finite and non-negative")
    if not isinstance(check_acoustic, (bool, np.bool_)):
        raise TypeError("check_acoustic must be a bool")
    if check_acoustic:
        diagnostics = acoustic_sum_rule_diagnostics(
            phi, gamma, tolerance=acoustic_tolerance
        )
        if not diagnostics["compatible"]:
            raise ValueError(
                "force_constants/strain_force_coupling violate the acoustic "
                "sum rule; inspect acoustic_sum_rule_diagnostics() or provide "
                "a translationally compatible Gamma/Phi before relaxed-ion fitting"
            )
    return -np.linalg.pinv(phi, rcond=float(svd_rcond)) @ gamma


def relaxed_piezoelectric(
    clamped_piezo: np.ndarray,
    born_effective_charges: np.ndarray,
    internal_strain: np.ndarray,
    volume: float,
    *,
    charge: float = ELEMENTARY_CHARGE,
    internal_strain_unit: str = "m",
) -> tuple[np.ndarray, np.ndarray]:
    """Combine clamped-ion and internal-strain piezoelectric contributions.

    ``born_effective_charges`` uses ``(atom, polarization, displacement)`` and
    ``internal_strain`` uses ``(atom, displacement, voigt)``.  ``volume`` is
    expressed in m^3 when the returned tensor is in C m^-2.  The
    ``internal_strain_unit`` argument declares the length unit used by
    ``internal_strain``; pass ``"angstrom"`` for calculator displacement fits.
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
    try:
        lambda_m = convert_values(lam, internal_strain_unit, "m")
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "internal_strain_unit must be a supported length unit (m or angstrom)"
        ) from exc
    contribution = float(charge) / float(volume) * np.einsum("iab,ibm->am", born, lambda_m)
    return e0 + contribution, contribution


def relaxed_elastic(
    clamped_elastic: np.ndarray,
    force_constants: np.ndarray,
    strain_force_coupling: np.ndarray,
    volume: float,
    *,
    svd_rcond: float = 1.0e-10,
    check_acoustic: bool = False,
    acoustic_tolerance: float = 1.0e-10,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return relaxed-ion ``C``, ``Lambda`` and the internal correction.

    ``check_acoustic`` is forwarded to :func:`internal_strain_response` so a
    production calculation can require translationally compatible ``Phi`` and
    ``Gamma`` before forming the elastic correction.
    """

    c0 = _finite(clamped_elastic, "clamped_elastic")
    phi = _finite(force_constants, "force_constants")
    gamma = _finite(strain_force_coupling, "strain_force_coupling")
    if c0.shape != (6, 6):
        raise ValueError(f"clamped_elastic must have shape (6, 6); got {c0.shape}")
    if not np.isfinite(volume) or float(volume) <= 0.0:
        raise ValueError("volume must be finite and positive")
    lam = internal_strain_response(
        phi,
        gamma,
        svd_rcond=svd_rcond,
        check_acoustic=check_acoustic,
        acoustic_tolerance=acoustic_tolerance,
    )
    correction = gamma.T @ (-lam) / float(volume)
    return c0 - correction, lam, correction
