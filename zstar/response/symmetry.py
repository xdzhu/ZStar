"""Representation-level symmetry reduction for arbitrary point/space groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


def _representations(values: Iterable[np.ndarray], name: str) -> tuple[np.ndarray, ...]:
    matrices = tuple(np.asarray(value, dtype=float) for value in values)
    if not matrices:
        raise ValueError(f"{name} must contain at least one group operation")
    dimension = matrices[0].shape
    if len(dimension) != 2 or dimension[0] != dimension[1]:
        raise ValueError(f"{name} matrices must be square; got {dimension}")
    for index, matrix in enumerate(matrices):
        if matrix.shape != dimension:
            raise ValueError(f"{name}[{index}] shape {matrix.shape} differs from {dimension}")
        if not np.all(np.isfinite(matrix)):
            raise ValueError(f"{name}[{index}] contains non-finite values")
    return matrices


@dataclass(frozen=True)
class IntertwinerBasis:
    """Null-space basis for matrices satisfying ``L Din = Dout L``."""

    output_dimension: int
    input_dimension: int
    basis: np.ndarray
    constraint_rank: int
    singular_values: np.ndarray
    tolerance: float

    @property
    def parameter_count(self) -> int:
        return int(self.basis.shape[1])

    @property
    def allowed_rank(self) -> int:
        return self.parameter_count

    def matrix_from_coefficients(self, coefficients: Iterable[float]) -> np.ndarray:
        values = np.asarray(tuple(coefficients), dtype=float)
        if values.shape != (self.parameter_count,):
            raise ValueError(
                f"expected {self.parameter_count} symmetry coefficients; got {values.shape}"
            )
        return np.reshape(self.basis @ values, (self.output_dimension, self.input_dimension), order="F")


def intertwiner_constraint_matrix(
    input_representations: Iterable[np.ndarray],
    output_representations: Iterable[np.ndarray],
) -> np.ndarray:
    """Build the linear constraints on ``vec(L)`` in column-major order."""

    inputs = _representations(input_representations, "input_representations")
    outputs = _representations(output_representations, "output_representations")
    if len(inputs) != len(outputs):
        raise ValueError("input and output representations must have equal operation count")
    input_dimension = inputs[0].shape[0]
    output_dimension = outputs[0].shape[0]
    rows = []
    identity_input = np.eye(input_dimension)
    identity_output = np.eye(output_dimension)
    for din, dout in zip(inputs, outputs):
        rows.append(np.kron(din.T, identity_output) - np.kron(identity_input, dout))
    return np.vstack(rows)


def intertwiner_basis(
    input_representations: Iterable[np.ndarray],
    output_representations: Iterable[np.ndarray],
    *,
    tolerance: float | None = None,
) -> IntertwinerBasis:
    """Return an SVD-stable basis of all symmetry-allowed response matrices."""

    inputs = _representations(input_representations, "input_representations")
    outputs = _representations(output_representations, "output_representations")
    constraints = intertwiner_constraint_matrix(inputs, outputs)
    _u, singular_values, vh = np.linalg.svd(constraints, full_matrices=True)
    scale = float(singular_values[0]) if singular_values.size else 1.0
    cutoff = float(tolerance) if tolerance is not None else max(constraints.shape) * np.finfo(float).eps * max(scale, 1.0)
    rank = int(np.count_nonzero(singular_values > cutoff))
    basis = vh[rank:].T.copy()
    return IntertwinerBasis(
        output_dimension=outputs[0].shape[0],
        input_dimension=inputs[0].shape[0],
        basis=basis,
        constraint_rank=rank,
        singular_values=singular_values,
        tolerance=cutoff,
    )


def project_intertwiner(
    matrix: np.ndarray,
    input_representations: Iterable[np.ndarray],
    output_representations: Iterable[np.ndarray],
) -> np.ndarray:
    """Project an arbitrary response matrix onto the group-allowed subspace."""

    value = np.asarray(matrix, dtype=float)
    inputs = _representations(input_representations, "input_representations")
    outputs = _representations(output_representations, "output_representations")
    if len(inputs) != len(outputs):
        raise ValueError("input and output representations must have equal operation count")
    if value.shape != (outputs[0].shape[0], inputs[0].shape[0]):
        raise ValueError(
            f"matrix shape {value.shape} does not match output/input dimensions "
            f"{outputs[0].shape[0], inputs[0].shape[0]}"
        )
    return sum(dout @ value @ din.T for din, dout in zip(inputs, outputs)) / len(inputs)


def intertwining_residual(
    matrix: np.ndarray,
    input_representations: Iterable[np.ndarray],
    output_representations: Iterable[np.ndarray],
) -> float:
    """Return the maximum Frobenius violation of all intertwining equations."""

    value = np.asarray(matrix, dtype=float)
    inputs = _representations(input_representations, "input_representations")
    outputs = _representations(output_representations, "output_representations")
    if len(inputs) != len(outputs):
        raise ValueError("input and output representations must have equal operation count")
    return float(max(np.linalg.norm(value @ din - dout @ value) for din, dout in zip(inputs, outputs)))
