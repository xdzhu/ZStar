from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from zstar.v2 import (
    BOHR_RADIUS,
    ELEMENTARY_CHARGE,
    collect_abacus_polarization_component,
    collect_abacus_polarization_stage,
    match_polarization_branch,
    parse_abacus_berry_polarization,
    unwrap_polarization_path,
)


def test_parse_abacus_berry_polarization_normalizes_supported_units():
    component = parse_abacus_berry_polarization(
        "P = 1.25D+00 (mod 3.5) (1.25, 0, 0) C/m^2"
    )
    assert component.unit == "C/m^2"
    assert component.raw_unit == "C/m^2"
    np.testing.assert_allclose([component.value, component.quantum], [1.25, 3.5])

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
    # The parser must prefer the explicit SI record when ABACUS emits both
    # the internal ``(e/Omega).bohr`` line and the converted C/m^2 line.
    np.testing.assert_allclose(component.value, 0.8906925)


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
