"""Numerical response fitting with actual perturbation vectors and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .mechanical import convert_stress_sign, stress_tensor_to_voigt
from .symmetry import IntertwinerBasis


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

    @property
    def complete(self) -> bool:
        return self.fit_rank >= self.allowed_rank


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


def fit_elastic_response(
    actual_strains: Iterable[Iterable[float]],
    stress_observations: np.ndarray | Iterable[object],
    *,
    reference_stress: np.ndarray | Iterable[float] | None = None,
    stress_sign: str = "tension-positive",
    allowed_basis: IntertwinerBasis | None = None,
    sample_weights: Iterable[float] | None = None,
    svd_cutoff: float | None = None,
) -> LinearFitResult:
    """Fit ``Δσ = C η`` with explicit stress-sign and rank diagnostics.

    Strain rows must be the actual serialized engineering-Voigt vectors from
    generated structures.  Stress may be supplied as symmetric 3x3 tensors
    or work-conjugate six-vectors.  ``backend-raw`` is rejected until the
    backend convention has been independently established.  If a reference
    stress is supplied it is subtracted before fitting, which avoids treating
    residual hydrostatic stress as an elastic response.
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
    return fit_linear_response(
        strains,
        converted,
        allowed_basis=allowed_basis,
        sample_weights=sample_weights,
        svd_cutoff=svd_cutoff,
    )
