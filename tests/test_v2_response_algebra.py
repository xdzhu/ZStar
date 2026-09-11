from __future__ import annotations

import numpy as np
import pytest

from zstar.v2 import (
    central_difference,
    convert_stress_sign,
    fit_elastic_response,
    fit_linear_response,
    fit_piezoelectric_response,
    internal_strain_response,
    intertwiner_basis,
    intertwining_residual,
    project_intertwiner,
    relaxed_elastic,
    relaxed_piezoelectric,
)


def test_stress_sign_conversion_rejects_backend_raw_and_flips_known_signs():
    stress = np.array([[1.0, -2.0], [3.0, 4.0]])
    np.testing.assert_allclose(
        convert_stress_sign(stress, from_sign="compression-positive"), -stress
    )
    np.testing.assert_allclose(
        convert_stress_sign(stress, from_sign="tension-positive"), stress
    )
    with pytest.raises(ValueError, match="unknown stress sign"):
        convert_stress_sign(stress, from_sign="backend-raw")


def test_fit_elastic_response_uses_reference_and_reports_rank():
    strains = np.array(
        [
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.02, 0.0, 0.0, 0.0, 0.0],
            [0.01, 0.02, 0.0, 0.0, 0.0, 0.0],
        ]
    )
    expected = np.diag([100.0, 200.0, 300.0, 40.0, 50.0, 60.0])
    residual_stress = np.array([2.0, -1.0, 0.5, 0.0, 0.0, 0.0])
    observations = residual_stress + strains @ expected.T
    result = fit_elastic_response(
        strains,
        observations,
        reference_stress=residual_stress,
    )
    np.testing.assert_allclose(result.matrix[:2, :2], expected[:2, :2], atol=1.0e-12)
    assert result.input_rank == 2
    assert result.fit_rank == 12
    assert result.allowed_rank == 36
    assert not result.complete
    assert result.residual_max < 1.0e-12


def test_fit_elastic_response_converts_compression_positive_tensor_stress():
    strains = np.array([[0.0] * 6, [0.01, 0.0, 0.0, 0.0, 0.0, 0.0]])
    expected = np.diag([100.0, 80.0, 70.0, 40.0, 50.0, 60.0])
    tension_stress = strains @ expected.T
    compression_positive = -np.asarray(
        [
            np.array(
                [
                    [row[0], row[5], row[4]],
                    [row[5], row[1], row[3]],
                    [row[4], row[3], row[2]],
                ]
            )
            for row in tension_stress
        ]
    )
    result = fit_elastic_response(
        strains,
        compression_positive,
        stress_sign="compression-positive",
    )
    np.testing.assert_allclose(result.matrix[:, 0], expected[:, 0])


def test_fit_piezoelectric_response_requires_branch_matched_si_polarization():
    strains = np.array(
        [
            [0.0] * 6,
            [0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.02, 0.0, 0.0, 0.0, 0.0],
            [0.01, 0.02, 0.0, 0.0, 0.0, 0.0],
        ]
    )
    expected = np.zeros((3, 6))
    expected[0, 0] = 1.2
    expected[1, 1] = -0.7
    expected[2, 0] = 0.3
    reference = np.array([0.4, -0.2, 0.1])
    observations = reference + strains @ expected.T
    result = fit_piezoelectric_response(
        strains,
        observations,
        reference_polarization=reference,
    )
    np.testing.assert_allclose(result.matrix[:, :2], expected[:, :2], atol=1.0e-12)
    assert result.input_rank == 2
    assert result.fit_rank == 6
    assert result.allowed_rank == 18
    assert not result.complete
    assert result.residual_max < 1.0e-12


def test_fit_piezoelectric_response_rejects_invalid_shapes_and_reference():
    with pytest.raises(ValueError, match=r"shape \(samples, 6\)"):
        fit_piezoelectric_response([[0.0] * 5], [[0.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match=r"shape \(samples, 3\)"):
        fit_piezoelectric_response([[0.0] * 6], [[0.0, 0.0]])
    with pytest.raises(ValueError, match="reference_polarization"):
        fit_piezoelectric_response(
            [[0.0] * 6],
            [[0.0, 0.0, 0.0]],
            reference_polarization=[0.0, 0.0],
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
