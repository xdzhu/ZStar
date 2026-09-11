"""Mechanics conventions shared by the draft ZStar v2 response API."""

from __future__ import annotations

from typing import Iterable

import numpy as np


ENGINEERING_VOIGT = ("xx", "yy", "zz", "yz", "xz", "xy")


def _matrix3(value: np.ndarray | Iterable[Iterable[float]], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != (3, 3):
        raise ValueError(f"{name} must have shape (3, 3); got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values")
    return array


def strain_tensor_to_voigt(strain: np.ndarray | Iterable[Iterable[float]]) -> np.ndarray:
    """Return ``(xx, yy, zz, 2yz, 2xz, 2xy)`` engineering strain."""

    tensor = _matrix3(strain, "strain")
    if not np.allclose(tensor, tensor.T, atol=1.0e-12, rtol=0.0):
        raise ValueError("strain tensor must be symmetric")
    return np.array(
        [tensor[0, 0], tensor[1, 1], tensor[2, 2], 2.0 * tensor[1, 2], 2.0 * tensor[0, 2], 2.0 * tensor[0, 1]],
        dtype=float,
    )


def voigt_to_strain_tensor(voigt: Iterable[float]) -> np.ndarray:
    values = np.asarray(tuple(voigt), dtype=float)
    if values.shape != (6,):
        raise ValueError(f"engineering strain Voigt vector must have shape (6,); got {values.shape}")
    if not np.all(np.isfinite(values)):
        raise ValueError("strain Voigt vector contains non-finite values")
    return np.array(
        [
            [values[0], values[5] / 2.0, values[4] / 2.0],
            [values[5] / 2.0, values[1], values[3] / 2.0],
            [values[4] / 2.0, values[3] / 2.0, values[2]],
        ],
        dtype=float,
    )


def stress_tensor_to_voigt(stress: np.ndarray | Iterable[Iterable[float]]) -> np.ndarray:
    """Return stress in the work-conjugate order without shear doubling."""

    tensor = _matrix3(stress, "stress")
    if not np.allclose(tensor, tensor.T, atol=1.0e-12, rtol=0.0):
        raise ValueError("stress tensor must be symmetric")
    return np.array(
        [tensor[0, 0], tensor[1, 1], tensor[2, 2], tensor[1, 2], tensor[0, 2], tensor[0, 1]],
        dtype=float,
    )


def voigt_to_stress_tensor(voigt: Iterable[float]) -> np.ndarray:
    values = np.asarray(tuple(voigt), dtype=float)
    if values.shape != (6,):
        raise ValueError(f"stress Voigt vector must have shape (6,); got {values.shape}")
    if not np.all(np.isfinite(values)):
        raise ValueError("stress Voigt vector contains non-finite values")
    return np.array(
        [
            [values[0], values[5], values[4]],
            [values[5], values[1], values[3]],
            [values[4], values[3], values[2]],
        ],
        dtype=float,
    )


def mechanical_stability(
    elastic: np.ndarray,
    *,
    indices: Iterable[int] | None = None,
    tolerance: float = 1.0e-10,
) -> dict[str, object]:
    """Return eigenvalue/conditioning diagnostics for a C matrix.

    For a 2D material, pass the in-plane Voigt indices explicitly.  No bulk
    stability claim is made for an omitted open-direction subspace.
    """

    matrix = np.asarray(elastic, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"elastic matrix must be square; got {matrix.shape}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("elastic matrix contains non-finite values")
    selected = tuple(range(matrix.shape[0])) if indices is None else tuple(int(i) for i in indices)
    if not selected or any(i < 0 or i >= matrix.shape[0] for i in selected):
        raise ValueError(f"invalid stability indices {selected}")
    submatrix = matrix[np.ix_(selected, selected)]
    symmetric = 0.5 * (submatrix + submatrix.T)
    antisymmetric_max = float(np.max(np.abs(submatrix - submatrix.T)))
    eigenvalues = np.linalg.eigvalsh(symmetric)
    scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
    positive = bool(float(np.min(eigenvalues)) > -float(tolerance) * scale)
    nonzero = np.abs(eigenvalues) > float(tolerance) * scale
    condition = float(np.inf if not np.any(nonzero) else np.max(np.abs(eigenvalues)) / np.min(np.abs(eigenvalues[nonzero])))
    return {
        "indices": list(selected),
        "eigenvalues": eigenvalues,
        "minimum_eigenvalue": float(np.min(eigenvalues)),
        "antisymmetric_max": antisymmetric_max,
        "condition_number": condition,
        "stable_within_tolerance": positive,
        "tolerance": float(tolerance),
    }
