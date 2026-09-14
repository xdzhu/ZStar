from __future__ import annotations

import numpy as np
import pytest

from zstar.dimensions import DimensionSpec
from zstar.v2 import (
    StructureSpec,
    allowed_response_basis,
    analyze_space_group,
    displacement_representation,
    fit_elastic_response,
    fit_linear_response,
    polarization_representation,
    space_group_report_to_dict,
    rotate_elastic_tensor,
    strain_representation,
    stress_representation,
    stress_tensor_to_voigt,
    symmetry_adapted_input_plan,
)
from zstar.v2.structure import _operation_permutation
import zstar.v2.structure as structure_module


def test_cubic_space_group_builds_representation_and_forbids_piezo():
    structure = StructureSpec(
        lattice=np.diag([5.43, 5.43, 5.43]),
        fractional_positions=np.array([[0.0, 0.0, 0.0]]),
        symbols=("Si",),
    )
    report = analyze_space_group(structure)
    assert report.status == "stable"
    assert report.space_group == "Pm-3m"
    assert report.operation_count == 48
    assert report.representatives == (0,)
    assert displacement_representation(report, 0).shape == (3, 3)
    assert polarization_representation(report, 0).shape == (3, 3)
    assert strain_representation(report, 0).shape == (6, 6)
    piezo_basis = allowed_response_basis(report, input_kind="strain", output_kind="polarization")
    assert piezo_basis.allowed_rank == 0


def test_space_group_report_serialization_retains_operations_for_audit():
    structure = StructureSpec(
        lattice=np.diag([5.43, 5.43, 5.43]),
        fractional_positions=np.array([[0.0, 0.0, 0.0]]),
        symbols=("Si",),
    )
    report = analyze_space_group(structure)
    serialized = space_group_report_to_dict(report)
    assert serialized["space_group"] == "Pm-3m"
    assert serialized["operation_count"] == 48
    assert len(serialized["operations"]) == 48
    operation = serialized["operations"][0]
    assert set(operation) == {
        "rotation_fractional",
        "translation_fractional",
        "rotation_cartesian",
        "permutation",
    }
    assert operation["permutation"] == [0]
    assert len(serialized["diagnostics"]["candidate_signatures"]) == 3


def test_p1_structure_keeps_all_response_degrees_of_freedom():
    structure = StructureSpec(
        lattice=np.array([[4.1, 0.0, 0.0], [0.2, 5.0, 0.0], [0.1, 0.3, 6.2]]),
        fractional_positions=np.array([[0.13, 0.27, 0.31], [0.61, 0.22, 0.79]]),
        symbols=("A", "B"),
    )
    report = analyze_space_group(structure, symprec_grid=(1.0e-5, 1.0e-4))
    assert report.status == "stable"
    assert report.space_group == "P1"
    assert report.operation_count == 1
    basis = allowed_response_basis(report, input_kind="displacement", output_kind="polarization")
    assert basis.allowed_rank == 18


def test_molecule_skips_periodic_space_group_reduction():
    structure = StructureSpec(
        lattice=np.eye(3) * 20.0,
        fractional_positions=np.array([[0.50, 0.50, 0.50], [0.55, 0.50, 0.50]]),
        symbols=("O", "H"),
        dimensionality=DimensionSpec(0),
    )
    report = analyze_space_group(structure)
    assert report.status == "molecular-no-periodic-symmetry"
    assert report.space_group is None
    assert report.operation_count == 1


def test_symmetry_adapted_strain_plan_identifies_unified_p4mm_responses():
    structure = StructureSpec(
        lattice=np.diag([3.9, 3.9, 4.1]),
        fractional_positions=np.array(
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [0.5, 0.5, 0.1],
             [0.5, 0.0, 0.6], [0.0, 0.5, 0.6]]
        ),
        symbols=("Ba", "Ti", "O", "O", "O"),
    )
    report = analyze_space_group(structure)
    plan = symmetry_adapted_input_plan(
        report,
        input_kind="strain",
        output_kinds=("polarization", "strain", "displacement"),
    )
    assert plan.complete
    assert plan.allowed_ranks == {"polarization": 3, "strain": 7, "displacement": 14}
    assert plan.identified_rank == 24
    assert plan.selected_indices == (0, 2, 3, 5)
    assert plan.vectors.shape == (4, 6)
    assert plan.to_dict()["complete"] is True


