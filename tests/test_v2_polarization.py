from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from zstar.v2 import (
    BOHR_RADIUS,
    ELEMENTARY_CHARGE,
    MatchedPolarizationEnsemble,
    PolarizationSample,
    assemble_cartesian_polarization,
    collect_abacus_polarization_component,
    collect_abacus_polarization_stage,
    collect_abacus_polarization_triplet,
    collect_pyatb_polarization,
    match_polarization_branch,
    match_polarization_ensemble,
    parse_abacus_berry_polarization,
    parse_pyatb_polarization,
    pyatb_directional_to_cartesian,
    unwrap_polarization_path,
)


def test_parse_abacus_berry_polarization_normalizes_supported_units():
    component = parse_abacus_berry_polarization(
        "P = 1.25D+00 (mod 3.5) (1.25, 0, 0) C/m^2"
    )
    assert component.unit == "C/m^2"
    assert component.raw_unit == "C/m^2"
    np.testing.assert_allclose([component.value, component.quantum], [1.25, 3.5])
    np.testing.assert_allclose(component.cartesian_value, [1.25, 0.0, 0.0])

    component = parse_abacus_berry_polarization(
        "P = 2 (mod 4) (2, 0, 0) e/bohr^2"
    )
    np.testing.assert_allclose(component.value, 2.0 * ELEMENTARY_CHARGE / BOHR_RADIUS**2)
    np.testing.assert_allclose(component.quantum, 4.0 * ELEMENTARY_CHARGE / BOHR_RADIUS**2)

    component = parse_abacus_berry_polarization(
        "P = 2 (mod 4) (2, 0, 0) (e/Ω).bohr",
        volume_bohr3=10.0,
    )
    np.testing.assert_allclose(component.value, 2.0 * ELEMENTARY_CHARGE / (10.0 * BOHR_RADIUS**2))

    with pytest.raises(ValueError, match="volume_bohr3"):
        parse_abacus_berry_polarization("P = 2 (mod 4) (2, 0, 0) (e/Ω).bohr")


def test_parse_abacus_berry_polarization_prefers_direct_si_record():
    component = parse_abacus_berry_polarization(
        "P = 7 (mod 18) (0, 0, 7) (e/Omega).bohr\n"
        "P = 0.89 (mod 2.17) (0, 0, 0.89) C/m^2\n",
        volume_bohr3=10.0,
    )
    np.testing.assert_allclose([component.value, component.quantum], [0.89, 2.17])
    assert component.raw_unit == "C/m^2"


def test_parse_abacus_berry_polarization_rejects_missing_record():
    with pytest.raises(ValueError, match="Berry polarization"):
        parse_abacus_berry_polarization("charge density convergence is achieved")


def test_collect_abacus_polarization_stage_keeps_wrapped_components_and_logs(tmp_path):
    output = tmp_path / "OUT.POLAR"
    output.mkdir()
    for axis, value in zip(("a", "b", "c"), (1.0, 2.0, 3.0)):
        (output / f"running_nscf_{axis}.log").write_text(
            f"P = {value} (mod 10) ({value}, 0, 0) C/m^2\n",
            encoding="utf-8",
        )
    sample = collect_abacus_polarization_stage(tmp_path)
    np.testing.assert_allclose(sample.values, [1.0, 2.0, 3.0])
    np.testing.assert_allclose(sample.quanta, [10.0, 10.0, 10.0])
    assert all(Path(path).is_file() for path in sample.logs)


def test_collect_abacus_polarization_stage_converts_internal_units_with_volume(tmp_path):
    output = tmp_path / "OUT.POLAR"
    output.mkdir()
    for axis, value in zip(("a", "b", "c"), (1.0, 2.0, 3.0)):
        (output / f"running_nscf_{axis}.log").write_text(
            "Volume (Bohr^3) = 10\n"
            f"P = {value} (mod 4) ({value}, 0, 0) (e/Omega).bohr\n",
            encoding="utf-8",
        )
    sample = collect_abacus_polarization_stage(tmp_path)
    factor = ELEMENTARY_CHARGE / (10.0 * BOHR_RADIUS**2)
    np.testing.assert_allclose(sample.values, np.asarray([1.0, 2.0, 3.0]) * factor)
    np.testing.assert_allclose(sample.quanta, 4.0 * factor)


