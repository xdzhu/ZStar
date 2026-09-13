"""Numerical response fitting with actual perturbation vectors and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .mechanical import ENGINEERING_VOIGT, convert_stress_sign, stress_tensor_to_voigt
from .polarization import MatchedPolarizationEnsemble
from .symmetry import IntertwinerBasis
from .units import convert_values


@dataclass(frozen=True)
class LinearFitResult:
    matrix: np.ndarray
    predicted: np.ndarray
    residual: np.ndarray
    input_rank: int
    allowed_rank: int
    fit_rank: int
    singular_values: np.ndarray
    condition_number: float
    residual_max: float
    residual_rms: float
    residual_relative: float
    suggested_input_indices: tuple[int, ...] = ()

    @property
    def complete(self) -> bool:
        return self.fit_rank >= self.allowed_rank


@dataclass(frozen=True)
class ProperPiezoelectricResult:
    """Proper/improper conversion for a symmetrized engineering-Voigt tensor.

    ``improper`` is the direct finite-difference derivative ``dP/deta`` and
    ``correction`` is the geometric term from Vanderbilt's proper response
    relation.  The matrices use polarization-axis by engineering-Voigt-axis
    order and C/m^2.  Keeping the correction separately prevents a proper
    result from being mistaken for the raw finite-difference tensor.
    """

    improper: np.ndarray
    correction: np.ndarray
    proper: np.ndarray
    voigt_convention: tuple[str, ...]

    def __post_init__(self) -> None:
        improper = np.asarray(self.improper, dtype=float)
        correction = np.asarray(self.correction, dtype=float)
        proper = np.asarray(self.proper, dtype=float)
        if improper.shape != (3, 6) or correction.shape != (3, 6) or proper.shape != (3, 6):
            raise ValueError("proper piezoelectric matrices must all have shape (3, 6)")
        if not all(np.all(np.isfinite(value)) for value in (improper, correction, proper)):
            raise ValueError("proper piezoelectric matrices must be finite")
        convention = tuple(str(value) for value in self.voigt_convention)
        if convention != ENGINEERING_VOIGT:
            raise ValueError(
                "proper piezoelectric conversion currently requires engineering Voigt "
                f"convention {ENGINEERING_VOIGT}; got {convention}"
            )
        object.__setattr__(self, "improper", improper)
        object.__setattr__(self, "correction", correction)
        object.__setattr__(self, "proper", proper)
        object.__setattr__(self, "voigt_convention", convention)


@dataclass(frozen=True)
class EnergyElasticFitResult:
    """Quadratic energy fit used as an independent elastic consistency check.

    The fitted model is
    ``E(eta) = E0 + Omega * sigma0 @ eta +
    0.5 * Omega * eta.T @ C @ eta`` where ``eta`` is the engineering-Voigt
    strain vector and the shear stress entries are *not* doubled.  ``elastic``
    is returned in the explicitly requested pressure unit.  The fit does not
    silently identify a rank-deficient strain set as a complete tensor.
    """

    elastic: np.ndarray
    reference_stress: np.ndarray
    reference_energy: float
    predicted_energy: np.ndarray
    residual: np.ndarray
    input_rank: int
    fit_rank: int
    allowed_rank: int
    singular_values: np.ndarray
    condition_number: float
    residual_max: float
    residual_rms: float
    energy_unit: str
    volume_unit: str
    elastic_unit: str

    @property
    def complete(self) -> bool:
        return self.fit_rank >= self.allowed_rank


def _energy_density_unit(energy_unit: str, volume_unit: str) -> str:
    """Canonicalize the limited energy/volume combinations in the v2 table."""

    energy = "".join(str(energy_unit).strip().lower().split())
    energy_label = {
        "ev": "ev",
        "electronvolt": "ev",
        "electronvolts": "ev",
        "j": "j",
        "joule": "j",
        "joules": "j",
    }.get(energy)
    volume = "".join(str(volume_unit).strip().lower().split())
    volume_label = {
        "a^3": "angstrom3",
        "a3": "angstrom3",
        "å^3": "angstrom3",
        "å3": "angstrom3",
        "angstrom^3": "angstrom3",
        "angstrom3": "angstrom3",
        "m^3": "m3",
        "m3": "m3",
    }.get(volume)
    if energy_label is None or volume_label is None:
        raise ValueError("energy_unit must be eV or J and volume_unit must be Angstrom^3 or m^3")
    return f"{energy_label}/{volume_label}"


def _quadratic_energy_design(strains: np.ndarray) -> np.ndarray:
    """Build the intercept/linear/symmetric-quadratic energy design matrix."""

    samples = strains.shape[0]
    pairs = [(left, right) for left in range(6) for right in range(left, 6)]
    design = np.empty((samples, 1 + 6 + len(pairs)), dtype=float)
    design[:, 0] = 1.0
    design[:, 1:7] = strains
    for offset, (left, right) in enumerate(pairs, start=7):
        design[:, offset] = (
            0.5 * strains[:, left] ** 2 if left == right
            else strains[:, left] * strains[:, right]
        )
    return design


def fit_energy_elastic_response(
    actual_strains: Iterable[Iterable[float]],
    energy_observations: Iterable[float],
    *,
    volume: float,
    energy_unit: str = "eV",
    volume_unit: str = "angstrom^3",
    elastic_unit: str = "GPa",
    allowed_basis: IntertwinerBasis | None = None,
    svd_cutoff: float | None = None,
) -> EnergyElasticFitResult:
    """Fit ``C`` from the total-energy curvature in engineering Voigt space.

    This is intentionally independent of :func:`fit_elastic_response`: it
    uses the quadratic energy model and the work-conjugate pairing
    ``sigma_voigt @ eta_engineering``.  The actual serialized strain vectors
    are used verbatim.  When ``allowed_basis`` is supplied, the quadratic
    Hessian is fitted in that symmetry-reduced, major-symmetric space; this is
    required for ensembles that contain only independent strain directions.
    An explicit energy/volume/output-unit triplet is required so an
    eV/Angstrom^3 curvature cannot be mistaken for GPa.
    """

    strains = np.asarray(tuple(tuple(row) for row in actual_strains), dtype=float)
    energies = np.asarray(tuple(energy_observations), dtype=float)
    if strains.ndim != 2 or strains.shape[1] != 6 or strains.shape[0] == 0:
        raise ValueError(f"actual_strains must have shape (samples, 6); got {strains.shape}")
    if energies.shape != (strains.shape[0],):
        raise ValueError(
            "energy_observations must have shape (samples,) matching actual_strains; "
            f"got {energies.shape}"
        )
    if not np.all(np.isfinite(strains)) or not np.all(np.isfinite(energies)):
        raise ValueError("strain and energy observations must be finite")
    if not np.isfinite(volume) or float(volume) <= 0.0:
        raise ValueError("volume must be finite and positive")
    if svd_cutoff is not None and (not np.isfinite(svd_cutoff) or float(svd_cutoff) < 0.0):
        raise ValueError("svd_cutoff must be finite and non-negative")
    density_unit = _energy_density_unit(energy_unit, volume_unit)
    # With a symmetry-complete strain ensemble the full quadratic model has
    # 28 unknowns (six linear stresses plus 21 elastic entries).  A reduced
    # space-group basis is essential when only symmetry-independent strain
    # directions were calculated.  The basis is intersected with thermodynamic
    # major symmetry before it is used as an energy Hessian basis.
    elastic_basis = None
    if allowed_basis is not None:
        elastic_basis = _major_symmetric_basis(allowed_basis)
        if elastic_basis.allowed_rank == 0:
            raise ValueError("allowed_basis has no major-symmetric elastic degrees of freedom")
        quadratic_columns = []
        for index in range(elastic_basis.allowed_rank):
            matrix = elastic_basis.matrix_from_coefficients(
                np.eye(elastic_basis.allowed_rank, dtype=float)[index]
            )
            quadratic_columns.append(0.5 * np.einsum("si,ij,sj->s", strains, matrix, strains))
        design = np.column_stack((np.ones(strains.shape[0]), strains, np.column_stack(quadratic_columns)))
    else:
        design = _quadratic_energy_design(strains)
    u, singular_values, vh = np.linalg.svd(design, full_matrices=False)
    del u, vh
    scale = float(singular_values[0]) if singular_values.size else 0.0
    cutoff = (1.0e-12 if svd_cutoff is None else float(svd_cutoff)) * scale
    input_rank = int(np.count_nonzero(singular_values > cutoff))
    # NumPy's ``rcond`` is relative to the largest singular value; ``cutoff``
    # above is absolute and is used only for the reported rank.
    coefficients, _, _, _ = np.linalg.lstsq(
        design, energies, rcond=(1.0e-12 if svd_cutoff is None else float(svd_cutoff))
    )
    predicted = design @ coefficients
    residual = predicted - energies
    # Coefficients after the intercept and six linear terms are the energy
    # Hessian entries in the same symmetric Voigt convention.  Divide by
    # Omega before converting the energy density.
    if elastic_basis is None:
        curvature = np.zeros((6, 6), dtype=float)
        for coefficient, (left, right) in zip(
            coefficients[7:], ((i, j) for i in range(6) for j in range(i, 6))
        ):
            curvature[left, right] = coefficient
            curvature[right, left] = coefficient
        allowed_rank = 28
        fit_rank = input_rank
    else:
        curvature = sum(
            coefficient * elastic_basis.matrix_from_coefficients(
                np.eye(elastic_basis.allowed_rank, dtype=float)[index]
            )
            for index, coefficient in enumerate(coefficients[7:])
        )
        allowed_rank = elastic_basis.allowed_rank
        quadratic_design = design[:, 7:]
        quadratic_singular_values = np.linalg.svd(quadratic_design, compute_uv=False)
        quadratic_scale = float(quadratic_singular_values[0]) if quadratic_singular_values.size else 0.0
        quadratic_cutoff = (1.0e-12 if svd_cutoff is None else float(svd_cutoff)) * quadratic_scale
        fit_rank = int(np.count_nonzero(quadratic_singular_values > quadratic_cutoff))
    raw = curvature / float(volume)
    elastic = convert_values(raw, density_unit, elastic_unit)
    condition = float(
        np.inf
        if input_rank == 0 or singular_values[input_rank - 1] == 0.0
        else singular_values[0] / singular_values[input_rank - 1]
    )
    return EnergyElasticFitResult(
        elastic=elastic,
        reference_stress=convert_values(coefficients[1:7] / float(volume), density_unit, elastic_unit),
        reference_energy=float(coefficients[0]),
        predicted_energy=predicted,
        residual=residual,
        input_rank=input_rank,
        fit_rank=fit_rank,
        allowed_rank=allowed_rank,
        singular_values=singular_values,
        condition_number=condition,
        residual_max=float(np.max(np.abs(residual))),
        residual_rms=float(np.sqrt(np.mean(residual**2))),
        energy_unit=str(energy_unit),
        volume_unit=str(volume_unit),
        elastic_unit=str(elastic_unit),
    )


def central_difference(
    y_plus: np.ndarray | Iterable[float] | float,
    y_minus: np.ndarray | Iterable[float] | float,
    x_plus: float,
    x_minus: float,
) -> np.ndarray:
    """Compute a finite difference using the serialized perturbation values."""

    denominator = float(x_plus) - float(x_minus)
    if not np.isfinite(denominator) or denominator == 0.0:
        raise ValueError("central-difference denominator must be finite and non-zero")
    plus = np.asarray(y_plus, dtype=float)
    minus = np.asarray(y_minus, dtype=float)
    if plus.shape != minus.shape:
        raise ValueError(f"finite-difference observations have shapes {plus.shape} and {minus.shape}")
    if not np.all(np.isfinite(plus)) or not np.all(np.isfinite(minus)):
        raise ValueError("finite-difference observations must be finite")
    return (plus - minus) / denominator


def proper_piezoelectric_response(
    improper: np.ndarray | Iterable[Iterable[float]],
    polarization: np.ndarray | Iterable[float],
    *,
    voigt_convention: Iterable[str] = ENGINEERING_VOIGT,
) -> ProperPiezoelectricResult:
    """Apply the proper-piezoelectric geometric correction.

    Vanderbilt's Cartesian relation is
    ``c_proper[i,j,k] = c_improper[i,j,k] + delta[j,k] P[i]
    - delta[i,j] P[k]``.  For the symmetric engineering shear columns used by
    v2, the ``yz``, ``xz`` and ``xy`` corrections are the average of the two
    Cartesian index orderings, hence the factor one-half.  ``polarization``
    must be the branch-matched reference value in C/m^2.  This function does
    not choose a Berry branch and does not alter the raw fit.
    """

    raw = np.asarray(improper, dtype=float)
    p = np.asarray(polarization, dtype=float)
    convention = tuple(str(value) for value in voigt_convention)
    if raw.shape != (3, 6):
        raise ValueError(f"improper piezoelectric tensor must have shape (3, 6); got {raw.shape}")
    if p.shape != (3,):
        raise ValueError(f"polarization must have shape (3,); got {p.shape}")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(p)):
        raise ValueError("improper piezoelectric tensor and polarization must be finite")
    if convention != ENGINEERING_VOIGT:
        raise ValueError(
            "proper piezoelectric conversion currently requires engineering Voigt "
            f"convention {ENGINEERING_VOIGT}; got {convention}"
        )

    correction = np.zeros((3, 6), dtype=float)
    # Normal columns: delta_jk P_i - delta_ij P_k, with j=k.
    for axis in range(3):
        correction[:, axis] = p
        correction[axis, axis] -= p[axis]
    # Engineering shear columns are eta_4=2 eps_yz, eta_5=2 eps_xz,
    # eta_6=2 eps_xy; symmetrize the Cartesian correction in each pair.
    for column, first, second in ((3, 1, 2), (4, 0, 2), (5, 0, 1)):
        correction[first, column] -= 0.5 * p[second]
        correction[second, column] -= 0.5 * p[first]
    return ProperPiezoelectricResult(
        improper=raw,
        correction=correction,
        proper=raw + correction,
        voigt_convention=convention,
    )


def _design_matrix(actual_vectors: np.ndarray, output_dimension: int) -> np.ndarray:
    samples, input_dimension = actual_vectors.shape
    design = np.zeros((samples * output_dimension, input_dimension * output_dimension), dtype=float)
    for sample, vector in enumerate(actual_vectors):
        for output in range(output_dimension):
            row = sample * output_dimension + output
            for input_index, value in enumerate(vector):
                design[row, output + output_dimension * input_index] = value
    return design


def fit_linear_response(
    actual_vectors: Iterable[Iterable[float]],
    observations: Iterable[Iterable[float]],
    *,
    allowed_basis: IntertwinerBasis | None = None,
    sample_weights: Iterable[float] | None = None,
    svd_cutoff: float | None = None,
) -> LinearFitResult:
    """Fit ``Y = X @ J.T`` and optionally constrain ``J`` by symmetry.

    ``actual_vectors`` must contain the vectors read from generated structures,
    not nominal requested step sizes.  The returned matrix uses output-axis by
    input-axis order, matching the response schema convention.
    """

    x = np.asarray(tuple(tuple(row) for row in actual_vectors), dtype=float)
    y = np.asarray(tuple(tuple(row) for row in observations), dtype=float)
    if x.ndim != 2 or y.ndim != 2:
        raise ValueError("actual_vectors and observations must be two-dimensional")
    if x.shape[0] != y.shape[0]:
        raise ValueError(f"sample counts differ: {x.shape[0]} and {y.shape[0]}")
    if x.shape[0] == 0 or x.shape[1] == 0 or y.shape[1] == 0:
        raise ValueError("response fit requires non-empty input and output dimensions")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("response fit inputs must be finite")
    samples, input_dimension = x.shape
    output_dimension = y.shape[1]
    design = _design_matrix(x, output_dimension)
    target = y.reshape(-1)
    if sample_weights is None:
        weights = np.ones(samples, dtype=float)
    else:
        weights = np.asarray(tuple(sample_weights), dtype=float)
        if weights.shape != (samples,) or not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
            raise ValueError("sample_weights must be finite, positive and match the sample count")
    row_weights = np.repeat(np.sqrt(weights), output_dimension)
    weighted_design = design * row_weights[:, None]
    weighted_target = target * row_weights
    input_singular_values = np.linalg.svd(x, compute_uv=False)
    input_rank = int(np.linalg.matrix_rank(x))

    if allowed_basis is None:
        basis = np.eye(input_dimension * output_dimension)
        allowed_rank = basis.shape[1]
    else:
        if allowed_basis.input_dimension != input_dimension or allowed_basis.output_dimension != output_dimension:
            raise ValueError("symmetry basis dimensions do not match response data")
        basis = np.asarray(allowed_basis.basis, dtype=float)
        allowed_rank = int(basis.shape[1])
    constrained_design = weighted_design @ basis
    singular_values = np.linalg.svd(constrained_design, compute_uv=False)
    scale = float(singular_values[0]) if singular_values.size else 0.0
    cutoff = float(svd_cutoff) if svd_cutoff is not None else max(constrained_design.shape) * np.finfo(float).eps * max(scale, 1.0)
    fit_rank = int(np.count_nonzero(singular_values > cutoff))
    coefficients, *_ = np.linalg.lstsq(constrained_design, weighted_target, rcond=cutoff)
    flat_matrix = basis @ coefficients
    matrix = np.reshape(flat_matrix, (output_dimension, input_dimension), order="F")
    predicted = x @ matrix.T
    residual = predicted - y
    residual_norm = float(np.linalg.norm(residual))
    target_norm = float(np.linalg.norm(y))
    residual_max = float(np.max(np.abs(residual)))
    residual_rms = float(np.sqrt(np.mean(residual**2)))
    residual_relative = residual_norm / target_norm if target_norm > 0.0 else residual_norm
    nonzero = singular_values > cutoff
    condition = float(
        np.inf
        if not np.any(nonzero)
        else singular_values[0] / singular_values[np.flatnonzero(nonzero)[-1]]
    )
    suggested: list[int] = []
    if fit_rank < allowed_rank:
        # Recommend canonical input directions that increase the constrained
        # design rank.  This is a diagnostic only: no missing observation is
        # synthesized and callers must generate both signs themselves.
        candidate_design = np.array(constrained_design, copy=True)
        candidate_rank = fit_rank
        for index in range(input_dimension):
            direction = np.eye(input_dimension, dtype=float)[index]
            block = _design_matrix(direction[None, :], output_dimension) @ basis
            trial = np.vstack([candidate_design, block])
            trial_rank = int(np.linalg.matrix_rank(trial, tol=cutoff))
            if trial_rank > candidate_rank:
                suggested.append(index)
                candidate_design = trial
                candidate_rank = trial_rank
            if candidate_rank >= allowed_rank:
                break
    return LinearFitResult(
        matrix=matrix,
        predicted=predicted,
        residual=residual,
        input_rank=input_rank,
        allowed_rank=allowed_rank,
        fit_rank=fit_rank,
        singular_values=singular_values,
        condition_number=condition,
        residual_max=residual_max,
        residual_rms=residual_rms,
        residual_relative=residual_relative,
        suggested_input_indices=tuple(suggested),
    )


def _stress_observations_to_voigt(observations: np.ndarray | Iterable[object]) -> np.ndarray:
    values = np.asarray(observations, dtype=float)
    if values.ndim == 3 and values.shape[1:] == (3, 3):
        return np.asarray([stress_tensor_to_voigt(value) for value in values], dtype=float)
    if values.ndim == 2 and values.shape[1] == 6:
        return values
    raise ValueError(
        "stress observations must have shape (samples, 3, 3) or (samples, 6); "
        f"got {values.shape}"
    )


def _major_symmetric_basis(allowed_basis: IntertwinerBasis | None) -> IntertwinerBasis:
    """Intersect an optional symmetry basis with the elastic major-symmetry subspace."""

    if allowed_basis is None:
        base = np.eye(36, dtype=float)
    else:
        if allowed_basis.input_dimension != 6 or allowed_basis.output_dimension != 6:
            raise ValueError("elastic symmetry basis must describe a 6x6 response")
        base = np.asarray(allowed_basis.basis, dtype=float)
    constraints = np.zeros((15, 36), dtype=float)
    row = 0
    for first in range(6):
        for second in range(first + 1, 6):
            constraints[row, first + 6 * second] = 1.0
            constraints[row, second + 6 * first] = -1.0
            row += 1
    projected = constraints @ base
    _u, singular_values, vh = np.linalg.svd(projected, full_matrices=True)
    scale = float(singular_values[0]) if singular_values.size else 1.0
    # Space-group rotations obtained from spglib are floating-point matrices.
    # A constitutive basis that is analytically major-symmetric can therefore
    # leave O(1e-11) antisymmetric noise after the intertwiner SVD.  Using only
    # machine epsilon here incorrectly collapses cubic/tetragonal bases (for
    # example, a cubic 3-parameter basis became rank one).  Keep the strict
    # machine-precision cutoff for an unconstrained basis, but allow a small,
    # explicit numerical symmetry tolerance when intersecting a supplied
    # space-group basis; genuine violations are O(1) and remain visible.
    numerical_symmetry_tolerance = 1.0e-10 if allowed_basis is not None else 0.0
    cutoff = max(
        max(projected.shape) * np.finfo(float).eps * max(scale, 1.0),
        numerical_symmetry_tolerance,
    )
    rank = int(np.count_nonzero(singular_values > cutoff))
    null_coefficients = vh[rank:].T.copy()
    symmetric_basis = base @ null_coefficients
    original_constraint_rank = 36 - int(base.shape[1])
    return IntertwinerBasis(
        output_dimension=6,
        input_dimension=6,
        basis=symmetric_basis,
        constraint_rank=original_constraint_rank + rank,
        singular_values=singular_values,
        tolerance=cutoff,
    )


def fit_elastic_response(
    actual_strains: Iterable[Iterable[float]],
    stress_observations: np.ndarray | Iterable[object],
    *,
    reference_stress: np.ndarray | Iterable[float] | None = None,
    stress_sign: str = "tension-positive",
    allowed_basis: IntertwinerBasis | None = None,
    enforce_major_symmetry: bool = False,
    sample_weights: Iterable[float] | None = None,
    svd_cutoff: float | None = None,
) -> LinearFitResult:
    """Fit ``Δσ = C η`` with explicit stress-sign and rank diagnostics.

    Strain rows must be the actual serialized engineering-Voigt vectors from
    generated structures.  Stress may be supplied as symmetric 3x3 tensors
    or work-conjugate six-vectors.  ``backend-raw`` is rejected until the
    backend convention has been independently established.  If a reference
    stress is supplied it is subtracted before fitting, which avoids treating
    residual hydrostatic stress as an elastic response.  Set
    ``enforce_major_symmetry=True`` to intersect the space-group basis with
    the thermodynamic constraint ``C == C.T``; the default keeps the raw
    representation fit explicit for auditing.
    """

    strains = np.asarray(tuple(tuple(row) for row in actual_strains), dtype=float)
    stresses = _stress_observations_to_voigt(stress_observations)
    if strains.ndim != 2 or strains.shape[1] != 6:
        raise ValueError(f"actual_strains must have shape (samples, 6); got {strains.shape}")
    if strains.shape[0] != stresses.shape[0]:
        raise ValueError(
            f"strain/stress sample counts differ: {strains.shape[0]} and {stresses.shape[0]}"
        )
    reference = np.zeros(6, dtype=float) if reference_stress is None else np.asarray(reference_stress, dtype=float)
    if reference.shape == (3, 3):
        reference = stress_tensor_to_voigt(reference)
    if reference.shape != (6,) or not np.all(np.isfinite(reference)):
        raise ValueError("reference_stress must have shape (6,) or (3, 3) and be finite")
    converted = convert_stress_sign(stresses - reference, from_sign=stress_sign)
    if not isinstance(enforce_major_symmetry, bool):
        raise TypeError("enforce_major_symmetry must be a bool")
    fit_basis = _major_symmetric_basis(allowed_basis) if enforce_major_symmetry else allowed_basis
    return fit_linear_response(
        strains,
        converted,
        allowed_basis=fit_basis,
        sample_weights=sample_weights,
        svd_cutoff=svd_cutoff,
    )


def fit_strain_force_coupling(
    actual_strains: Iterable[Iterable[float]],
    force_observations: np.ndarray | Iterable[object],
    *,
    reference_forces: np.ndarray | Iterable[float] | None = None,
    allowed_basis: IntertwinerBasis | None = None,
    sample_weights: Iterable[float] | None = None,
    svd_cutoff: float | None = None,
) -> LinearFitResult:
    """Fit ``Gamma = -dF/deta`` from fixed-ion strain force observations.

    ``force_observations`` may have shape ``(samples, atoms, 3)`` or a
    flattened ``(samples, 3*atoms)`` representation.  The sign follows
    ``F = -dE/du`` and therefore the fitted matrix is the energy Hessian
    coupling ``Gamma = d^2E/(du deta)``.  For a nonzero residual reference
    force, pass the force vector from the zero-strain geometry explicitly;
    omitting it assumes the observations have already been reference-
    subtracted.  The returned numeric unit is the force unit of the input
    observations (per unit engineering strain).
    """

    strains = np.asarray(tuple(tuple(row) for row in actual_strains), dtype=float)
    forces = np.asarray(force_observations, dtype=float)
    if forces.ndim == 3 and forces.shape[-1] == 3 and forces.shape[-2] > 0:
        forces = forces.reshape(forces.shape[0], -1)
    if forces.ndim != 2 or forces.shape[0] == 0 or forces.shape[1] == 0:
        raise ValueError(
            "force_observations must have shape (samples, atoms, 3) or "
            f"(samples, 3*atoms); got {forces.shape}"
        )
    if strains.ndim != 2 or strains.shape[1] != 6:
        raise ValueError(f"actual_strains must have shape (samples, 6); got {strains.shape}")
    if strains.shape[0] != forces.shape[0]:
        raise ValueError(
            f"strain/force sample counts differ: {strains.shape[0]} and {forces.shape[0]}"
        )
    if not np.all(np.isfinite(strains)) or not np.all(np.isfinite(forces)):
        raise ValueError("strain and force observations must be finite")
    reference = (
        np.zeros(forces.shape[1], dtype=float)
        if reference_forces is None
        else np.asarray(reference_forces, dtype=float)
    )
    if reference.ndim == 2 and reference.shape[-1] == 3:
        reference = reference.reshape(-1)
    if reference.shape != (forces.shape[1],) or not np.all(np.isfinite(reference)):
        raise ValueError(
            "reference_forces must have shape (3*atoms,) or (atoms, 3) and be finite"
        )
    return fit_linear_response(
        strains,
        -(forces - reference),
        allowed_basis=allowed_basis,
        sample_weights=sample_weights,
        svd_cutoff=svd_cutoff,
    )


def fit_piezoelectric_response(
    actual_strains: Iterable[Iterable[float]],
    polarization_observations: np.ndarray | Iterable[object],
    *,
    reference_polarization: np.ndarray | Iterable[float] | None = None,
    allowed_basis: IntertwinerBasis | None = None,
    sample_weights: Iterable[float] | None = None,
    svd_cutoff: float | None = None,
) -> LinearFitResult:
    """Fit a branch-matched polarization response ``ΔP = e η``.

    ``polarization_observations`` must already be expressed in one continuous
    Berry branch and in C/m².  Branch matching is deliberately kept separate
    from this numerical fit; wrapped values or mixed units must not be passed
    here.  The returned matrix has polarization-axis by engineering-Voigt-axis
    order.  This draft reports the direct derivative only; it does not apply
    the proper/improper geometric correction or claim a relaxed-ion result.
    """

    strains = np.asarray(tuple(tuple(row) for row in actual_strains), dtype=float)
    polarizations = np.asarray(tuple(tuple(row) for row in polarization_observations), dtype=float)
    if strains.ndim != 2 or strains.shape[1] != 6:
        raise ValueError(f"actual_strains must have shape (samples, 6); got {strains.shape}")
    if polarizations.ndim != 2 or polarizations.shape[1] != 3:
        raise ValueError(
            "polarization_observations must have shape (samples, 3); "
            f"got {polarizations.shape}"
        )
    if strains.shape[0] != polarizations.shape[0]:
        raise ValueError(
            "strain/polarization sample counts differ: "
            f"{strains.shape[0]} and {polarizations.shape[0]}"
        )
    reference = (
        np.zeros(3, dtype=float)
        if reference_polarization is None
        else np.asarray(reference_polarization, dtype=float)
    )
    if reference.shape != (3,) or not np.all(np.isfinite(reference)):
        raise ValueError("reference_polarization must have shape (3,) and be finite")
    if not np.all(np.isfinite(strains)) or not np.all(np.isfinite(polarizations)):
        raise ValueError("strain and polarization observations must be finite")
    return fit_linear_response(
        strains,
        polarizations - reference,
        allowed_basis=allowed_basis,
        sample_weights=sample_weights,
        svd_cutoff=svd_cutoff,
    )


def fit_internal_strain_response(
    actual_strains: Iterable[Iterable[float]],
    displacement_observations: np.ndarray | Iterable[object],
    *,
    reference_displacement: np.ndarray | Iterable[float] | None = None,
    allowed_basis: IntertwinerBasis | None = None,
    sample_weights: Iterable[float] | None = None,
    svd_cutoff: float | None = None,
) -> LinearFitResult:
    """Fit ``Delta u = Lambda eta`` from fixed-cell relaxed structures.

    ``displacement_observations`` has shape ``(samples, atoms, 3)`` and must
    contain Cartesian displacements of the relaxed ions relative to the
    clamped strained structures.  The returned :class:`LinearFitResult` uses
    flattened ``(atom, cartesian)`` output rows; reshape its ``matrix`` to
    ``(atoms, 3, 6)`` for the tensor convention of the v2 response schema.
    An optional ``allowed_basis`` constrains the flattened displacement output
    to a validated space-group intertwiner subspace.
    No acoustic gauge is silently imposed: translation removal or a specified
    gauge must be performed explicitly before using ``Lambda`` in the relaxed
    piezoelectric/elastic algebra.
    """

    strains = np.asarray(tuple(tuple(row) for row in actual_strains), dtype=float)
    displacements = np.asarray(displacement_observations, dtype=float)
    if strains.ndim != 2 or strains.shape[1] != 6:
        raise ValueError(f"actual_strains must have shape (samples, 6); got {strains.shape}")
    if displacements.ndim != 3 or displacements.shape[0] != strains.shape[0] or displacements.shape[2] != 3:
        raise ValueError(
            "displacement_observations must have shape (samples, atoms, 3) matching actual_strains; "
            f"got {displacements.shape}"
        )
    if not np.all(np.isfinite(strains)) or not np.all(np.isfinite(displacements)):
        raise ValueError("strain and displacement observations must be finite")
    reference = np.zeros(displacements.shape[1:], dtype=float) if reference_displacement is None else np.asarray(
        reference_displacement, dtype=float
    )
    if reference.shape != displacements.shape[1:] or not np.all(np.isfinite(reference)):
        raise ValueError(
            "reference_displacement must have shape (atoms, 3) and be finite; "
            f"got {reference.shape}"
        )
    return fit_linear_response(
        strains,
        (displacements - reference).reshape(displacements.shape[0], -1),
        allowed_basis=allowed_basis,
        sample_weights=sample_weights,
        svd_cutoff=svd_cutoff,
    )


def fit_piezoelectric_ensemble(
    ensemble: MatchedPolarizationEnsemble,
    *,
    reference_strain_tolerance: float = 1.0e-12,
    residual_tolerance: float | None = None,
    allowed_basis: IntertwinerBasis | None = None,
    sample_weights: Iterable[float] | None = None,
    svd_cutoff: float | None = None,
) -> LinearFitResult:
    """Fit ``e`` directly from a reference-matched polarization ensemble.

    The selected reference stage must represent zero strain within
    ``reference_strain_tolerance`` because this draft fit has no intercept.
    ``residual_tolerance`` is an explicit guard against fitting a branch jump or
    an inconsistent Cartesian transformation as if it were a linear response.
    """

    if not isinstance(ensemble, MatchedPolarizationEnsemble):
        raise TypeError("ensemble must be a MatchedPolarizationEnsemble")
    tolerance = float(reference_strain_tolerance)
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("reference_strain_tolerance must be finite and non-negative")
    if np.linalg.norm(ensemble.actual_strains[ensemble.reference_index]) > tolerance:
        raise ValueError(
            "reference stage strain is not zero within reference_strain_tolerance; "
            "fit a path with a zero-strain reference or use an intercept-aware model"
        )
    if residual_tolerance is not None:
        limit = float(residual_tolerance)
        if not np.isfinite(limit) or limit < 0.0:
            raise ValueError("residual_tolerance must be finite and non-negative")
        if np.any(ensemble.residuals > limit):
            raise ValueError(
                "polarization ensemble residual exceeds residual_tolerance; "
                "inspect branch matching before fitting"
            )
    reference = ensemble.matched_values[ensemble.reference_index]
    return fit_piezoelectric_response(
        ensemble.actual_strains,
        ensemble.matched_values,
        reference_polarization=reference,
        allowed_basis=allowed_basis,
        sample_weights=sample_weights,
        svd_cutoff=svd_cutoff,
    )
