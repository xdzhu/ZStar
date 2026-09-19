from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/data/v2_pzt_strain005plus_terminal_audit_20260919.json"


def test_pzt_strain005plus_terminal_failure_is_not_promoted() -> None:
    record = json.loads(AUDIT.read_text(encoding="utf-8"))

    assert record["stage"] == "strain-005+"
    assert record["status"] == "terminal_ionic_nonconvergence_rejected"
    assert record["scf_converged"] is True
    assert record["ionic_relaxation_converged"] is False
    assert record["accepted_response_point"] is False
    assert record["accepted_full_tensor"] is False
    assert record["pyatb"]["executed"] is False

    gate = record["force_gate"]
    assert gate["metric"] == "maximum_absolute_cartesian_component"
    assert gate["observed_eV_per_angstrom"] > gate["threshold_eV_per_angstrom"]
    assert gate["passed"] is False

    ensemble = record["ensemble_status"]
    assert ensemble["accepted_strain_points"] == 11
    assert ensemble["required_strain_points"] == 12
    assert ensemble["complete_central_difference_e_C_d_available"] is False


def test_pzt_strain005plus_resource_and_hash_provenance() -> None:
    record = json.loads(AUDIT.read_text(encoding="utf-8"))
    runtime = record["runtime"]

    assert (runtime["node"], runtime["mpi"], runtime["omp"]) == ("cu26", 40, 1)
    assert runtime["rank_wall_core_hours"] == pytest.approx(
        runtime["elapsed_seconds"] * runtime["mpi"] / 3600.0
    )
    assert record["provenance"]["active_inputs_modified"] is False
    assert record["provenance"]["automatic_retry"] is False
    assert all(len(value) == 64 for value in record["sha256"].values())
