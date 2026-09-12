from __future__ import annotations

import numpy as np

from zstar.dimensions import DimensionSpec
from zstar.v2 import (
    StructureSpec,
    allowed_response_basis,
    analyze_space_group,
    displacement_representation,
    polarization_representation,
    strain_representation,
    symmetry_adapted_input_plan,
)


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
