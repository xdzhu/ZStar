import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "examples" / "Piezoelectric_Response"


@pytest.mark.parametrize("name", ["AlN", "ZnO"])
def test_curated_piezoelectric_case_is_self_contained_and_validated(name):
    case = CASES / name
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_piezoelectric_example.py"), str(case)],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)
    assert report["status"] == "validated"
    assert "d33" in " ".join(report)
    assert "dft_functional      pbe" in (case / "run" / "INPUT").read_text(encoding="utf-8")
    assert (case / "run.sh").is_file()


def test_public_case_index_excludes_unfinished_pzt():
    index = (CASES / "README.md").read_text(encoding="utf-8")
    assert "AlN" in index and "ZnO" in index
    assert "incomplete PZT" in index
    assert not (CASES / "PZT").exists()
