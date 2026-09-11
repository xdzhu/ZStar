from __future__ import annotations

import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from zstar.v2 import (
    collect_abacus_stage,
    collect_abacus_strain_response,
    plan_central_stages,
)
from zstar.v2.ensemble import ResponseEnsemble


CASE_STRU = Path("examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/run/STRU")


def _log(stress: bool = True) -> str:
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


def _stage(path: Path, *, stress: bool = True) -> None:
    path.mkdir(parents=True)
    shutil.copy2(CASE_STRU, path / "STRU")
    output = path / "OUT.POLAR"
    output.mkdir()
    (output / "running_scf.log").write_text(_log(stress), encoding="utf-8")
    (path / "time.json").write_text(json.dumps({"total": 1.25}), encoding="utf-8")


def test_collect_abacus_stage_parses_force_stress_and_iterations(tmp_path):
    stage = tmp_path / "reference"
    _stage(stage)
    record = collect_abacus_stage(stage)
    assert record["forces"].shape == (5, 3)
    np.testing.assert_allclose(record["stress"], np.eye(3) * 0.4)
    assert record["scf_iterations"] == 1
    assert record["scf_converged"] is True


def test_collect_abacus_stage_rejects_missing_stress(tmp_path):
    stage = tmp_path / "reference"
    _stage(stage, stress=False)
    with pytest.raises(ValueError, match="TOTAL-STRESS"):
        collect_abacus_stage(stage)


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
    assert document.metadata["polarization_collected"] is False