def test_collect_abacus_polarization_component_reads_realistic_single_log(tmp_path):
    output = tmp_path / "OUT.POLAR"
    output.mkdir()
    (tmp_path / "INPUT").write_text(
        "INPUT_PARAMETERS\ncalculation nscf\ngdir 3\nberry_phase 1\n",
        encoding="utf-8",
    )
    (output / "running_nscf.log").write_text(
        "P = 7.4095194 (mod 18.0922373) (0, 0, 7.4095194) (e/Omega).bohr\n"
        "P = 0.8906925 (mod 2.1748536) (0, 0, 0.8906925) C/m^2\n",
        encoding="utf-8",
    )
    component = collect_abacus_polarization_component(tmp_path)
    assert component.gdir == 3
    assert component.raw_unit == "C/m^2"
    np.testing.assert_allclose(component.cartesian_value, [0.0, 0.0, 0.8906925])
    # The parser must prefer the explicit SI record when ABACUS emits both
    # the internal ``(e/Omega).bohr`` line and the converted C/m^2 line.
    np.testing.assert_allclose(component.value, 0.8906925)


def test_collect_abacus_polarization_triplet_orders_by_declared_gdir(tmp_path):
    stages = {}
    for direction, value in ((1, 1.0), (2, 2.0), (3, 3.0)):
        stage = tmp_path / f"gdir-{direction}"
        output = stage / "OUT.POLAR"
        output.mkdir(parents=True)
        (stage / "INPUT").write_text(f"gdir {direction}\n", encoding="utf-8")
        vector = [0.0, 0.0, 0.0]
        vector[direction - 1] = value
        (output / "running_nscf.log").write_text(
            f"P = {value} (mod 10) ({vector[0]}, {vector[1]}, {vector[2]}) C/m^2\n",
            encoding="utf-8",
        )
        stages[direction] = stage
    sample = collect_abacus_polarization_triplet({3: stages[3], 1: stages[1], 2: stages[2]})
    np.testing.assert_allclose(sample.values, [1.0, 2.0, 3.0])
    np.testing.assert_allclose(sample.cartesian_values, np.diag([1.0, 2.0, 3.0]))
    assert all(Path(path).is_file() for path in sample.logs)


def test_assemble_cartesian_polarization_sums_directional_components():
    sample = PolarizationSample(
        values=[1.0, 2.0, 3.0],
        quanta=[10.0, 10.0, 10.0],
        cartesian_values=np.diag([1.0, 2.0, 3.0]),
    )
    np.testing.assert_allclose(assemble_cartesian_polarization(sample), [1.0, 2.0, 3.0])


def test_assemble_cartesian_polarization_rejects_missing_directional_tuple():
    sample = PolarizationSample(values=[0.0, 0.0, 0.0], quanta=[1.0, 1.0, 1.0])
    with pytest.raises(ValueError, match="cannot be zero-filled"):
        assemble_cartesian_polarization(sample)


def test_collect_abacus_polarization_triplet_rejects_missing_or_duplicate_gdir(tmp_path):
    stages = []
    for direction in (1, 1, 2):
        stage = tmp_path / f"duplicate-{len(stages)}"
        output = stage / "OUT.POLAR"
        output.mkdir(parents=True)
        (stage / "INPUT").write_text(f"gdir {direction}\n", encoding="utf-8")
        (output / "running_nscf.log").write_text(
            "P = 0 (mod 1) (0, 0, 0) C/m^2\n",
            encoding="utf-8",
        )
        stages.append(stage)
    with pytest.raises(ValueError, match="unique gdir"):
        collect_abacus_polarization_triplet(stages)
    with pytest.raises(ValueError, match="three distinct stage directories"):
        collect_abacus_polarization_triplet({1: stages[0], 2: stages[2], 3: stages[2]})


