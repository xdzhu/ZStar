from __future__ import annotations

import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from zstar.v2 import (
    collect_abacus_stage,
    collect_abacus_strain_response,
    collect_pyatb_strain_response,
    plan_central_stages,
)
from zstar.v2.ensemble import ResponseEnsemble


CASE_STRU = Path("examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/run/STRU")


def _log(stress: bool = True, energy: bool = True) -> str:
    values = "\n".join(
        f" {label:>10s}  0.0000000000  0.0000000000  0.0000000000"
        for label in ("Ba1", "Ti1", "O1", "O2", "O3")
    )
    block = """
charge density convergence is achieved
E_Harris        -274.1  -3729.3
TOTAL-FORCE (eV/Angstrom)
----------------------------------------------------------------
{values}
----------------------------------------------------------------
""".format(values=values)
    if energy:
        block += "!FINAL_ETOT_IS -274.1000000000 eV\n"
    if stress:
        block += """
TOTAL-STRESS (KBAR)
----------------------------------------------------------------
 0.4 0.0 0.0
 0.0 0.4 0.0
 0.0 0.0 0.4
----------------------------------------------------------------
"""
    return block


def _stage(path: Path, *, stress: bool = True, energy: bool = True) -> None:
    path.mkdir(parents=True)
    shutil.copy2(CASE_STRU, path / "STRU")
    output = path / "OUT.POLAR"
    output.mkdir()
    (output / "running_scf.log").write_text(_log(stress, energy), encoding="utf-8")
    (path / "time.json").write_text(json.dumps({"total": 1.25}), encoding="utf-8")


def _polarization_triplet(path: Path, values: tuple[float, float, float], *, tuples: bool = True) -> dict[int, Path]:
    paths: dict[int, Path] = {}
    for direction, value in enumerate(values, start=1):
        stage = path / f"gdir-{direction}"
        output = stage / "OUT.POLAR"
        output.mkdir(parents=True)
        (stage / "INPUT").write_text(f"gdir {direction}\n", encoding="utf-8")
        suffix = f" ({value}, 0, 0)" if tuples else ""
        (output / "running_nscf.log").write_text(
            f"P = {value} (mod 10){suffix} C/m^2\n",
            encoding="utf-8",
        )
        paths[direction] = stage
    return paths


def test_collect_abacus_stage_parses_force_stress_and_iterations(tmp_path):
    stage = tmp_path / "reference"
    _stage(stage)
    record = collect_abacus_stage(stage)
    assert record["forces"].shape == (5, 3)
    np.testing.assert_allclose(record["stress"], np.eye(3) * 0.4)
    assert record["scf_iterations"] == 1
    assert record["scf_converged"] is True
    assert np.isclose(record["energy"], -274.1)


def test_collect_abacus_stage_rejects_missing_stress(tmp_path):
    stage = tmp_path / "reference"
    _stage(stage, stress=False)
    with pytest.raises(ValueError, match="TOTAL-STRESS"):
        collect_abacus_stage(stage)


def test_collect_abacus_stage_rejects_nonconverged_scf(tmp_path):
    stage = tmp_path / "reference"
    _stage(stage)
    log = next((stage / "OUT.POLAR").glob("running_scf.log"))
    log.write_text(log.read_text(encoding="utf-8").replace("charge density convergence is achieved\n", ""), encoding="utf-8")
    with pytest.raises(ValueError, match="not marked converged"):
        collect_abacus_stage(stage)


def test_collect_abacus_stage_rejects_invalid_timing_json(tmp_path):
    stage = tmp_path / "reference"
    _stage(stage)
    (stage / "time.json").write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid ABACUS time.json"):
        collect_abacus_stage(stage)


def test_collect_abacus_stage_keeps_missing_energy_explicit(tmp_path):
    stage = tmp_path / "reference"
    _stage(stage, energy=False)
    record = collect_abacus_stage(stage)
    assert record["energy"] is None


