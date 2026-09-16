from __future__ import annotations

import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from zstar.v2 import (
    collect_abacus_stage,
    collect_abacus_strain_response,
    collect_pyatb_strain_response,
    plan_central_stages,
    voigt_to_strain_tensor,
)
from zstar.v2.ensemble import ResponseEnsemble
from zstar.shared_response import read_structure, write_structure
from zstar.v2.abacus import _augment_reference_symmetry
from zstar.dimensions import DimensionSpec


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


def _stage(
    path: Path,
    *,
    stress: bool = True,
    energy: bool = True,
    relaxed: bool = False,
    strain_vector: tuple[float, ...] | None = None,
) -> None:
    path.mkdir(parents=True)
    shutil.copy2(CASE_STRU, path / "STRU")
    if strain_vector is not None:
        atoms = read_structure(path / "STRU")
        atoms.cell = np.asarray(atoms.cell) @ (np.eye(3) + voigt_to_strain_tensor(strain_vector)).T
        write_structure(path / "STRU", path / "STRU", atoms)
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
    assert np.isclose(record["force_max_eV_per_angstrom"], 0.0)
    assert np.isclose(record["stress_max_abs_kbar"], 0.4)
    assert record["scf_iterations"] == 1
    assert record["scf_converged"] is True
    assert np.isclose(record["energy"], -274.1)
    assert record["force_blocks_count"] == 1
    np.testing.assert_allclose(record["initial_forces"], record["forces"])
    assert record["band_gap"] is None


def test_collect_abacus_stage_extracts_occupation_manifold_gap(tmp_path):
    stage = tmp_path / "reference"
    _stage(stage)
    (stage / "OUT.POLAR" / "istate.info").write_text(
        "BAND Energy(ev) Occupation Kpoint = 1\n"
        "     1       -3.0     0.03125\n"
        "     2        1.5     0.03125\n"
        "     3        4.0     0\n"
        "     4        6.0     0\n",
        encoding="utf-8",
    )
    record = collect_abacus_stage(stage)
    gap = record["band_gap"]
    assert gap is not None
    assert gap["insulating"] is True
    assert gap["gap_eV"] == pytest.approx(2.5)
    assert gap["vbm_eV"] == pytest.approx(1.5)
    assert gap["cbm_eV"] == pytest.approx(4.0)