def test_collect_abacus_polarization_triplet_accepts_string_numeric_keys_from_json(tmp_path):
    stages = {}
    for direction, value in ((1, 1.0), (2, 2.0), (3, 3.0)):
        stage = tmp_path / f"json-gdir-{direction}"
        output = stage / "OUT.POLAR"
        output.mkdir(parents=True)
        (stage / "INPUT").write_text(f"gdir {direction}\n", encoding="utf-8")
        vector = [0.0, 0.0, 0.0]
        vector[direction - 1] = value
        (output / "running_nscf.log").write_text(
            f"P = {value} (mod 10) ({vector[0]}, {vector[1]}, {vector[2]}) C/m^2\n",
            encoding="utf-8",
        )
        stages[direction] = stage
    sample = collect_abacus_polarization_triplet({str(key): value for key, value in stages.items()})
    np.testing.assert_allclose(sample.values, [1.0, 2.0, 3.0])


def test_branch_matching_returns_integer_shifts_and_delta():
    match = match_polarization_branch(
        [1.0, 2.0, 3.0],
        [11.0, -18.0, 33.0],
        [10.0, 20.0, 30.0],
    )
    np.testing.assert_allclose(match.matched, [1.0, 2.0, 3.0])
    np.testing.assert_array_equal(match.branch_shift, [-1, 1, -1])
    np.testing.assert_allclose(match.delta, [0.0, 0.0, 0.0])
    assert match.residual == 0.0


def test_branch_matching_handles_nonorthogonal_quantum_basis():
    quantum = np.array(
        [
            [2.0, 1.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 3.0],
        ]
    )
    wrapped = quantum @ np.array([1.0, -1.0, 2.0])
    match = match_polarization_branch(
        [0.0, 0.0, 0.0],
        wrapped,
        quantum,
    )
    np.testing.assert_allclose(match.matched, [0.0, 0.0, 0.0])
    np.testing.assert_array_equal(match.branch_shift, [-1, 1, -2])
    np.testing.assert_allclose(match.residual, 0.0)


def test_branch_matching_does_not_shift_nonperiodic_components():
    match = match_polarization_branch(
        [1.0, 2.0, 7.0],
        [11.0, 22.0, 9.0],
        [10.0, 20.0, 30.0],
        periodic_axes=("x", "y"),
    )
    np.testing.assert_allclose(match.matched, [1.0, 2.0, 9.0])
    np.testing.assert_array_equal(match.branch_shift, [-1, -1, 0])
    np.testing.assert_allclose(match.residual, 2.0)
    with pytest.raises(ValueError, match="exceeds max_residual"):
        unwrap_polarization_path(
            [[1.0, 2.0, 7.0], [11.0, 22.0, 9.0]],
            [10.0, 20.0, 30.0],
            periodic_axes=("x", "y"),
            max_residual=1.0,
        )


