from __future__ import annotations

import numpy as np
import pytest

from zstar.v2 import (
    central_difference,
    fit_linear_response,
    internal_strain_response,
    intertwiner_basis,
    intertwining_residual,
    project_intertwiner,
    relaxed_elastic,
    relaxed_piezoelectric,
)


def test_actual_serialized_vectors_are_used_for_central_difference():
    derivative = central_difference(0.24, -0.16, 0.12, -0.08)
    assert np.isclose(derivative, 2.0)
    with pytest.raises(ValueError, match="non-zero"):
        central_difference(1.0, 0.0, 0.1, 0.1)


def test_generic_intertwiner_basis_and_projection():
    rotation = np.diag([1.0, -1.0])
    basis = intertwiner_basis((np.eye(2), rotation), (np.eye(2), rotation))
    assert basis.allowed_rank == 2
    diagonal = np.diag([2.0, 3.0])
    assert intertwining_residual(diagonal, (np.eye(2), rotation), (np.eye(2), rotation)) < 1.0e-12
    projected = project_intertwiner(np.ones((2, 2)), (np.eye(2), rotation), (np.eye(2), rotation))
    np.testing.assert_allclose(projected, np.diag([1.0, 1.0]))


def test_symmetry_constrained_fit_recovers_allowed_response():
    rotation = np.diag([1.0, -1.0])
    basis = intertwiner_basis((np.eye(2), rotation), (np.eye(2), rotation))
    x = np.array([[1.0, 0.0], [0.0, 1.0], [2.0, 3.0], [-1.0, 2.0]])
    expected = np.diag([2.0, -4.0])
    y = x @ expected.T
    result = fit_linear_response(x, y, allowed_basis=basis)
    np.testing.assert_allclose(result.matrix, expected, atol=1.0e-12)
    assert result.complete
    assert result.fit_rank == result.allowed_rank == 2
    assert result.residual_max < 1.0e-12


def test_rank_deficiency_is_reported_instead_of_zero_filling():
    rotation = np.diag([1.0, -1.0])
    basis = intertwiner_basis((np.eye(2), rotation), (np.eye(2), rotation))
    x = np.array([[1.0, 0.0], [2.0, 0.0]])
    y = x @ np.diag([2.0, -4.0]).T
    result = fit_linear_response(x, y, allowed_basis=basis)
    assert result.fit_rank < result.allowed_rank
    assert not result.complete


def test_relaxed_ion_algebra_matches_definitions():
    phi = np.diag(np.arange(1.0, 7.0))
    gamma = np.arange(36.0).reshape(6, 6) / 10.0
    expected_lambda = -np.linalg.pinv(phi) @ gamma
    np.testing.assert_allclose(internal_strain_response(phi, gamma), expected_lambda)

    e0 = np.arange(18.0).reshape(3, 6) / 10.0
    born = np.zeros((2, 3, 3))
    born[0] = np.eye(3)
    born[1] = 2.0 * np.eye(3)
    lam = np.ones((2, 3, 6))
    relaxed, contribution = relaxed_piezoelectric(e0, born, lam, 2.0, charge=1.0)
    expected_contribution = np.einsum("iab,ibm->am", born, lam) / 2.0
    np.testing.assert_allclose(contribution, expected_contribution)
    np.testing.assert_allclose(relaxed, e0 + expected_contribution)

    c0 = np.eye(6) * 10.0
    crel, lam2, correction = relaxed_elastic(c0, phi, gamma, 2.0)
    np.testing.assert_allclose(lam2, expected_lambda)
    expected_correction = gamma.T @ np.linalg.pinv(phi) @ gamma / 2.0
    np.testing.assert_allclose(correction, expected_correction)
    np.testing.assert_allclose(crel, c0 - expected_correction)


def test_algebra_rejects_invalid_shapes_and_volume():
    with pytest.raises(ValueError, match="volume"):
        relaxed_piezoelectric(np.zeros((3, 6)), np.zeros((1, 3, 3)), np.zeros((1, 3, 6)), 0.0)
    with pytest.raises(ValueError, match="square"):
        internal_strain_response(np.zeros((2, 3)), np.zeros((2, 6)))