def test_collect_abacus_stage_keeps_initial_and_final_force_blocks(tmp_path):
    stage = tmp_path / "relaxed-multi-block"
    _stage(stage, relaxed=True)
    log = stage / "OUT.POLAR" / "running_relax.log"
    extra = _log().replace("0.0000000000", "0.1250000000", 1)
    log.write_text(log.read_text(encoding="utf-8") + "\n" + extra + "\nRelaxation is converged!\n", encoding="utf-8")
    record = collect_abacus_stage(stage)
    assert record["force_blocks_count"] == 2
    assert np.isclose(record["initial_force_max_eV_per_angstrom"], 0.0)
    assert np.isclose(record["force_max_eV_per_angstrom"], 0.125)
    assert np.isclose(record["initial_forces"][0, 0], 0.0)
    assert np.isclose(record["forces"][0, 0], 0.125)


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
    reference_log = root / "reference" / "OUT.POLAR" / "running_scf.log"
    reference_log.write_text(
        "\n".join(
            line.replace("0.0000000000", "0.0005000000", 1) if "Ba1" in line else line
            for line in reference_log.read_text(encoding="utf-8").splitlines()
        )
        + "\n",
        encoding="utf-8",
    )
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, relaxed=True, strain_vector=stage.requested_vector)
        (root / stage.stage_id / "INPUT").write_text(
            "scf_thr 1e-8\nforce_thr_ev 1e-5\nrelax_nmax 100\n", encoding="utf-8"
        )
    ResponseEnsemble(
        reference_hash="synthetic",
        metadata={
            "ion_relaxation": "relaxed-ion",
            "response_reference_force_thr_ev": 1.0e-3,
            "force_thr_ev": 1.0e-5,
        },
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
    initial_forces = document.quantity("forces_initial")
    assert quantity.shape == (3, 5, 3)
    assert initial_forces.shape == (3, 5, 3)
    assert initial_forces.ion_relaxation == "clamped-ion"
    assert initial_forces.provenance["definition"] == "first TOTAL-FORCE block in each relaxed-ion log"
    assert quantity.ion_relaxation == "relaxed-ion"
    assert quantity.provenance["acoustic_gauge"] == "unfixed_raw_displacement"
    np.testing.assert_allclose(quantity.values[0], 0.0)
    # The tracked tetragonal fixture has c = 4.1 Å; the synthetic relaxed
    # structure moves atom 1 by 0.01 in fractional z.
    np.testing.assert_allclose(quantity.values[1:, 1, 2], 0.01 * 4.1, atol=1.0e-12)
    assert document.metadata["internal_displacement_collected"] is True
    assert document.metadata["reference_force_max_eV_per_angstrom"] == pytest.approx(5.0e-4)
    assert document.metadata["reference_force_thr_eV_per_angstrom"] == 1.0e-3
    assert document.provenance["reference_force_max_eV_per_angstrom"] == pytest.approx(5.0e-4)
    assert document.provenance["reference_force_thr_eV_per_angstrom"] == 1.0e-3
    assert document.convergence["force_thr_ev"] == 1.0e-5
    assert document.convergence["strain_force_thr_ev_values"] == [1.0e-5]
    assert document.convergence["serialized_scf_thr_values"] == [1.0e-8]
    assert document.metadata["strain_force_thr_ev_values"] == [1.0e-5]
    assert document.metadata["strain_relax_nmax_values"] == [100.0]
    assert document.provenance["stages"][1]["configured_force_thr_ev"] == "1e-5"
    assert document.provenance["stages"][1]["configured_relax_nmax"] == "100"


def test_collect_abacus_strain_response_rejects_unrelaxed_reference(tmp_path):
    root = tmp_path / "relaxed-unbalanced-reference"
    _stage(root / "reference")
    reference_log = root / "reference" / "OUT.POLAR" / "running_scf.log"
    reference_log.write_text(
        "\n".join(
            line.replace("0.0000000000", "0.0200000000", 1) if "Ba1" in line else line
            for line in reference_log.read_text(encoding="utf-8").splitlines()
        )
        + "\n",
        encoding="utf-8",
    )
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, relaxed=True, strain_vector=stage.requested_vector)
    ResponseEnsemble(
        reference_hash="synthetic",
        metadata={"ion_relaxation": "relaxed-ion", "force_thr_ev": 1.0e-3},
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    with pytest.raises(ValueError, match="reference is not internally equilibrated"):
        collect_abacus_strain_response(root)


def test_collect_abacus_strain_response_rejects_stale_stage_coordinates(tmp_path):
    root = tmp_path / "relaxed-stale-stage"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, relaxed=True, strain_vector=stage.requested_vector)
    shutil.copy2(root / stages[0].stage_id / "STRU", root / stages[0].stage_id / "STRU_INITIAL")
    stale = read_structure(root / stages[0].stage_id / "STRU_INITIAL")
    scaled_positions = np.asarray(stale.scaled_positions, dtype=float)
    scaled_positions[0, 2] += 1.0e-5
    stale.scaled_positions = scaled_positions
    write_structure(root / stages[0].stage_id / "STRU_INITIAL", root / stages[0].stage_id / "STRU_INITIAL", stale)
    ResponseEnsemble(
        reference_hash="synthetic",
        metadata={"ion_relaxation": "relaxed-ion", "force_thr_ev": 1.0e-3},
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    with pytest.raises(ValueError, match="initial fractional coordinates differ from reference"):
        collect_abacus_strain_response(root)


def test_collect_abacus_strain_response_rejects_mismatched_serialized_strain(tmp_path):
    root = tmp_path / "mismatched-serialized-strain"
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
    with pytest.raises(ValueError, match="serialized cell strain differs"):
        collect_abacus_strain_response(root)


def test_collect_abacus_strain_response_rejects_relaxed_stage_without_final_structure(tmp_path):
    root = tmp_path / "relaxed-missing"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, relaxed=False, strain_vector=stage.requested_vector)
    ResponseEnsemble(
        reference_hash="synthetic",
        metadata={"ion_relaxation": "relaxed-ion", "force_thr_ev": 1.0e-3},
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
        _stage(root / stage.stage_id, strain_vector=stage.requested_vector)
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


@pytest.mark.parametrize(
    ("status", "message"),
    [
        ("failed", "rerun the failed stage"),
        ("skipped", "remove the skipped stage or regenerate the ensemble"),
    ],
)
def test_collect_abacus_strain_response_rejects_terminal_failed_stage_status(
    tmp_path, status, message
):
    root = tmp_path / f"terminal-{status}"
    _stage(root / "reference")
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, strain_vector=stage.requested_vector)
    failed_stage = stages[0].__class__(
        **{
            **stages[0].to_dict(),
            "actual_vector": stages[0].requested_vector,
            "status": status,
            "error": "synthetic terminal state",
        }
    )
    manifest_stages = (failed_stage, *tuple(
        stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
        for stage in stages[1:]
    ))
    ResponseEnsemble(
        reference_hash="synthetic",
        stages=manifest_stages,
    ).write(root / "ensemble.json")
    with pytest.raises(ValueError, match=message):
        collect_abacus_strain_response(root)