def test_match_polarization_ensemble_matches_each_stage_to_reference():
    strains = [
        [0.0] * 6,
        [0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
        [-0.01, 0.0, 0.0, 0.0, 0.0, 0.0],
    ]
    wrapped = [
        [1.0, 2.0, 3.0],
        [11.0, -18.0, 33.0],
        [-9.0, 22.0, -27.0],
    ]
    matched = match_polarization_ensemble(strains, wrapped, [10.0, 20.0, 30.0])
    assert isinstance(matched, MatchedPolarizationEnsemble)
    np.testing.assert_allclose(matched.actual_strains, strains)
    np.testing.assert_allclose(matched.matched_values, np.tile([1.0, 2.0, 3.0], (3, 1)))
    np.testing.assert_array_equal(matched.branch_shifts, [[0, 0, 0], [-1, 1, -1], [1, -1, 1]])
    np.testing.assert_allclose(matched.residuals, 0.0)
    np.testing.assert_allclose(matched.quantum_vectors[1], np.diag([10.0, 20.0, 30.0]))


def test_match_polarization_ensemble_rejects_incomplete_or_large_residual_data():
    with pytest.raises(ValueError, match="non-empty finite array"):
        match_polarization_ensemble([], [], [1.0, 1.0, 1.0])
    with pytest.raises(ValueError, match="quantum_vectors must have shape"):
        match_polarization_ensemble([[0.0] * 6], [[0.0, 0.0, 0.0]], [[1.0, 1.0]])
    with pytest.raises(ValueError, match="exceeds max_residual"):
        match_polarization_ensemble(
            [[0.0] * 6, [0.01, 0.0, 0.0, 0.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            [10.0, 10.0, 10.0],
            max_residual=0.5,
        )


def test_unwrap_polarization_path_is_sequential_and_reports_branches():
    path = unwrap_polarization_path(
        [[1.0, 2.0, 3.0], [11.0, -18.0, 33.0], [21.0, -38.0, 63.0]],
        [10.0, 20.0, 30.0],
    )
    np.testing.assert_allclose(path.values, np.tile([1.0, 2.0, 3.0], (3, 1)))
    np.testing.assert_array_equal(path.branch_shifts, [[0, 0, 0], [-1, 1, -1], [-2, 2, -2]])
    np.testing.assert_allclose(path.residuals, 0.0)


def test_branch_matching_rejects_rank_deficient_active_quantum_basis():
    with pytest.raises(ValueError, match="rank-deficient"):
        match_polarization_branch(
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
            np.zeros((3, 3)),
        )


def test_parse_pyatb_polarization_reads_all_three_directions_once():
    sample = parse_pyatb_polarization(
        "The calculated polarization direction is in a, P = 1.0 (mod 2.0) C/m^2.\n"
        "The calculated polarization direction is in b, P = -2.0 (mod 3.0) C/m^2.\n"
        "The calculated polarization direction is in c, P = 4.0 (mod 5.0) C/m^2.\n",
        source="polarization.dat",
    )
    np.testing.assert_allclose(sample.values, [1.0, -2.0, 4.0])
    np.testing.assert_allclose(sample.quanta, [2.0, 3.0, 5.0])
    assert sample.axes == ("a", "b", "c")
    assert sample.logs == ("polarization.dat",) * 3


def test_parse_pyatb_polarization_rejects_duplicate_or_missing_direction():
    text = (
        "The calculated polarization direction is in a, P = 1 (mod 2) C/m^2.\n"
        "The calculated polarization direction is in a, P = 2 (mod 2) C/m^2.\n"
        "The calculated polarization direction is in c, P = 3 (mod 2) C/m^2.\n"
    )
    with pytest.raises(ValueError, match="duplicate"):
        parse_pyatb_polarization(text)
    with pytest.raises(ValueError, match="missing"):
        parse_pyatb_polarization(
            "The calculated polarization direction is in a, P = 1 (mod 2) C/m^2.\n"
            "The calculated polarization direction is in b, P = 2 (mod 2) C/m^2.\n"
        )


def test_pyatb_directional_to_cartesian_combines_nonorthogonal_lattice_basis():
    lattice = np.asarray([[2.0, 0.0, 0.0], [1.0, 2.0, 0.0], [0.0, 0.0, 3.0]])
    cartesian = np.asarray([1.5, -0.5, 2.0])
    directions = lattice / np.linalg.norm(lattice, axis=1)[:, None]
    directional = np.asarray([1.5, -0.5, 2.0])
    np.testing.assert_allclose(
        pyatb_directional_to_cartesian(directional, lattice),
        directional @ directions,
    )


def test_collect_pyatb_polarization_reads_one_run_and_geometry(tmp_path):
    output = tmp_path / "pyatb" / "Out"
    (output / "Polarization").mkdir(parents=True)
    (output / "Polarization" / "polarization.dat").write_text(
        "The calculated polarization direction is in a, P = 1 (mod 2) C/m^2.\n"
        "The calculated polarization direction is in b, P = 2 (mod 3) C/m^2.\n"
        "The calculated polarization direction is in c, P = 3 (mod 4) C/m^2.\n",
        encoding="utf-8",
    )
    (output / "input.json").write_text(
        '{"LATTICE":{"lattice_constant":2.0,'
        '"lattice_vector":[[1,0,0],[0,1,0],[0,0,1]]}}',
        encoding="utf-8",
    )
    sample, lattice = collect_pyatb_polarization(tmp_path)
    np.testing.assert_allclose(sample.values, [1, 2, 3])
    np.testing.assert_allclose(lattice, 2.0 * np.eye(3))
