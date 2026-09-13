"""Analytic response relations used before calculator-backed implementation."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class InternalStrainSolution:
    """Audited solution of ``Phi @ Lambda + Gamma = 0``.

    ``lambda_response`` is the minimum-norm Cartesian response.  The other
    fields are deliberately retained instead of being hidden behind a
    pseudoinverse: a small residual can be numerical noise, while a large one
    means that the supplied ``Phi``/``Gamma`` pair is not a realizable relaxed
    equilibrium response (for example because of an atom-order or boundary
    mismatch).
    """

    lambda_response: np.ndarray
    equilibrium_residual: np.ndarray
    translation_gauge_residual: np.ndarray
    singular_values: np.ndarray
    rank: int
    residual_max: float
    residual_rms: float
    residual_relative: float
    translation_gauge_max: float
    svd_rcond: float

    def __post_init__(self) -> None:
        for name in (
            "lambda_response",
            "equilibrium_residual",
            "translation_gauge_residual",
            "singular_values",
        ):
            value = np.asarray(getattr(self, name), dtype=float)
            if not np.all(np.isfinite(value)):
                raise ValueError(f"{name} contains non-finite values")
            object.__setattr__(self, name, value)
        if int(self.rank) < 0:
            raise ValueError("rank must be non-negative")
        for name in (
            "residual_max",
            "residual_rms",
            "residual_relative",
            "translation_gauge_max",
            "svd_rcond",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
            object.__setattr__(self, name, value)


def solve_internal_strain_response(
    force_constants: np.ndarray,
    strain_force_coupling: np.ndarray,
    *,
    svd_rcond: float = 1.0e-10,
    check_acoustic: bool = False,
    acoustic_tolerance: float = 1.0e-10,
    residual_tolerance: float | None = None,
) -> InternalStrainSolution:
    """Solve and audit the internal-strain equilibrium equation.

    The equation is ``Phi @ Lambda + Gamma = 0`` with the convention used by
    :func:`fit_strain_force_coupling`, namely ``Gamma = -dF/deta``.  The
    Moore--Penrose solution is used only after validating the shapes.  Unlike
    :func:`internal_strain_response`, this function exposes the equilibrium
    residual and the translation gauge so a caller can impose a production
    acceptance threshold.  ``check_acoustic`` rejects violated translational
    sum rules; ``residual_tolerance`` additionally rejects an incompatible
    non-translational null-space component.
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
        raise ValueError(
            f"strain_force_coupling must have shape ({phi.shape[0]}, nstrain); "
            f"got {gamma.shape}"
        )
    if not np.isfinite(svd_rcond) or float(svd_rcond) < 0.0:
        raise ValueError("svd_rcond must be finite and non-negative")
    if residual_tolerance is not None and (
        not np.isfinite(residual_tolerance) or float(residual_tolerance) < 0.0
    ):
        raise ValueError("residual_tolerance must be finite and non-negative")

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

    # Keep the SVD here so the reported rank is tied to exactly the inverse
    # used for Lambda, rather than inferred from a second decomposition.
    u, singular_values, vh = np.linalg.svd(phi, full_matrices=False)
    del u, vh  # the singular vectors are not part of the public diagnostic
    if singular_values.size:
        cutoff = float(svd_rcond) * float(singular_values[0])
    else:  # guarded above, retained for defensive clarity
        cutoff = 0.0
    rank = int(np.count_nonzero(singular_values > cutoff))
    inverse = np.linalg.pinv(phi, rcond=float(svd_rcond))
    lambda_response = -inverse @ gamma
    equilibrium_residual = phi @ lambda_response + gamma
    residual_abs = np.abs(equilibrium_residual)
    residual_max = float(np.max(residual_abs)) if residual_abs.size else 0.0
    residual_rms = float(np.sqrt(np.mean(equilibrium_residual**2))) if equilibrium_residual.size else 0.0
    gamma_scale = max(float(np.linalg.norm(gamma, ord=2)), 1.0)
    residual_relative = residual_rms / gamma_scale
    translations = _acoustic_translation_basis(phi.shape[0] // 3)
    translation_gauge_residual = translations.T @ lambda_response
    translation_gauge_max = (
        float(np.max(np.abs(translation_gauge_residual)))
        if translation_gauge_residual.size
        else 0.0
    )
    solution = InternalStrainSolution(
        lambda_response=lambda_response,
        equilibrium_residual=equilibrium_residual,
        translation_gauge_residual=translation_gauge_residual,
        singular_values=singular_values,
        rank=rank,
        residual_max=residual_max,
        residual_rms=residual_rms,
        residual_relative=float(residual_relative),
        translation_gauge_max=translation_gauge_max,
        svd_rcond=float(svd_rcond),
    )
    if residual_tolerance is not None and solution.residual_relative > float(residual_tolerance):
        raise ValueError(
            "internal-strain equilibrium residual exceeds residual_tolerance; "
            f"got relative residual {solution.residual_relative:.6g} > "
            f"{float(residual_tolerance):.6g}; inspect Gamma/Phi axes, units, "
            "and non-translational zero modes"
        )
    return solution


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

    if not isinstance(check_acoustic, (bool, np.bool_)):
        raise TypeError("check_acoustic must be a bool")
    return solve_internal_strain_response(
        force_constants,
        strain_force_coupling,
        svd_rcond=svd_rcond,
        check_acoustic=check_acoustic,
        acoustic_tolerance=acoustic_tolerance,
    ).lambda_response


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
    energy_unit: str | None = None,
    length_unit: str | None = None,
    volume_unit: str | None = None,
    elastic_unit: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return relaxed-ion ``C``, ``Lambda`` and the internal correction.

    ``check_acoustic`` is forwarded to :func:`internal_strain_response` so a
    production calculation can require translationally compatible ``Phi`` and
    ``Gamma`` before forming the elastic correction.  The legacy call without
    unit keywords returns the raw algebraic correction for synthetic tests.
    For calculator data, provide all four unit keywords: ``force_constants``
    are then interpreted as energy/length^2, ``strain_force_coupling`` as
    energy/length, ``volume`` in the declared volume unit, and ``clamped_elastic``
    and the returned correction in ``elastic_unit``.  This explicit mode
    converts eV/Angstrom^3 to Pa/GPa/kbar and never guesses units.
    """

    c0 = _finite(clamped_elastic, "clamped_elastic")
    phi = _finite(force_constants, "force_constants")
    gamma = _finite(strain_force_coupling, "strain_force_coupling")
    if c0.shape != (6, 6):
        raise ValueError(f"clamped_elastic must have shape (6, 6); got {c0.shape}")
    if not np.isfinite(volume) or float(volume) <= 0.0:
        raise ValueError("volume must be finite and positive")
    unit_values = (energy_unit, length_unit, volume_unit, elastic_unit)
    if any(value is not None for value in unit_values) and not all(value is not None for value in unit_values):
        raise ValueError(
            "energy_unit, length_unit, volume_unit and elastic_unit must be provided together"
        )
    lam = internal_strain_response(
        phi,
        gamma,
        svd_rcond=svd_rcond,
        check_acoustic=check_acoustic,
        acoustic_tolerance=acoustic_tolerance,
    )
    correction_raw = gamma.T @ (-lam) / float(volume)
    if all(value is not None for value in unit_values):
        energy_name = "".join(str(energy_unit).strip().lower().split())
        energy_aliases = {
            "ev": "ev",
            "electronvolt": "ev",
            "electronvolts": "ev",
            "j": "j",
            "joule": "j",
            "joules": "j",
        }
        energy_label = energy_aliases.get(energy_name)
        if energy_label is None:
            raise ValueError("energy_unit must be eV or J in unit-aware relaxed_elastic mode")
        length_name = "".join(str(length_unit).strip().lower().split())
        length_aliases = {
            "a": "angstrom",
            "å": "angstrom",
            "angstrom": "angstrom",
            "angstroms": "angstrom",
            "m": "m",
            "meter": "m",
            "meters": "m",
            "metre": "m",
            "metres": "m",
        }
        length_label = length_aliases.get(length_name)
        if length_label is None:
            raise ValueError("length_unit must be Angstrom or m in unit-aware relaxed_elastic mode")
        volume_name = "".join(str(volume_unit).strip().lower().split())
        volume_aliases = {
            "a^3": "angstrom3",
            "a3": "angstrom3",
            "å^3": "angstrom3",
            "å3": "angstrom3",
            "angstrom^3": "angstrom3",
            "angstrom3": "angstrom3",
            "m^3": "m3",
            "m3": "m3",
        }
        volume_label = volume_aliases.get(volume_name)
        expected_volume = "angstrom3" if length_label == "angstrom" else "m3"
        if volume_label != expected_volume:
            raise ValueError(
                f"volume_unit {volume_unit!r} must be the cube of length_unit {length_unit!r}"
            )
        # The raw correction is divided by a volume expressed in the same
        # length basis as Phi/Gamma.  Convert only the final energy density.
        density_unit = f"{energy_label}/{length_label}^3"
        try:
            correction = convert_values(correction_raw, density_unit, str(elastic_unit))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "elastic_unit must be a supported pressure unit (Pa, GPa or kbar)"
            ) from exc
    else:
        correction = correction_raw
    return c0 - correction, lam, correction
