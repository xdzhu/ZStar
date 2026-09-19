import json
from types import SimpleNamespace

import numpy as np
import pytest

from tools.continue_v2_pbe_piezo import run_logged, structure_gate


def test_phase_gate_uses_fixed_symprec_and_rejects_wrong_phase(monkeypatch):
    import spglib
    seen = {}
    def dataset(cell, symprec):
        seen['symprec'] = symprec
        return SimpleNamespace(number=186)
    monkeypatch.setattr(spglib, 'get_symmetry_dataset', dataset)
    assert structure_gate(np.eye(3), [[0,0,0]], ['Al'], 186) == 186
    assert seen['symprec'] == .001
    with pytest.raises(ValueError, match='Phase changed'):
        structure_gate(np.eye(3), [[0,0,0]], ['Al'], 99)


def test_failed_execution_keeps_provenance_and_never_blindly_retries(tmp_path, monkeypatch):
    calls = []
    def failed(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr('tools.continue_v2_pbe_piezo.subprocess.run', failed)
    with pytest.raises(RuntimeError, match='failed with 1'):
        run_logged(['calculator'], tmp_path, 'relax', 32)
    provenance = json.loads((tmp_path/'relax_execution.json').read_text())
    assert provenance['mpi'] == 32 and provenance['omp'] == 1
    assert provenance['returncode'] == 1
    with pytest.raises(RuntimeError, match='no blind retry'):
        run_logged(['calculator'], tmp_path, 'relax', 32)
    assert calls == [['calculator']]


def test_successful_execution_can_resume_without_new_calculator(tmp_path, monkeypatch):
    calls = []
    def success(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr('tools.continue_v2_pbe_piezo.subprocess.run', success)
    run_logged(['calculator'], tmp_path, 'fixed_cell', 40)
    run_logged(['calculator'], tmp_path, 'fixed_cell', 40)
    assert calls == [['calculator']]