def test_unified_strain_plan_accepts_force_and_tensorial_stress_outputs():
    structure = StructureSpec(
        lattice=np.diag([3.9, 3.9, 4.1]),
        fractional_positions=np.array(
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [0.5, 0.5, 0.1],
             [0.5, 0.0, 0.6], [0.0, 0.5, 0.6]]
        ),
        symbols=("Ba", "Ti", "O", "O", "O"),
    )
    report = analyze_space_group(structure)
    assert stress_representation(np.eye(3)).shape == (6, 6)
    force_basis = allowed_response_basis(report, input_kind="strain", output_kind="force")
    stress_basis = allowed_response_basis(report, input_kind="strain", output_kind="stress")
    displacement_basis = allowed_response_basis(
        report, input_kind="strain", output_kind="displacement"
    )
    assert force_basis.allowed_rank == displacement_basis.allowed_rank == 14
    assert stress_basis.allowed_rank == 7
    plan = symmetry_adapted_input_plan(
        report,
        input_kind="strain",
        output_kinds=("polarization", "force", "stress", "displacement"),
    )
    assert plan.complete
    assert plan.allowed_ranks == {
        "polarization": 3,
        "force": 14,
        "stress": 7,
        "displacement": 14,
    }
    assert plan.identified_rank == 38
    assert plan.selected_indices == (0, 2, 3, 5)


def test_cubic_elastic_basis_survives_major_symmetry_intersection():
    """Numerical spglib rotations must not collapse the cubic C basis."""

    structure = StructureSpec(
        lattice=np.diag([5.43, 5.43, 5.43]),
        fractional_positions=np.array([[0.0, 0.0, 0.0]]),
        symbols=("Si",),
    )
    report = analyze_space_group(structure)
    basis = allowed_response_basis(report, input_kind="strain", output_kind="stress")
    assert basis.allowed_rank == 3

    stiffness = np.array(
        [
            [500.0, 150.0, 150.0, 0.0, 0.0, 0.0],
            [150.0, 500.0, 150.0, 0.0, 0.0, 0.0],
            [150.0, 150.0, 500.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 200.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 200.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 200.0],
        ]
    )
    strains = np.vstack((np.eye(6), -np.eye(6))) * 1.0e-3
    result = fit_elastic_response(
        strains,
        strains @ stiffness.T,
        allowed_basis=basis,
        enforce_major_symmetry=True,
    )
    assert result.allowed_rank == 3
    assert result.complete
    np.testing.assert_allclose(result.matrix, stiffness, atol=1.0e-8)
    assert result.residual_max < 1.0e-10


def test_stress_representation_preserves_tensorial_shear_under_rotation():
    angle = np.deg2rad(37.0)
    rotation = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    stress = np.array([[2.0, 0.3, -0.4], [0.3, -1.0, 0.7], [-0.4, 0.7, 3.0]])
    transformed = rotation @ stress @ rotation.T
    np.testing.assert_allclose(
        stress_representation(rotation) @ stress_tensor_to_voigt(stress),
        stress_tensor_to_voigt(transformed),
        atol=1.0e-12,
    )


def test_rotate_elastic_tensor_round_trips_engineering_voigt_matrix():
    angle = np.deg2rad(37.0)
    rotation = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    elastic = np.array(
        [
            [210.0, 71.0, 64.0, 3.0, 5.0, 7.0],
            [71.0, 225.0, 69.0, 11.0, 13.0, 17.0],
            [64.0, 69.0, 240.0, 19.0, 23.0, 29.0],
            [3.0, 11.0, 19.0, 82.0, 31.0, 37.0],
            [5.0, 13.0, 23.0, 31.0, 91.0, 41.0],
            [7.0, 17.0, 29.0, 37.0, 41.0, 103.0],
        ]
    )
    rotated = rotate_elastic_tensor(elastic, rotation)
    recovered = rotate_elastic_tensor(rotated, rotation.T)
    np.testing.assert_allclose(recovered, elastic, atol=1.0e-10)


