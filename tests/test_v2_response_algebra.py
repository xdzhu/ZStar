from __future__ import annotations

import numpy as np
import pytest

from zstar.v2 import (
    acoustic_sum_rule_diagnostics,
    central_difference,
    convert_stress_sign,
    fit_elastic_response,
    fit_energy_elastic_response,
    fit_strain_force_coupling,
    fit_internal_strain_response,
    fit_linear_response,
    fit_piezoelectric_ensemble,
    fit_piezoelectric_response,
    fit_proper_piezoelectric_response,
    internal_strain_response,
    intertwiner_basis,
    intertwining_residual,
    project_intertwiner,
    proper_piezoelectric_response,
    relaxed_elastic,
    relaxed_piezoelectric,
    remove_acoustic_translation,
    solve_internal_strain_response,
    match_polarization_ensemble,
)
from zstar.v2.structure import StructureSpec, allowed_response_basis, analyze_space_group


def test_remove_acoustic_translation_requires_explicit_positive_gauge_weights():
    displacements = np.array(
        [
            [[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]],
            [[-2.0, 0.0, 2.0], [0.0, 2.0, 4.0]],
        ]
    )
    fixed = remove_acoustic_translation(displacements)
    np.testing.assert_allclose(fixed.mean(axis=-2), 0.0)
    weighted = remove_acoustic_translation(displacements[0], weights=[1.0, 3.0])
    np.testing.assert_allclose(np.average(weighted, axis=0, weights=[1.0, 3.0]), 0.0)
    with pytest.raises(ValueError, match="positive"):
        remove_acoustic_translation(displacements[0], weights=[1.0, 0.0])


def test_acoustic_sum_rule_diagnostics_reports_translation_compatible_inputs():
    phi = np.kron(np.array([[1.0, -1.0], [-1.0, 1.0]]), np.eye(3))
    gamma = np.array(
        [
            [1.0, 0.2], [0.0, 0.1], [0.3, 0.4],
            [-1.0, -0.2], [0.0, -0.1], [-0.3, -0.4],
        ]
    )
    diagnostics = acoustic_sum_rule_diagnostics(phi, gamma, tolerance=1.0e-12)
    assert diagnostics["natoms"] == 2
    assert diagnostics["compatible"] is True
    assert diagnostics["force_constants_translation_residual_max"] < 1.0e-12
    assert diagnostics["strain_force_translation_residual_max"] < 1.0e-12
    lam = internal_strain_response(
        phi, gamma, check_acoustic=True, acoustic_tolerance=1.0e-12
    )
    translations = np.asarray(diagnostics["translation_basis"])
    np.testing.assert_allclose(translations.T @ lam, 0.0, atol=1.0e-12)


def test_internal_strain_response_can_reject_acoustic_sum_rule_violation():
    phi = np.kron(np.array([[1.0, -1.0], [-1.0, 1.0]]), np.eye(3))
    gamma = np.zeros((6, 1))
    gamma[0, 0] = 1.0
    with pytest.raises(ValueError, match="acoustic sum rule"):
        internal_strain_response(phi, gamma, check_acoustic=True)
    diagnostics = acoustic_sum_rule_diagnostics(phi, gamma)
    assert diagnostics["compatible"] is False
    assert diagnostics["strain_force_coupling_compatible"] is False
    with pytest.raises(ValueError, match="acoustic sum rule"):
        relaxed_elastic(np.eye(6), phi, gamma, 1.0, check_acoustic=True)


def test_internal_strain_solver_reports_equilibrium_and_translation_gauge():
    phi = np.kron(np.array([[1.0, -1.0], [-1.0, 1.0]]), np.eye(3))
    gamma = np.array(
        [
            [1.0, 0.2], [0.0, 0.1], [0.3, 0.4],
            [-1.0, -0.2], [0.0, -0.1], [-0.3, -0.4],
        ]
    )
    result = solve_internal_strain_response(
        phi,
        gamma,
        check_acoustic=True,
        acoustic_tolerance=1.0e-12,
        residual_tolerance=1.0e-12,
    )
    np.testing.assert_allclose(result.equilibrium_residual, 0.0, atol=1.0e-12)
    np.testing.assert_allclose(result.translation_gauge_residual, 0.0, atol=1.0e-12)
    assert result.rank == 3
    assert result.residual_max < 1.0e-12
    assert result.residual_relative < 1.0e-12


