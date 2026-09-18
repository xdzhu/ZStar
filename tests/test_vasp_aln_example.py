"""Preflight and failure-path tests for the polar native-backend example."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


CASE = Path(__file__).resolve().parents[1] / "examples" / "VASP_Native_Response" / "AlN"


def test_aln_seed_and_native_parallel_settings():
    import spglib
    from zstar.structure_io import read_structure

    seed = read_structure(CASE / "run" / "POSCAR")
    dataset = spglib.get_symmetry_dataset((seed.lattice_angstrom, seed.positions_fractional, [13, 13, 7, 7]))
    assert dataset.number == 186
    assert dataset.pointgroup == "6mm"
    assert np.allclose(seed.lattice_angstrom[2, :2], 0)
    incar = (CASE / "run" / "INCAR").read_text()
    assert "NCORE = 4" in incar
    assert "NPAR" not in incar
    slurm = (CASE / "run_hf.slurm").read_text()
    assert "--ntasks=64" in slurm
    assert "--exclusive" not in slurm and "--nodelist" not in slurm


@pytest.fixture
def acceptance_data(tmp_path, monkeypatch):
    from pymatgen.io.vasp import outputs

    spec = importlib.util.spec_from_file_location("aln_verifier", CASE / "verify_results.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    e = np.zeros((3, 6))
    e[0, 4] = e[1, 3] = -0.4
    e[2, :3] = [-0.58, -0.58, 1.46]
    c = np.eye(6) * 200
    epsilon = np.diag([4.5, 4.5, 4.7])
    born = np.asarray([np.eye(3) * 2.7] * 2 + [-np.eye(3) * 2.7] * 2)
    modes = SimpleNamespace(frequencies_cm1=np.asarray([0, 0, 0] + [500] * 9))
    tensor = {"piezoelectric_total_C_m2": e.tolist(), "elastic_relaxed_GPa": c.tolist(),
              "piezoelectric_d_pm_V": (e @ np.linalg.inv(c) * 1000).tolist(),
              "epsilon_static": (epsilon + np.eye(3) * 4).tolist()}
    for route in ("dfpt", "elastic"):
        folder = tmp_path / ".work" / route
        folder.mkdir(parents=True)
        (folder / "vasp_bec.json").write_text(json.dumps({"atoms": [{"tensor": b.tolist()} for b in born]}))
        (folder / "vasp_native_response.json").write_text(json.dumps({
            "tensors": tensor, "diagnostics": {"static_dielectric_max_abs": 1e-4}}))
    monkeypatch.setattr(module, "parse_vasp_outcar", lambda path: (epsilon, born))
    monkeypatch.setattr(module, "load_vasp_gamma_modes", lambda path: modes)
    monkeypatch.setattr(outputs, "Vasprun", lambda *args, **kwargs: SimpleNamespace(
        epsilon_static=epsilon, eigenvalue_band_properties=(4.0, None, None, False)))
    return module, tmp_path, modes


def test_aln_verifier_accepts_consistent_tensors(acceptance_data):
    module, root, _ = acceptance_data
    report = module.validate(root)
    assert report["passed"]
    assert report["checks"]["elastic: e = d C"]
    assert json.loads(json.dumps(report))["passed"] is True


def test_aln_verifier_rejects_missing_derived_d(acceptance_data):
    module, root, _ = acceptance_data
    path = root / ".work" / "elastic" / "vasp_native_response.json"
    record = json.loads(path.read_text())
    del record["tensors"]["piezoelectric_d_pm_V"]
    path.write_text(json.dumps(record))
    report = module.validate(root)
    assert not report["passed"]
    assert not report["checks"]["elastic: reliable derived d emitted"]


def test_aln_verifier_rejects_unstable_optical_modes(acceptance_data):
    module, root, modes = acceptance_data
    modes.frequencies_cm1[3] = -100
    assert not module.validate(root)["passed"]


def test_aln_verifier_rejects_broken_piezo_symmetry(acceptance_data):
    module, root, _ = acceptance_data
    path = root / ".work" / "elastic" / "vasp_native_response.json"
    record = json.loads(path.read_text())
    record["tensors"]["piezoelectric_total_C_m2"][0][0] = 1
    path.write_text(json.dumps(record))
    report = module.validate(root)
    assert not report["checks"]["elastic: 6mm piezo tensor"]
    assert not report["passed"]


def test_native_strain_xml_epsilon_outside_calculation_is_read(acceptance_data):
    module, root, _ = acceptance_data
    path = root / "strain.xml"
    path.write_text("<modeling><varray name='epsilon'><v>4.5 0 0</v>"
                    "<v>0 4.5 0</v><v>0 0 4.7</v></varray><calculation/></modeling>")
    epsilon = module.xml_dielectric(SimpleNamespace(epsilon_static=[]), path)
    np.testing.assert_allclose(epsilon, np.diag([4.5, 4.5, 4.7]))


def test_missing_native_strain_xml_epsilon_fails_with_guidance(acceptance_data):
    module, root, _ = acceptance_data
    path = root / "strain.xml"
    path.write_text("<modeling><calculation/></modeling>")
    with pytest.raises(ValueError, match="No electronic dielectric tensor"):
        module.xml_dielectric(SimpleNamespace(epsilon_static=[]), path)


@pytest.fixture
def spectral_data(tmp_path, monkeypatch):
    import csv

    spec = importlib.util.spec_from_file_location("aln_spectra_verifier", CASE / "verify_spectra.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    frequencies = np.asarray([0.] * 3 + list(range(200, 1100, 100)))
    numbers = np.arange(4, 13)
    monkeypatch.setattr(module, "load_gamma_modes", lambda _: SimpleNamespace(frequencies_cm1=frequencies))
    monkeypatch.setattr(module, "load_raman_tensors", lambda _: (numbers, np.ones((9, 3, 3)), "native"))
    branches = [("E2", [4, 5], 1.), ("B1", [6], 2.), ("A1", [7], 3.),
                ("E2", [8, 9], 4.), ("E1", [10, 11], 5.), ("B1", [12], 6.)]
    monkeypatch.setattr(module, "read_irreps_yaml", lambda _: ("6mm", branches))
    results = tmp_path / "results"
    results.mkdir()
    (results / "spectra_results.json").write_text(json.dumps({"frequencies_cm-1": frequencies[3:].tolist()}))
    for kind, field in (("ir", "intensity_total"), ("raman", "activity_normalized")):
        folder = results / f"{kind}_spectrum"
        folder.mkdir()
        allowed = {7, 10, 11} if kind == "ir" else {4, 5, 7, 8, 9, 10, 11}
        with (folder / f"{kind}_modes.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["mode", "frequency_cm-1", field])
            for number in numbers:
                writer.writerow([number, frequencies[number - 1], 1. if number in allowed else 0.])
    return module, tmp_path


def test_aln_spectra_verifier_accepts_expected_selection_rules(spectral_data):
    module, root = spectral_data
    assert json.loads(json.dumps(module.validate(root)))["passed"] is True


def test_aln_spectra_verifier_rejects_wrong_point_group(spectral_data, monkeypatch):
    module, root = spectral_data
    original = module.read_irreps_yaml
    monkeypatch.setattr(module, "read_irreps_yaml", lambda path: ("3m", original(path)[1]))
    assert not module.validate(root)["passed"]


def test_aln_spectra_verifier_rejects_frequency_id_mismatch(spectral_data):
    module, root = spectral_data
    path = root / "results/spectra_results.json"
    record = json.loads(path.read_text())
    record["frequencies_cm-1"][0] += 10
    path.write_text(json.dumps(record))
    assert not module.validate(root)["checks"]["JSON IDs match exported mode frequencies"]


def test_retained_aln_spectra_pass_delivery_selection_rules():
    spec = importlib.util.spec_from_file_location("retained_aln_spectra_verifier", CASE / "verify_spectra.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.validate(CASE)["passed"]
    native = json.loads((CASE / "results/dfpt/vasp_native_response.json").read_text())
    assert "electromechanical_warning" in native["diagnostics"]