def test_rotate_elastic_tensor_maps_sic_primitive_fit_to_cubic_axes():
    # The rhombohedral primitive-cell matrix from the 3D SiC ABACUS audit.
    elastic = np.array(
        [
            [489.8088, 68.4934, 26.3579, 59.5886, 0.0, 0.0],
            [68.4934, 489.8088, 26.3579, -59.5886, 0.0, 0.0],
            [26.3579, 26.3579, 531.9443, 0.0, 0.0, 0.0],
            [59.5886, -59.5886, 0.0, 168.5222, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 168.5222, 59.5886],
            [0.0, 0.0, 0.0, 0.0, 59.5886, 210.6577],
        ]
    )
    rotation = np.array(
        [
            [0.7071067811865476, -0.4082482904638631, 0.5773502691896258],
            [0.0, 0.8164965809277261, 0.5773502691896258],
            [-0.7071067811865476, -0.4082482904638631, 0.5773502691896258],
        ]
    )
    cubic = rotate_elastic_tensor(elastic, rotation)
    np.testing.assert_allclose(cubic[0, 0], 363.4023, atol=2.0e-3)
    np.testing.assert_allclose(cubic[0, 1], 110.6289, atol=2.0e-3)
    np.testing.assert_allclose(cubic[3, 3], 252.7932, atol=2.0e-3)
    np.testing.assert_allclose(cubic[0, 3:], 0.0, atol=2.0e-6)
    np.testing.assert_allclose(cubic[3:, :3], 0.0, atol=2.0e-6)


def test_rotate_elastic_tensor_rejects_non_rotation_and_nonengineering_voigt():
    with pytest.raises(ValueError, match="orthogonal"):
        rotate_elastic_tensor(np.eye(6), np.eye(3) * 2.0)
    improper = np.diag([-1.0, 1.0, 1.0])
    with pytest.raises(ValueError, match="determinant"):
        rotate_elastic_tensor(np.eye(6), improper)
    with pytest.raises(ValueError, match="engineering Voigt"):
        rotate_elastic_tensor(np.eye(6), np.eye(3), voigt_convention=("xx",) * 6)


def test_symmetry_adapted_strain_plan_keeps_all_components_for_p1():
    structure = StructureSpec(
        lattice=np.array([[4.1, 0.0, 0.0], [0.2, 5.0, 0.0], [0.1, 0.3, 6.2]]),
        fractional_positions=np.array([[0.13, 0.27, 0.31], [0.61, 0.22, 0.79]]),
        symbols=("A", "B"),
    )
    report = analyze_space_group(structure, symprec_grid=(1.0e-5, 1.0e-4))
    plan = symmetry_adapted_input_plan(report, input_kind="strain", output_kinds=("polarization", "strain"))
    assert plan.complete
    assert plan.selected_indices == tuple(range(6))
    np.testing.assert_allclose(plan.vectors, np.eye(6))


def test_hexagonal_low_dimensional_plan_handles_polar_response_and_six_strain_modes():
    a = 2.5
    structure = StructureSpec(
        lattice=np.array([[a, 0.0, 0.0], [-0.5 * a, 0.5 * np.sqrt(3.0) * a, 0.0], [0.0, 0.0, 20.0]]),
        fractional_positions=np.array([[0.0, 0.0, 0.0], [1.0 / 3.0, 2.0 / 3.0, 0.0]]),
        symbols=("B", "N"),
        dimensionality=DimensionSpec(2, ("x", "y")),
    )
    report = analyze_space_group(structure)
    assert report.status == "stable"
    assert report.space_group == "P-6m2"
    assert report.operation_count == 12
    plan = symmetry_adapted_input_plan(report, input_kind="strain", output_kinds=("polarization", "strain"))
    assert plan.complete
    assert plan.allowed_ranks == {"polarization": 1, "strain": 6}
    assert plan.identified_rank == 7
    assert plan.selected_indices == (0, 2, 3)


def test_orthorhombic_plan_keeps_elastic_modes_when_piezo_is_forbidden():
    structure = StructureSpec(
        lattice=np.diag([4.0, 5.0, 6.0]),
        fractional_positions=np.array([[0.0, 0.0, 0.0]]),
        symbols=("X",),
    )
    report = analyze_space_group(structure)
    assert report.status == "stable"
    assert report.space_group == "Pmmm"
    assert report.operation_count == 8
    piezo = allowed_response_basis(report, input_kind="strain", output_kind="polarization")
    assert piezo.allowed_rank == 0
    plan = symmetry_adapted_input_plan(report, input_kind="strain", output_kinds=("polarization", "strain"))
    assert plan.complete
    assert plan.allowed_ranks == {"polarization": 0, "strain": 12}
    assert plan.identified_rank == 12