def test_internal_strain_solver_rejects_nontranslational_incompatible_gamma():
    # A singular Phi with an extra null mode cannot balance this Gamma.  A
    # pseudoinverse alone would silently return a least-squares displacement;
    # the strict residual gate must reject it.
    phi = np.diag([0.0, 1.0, 1.0])
    gamma = np.array([[1.0], [0.0], [0.0]])
    with pytest.raises(ValueError, match="equilibrium residual"):
        solve_internal_strain_response(phi, gamma, residual_tolerance=1.0e-12)


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


def test_fit_elastic_response_can_enforce_major_symmetry():
    rng = np.random.default_rng(20260912)
    strains = rng.normal(size=(24, 6))
    stiffness = np.array(
        [
            [220.0, 80.0, 70.0, 0.0, 0.0, 0.0],
            [80.0, 210.0, 75.0, 0.0, 0.0, 0.0],
            [70.0, 75.0, 250.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 90.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 95.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 85.0],
        ]
    )
    result = fit_elastic_response(
        strains,
        strains @ stiffness.T,
        enforce_major_symmetry=True,
    )
    np.testing.assert_allclose(result.matrix, stiffness, atol=1.0e-10)
    assert result.allowed_rank == 21
    assert result.fit_rank == 21
    assert result.complete
    assert result.residual_max < 1.0e-10


def test_fit_energy_elastic_response_recovers_work_conjugate_curvature_and_units():
    rng = np.random.default_rng(20260913)
    strains = rng.normal(scale=0.08, size=(45, 6))
    volume = 12.5
    reference_stress = np.array([0.12, -0.08, 0.04, 0.01, -0.02, 0.03])
    elastic_ev_a3 = np.array(
        [
            [2.20, 0.40, 0.30, 0.00, 0.00, 0.00],
            [0.40, 2.10, 0.35, 0.00, 0.00, 0.00],
            [0.30, 0.35, 2.50, 0.00, 0.00, 0.00],
            [0.00, 0.00, 0.00, 0.90, 0.00, 0.00],
            [0.00, 0.00, 0.00, 0.00, 0.95, 0.00],
            [0.00, 0.00, 0.00, 0.00, 0.00, 0.85],
        ]
    )
    reference_energy = -17.3
    energies = (
        reference_energy
        + volume * (strains @ reference_stress)
        + 0.5 * volume * np.einsum("si,ij,sj->s", strains, elastic_ev_a3, strains)
    )
    result = fit_energy_elastic_response(
        strains,
        energies,
        volume=volume,
        energy_unit="eV",
        volume_unit="angstrom^3",
        elastic_unit="eV/angstrom^3",
    )
    np.testing.assert_allclose(result.elastic, elastic_ev_a3, atol=1.0e-10)
    np.testing.assert_allclose(result.reference_stress, reference_stress, atol=1.0e-10)
    assert result.reference_energy == pytest.approx(reference_energy)
    assert result.complete
    assert result.input_rank == result.fit_rank == result.allowed_rank == 28
    assert result.residual_max < 1.0e-10


def test_fit_energy_elastic_response_reports_rank_deficiency():
    strains = np.zeros((5, 6))
    strains[:, 0] = np.linspace(-0.02, 0.02, 5)
    energies = 1.0 + 0.5 * strains[:, 0] ** 2
    result = fit_energy_elastic_response(
        strains,
        energies,
        volume=1.0,
        energy_unit="eV",
        volume_unit="angstrom^3",
        elastic_unit="GPa",
    )
    assert not result.complete
    assert result.input_rank == 3
    assert result.fit_rank < result.allowed_rank
    assert result.residual_max < 1.0e-12


