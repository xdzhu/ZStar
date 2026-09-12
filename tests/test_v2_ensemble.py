from __future__ import annotations

import numpy as np
import pytest

from zstar.v2 import (
    PerturbationStage,
    ResponseEnsemble,
    V2StateStore,
    plan_central_stages,
)


def test_central_plan_is_deterministic_and_requires_actual_vectors():
    stages = plan_central_stages(
        ([1.0, 0.0], [0.0, 1.0]),
        kind="strain",
        unit="1",
        expected_outputs=("polarization", "forces", "stress"),
        prefix="strain",
    )
    assert [stage.stage_id for stage in stages] == ["strain-001-", "strain-001+", "strain-002-", "strain-002+"]
    assert stages[0].requested_vector == (-1.0, 0.0)
    assert stages[1].actual_vector is None
    assert stages[1].fit_ready is False


def test_ensemble_and_v2_state_store_resume_atomically(tmp_path):
    stages = plan_central_stages(([0.01, 0.0],), kind="strain", prefix="strain")
    ensemble = ResponseEnsemble(reference_hash="abc", stages=stages, dimensionality=3)
    manifest = ensemble.write(tmp_path / "manifest.json")
    loaded = ResponseEnsemble.read(manifest)
    assert loaded.periodic_axes == ("x", "y", "z")
    assert len(loaded.pending) == 2
    completed = PerturbationStage(
        **{
            **loaded.stage("strain-001+").to_dict(),
            "actual_vector": [0.0102, 0.0],
            "status": "complete",
            "result_path": "results/strain-001+.json",
        }
    )
    resumed = loaded.with_stage(completed)
    store = V2StateStore(tmp_path)
    state_path = store.write_stage(completed)
    assert state_path.parent.name == "stages"
    assert store.read_stage("strain-001+").fit_ready
    assert len(resumed.completed) == 1
    assert (tmp_path / ".zstar" / "stages" / "strain-001+.json.tmp").exists() is False


def test_stage_validation_rejects_unsafe_or_invalid_state(tmp_path):
    with pytest.raises(ValueError, match="unsupported perturbation"):
        PerturbationStage(stage_id="a", kind="unknown", requested_vector=(1.0,))
    with pytest.raises(ValueError, match="safe"):
        V2StateStore(tmp_path).path_for("../escape")
    with pytest.raises(ValueError, match="finite"):
        plan_central_stages(([np.nan],), kind="displacement")
