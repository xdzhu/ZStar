"""Tests for the finite-displacement force-only extraction used by the BTO example."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


COLLECTOR = Path(__file__).parents[1] / "examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/run/collect_bec_batch.py"
COMPACTOR = Path(__file__).parents[1] / "examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/run/compact_wuzhen_bec_outputs.py"
SPEC = importlib.util.spec_from_file_location("zstar_bec_collector", COLLECTOR)
assert SPEC and SPEC.loader
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)
COMPACT_SPEC = importlib.util.spec_from_file_location("zstar_bec_compactor", COMPACTOR)
assert COMPACT_SPEC and COMPACT_SPEC.loader
compactor = importlib.util.module_from_spec(COMPACT_SPEC)
COMPACT_SPEC.loader.exec_module(compactor)


def test_abacus_energy_parser_uses_final_marker(tmp_path):
    stage = tmp_path / "0.no-move" / "OUT.POLAR"
    stage.mkdir(parents=True)
    (stage / "running_scf.log").write_text(
        "final etot is -1.0 eV\n!FINAL_ETOT_IS -1.234567 eV\n",
        encoding="utf-8",
    )
    assert collector._read_abacus_energy(stage.parent) == -1.234567


def test_kpoint_metadata_reads_supercell_mesh_instead_of_primitive_default(tmp_path):
    stage = tmp_path / "0.no-move"
    stage.mkdir(parents=True)
    (stage / "KPT").write_text(
        "K_POINTS\n0\nGamma\n5 5 5 0 0 0\n", encoding="utf-8"
    )
    assert collector._read_kpoints_label(stage) == "Gamma 5x5x5"


def test_kpoint_metadata_records_abacus_automatic_kspacing_without_kpt(tmp_path):
    stage = tmp_path / "0.no-move"
    stage.mkdir(parents=True)
    (stage / "INPUT-scf").write_text("kspacing            0.1\n", encoding="utf-8")
    assert collector._read_kpoints_label(stage) == "ABACUS automatic kspacing=0.1 (1/bohr)"


def test_force_only_family_keeps_bec_missing_and_parent_link(tmp_path, monkeypatch):
    frame_root = tmp_path / "frame-7"
    for name, energy in (("0.no-move", -10.0), ("disp-001", -9.9)):
        stage = frame_root / name / "OUT.POLAR"
        stage.mkdir(parents=True)
        (stage.parent / "STRU").write_text("mock", encoding="utf-8")
        (stage / "running_scf.log").write_text(
            f"!FINAL_ETOT_IS {energy} eV\n", encoding="utf-8"
        )

    class FakeAtoms:
        symbols = ["Ba", "Ti", "O"]
        cell = np.eye(3)
        positions = np.zeros((3, 3))

    def fake_read_structure(path):
        atoms = FakeAtoms()
        if Path(path).parent.name == "disp-001":
            atoms.positions = np.array([[0.01, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        return atoms

    monkeypatch.setattr("zstar.workflow.scf_is_complete", lambda stage: True)
    monkeypatch.setattr("zstar.shared_response.read_structure", fake_read_structure)
    monkeypatch.setattr(
        "zstar.shared_response.actual_displacement",
        lambda reference, displaced: (0, np.array([0.01, 0.0, 0.0])),
    )
    monkeypatch.setattr(
        "zstar.shared_abacus.read_forces",
        lambda stage: np.ones((3, 3), dtype=float),
    )
    parent = {
        "frame_id": "7",
        "structure_id": "parent-7",
        "chemical_symbols": ["Ba", "Ti", "O"],
        "cell": np.eye(3).tolist(),
        "positions": np.zeros((3, 3)).tolist(),
        "energy": -10.25,
        "forces": np.full((3, 3), 0.25).tolist(),
        "pbc": [True, True, True],
        "temperature": 300.0,
        "phase_label": "cubic",
    }
    rows = collector._collect_force_only_frames(parent, frame_root)
    assert [row.frame_id for row in rows] == ["7::0.no-move", "7::disp-001"]
    assert all(not row.born_effective_charges_available for row in rows)
    assert all(row.born_effective_charges is None for row in rows)
    assert rows[1].metadata["parent_frame_id"] == "7"
    assert rows[1].metadata["data_role"] == "finite-displacement-force-only-support"
    assert rows[1].metadata["correlation_group"] == "bec-family:7"
    assert rows[1].metadata["displaced_atom_index"] == 0
    assert rows[1].energy == -9.9
    assert rows[0].energy == -10.25
    assert np.allclose(rows[0].forces, 0.25)
    assert rows[0].metadata["force_source"] == "selected-parent-dft-label"
    assert rows[0].metadata["energy_source"] == "selected-parent-dft-label"


def test_reference_force_fallback_does_not_require_second_scf(tmp_path, monkeypatch):
    frame_root = tmp_path / "frame-9"
    for name, log in (("0.no-move", "!FINAL_ETOT_IS -11.0 eV\n"), ("disp-001", "!FINAL_ETOT_IS -10.9 eV\nTOTAL-FORCE (eV/Angstrom)\n")):
        stage = frame_root / name / "OUT.POLAR"
        stage.mkdir(parents=True)
        (stage.parent / "STRU").write_text("mock", encoding="utf-8")
        (stage / "running_scf.log").write_text(log, encoding="utf-8")

    class FakeAtoms:
        symbols = ["Ba", "Ti", "O"]
        cell = np.eye(3)
        positions = np.zeros((3, 3))

    def fake_read_structure(path):
        atoms = FakeAtoms()
        if Path(path).parent.name == "disp-001":
            atoms.positions = np.array([[0.01, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        return atoms

    def force_reader(stage):
        if stage.name == "0.no-move":
            raise RuntimeError("reference log intentionally has no force block")
        return np.ones((3, 3), dtype=float)

    monkeypatch.setattr("zstar.workflow.scf_is_complete", lambda stage: True)
    monkeypatch.setattr("zstar.shared_response.read_structure", fake_read_structure)
    monkeypatch.setattr("zstar.shared_response.actual_displacement", lambda reference, displaced: (0, np.array([0.01, 0.0, 0.0])))
    monkeypatch.setattr("zstar.shared_abacus.read_forces", force_reader)
    parent = {
        "frame_id": "9",
        "structure_id": "parent-9",
        "chemical_symbols": ["Ba", "Ti", "O"],
        "cell": np.eye(3).tolist(),
        "positions": np.zeros((3, 3)).tolist(),
        "energy": -11.25,
        "forces": np.full((3, 3), 0.125).tolist(),
        "pbc": [True, True, True],
        "temperature": 600.0,
        "phase_label": "cubic",
    }
    rows = collector._collect_force_only_frames(parent, frame_root)
    assert rows[0].energy == -11.25
    assert np.allclose(rows[0].forces, 0.125)
    assert rows[0].metadata["force_source"] == "selected-parent-dft-label"
    assert rows[1].metadata["force_source"] == "bec-workflow-abacus-scf"


def test_reference_force_fallback_reorders_extxyz_species_blocks(tmp_path, monkeypatch):
    frame_root = tmp_path / "frame-10"
    for name in ("0.no-move", "disp-001"):
        stage = frame_root / name / "OUT.POLAR"
        stage.mkdir(parents=True)
        (stage.parent / "STRU").write_text("mock", encoding="utf-8")
        (stage / "running_scf.log").write_text(
            "!FINAL_ETOT_IS -12.0 eV\nTOTAL-FORCE (eV/Angstrom)\n",
            encoding="utf-8",
        )

    class FakeAtoms:
        # ABACUS species-block order differs from the selected ExtXYZ order.
        symbols = ["Ba", "Ti", "O"]
        cell = np.eye(3)
        positions = np.zeros((3, 3))

    monkeypatch.setattr("zstar.workflow.scf_is_complete", lambda stage: True)
    monkeypatch.setattr("zstar.shared_response.read_structure", lambda path: FakeAtoms())
    monkeypatch.setattr("zstar.shared_response.actual_displacement", lambda reference, displaced: (0, np.zeros(3)))
    monkeypatch.setattr("zstar.shared_abacus.read_forces", lambda stage: np.ones((3, 3)))
    parent = {
        "frame_id": "10",
        "structure_id": "parent-10",
        "chemical_symbols": ["Ba", "O", "Ti"],
        "cell": np.eye(3).tolist(),
        "positions": np.zeros((3, 3)).tolist(),
        "energy": -12.5,
        "forces": [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]],
        "pbc": [True, True, True],
    }
    rows = collector._collect_force_only_frames(parent, frame_root)
    assert rows[0].chemical_symbols == ["Ba", "Ti", "O"]
    assert np.asarray(rows[0].forces).tolist() == [[1.0, 0.0, 0.0], [3.0, 0.0, 0.0], [2.0, 0.0, 0.0]]
    assert rows[0].metadata["parent_force_atom_permutation"] == [0, 2, 1]


def test_compact_energy_and_force_parser_keeps_final_labels(tmp_path):
    stage = tmp_path / "disp-001" / "OUT.POLAR"
    stage.mkdir(parents=True)
    (stage / "running_scf.log").write_text(
        "!FINAL_ETOT_IS -2.5 eV\n"
        "TOTAL-FORCE (eV/Angstrom)\n"
        "1 Ba 0.1 -0.2 0.3\n"
        "2 O -0.1 0.2 -0.3\n"
        "total time 1 sec\n",
        encoding="utf-8",
    )
    energy, forces = compactor._energy_and_forces(stage.parent, 2)
    assert energy == -2.5
    assert forces == [[0.1, -0.2, 0.3], [-0.1, 0.2, -0.3]]


def test_compact_reference_can_use_existing_parent_labels_without_rerun(tmp_path):
    stage = tmp_path / "0.no-move" / "OUT.POLAR"
    stage.mkdir(parents=True)
    (stage / "running_scf.log").write_text(
        "!FINAL_ETOT_IS -2.5 eV\ncharge density convergence is achieved\n",
        encoding="utf-8",
    )
    energy, forces = compactor._energy_and_forces(
        stage.parent,
        2,
        reference_labels=(-2.75, [[0.1, -0.2, 0.3], [-0.1, 0.2, -0.3]]),
    )
    assert energy == -2.75
    assert forces == [[0.1, -0.2, 0.3], [-0.1, 0.2, -0.3]]


def test_compactor_counts_scientific_notation_coordinates(tmp_path):
    source = tmp_path / "stage"
    source.mkdir()
    (source / "STRU").write_text(
        "ATOMIC_POSITIONS\nDirect\n"
        "Ba\n0\n1\n-2.3e-05 0.1 0.2 m 1 1 1\n"
        "O\n0\n1\n0.3 0.4 0.5 m 1 1 1\n",
        encoding="utf-8",
    )
    # This is a focused regression for the coordinate-counting expression;
    # the first coordinate must not be lost merely because it uses `e-05`.
    text = (source / "STRU").read_text(encoding="utf-8")
    match = compactor.re.search(r"(?is)ATOMIC_POSITIONS.*", text)
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    coordinate = compactor.re.compile(r"^\s*%s\s+%s\s+%s\b" % (number, number, number))
    assert sum(bool(coordinate.match(line)) for line in match.group(0).splitlines()) == 2


def test_incomplete_manifest_stage_set_is_rejected(tmp_path):
    frame_root = tmp_path / "frame-8"
    (frame_root / "0.no-move").mkdir(parents=True)
    (frame_root / "disp-001").mkdir()
    (frame_root / "shared_response.json").write_text(
        '{"stages": [{"name": "disp-001"}, {"name": "disp-002"}]}\n',
        encoding="utf-8",
    )
    try:
        collector._response_stages(frame_root)
    except RuntimeError as exc:
        assert "expected" in str(exc)
    else:
        raise AssertionError("an absent displacement stage must reject the family")


def test_force_reader_falls_back_when_phonopy_parser_has_unbound_natom(tmp_path, monkeypatch):
    from zstar import shared_abacus

    stage = tmp_path / "0.no-move" / "OUT.POLAR"
    stage.mkdir(parents=True)
    (stage / "running_scf.log").write_text(
        "charge density convergence is achieved\n"
        "TOTAL-FORCE (eV/Angstrom)\n"
        "1 Ba 0.1 -0.2 0.3\n"
        "2 O -0.1 0.2 -0.3\n"
        "total time 1 sec\n",
        encoding="utf-8",
    )

    class FakeAtoms:
        def __len__(self):
            return 2

    monkeypatch.setattr(shared_abacus, "read_structure", lambda path: FakeAtoms())
    monkeypatch.setattr("zstar.workflow.scf_is_complete", lambda path: True)

    def broken_parser(path):
        raise UnboundLocalError("natom")

    monkeypatch.setattr("phonopy.interface.abacus.read_abacus_output", broken_parser)
    values = shared_abacus.read_forces(stage.parent)
    assert values.tolist() == [[0.1, -0.2, 0.3], [-0.1, 0.2, -0.3]]