def test_fit_energy_elastic_response_accepts_symmetry_reduced_elastic_basis():
    """A six-pair central ensemble can fit a cubic Hessian after reduction."""

    structure = StructureSpec(
        lattice=np.diag([5.43, 5.43, 5.43]),
        fractional_positions=np.array([[0.0, 0.0, 0.0]]),
        symbols=("Si",),
    )
    report = analyze_space_group(structure)
    basis = allowed_response_basis(report, input_kind="strain", output_kind="stress")
    assert basis.allowed_rank == 3
    elastic = sum(
        coefficient * basis.matrix_from_coefficients(np.eye(3)[index])
        for index, coefficient in enumerate((2.0, 3.0, 4.0))
    )
    # A pure-axis energy pair does not distinguish the cubic C12 cross term in
    # a conventional Cartesian cell; include one mixed normal strain so the
    # reduced quadratic design is genuinely rank-complete.
    mixed = np.array([[1.0, 1.0, 0.0, 0.0, 0.0, 0.0], [-1.0, -1.0, 0.0, 0.0, 0.0, 0.0]])
    strains = np.vstack((np.zeros((1, 6)), np.eye(6), -np.eye(6), mixed)) * 1.0e-2
    volume = 20.0
    energies = -4.0 + 0.5 * volume * np.einsum("si,ij,sj->s", strains, elastic, strains)
    result = fit_energy_elastic_response(
        strains,
        energies,
        volume=volume,
        energy_unit="eV",
        volume_unit="angstrom^3",
        elastic_unit="eV/angstrom^3",
        allowed_basis=basis,
    )
    assert result.allowed_rank == result.fit_rank == 3
    assert result.complete
    np.testing.assert_allclose(result.elastic, elastic, atol=1.0e-10)
    assert result.residual_max < 1.0e-12


def test_fit_elastic_response_rejects_non_boolean_major_symmetry_flag():
    with pytest.raises(TypeError, match="enforce_major_symmetry"):
        fit_elastic_response([[0.0] * 6], [[0.0] * 6], enforce_major_symmetry=1)


