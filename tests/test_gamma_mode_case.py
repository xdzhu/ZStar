import json
import subprocess
import sys
from pathlib import Path

import pytest


CASE = Path(__file__).resolve().parents[1] / "examples" / "Benchmarks" / "cs2sno3_gamma_modes"


def test_cs2sno3_reproduces_translation_and_optical_diagnostics():
    result = subprocess.run(
        [sys.executable, "reproduce.py"],
        cwd=CASE / "run",
        capture_output=True,
        text=True,
        check=True,
    )
    assert "raw_primitive_dfpt: flagged=[1]" in result.stdout
    observed = json.loads((CASE / "run" / "output" / "mode_audit.json").read_text())
    expected = json.loads((CASE / "results" / "expected_mode_audit.json").read_text())
    for name in expected:
        assert observed[name]["flagged_mode_numbers"] == expected[name]["flagged_mode_numbers"]
        assert observed[name]["atom_count"] == expected[name]["atom_count"]
        for actual, reference in zip(observed[name]["negative_modes"], expected[name]["negative_modes"]):
            assert actual["classification"] == reference["classification"]
            assert actual["frequency_cm-1"] == pytest.approx(reference["frequency_cm-1"], abs=0.05)
            assert actual["translation_overlap"] == pytest.approx(reference["translation_overlap"], abs=0.01)