def test_collect_abacus_strain_response_does_not_zero_fill_missing_energy(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference", energy=False)
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, energy=False, strain_vector=stage.requested_vector)
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
        _stage(root / stage.stage_id, strain_vector=stage.requested_vector)
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
        _stage(root / stage.stage_id, strain_vector=stage.requested_vector)
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
        _stage(root / stage.stage_id, strain_vector=stage.requested_vector)
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
        _stage(root / stage.stage_id, strain_vector=stage.requested_vector)
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
    assert document.metadata["polarization_cartesian_collected"] is True
    assert document.metadata["pyatb_run_count"] == 3
    assert document.symmetry["reference_observed"]["operation_count"] > 0
    assert document.metadata["symmetry_audit"]["representation_source"] == "observed_reference"
    cartesian_provenance = document.quantity("polarization_cartesian").provenance
    assert cartesian_provenance["branch_matched"] is True
    assert cartesian_provenance["branch_matching_quantity"] == "polarization_directional_matched"
    assert cartesian_provenance["branch_reference_stage"] == 0
    assert cartesian_provenance["branch_shift_max"] == 0
    assert np.isfinite(cartesian_provenance["branch_residual_max"])
    assert cartesian_provenance["branch_residual_max"] == document.metadata["branch_residual_max"]
    np.testing.assert_allclose(
        document.quantity("polarization_directional").values,
        [[0.0, 0.0, 0.0], [0.1, 0.2, 0.3], [0.1, 0.2, 0.3]],
    )
    np.testing.assert_allclose(
        document.quantity("polarization_cartesian").values,
        [[0.0, 0.0, 0.0], [0.1, 0.2, 0.3], [0.1, 0.2, 0.3]],
    )


def test_observed_symmetry_uses_fixed_v2_tolerance():
    data = json.loads(
        Path("examples/3D_Bulk/wurtzite_AlN_v2/results/response_document.json")
        .read_text(encoding="utf-8")
    )
    structure = data["structure"]
    reference = SimpleNamespace(
        cell=np.asarray(structure["lattice_angstrom"], dtype=float),
        scaled_positions=np.asarray(structure["fractional_positions"], dtype=float),
        symbols=tuple(structure["symbols"]),
    )
    preparation = dict(data["symmetry"])
    # The tracked reference has ~1e-4 fractional-coordinate round-off.  v2
    # uses the single declared 1e-3 tolerance for both preparation and audit.
    result = _augment_reference_symmetry(preparation, reference, DimensionSpec(3))
    assert result["reference_observed"]["space_group"] == "P6_3mc"
    assert result["reference_observed"]["symprec"] == pytest.approx(1.0e-3)
    assert result["reference_observed"]["diagnostics"]["operational_symprec_source"] == "fixed_v2_symprec"
    assert "tight_probe" not in result["reference_observed"]["diagnostics"]
    assert result["comparison"]["status"] == "consistent"