def test_fit_strain_force_coupling_recovers_gamma_with_force_sign_and_reference():
    strains = np.array(
        [
            [0.0] * 6,
            [0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
            [-0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
        ]
    )
    gamma = np.zeros((3, 6))
    gamma[:, 0] = [2.0, -3.0, 4.0]
    reference = np.array([0.4, -0.2, 0.1])
    forces = reference - strains @ gamma.T

    flat_result = fit_strain_force_coupling(
        strains,
        forces,
        reference_forces=reference,
    )
    tensor_result = fit_strain_force_coupling(
        strains,
        forces.reshape(3, 1, 3),
        reference_forces=reference.reshape(1, 3),
    )
    np.testing.assert_allclose(flat_result.matrix[:, 0], gamma[:, 0], atol=1.0e-12)
    np.testing.assert_allclose(tensor_result.matrix, flat_result.matrix, atol=1.0e-12)
    assert flat_result.residual_max < 1.0e-12
    assert flat_result.input_rank == 1
    assert flat_result.fit_rank == 3
    assert not flat_result.complete

    with pytest.raises(ValueError, match=r"shape \(samples, 6\)"):
        fit_strain_force_coupling([[0.0] * 5], [[0.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match="reference_forces"):
        fit_strain_force_coupling(strains, forces, reference_forces=[0.0, 1.0])


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


def test_fit_internal_strain_response_recovers_cartesian_lambda_without_gauge_projection():
    strains = np.array(
        [
            [0.0] * 6,
            [0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, -0.02, 0.0, 0.0, 0.0, 0.0],
            [0.01, -0.02, 0.0, 0.0, 0.0, 0.0],
        ]
    )
    expected = np.zeros((2, 3, 6))
    expected[0, 0, 0] = 0.4
    expected[0, 1, 1] = -0.7
    expected[1, 2, 0] = 0.2
    reference = np.array([[0.1, -0.2, 0.3], [-0.4, 0.5, -0.6]])
    observations = reference + np.einsum("sm,ibm->sib", strains, expected)
    result = fit_internal_strain_response(
        strains,
        observations,
        reference_displacement=reference,
    )
    np.testing.assert_allclose(result.matrix.reshape(2, 3, 6), expected, atol=1.0e-12)
    assert result.input_rank == 2
    assert result.fit_rank == 12
    assert result.allowed_rank == 36
    assert not result.complete
    assert result.residual_max < 1.0e-12


def test_fit_internal_strain_response_rejects_wrong_observation_shape():
    with pytest.raises(ValueError, match="displacement_observations"):
        fit_internal_strain_response([[0.0] * 6], np.zeros((1, 3)))


def test_proper_piezoelectric_response_applies_vanderbilt_correction_in_engineering_voigt():
    polarization = np.array([0.1, 0.2, 0.3])
    result = proper_piezoelectric_response(np.zeros((3, 6)), polarization)

    expected = np.zeros((3, 6))
    expected[:, 0] = [0.0, 0.2, 0.3]
    expected[:, 1] = [0.1, 0.0, 0.3]
    expected[:, 2] = [0.1, 0.2, 0.0]
    expected[1, 3] = -0.5 * polarization[2]
    expected[2, 3] = -0.5 * polarization[1]
    expected[0, 4] = -0.5 * polarization[2]
    expected[2, 4] = -0.5 * polarization[0]
    expected[0, 5] = -0.5 * polarization[1]
    expected[1, 5] = -0.5 * polarization[0]

    np.testing.assert_allclose(result.correction, expected)
    np.testing.assert_allclose(result.proper, expected)
    np.testing.assert_allclose(result.proper, result.improper + result.correction)


def test_proper_piezoelectric_response_rejects_tensorial_shear_convention():
    with pytest.raises(ValueError, match="engineering Voigt"):
        proper_piezoelectric_response(
            np.zeros((3, 6)), np.zeros(3), voigt_convention=("xx", "yy", "zz", "xy", "xz", "yz")
        )
    with pytest.raises(ValueError, match="engineering Voigt"):
        proper_piezoelectric_response(
            np.zeros((3, 6)), np.zeros(3), voigt_convention=("xx", "yy", "zz", "2yz", "2xz", "2xy")
        )


def test_fit_piezoelectric_ensemble_connects_branch_matching_to_fit():
    strains = np.array(
        [
            [0.0] * 6,
            [0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
            [-0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
        ]
    )
    expected = np.zeros((3, 6))
    expected[0, 0] = 1.2
    expected[1, 0] = -0.4
    reference = np.array([0.4, -0.2, 0.1])
    wrapped = reference + strains @ expected.T
    wrapped[1] += [10.0, -20.0, 30.0]
    wrapped[2] += [-10.0, 20.0, -30.0]
    ensemble = match_polarization_ensemble(strains, wrapped, [10.0, 20.0, 30.0])
    # The residual is the physical reference-to-stage mismatch after branch
    # shifts, so it may be non-zero even for a valid response.
    result = fit_piezoelectric_ensemble(ensemble, residual_tolerance=0.1)
    np.testing.assert_allclose(result.matrix[:, 0], expected[:, 0], atol=1.0e-12)
    assert result.residual_max < 1.0e-12

    nonzero_reference = match_polarization_ensemble(
        strains + np.array([0.1, 0, 0, 0, 0, 0]),
        wrapped,
        [10.0, 20.0, 30.0],
    )
    with pytest.raises(ValueError, match="reference stage strain is not zero"):
        fit_piezoelectric_ensemble(nonzero_reference)

    with pytest.raises(ValueError, match="residual_tolerance"):
        fit_piezoelectric_ensemble(ensemble, residual_tolerance=-1.0)


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
    assert result.suggested_input_indices == (1,)


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

    # Calculator displacement fits are commonly stored in Angstrom.  The
    # relaxed-ion formula is SI when volume is m^3, so the conversion must be
    # explicit rather than silently treating an Angstrom value as metres.
    _, angstrom_contribution = relaxed_piezoelectric(
        np.zeros((3, 6)), born, lam, 2.0, charge=1.0,
        internal_strain_unit="angstrom",
    )
    np.testing.assert_allclose(angstrom_contribution, expected_contribution * 1.0e-10)
    with pytest.raises(ValueError, match="internal_strain_unit"):
        relaxed_piezoelectric(np.zeros((3, 6)), born, lam, 2.0, internal_strain_unit="eV")

    c0 = np.eye(6) * 10.0
    crel, lam2, correction = relaxed_elastic(c0, phi, gamma, 2.0)
    np.testing.assert_allclose(lam2, expected_lambda)
    expected_correction = gamma.T @ np.linalg.pinv(phi) @ gamma / 2.0
    np.testing.assert_allclose(correction, expected_correction)
    np.testing.assert_allclose(crel, c0 - expected_correction)


def test_relaxed_elastic_unit_aware_mode_converts_ev_per_angstrom3_to_gpa():
    c0 = np.eye(6) * 1000.0
    phi = np.eye(3)
    gamma = np.zeros((3, 6))
    gamma[:, :3] = np.eye(3)
    crel, lam, correction = relaxed_elastic(
        c0,
        phi,
        gamma,
        1.0,
        energy_unit="eV",
        length_unit="angstrom",
        volume_unit="angstrom^3",
        elastic_unit="GPa",
    )
    expected = 160.2176634  # 1 eV/Angstrom^3 in GPa
    np.testing.assert_allclose(lam, -gamma)
    np.testing.assert_allclose(np.diag(correction)[:3], expected, rtol=1.0e-12)
    np.testing.assert_allclose(np.diag(correction)[3:], 0.0, atol=1.0e-12)
    np.testing.assert_allclose(np.diag(crel)[:3], 1000.0 - expected, rtol=1.0e-12)
    _, _, si_correction = relaxed_elastic(
        c0,
        phi,
        gamma,
        1.0,
        energy_unit="J",
        length_unit="m",
        volume_unit="m^3",
        elastic_unit="Pa",
    )
    np.testing.assert_allclose(np.diag(si_correction)[:3], 1.0, atol=1.0e-12)
    with pytest.raises(ValueError, match="provided together"):
        relaxed_elastic(c0, phi, gamma, 1.0, elastic_unit="GPa")
    with pytest.raises(ValueError, match="cube of length_unit"):
        relaxed_elastic(
            c0,
            phi,
            gamma,
            1.0,
            energy_unit="eV",
            length_unit="angstrom",
            volume_unit="m^3",
            elastic_unit="GPa",
        )


def test_algebra_rejects_invalid_shapes_and_volume():
    with pytest.raises(ValueError, match="volume"):
        relaxed_piezoelectric(np.zeros((3, 6)), np.zeros((1, 3, 3)), np.zeros((1, 3, 6)), 0.0)
    with pytest.raises(ValueError, match="square"):
        internal_strain_response(np.zeros((2, 3)), np.zeros((2, 6)))


def test_fit_proper_piezoelectric_response_keeps_raw_fit_and_applies_reference_correction():
    rng = np.random.default_rng(20260913)
    strains = rng.normal(scale=0.01, size=(40, 6))
    reference = np.array([0.0, 0.0, 0.39517389498898037])
    raw = rng.normal(size=(3, 6))
    polarizations = reference + strains @ raw.T
    result = fit_proper_piezoelectric_response(
        strains,
        polarizations,
        reference_polarization=reference,
    )
    np.testing.assert_allclose(result.raw_fit.matrix, raw, atol=1.0e-11)
    np.testing.assert_allclose(result.proper.improper, raw, atol=1.0e-12)
    expected = proper_piezoelectric_response(raw, reference)
    np.testing.assert_allclose(result.proper.correction, expected.correction, atol=1.0e-12)
    np.testing.assert_allclose(result.proper.proper, expected.proper, atol=1.0e-12)
    assert result.raw_fit.complete
    assert result.raw_fit.residual_max < 1.0e-12


def test_fit_proper_piezoelectric_response_rejects_invalid_reference_shape():
    with pytest.raises(ValueError, match="reference_polarization"):
        fit_proper_piezoelectric_response(
            [[0.0] * 6, [0.01, 0.0, 0.0, 0.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [0.01, 0.0, 0.0]],
            reference_polarization=[0.0, 0.0],
        )
