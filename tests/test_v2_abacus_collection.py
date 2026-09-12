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
from zstar.shared_response import read_structure, write_structure


# Use the tracked v2 fixture.  The historical cubic phonon input is generated
# by some v1 workflows and is intentionally not a required checkout artifact.
CASE_STRU = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs/STRU")


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


def _stage(path: Path, *, stress: bool = True, energy: bool = True, relaxed: bool = False) -> None:
    path.mkdir(parents=True)
    shutil.copy2(CASE_STRU, path / "STRU")
    output = path / "OUT.POLAR"
    output.mkdir()
    log_text = _log(stress, energy)
    log_name = "running_scf.log"
    if relaxed:
        log_text = log_text.replace("charge density convergence is achieved\n", "")
        log_text += "\nRelaxation is converged!\n"
        log_name = "running_relax.log"
        atoms = read_structure(path / "STRU")
        scaled_positions = np.asarray(atoms.scaled_positions, dtype=float)
        scaled_positions[1, 2] += 0.01
        atoms.scaled_positions = scaled_positions
        write_structure(path / "STRU", output / "STRU_ION_D", atoms)
    (output / log_name).write_text(log_text, encoding="utf-8")
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


def test_collect_abacus_stage_accepts_relax_log_and_marks_ionic_convergence(tmp_path):
    stage = tmp_path / "relaxed"
    _stage(stage, relaxed=True)
    record = collect_abacus_stage(stage)
    assert record["scf_converged"] is False
    assert record["ionic_relaxation_converged"] is True
    assert record["log_kind"] == "running_relax.log"
    relaxed_path = Path(record["relaxed_structure_path"])
    assert relaxed_path.name == "STRU_ION_D"
    assert relaxed_path.parent.name == "OUT.POLAR"
    assert record["relaxed_structure"] is not None


def test_collect_abacus_stage_rejects_unconverged_relax_log(tmp_path):
    stage = tmp_path / "relaxed-unconverged"
    _stage(stage, relaxed=True)
    log = stage / "OUT.POLAR" / "running_relax.log"
    log.write_text(log.read_text(encoding="utf-8").replace("Relaxation is converged!", "Relaxation is not converged yet!"), encoding="utf-8")
    with pytest.raises(ValueError, match="ionic relaxation is not marked converged"):
        collect_abacus_stage(stage)


def test_collect_abacus_strain_response_collects_internal_displacements(tmp_path):
    root = tmp_path / "relaxed-ensemble"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, relaxed=True)
    ResponseEnsemble(
        reference_hash="synthetic",
        metadata={"ion_relaxation": "relaxed-ion"},
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
    quantity = document.quantity("internal_displacement")
    assert quantity.shape == (3, 5, 3)
    assert quantity.ion_relaxation == "relaxed-ion"
    np.testing.assert_allclose(quantity.values[0], 0.0)
    # The tracked tetragonal fixture has c = 4.1 Å; the synthetic relaxed
    # structure moves atom 1 by 0.01 in fractional z.
    np.testing.assert_allclose(quantity.values[1:, 1, 2], 0.01 * 4.1, atol=1.0e-12)
    assert document.metadata["internal_displacement_collected"] is True


def test_collect_abacus_strain_response_rejects_relaxed_stage_without_final_structure(tmp_path):
    root = tmp_path / "relaxed-missing"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, relaxed=False)
    ResponseEnsemble(
        reference_hash="synthetic",
        metadata={"ion_relaxation": "relaxed-ion"},
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    with pytest.raises(ValueError, match=r"missing OUT\.\*/STRU_ION_D"):
        collect_abacus_strain_response(root)


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
