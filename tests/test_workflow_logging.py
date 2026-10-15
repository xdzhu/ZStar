import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
from phonopy.structure.atoms import PhonopyAtoms
import pytest

from zstar.shared_response import symmetry_operations
from zstar.workflow import (
    StageState, WorkflowStage, WorkflowStateStore, _run_shell,
    format_status_table, run_serial_workflow,
)


def _command(*arguments):
    return (subprocess.list2cmdline(arguments) if os.name == "nt"
            else shlex.join(arguments))


def test_external_output_is_teed_before_process_exits(tmp_path, monkeypatch):
    marker = tmp_path / "observed"
    script = tmp_path / "child.py"
    script.write_text(
        "import pathlib, sys, time\n"
        "print('CHILD_READY', flush=True)\n"
        "print('CHILD_STDERR', file=sys.stderr, flush=True)\n"
        "marker = pathlib.Path(sys.argv[1])\n"
        "deadline = time.monotonic() + 10\n"
        "while not marker.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.01)\n"
        "sys.exit(0 if marker.exists() else 9)\n",
        encoding="utf-8",
    )

    class LiveOutput(io.StringIO):
        def write(self, text):
            if "CHILD_READY" in text:
                marker.touch()
            return super().write(text)

    output = LiveOutput()
    monkeypatch.setattr(sys, "stdout", output)
    log = tmp_path / "stage.log"
    _run_shell(_command(sys.executable, "-u", str(script), str(marker)),
               cwd=tmp_path, env=os.environ.copy(), log_path=log, dry_run=False,
               stage="disp-002", component="ABACUS SCF")
    text = output.getvalue()
    assert "[disp-002] [ABACUS SCF] [START]" in text
    assert "CHILD_READY" in text and "CHILD_STDERR" in text
    assert "[PASS] exit=0" in text
    saved = log.read_text(encoding="utf-8")
    assert "CHILD_READY" in saved and "CHILD_STDERR" in saved


def test_process_failure_has_stage_log_and_exit_code(tmp_path, capsys):
    log = tmp_path / "failure.log"
    command = _command(sys.executable, "-c", "import sys; print('solver failed'); sys.exit(7)")
    with pytest.raises(RuntimeError, match="PYATB band failed with exit code 7") as caught:
        _run_shell(command, cwd=tmp_path, env=os.environ.copy(), log_path=log,
                   dry_run=False, stage="0.no-move", component="PYATB band")
    assert str(log) in str(caught.value)
    output = capsys.readouterr().out
    assert "solver failed" in output
    assert "[0.no-move] [PYATB band] [FAIL] exit=7" in output


def test_scf_failure_persists_last_step_and_readable_summary(tmp_path, monkeypatch, capsys):
    reference = tmp_path / "0.no-move"
    reference.mkdir()
    (reference / "INPUT-scf").write_text("INPUT_PARAMETERS\n", encoding="utf-8")
    def fail_command(*args, **kwargs):
        raise RuntimeError("simulated solver failure")

    monkeypatch.setattr("zstar.workflow._run_shell", fail_command)
    with pytest.raises(RuntimeError, match="simulated solver failure"):
        run_serial_workflow(tmp_path, check_insulating=False, dry_run=True)
    store = WorkflowStateStore(tmp_path)
    state = store.load(WorkflowStage("0.no-move", reference, reference=True))
    assert state.status == state.scf == "failed"
    assert state.active_step == "ABACUS SCF"
    assert state.log_path and state.updated_at
    assert "ABACUS SCF" in format_status_table([state])
    assert "simulated solver failure" in (store.state_dir / "progress.log").read_text()
    assert "[stage-failed] [FAIL]" in capsys.readouterr().out


def test_state_remains_inspectable_after_a_worker_disappears(tmp_path):
    store = WorkflowStateStore(tmp_path)
    state = StageState("disp-003", str(tmp_path / "disp-003"), status="running", pyatb="running")
    store.step(state, "PYATB polarization/dielectric")
    loaded = store.load(WorkflowStage(state.name, Path(state.path)))
    assert loaded.active_step == state.active_step
    assert loaded.updated_at
    assert "last saved state" in format_status_table([loaded])


def test_canonical_status_json_is_parseable(tmp_path, capsys):
    from zstar.cli import zstar_cli

    reference = tmp_path / "0.no-move"
    reference.mkdir()
    store = WorkflowStateStore(tmp_path)
    state = StageState("0.no-move", str(reference), status="running", scf="running")
    store.step(state, "ABACUS SCF")
    capsys.readouterr()
    zstar_cli(["bec", "stat", "--root", str(tmp_path), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data[0]["active_step"] == "ABACUS SCF"
    assert data[0]["updated_at"] and data[0]["started_at"]


@pytest.mark.parametrize("distorted", [False, True])
def test_symmetry_report_records_metric_and_actionable_failure(tmp_path, distorted, capsys):
    cell = np.diag([4.0, 4.001 if distorted else 4.0, 4.0])
    atoms = PhonopyAtoms(symbols=["Si"], cell=cell, scaled_positions=[[0, 0, 0]])
    rotation = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]])
    phonon = SimpleNamespace(supercell=atoms, symmetry=SimpleNamespace(
        tolerance=1e-3, symmetry_operations={"rotations": [rotation], "translations": [[0, 0, 0]]}))
    path = tmp_path / "symmetry.json"
    if distorted:
        with pytest.raises(ValueError, match=r"stricter --symmprec .*0.0001"):
            symmetry_operations(phonon, diagnostics_path=path)
    else:
        assert len(symmetry_operations(phonon, diagnostics_path=path)) == 1
    data = json.loads(path.read_text())
    assert data["status"] == ("FAIL" if distorted else "PASS")
    assert data["symprec_A"] == 1e-3
    assert data["orthogonalization_applied"] is False
    assert (data["max_orthogonality_error"] > 1e-7) == distorted
    assert f"[SYMMETRY] [{data['status']}]" in capsys.readouterr().out