def test_five_symmetry_plans_reconstruct_known_allowed_responses_exactly():
    a = 2.5
    hexagonal = StructureSpec(
        lattice=np.array([[a, 0.0, 0.0], [-0.5 * a, 0.5 * np.sqrt(3.0) * a, 0.0], [0.0, 0.0, 20.0]]),
        fractional_positions=np.array([[0.0, 0.0, 0.0], [1.0 / 3.0, 2.0 / 3.0, 0.0]]),
        symbols=("B", "N"),
        dimensionality=DimensionSpec(2, ("x", "y")),
    )
    structures = (
        StructureSpec(np.diag([5.43, 5.43, 5.43]), np.array([[0.0, 0.0, 0.0]]), ("Si",)),
        StructureSpec(
            np.diag([3.9, 3.9, 4.1]),
            np.array([[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0.5, 0.1], [0.5, 0, 0.6], [0, 0.5, 0.6]]),
            ("Ba", "Ti", "O", "O", "O"),
        ),
        hexagonal,
        StructureSpec(np.diag([4.0, 5.0, 6.0]), np.array([[0.0, 0.0, 0.0]]), ("X",)),
        StructureSpec(
            np.array([[4.1, 0.0, 0.0], [0.2, 5.0, 0.0], [0.1, 0.3, 6.2]]),
            np.array([[0.13, 0.27, 0.31], [0.61, 0.22, 0.79]]),
            ("A", "B"),
        ),
    )
    for structure in structures:
        report = analyze_space_group(structure)
        plan = symmetry_adapted_input_plan(
            report, input_kind="strain", output_kinds=("polarization", "strain")
        )
        assert plan.complete
        actual = plan.vectors
        for output_kind in ("polarization", "strain"):
            basis = allowed_response_basis(
                report, input_kind="strain", output_kind=output_kind
            )
            coefficients = np.arange(basis.allowed_rank, dtype=float) + 1.0
            matrix = (
                basis.matrix_from_coefficients(coefficients)
                if basis.allowed_rank
                else np.zeros((basis.output_dimension, basis.input_dimension))
            )
            fitted = fit_linear_response(
                actual, actual @ matrix.T, allowed_basis=basis
            )
            assert fitted.complete
            assert fitted.fit_rank == basis.allowed_rank
            assert fitted.residual_max < 1.0e-10
            np.testing.assert_allclose(fitted.matrix, matrix, atol=1.0e-10)


def test_operation_permutation_uses_bipartite_matching_for_near_degenerate_sites():
    structure = StructureSpec(
        lattice=np.eye(3),
        fractional_positions=np.array([[0.0, 0.0, 0.0], [6.0e-8, 0.0, 0.0]]),
        symbols=("X", "X"),
    )
    permutation = _operation_permutation(
        structure,
        np.diag([-1.0, 1.0, 1.0]),
        np.array([3.0e-8, 0.0, 0.0]),
        tolerance=5.0e-8,
    )
    assert permutation == (1, 0)


def test_periodic_symmetry_analysis_rejects_missing_spglib(monkeypatch):
    structure = StructureSpec(
        lattice=np.eye(3) * 4.0,
        fractional_positions=np.array([[0.0, 0.0, 0.0]]),
        symbols=("X",),
    )
    monkeypatch.setattr(structure_module, "spglib", None)
    with pytest.raises(RuntimeError, match="spglib is required"):
        analyze_space_group(structure)


def test_symmetry_analysis_marks_empty_spglib_dataset_untrusted(monkeypatch):
    structure = StructureSpec(
        lattice=np.eye(3) * 4.0,
        fractional_positions=np.array([[0.0, 0.0, 0.0]]),
        symbols=("X",),
    )

    class EmptySpglib:
        @staticmethod
        def get_symmetry_dataset(*_args, **_kwargs):
            return None

    monkeypatch.setattr(structure_module, "spglib", EmptySpglib())
    report = analyze_space_group(structure, symprec_grid=(1.0e-5,))
    assert report.status == "symmetry_untrusted"
    assert report.operations == ()
    with pytest.raises(ValueError, match="without operations"):
        symmetry_adapted_input_plan(report, input_kind="strain")
