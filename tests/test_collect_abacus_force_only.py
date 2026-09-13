"""Regression tests for collecting completed ABACUS labels verbatim."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/run/collect_abacus_force_only.py"
SPEC = importlib.util.spec_from_file_location("collect_abacus_force_only", SOURCE)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


def test_read_stage_copies_final_energy_and_forces_without_shift(tmp_path):
    stage = tmp_path / "0.no-move"
    out = stage / "OUT.POLAR"
    out.mkdir(parents=True)
    (stage / "STRU").write_text(
        "LATTICE_CONSTANT\n1.0\nLATTICE_VECTORS\n1 0 0\n0 1 0\n0 0 1\n"
        "ATOMIC_POSITIONS\nDirect\nBa\n0\n1\n0 0 0\n",
        encoding="utf-8",
    )
    (out / "running_scf.log").write_text(
        "!FINAL_ETOT_IS -3728.664663462338 eV\n"
        "TOTAL-FORCE (eV/Angstrom)\n"
        "1 Ba 0.125 -0.25 0.5\n",
        encoding="utf-8",
    )
    row = collector.read_stage(stage)
    assert row["energy"] == -3728.664663462338
    assert row["forces"] == [[0.125, -0.25, 0.5]]


def test_collected_row_marks_bec_explicitly_missing(tmp_path):
    parent = tmp_path / "frame-42"
    stage = parent / "0.no-move"
    out = stage / "OUT.POLAR"
    out.mkdir(parents=True)
    (parent / ".zstar").mkdir()
    (parent / ".zstar" / "bec.json").write_text("{}", encoding="utf-8")
    (stage / "STRU").write_text(
        "LATTICE_CONSTANT\n1.0\nLATTICE_VECTORS\n1 0 0\n0 1 0\n0 0 1\n"
        "ATOMIC_POSITIONS\nDirect\nBa\n0\n1\n0 0 0\n",
        encoding="utf-8",
    )
    (out / "running_scf.log").write_text(
        "!FINAL_ETOT_IS -1.0 eV\nTOTAL-FORCE (eV/Angstrom)\n1 Ba 0 0 0\n",
        encoding="utf-8",
    )
    rows = collector.collect(parent)
    assert len(rows) == 1
    assert rows[0]["born_effective_charges_available"] is False
    assert rows[0]["born_effective_charges"] is None
    assert rows[0]["energy"] == -1.0