def test_collect_abacus_strain_response_builds_v2_document(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id)
    ResponseEnsemble(
        reference_hash="synthetic",
        stages=tuple(
            stage.__class__(
                **{
                    **stage.to_dict(),
                    "actual_vector": stage.requested_vector,
                }
            )
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    document = collect_abacus_strain_response(root)
    assert document.backend == "abacus"
    assert document.quantity("strain_vector").shape == (3, 6)
    assert document.quantity("forces").shape == (3, 5, 3)
    assert document.quantity("stress_raw").unit == "kbar"
    assert document.quantity("energy").shape == (3,)
    assert document.metadata["polarization_collected"] is False
    assert document.metadata["energy_collected"] is True


def test_collect_abacus_strain_response_rejects_declared_missing_stage(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    ResponseEnsemble(
        reference_hash="synthetic",
        stages=stages,
    ).write(root / "ensemble.json")
    with pytest.raises(ValueError, match="running_scf.log"):
        collect_abacus_strain_response(root)


def test_collect_abacus_strain_response_does_not_zero_fill_missing_energy(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference", energy=False)
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, energy=False)
    ResponseEnsemble(
        reference_hash="synthetic",
        stages=tuple(
            stage.__class__(
                **{
                    **stage.to_dict(),
                    "actual_vector": stage.requested_vector,
                }
            )
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    document = collect_abacus_strain_response(root)
    assert "energy" not in {quantity.name for quantity in document.quantities}
    assert document.metadata["energy_collected"] is False


def test_collect_abacus_strain_response_optionally_adds_polarization_quantities(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id)
    ResponseEnsemble(
        reference_hash="synthetic",
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    polarization = {"reference": _polarization_triplet(tmp_path / "polar" / "reference", (0.0, 0.0, 0.0))}
    for stage in stages:
        polarization[stage.stage_id] = _polarization_triplet(
            tmp_path / "polar" / stage.stage_id,
            (0.1, 0.2, 0.3),
        )
    document = collect_abacus_strain_response(root, polarization_stages=polarization)
    assert document.quantity("polarization_gdir").shape == (3, 3)
    assert document.quantity("polarization_quantum").shape == (3, 3)
    assert document.quantity("polarization_cartesian_directional").shape == (3, 3, 3)
    np.testing.assert_allclose(
        document.quantity("polarization_cartesian").values,
        [[0.0, 0.0, 0.0], [0.6, 0.0, 0.0], [0.6, 0.0, 0.0]],
    )
    assert document.quantity("polarization_gdir").coordinate_system == "lattice_direction_scalar"
    assert document.metadata["polarization_collected"] is True
    assert document.metadata["polarization_cartesian_collected"] is True


def test_collect_abacus_strain_response_rejects_missing_polarization_mapping(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id)
    ResponseEnsemble(
        reference_hash="synthetic",
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    with pytest.raises(ValueError, match="missing mappings"):
        collect_abacus_strain_response(root, polarization_stages={})


def test_collect_abacus_strain_response_rejects_low_dimensional_berry_without_normalization(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id)
    ResponseEnsemble(
        reference_hash="synthetic",
        dimensionality=2,
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    polarization = {"reference": _polarization_triplet(tmp_path / "polar" / "reference", (0.0, 0.0, 0.0))}
    for stage in stages:
        polarization[stage.stage_id] = _polarization_triplet(
            tmp_path / "polar" / stage.stage_id,
            (0.1, 0.2, 0.3),
        )
    with pytest.raises(ValueError, match="dimensionality=3"):
        collect_abacus_strain_response(root, polarization_stages=polarization)


def _pyatb_output(stage: Path, values: tuple[float, float, float]) -> None:
    output = stage / "pyatb" / "Out"
    (output / "Polarization").mkdir(parents=True)
    (output / "Polarization" / "polarization.dat").write_text(
        "".join(
            f"The calculated polarization direction is in {axis}, "
            f"P = {value} (mod 10) C/m^2.\n"
            for axis, value in zip(("a", "b", "c"), values)
        ),
        encoding="utf-8",
    )
    (output / "Polarization" / "zstar_precision.json").write_text(
        '{"adapter":"zstar.pyatb_precision","numerical_kernel_changed":false}',
        encoding="utf-8",
    )
    (output / "input.json").write_text(
        '{"LATTICE":{"lattice_constant":1.0,'
        '"lattice_vector":[[1,0,0],[0,1,0],[0,0,1]]}}',
        encoding="utf-8",
    )


def test_collect_pyatb_strain_response_uses_one_three_direction_run_per_stage(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference")
    _pyatb_output(root / "reference", (0.0, 0.0, 0.0))
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id)
        _pyatb_output(root / stage.stage_id, (0.1, 0.2, 0.3))
    ResponseEnsemble(
        reference_hash="synthetic",
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    document = collect_pyatb_strain_response(root)
    assert document.backend == "abacus+pyatb"
    assert document.metadata["polarization_backend"] == "pyatb"
    assert document.metadata["pyatb_run_count"] == 3
    np.testing.assert_allclose(
        document.quantity("polarization_directional").values,
        [[0.0, 0.0, 0.0], [0.1, 0.2, 0.3], [0.1, 0.2, 0.3]],
    )
    np.testing.assert_allclose(
        document.quantity("polarization_cartesian").values,
        [[0.0, 0.0, 0.0], [0.1, 0.2, 0.3], [0.1, 0.2, 0.3]],
    )


def test_collect_pyatb_strain_response_rejects_quantized_writer_by_default(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference")
    _pyatb_output(root / "reference", (0.0, 0.0, 0.0))
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id)
        _pyatb_output(root / stage.stage_id, (0.1, 0.2, 0.3))
    ResponseEnsemble(
        reference_hash="synthetic",
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    (root / "reference" / "pyatb" / "Out" / "Polarization" / "zstar_precision.json").unlink()
    with pytest.raises(ValueError, match="precision writer metadata"):
        collect_pyatb_strain_response(root)
    document = collect_pyatb_strain_response(root, require_precision=False)
    assert document.metadata["pyatb_precision_complete"] is False