def test_collect_pyatb_strain_response_uses_each_stage_lattice_basis(tmp_path):
    root = tmp_path / "stage-specific-basis"
    _stage(root / "reference")
    _pyatb_output(root / "reference", (0.0, 0.0, 0.0))
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        path = root / stage.stage_id
        _stage(path, strain_vector=stage.requested_vector)
        _pyatb_output(path, (1.0, 0.0, 0.0))
        shear = 0.2 if stage.sign == "+" else -0.2
        (path / "pyatb" / "Out" / "input.json").write_text(
            json.dumps({"LATTICE": {"lattice_constant": 1.0,
                                      "lattice_vector": [[1.0, 0.0, shear],
                                                          [0.0, 1.0, 0.0],
                                                          [0.0, 0.0, 1.0]]}}),
            encoding="utf-8",
        )
    ResponseEnsemble(
        reference_hash="synthetic",
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")

    document = collect_pyatb_strain_response(root)
    cartesian = document.quantity("polarization_cartesian").values
    np.testing.assert_allclose(cartesian[1], [1.0 / np.sqrt(1.04), 0.0, -0.2 / np.sqrt(1.04)])
    np.testing.assert_allclose(cartesian[2], [1.0 / np.sqrt(1.04), 0.0, 0.2 / np.sqrt(1.04)])
    assert not np.allclose(cartesian[1], cartesian[2])


def test_collect_pyatb_strain_response_normalizes_explicit_two_dimensional_polarization(tmp_path):
    root = tmp_path / "slab-ensemble"
    _stage(root / "reference")
    _pyatb_output(root / "reference", (0.0, 0.0, 0.0))
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, strain_vector=stage.requested_vector)
        _pyatb_output(root / stage.stage_id, (0.1, 0.2, 0.3))
    ResponseEnsemble(
        reference_hash="synthetic",
        dimensionality=2,
        stages=tuple(
            stage.__class__(**{**stage.to_dict(), "actual_vector": stage.requested_vector})
            for stage in stages
        ),
    ).write(root / "ensemble.json")
    with pytest.raises(ValueError, match="dimensionality=3"):
        collect_pyatb_strain_response(root)
    document = collect_pyatb_strain_response(root, normalize_low_dimensional=True)
    intrinsic = document.quantity("polarization_intrinsic")
    assert intrinsic.unit == "C/m"
    assert intrinsic.normalization == "sheet_area"
    assert intrinsic.periodic_axes == ("x", "y")
    np.testing.assert_allclose(
        intrinsic.values,
        [[0.0, 0.0, 0.0], [1.0e-11, 2.0e-11, 0.0], [1.0e-11, 2.0e-11, 0.0]],
    )
    assert intrinsic.provenance["geometric_factor_units"] == ["m", "m", "m"]
    assert document.metadata["low_dimensional_normalization"] is True


def test_collect_pyatb_strain_response_rejects_quantized_writer_by_default(tmp_path):
    root = tmp_path / "ensemble"
    _stage(root / "reference")
    _pyatb_output(root / "reference", (0.0, 0.0, 0.0))
    stages = plan_central_stages(([0.001, 0, 0, 0, 0, 0],), kind="strain", prefix="strain")
    for stage in stages:
        _stage(root / stage.stage_id, strain_vector=stage.requested_vector)
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


def test_collect_pyatb_strain_response_rejects_explicit_metallic_ensemble(tmp_path):
    root = tmp_path / "metallic"
    root.mkdir()
    (root / "ensemble.json").write_text(
        json.dumps(
            {
                "schema": "zstar-v2-ensemble",
                "schema_version": "0.1",
                "reference_hash": "synthetic",
                "dimensionality": 3,
                "metadata": {"insulating": False},
                "stages": [
                    {
                        "stage_id": "strain-001+",
                        "kind": "strain",
                        "requested_vector": [0.001, 0, 0, 0, 0, 0],
                        "actual_vector": [0.001, 0, 0, 0, 0, 0],
                        "unit": "engineering_strain",
                        "expected_outputs": [],
                        "sign": "+",
                        "status": "planned",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not applicable to a metallic ensemble"):
        collect_pyatb_strain_response(root)
