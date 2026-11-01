import io
import json
from contextlib import redirect_stdout

import numpy as np
import pytest
import yaml

from zstar.cli_frontend import handle_canonical_cli
from zstar.spectra import (
    THZ_TO_CM1,
    GammaModes,
    _selected_mode_indices,
    assess_gamma_modes,
    validate_gamma_stability,
)
from zstar.spectroscopy_backends import _mode_indices


def _two_atom_modes(frequencies_cm1):
    masses = np.array([28.0, 12.0])
    heavy, light = np.sqrt(masses / masses.sum())
    vectors = np.zeros((6, 2, 3), dtype=complex)
    for axis in range(3):
        vectors[axis, 0, axis] = heavy
        vectors[axis, 1, axis] = light
        vectors[axis + 3, 0, axis] = light
        vectors[axis + 3, 1, axis] = -heavy
    return GammaModes(
        frequencies_thz=np.asarray(frequencies_cm1, dtype=float) / THZ_TO_CM1,
        eigenvectors=vectors,
        masses_amu=masses,
        lattice_angstrom=np.eye(3) * 5.0,
        symbols=("Si", "C"),
        positions_fractional=np.array([[0, 0, 0], [0.25, 0.25, 0.25]]),
    )


def test_small_imaginary_translation_is_tolerated():
    modes = _two_atom_modes([-3.0, -2.0, 0.5, 100.0, 150.0, 200.0])
    rows = assess_gamma_modes(modes)
    assert [row["classification"] for row in rows] == [
        "translation", "translation", "translation",
        "non-translation", "non-translation", "non-translation",
    ]
    assert all(row["translation_overlap"] == pytest.approx(1.0) for row in rows[:3])
    assert validate_gamma_stability(modes).size == 0


def test_saved_gamma_report_distinguishes_drift_from_internal_instability(tmp_path, capsys):
    from zstar.spectra import write_gamma_mode_audit

    modes = _two_atom_modes([-3.0, -2.0, 0.5, -0.1, 150.0, 200.0])
    path = tmp_path / "gamma_modes.json"
    report = write_gamma_mode_audit(modes, path)
    assert report["negative_mode_numbers"] == [1, 2, 4]
    assert report["flagged_mode_numbers"] == [4]
    assert not report["harmonic_response_allowed"]
    assert json.loads(path.read_text())["modes"][0]["classification"] == "translation"
    output = capsys.readouterr().out
    assert "class=non-translation" in output
    assert "[STABILITY] [BLOCKED]" in output


def test_dielectric_refusal_is_saved_even_without_output_folder(tmp_path, monkeypatch, capsys):
    from zstar.cli import zstar_cli
    from zstar.workflow import workflow_status

    monkeypatch.chdir(tmp_path)
    (tmp_path / "0.no-move").mkdir()
    monkeypatch.setattr("zstar.spectra.load_gamma_modes", lambda _: _two_atom_modes([-3, 0, 0, -0.1, 150, 200]))
    with pytest.raises(ValueError, match="non-translation"):
        zstar_cli(["dielectric", "static", "--outdir", "dielectric"])
    assert not (tmp_path / "dielectric").exists()
    state = json.loads((tmp_path / ".zstar/stages/dielectric-static.json").read_text())
    assert state["status"] == state["dielectric"] == "failed"
    assert state["active_step"] == "Gamma stability"
    assert "non-translation" in state["error"]
    assert (tmp_path / ".zstar/gamma_modes.json").is_file()
    assert workflow_status(tmp_path)[-1].name == "dielectric-static"
    assert "[stage-failed] [FAIL]" in capsys.readouterr().out


def test_dielectric_success_has_completed_record_and_gamma_report(tmp_path, monkeypatch):
    from zstar.cli import zstar_cli
    from zstar.spectra import BornData

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("zstar.spectra.load_gamma_modes", lambda _: _two_atom_modes([-3, 0, 0, 100, 150, 200]))
    born = BornData(np.array([np.eye(3), -np.eye(3)]), np.eye(3) * 2, "test")
    monkeypatch.setattr("zstar.spectra.read_born_data", lambda *args, **kwargs: born)
    zstar_cli(["dielectric", "static", "--outdir", "dielectric"])
    state = json.loads((tmp_path / ".zstar/stages/dielectric-static.json").read_text())
    assert state["status"] == state["dielectric"] == "completed"
    assert state["active_step"] == "complete"
    assert state["started_at"] and state["finished_at"]
    report = json.loads((tmp_path / ".zstar/gamma_modes.json").read_text())
    assert report["harmonic_response_allowed"]
    assert (tmp_path / "dielectric/static_response.json").is_file()


def test_small_imaginary_internal_mode_is_not_hidden_by_acoustic_tolerance():
    modes = _two_atom_modes([-3.0, -2.0, 0.5, -2.0, 150.0, 200.0])
    with pytest.raises(ValueError, match=r"4:-2.00 cm-1 \(non-translation"):
        validate_gamma_stability(modes)
    np.testing.assert_array_equal(
        validate_gamma_stability(modes, allow_imaginary=True), [4]
    )


def test_mixed_mode_is_not_mistaken_for_translation():
    modes = _two_atom_modes([-23.0, 0.0, 0.0, 100.0, 150.0, 30.0])
    vectors = modes.eigenvectors.copy()
    acoustic = vectors[0].copy()
    optical = vectors[5].copy()
    vectors[0] = np.sqrt(2.0 / 3.0) * acoustic + np.sqrt(1.0 / 3.0) * optical
    vectors[5] = -np.sqrt(1.0 / 3.0) * acoustic + np.sqrt(2.0 / 3.0) * optical
    modes = GammaModes(
        modes.frequencies_thz, vectors, modes.masses_amu,
        modes.lattice_angstrom, modes.symbols, modes.positions_fractional,
    )
    assert assess_gamma_modes(modes)[0]["translation_overlap"] == pytest.approx(2.0 / 3.0)
    with pytest.raises(ValueError, match=r"1:-23.00 cm-1 \(mixed"):
        validate_gamma_stability(modes)
    positive = GammaModes(
        np.array([23.0, 0.0, 0.0, 100.0, 150.0, 30.0]) / THZ_TO_CM1,
        vectors, modes.masses_amu, modes.lattice_angstrom,
        modes.symbols, modes.positions_fractional,
    )
    with pytest.warns(UserWarning, match="acoustic sum rule"):
        assert validate_gamma_stability(positive).size == 0


def test_ninety_five_percent_translation_is_still_mixed():
    modes = _two_atom_modes([-2.0, 0.0, 0.0, 100.0, 150.0, 30.0])
    vectors = modes.eigenvectors.copy()
    vectors[0] = np.sqrt(0.95) * modes.eigenvectors[0] + np.sqrt(0.05) * modes.eigenvectors[3]
    mixed = GammaModes(modes.frequencies_thz, vectors, modes.masses_amu,
                       modes.lattice_angstrom, modes.symbols, modes.positions_fractional)
    row = assess_gamma_modes(mixed)[0]
    assert row['classification'] == 'mixed'
    assert row['internal_overlap'] == pytest.approx(0.05)
    with pytest.raises(ValueError, match='mixed'):
        validate_gamma_stability(mixed)


def test_large_imaginary_translation_is_still_rejected():
    modes = _two_atom_modes([-25.0, 0.0, 0.0, 100.0, 150.0, 200.0])
    with pytest.raises(ValueError, match=r"1:-25.00 cm-1 \(translation"):
        validate_gamma_stability(modes)


def test_positive_acoustic_drift_is_not_selected_as_a_spectral_mode():
    modes = _two_atom_modes([10.0, 0.0, 0.0, 100.0, 150.0, 200.0])
    np.testing.assert_array_equal(_selected_mode_indices(modes, None, 5.0), [3, 4, 5])
    np.testing.assert_array_equal(_mode_indices(modes, None, 5.0), [3, 4, 5])
    np.testing.assert_array_equal(_selected_mode_indices(modes, [1, 4], 5.0), [0, 3])


def test_overlap_is_invariant_to_global_eigenvector_phase():
    modes = _two_atom_modes([-3.0, 0.0, 0.0, 100.0, 150.0, 200.0])
    rotated = GammaModes(
        modes.frequencies_thz,
        modes.eigenvectors * np.exp(0.31j),
        modes.masses_amu,
        modes.lattice_angstrom,
        modes.symbols,
        modes.positions_fractional,
    )
    assert [row["translation_overlap"] for row in assess_gamma_modes(rotated)] == pytest.approx(
        [row["translation_overlap"] for row in assess_gamma_modes(modes)]
    )


def test_molecular_rotations_are_distinguished_from_internal_vibrations():
    vectors = np.zeros((6, 2, 3), dtype=complex)
    for axis in range(3):
        vectors[axis, :, axis] = 1.0 / np.sqrt(2.0)
    vectors[3, :, 0] = [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0)]
    vectors[4, :, 1] = [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0)]
    vectors[5, :, 2] = [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0)]
    frequencies = np.array([-2.0, 0.0, 0.0, -3.0, -1.0, 3000.0])
    modes = GammaModes(
        frequencies_thz=frequencies / THZ_TO_CM1,
        eigenvectors=vectors,
        masses_amu=np.ones(2),
        lattice_angstrom=np.eye(3) * 10.0,
        symbols=("H", "H"),
        positions_fractional=np.array([[0.5, 0.5, 0.45], [0.5, 0.5, 0.55]]),
    )
    rows = assess_gamma_modes(modes, dimensionality=0)
    assert [row["classification"] for row in rows] == [
        "translation", "translation", "translation", "rotation", "rotation", "internal",
    ]
    assert validate_gamma_stability(modes, dimensionality=0).size == 0
    large_rotation = GammaModes(
        frequencies_thz=np.array([-2.0, 0.0, 0.0, -30.0, -1.0, 3000.0]) / THZ_TO_CM1,
        eigenvectors=vectors,
        masses_amu=modes.masses_amu,
        lattice_angstrom=modes.lattice_angstrom,
        symbols=modes.symbols,
        positions_fractional=modes.positions_fractional,
    )
    with pytest.warns(UserWarning, match="rigid-rotation"):
        assert validate_gamma_stability(large_rotation, dimensionality=0).size == 0
    unstable = GammaModes(
        frequencies_thz=np.array([-2.0, 0.0, 0.0, -3.0, -1.0, -2.0]) / THZ_TO_CM1,
        eigenvectors=vectors,
        masses_amu=modes.masses_amu,
        lattice_angstrom=modes.lattice_angstrom,
        symbols=modes.symbols,
        positions_fractional=modes.positions_fractional,
    )
    with pytest.raises(ValueError, match=r"6:-2.00 cm-1 \(internal"):
        validate_gamma_stability(unstable, dimensionality=0)


def test_one_dimensional_axial_rotation_is_candidate_not_stability_exemption():
    vectors = np.zeros((6, 2, 3), dtype=complex)
    for axis in range(3):
        vectors[axis, :, axis] = 1 / np.sqrt(2.0)
        vectors[axis + 3, :, axis] = [1 / np.sqrt(2.0), -1 / np.sqrt(2.0)]
    modes = GammaModes(
        frequencies_thz=np.array([0, 0, 0, 100, -1, 200]) / THZ_TO_CM1,
        eigenvectors=vectors, masses_amu=np.ones(2),
        lattice_angstrom=np.diag([10.0, 10.0, 4.0]), symbols=('H', 'H'),
        positions_fractional=np.array([[0.95, 0.5, 0.5], [0.05, 0.5, 0.5]]),
    )
    rows = assess_gamma_modes(modes, dimensionality=1)
    assert rows[4]['classification'] == 'axial-rotation-candidate'
    assert rows[4]['rotation_overlap'] == pytest.approx(1.0)
    with pytest.raises(ValueError, match='axial-rotation-candidate'):
        validate_gamma_stability(modes, dimensionality=1)
    from zstar.raman_response import internal_mode_indices
    with pytest.raises(ValueError, match='axial-rotation-candidate'):
        internal_mode_indices(modes, 1)
    frequencies = np.array([0, 0, 0, 100, 10, 200]) / THZ_TO_CM1
    positive = GammaModes(frequencies, vectors, modes.masses_amu, modes.lattice_angstrom,
                          modes.symbols, modes.positions_fractional)
    selected, report = internal_mode_indices(positive, 1)
    assert 4 not in selected
    assert report['one_dimensional_axial_candidates'] == [5]
    assert 4 not in _selected_mode_indices(positive, None, 5, dimensionality=1)
    assert 4 not in _mode_indices(positive, None, 5, dimensionality=1)
    high = GammaModes(np.array([0, 0, 0, 100, 25, 200]) / THZ_TO_CM1,
                      vectors, modes.masses_amu, modes.lattice_angstrom,
                      modes.symbols, modes.positions_fractional)
    with pytest.raises(ValueError, match='far from zero'):
        _selected_mode_indices(high, None, 5, dimensionality=1)


def test_force_diagnostics_exposes_rigid_internal_coupling_without_claiming_stability():
    from zstar.force_diagnostics import gamma_force_diagnostics
    from zstar.spectra import rigid_motion_bases

    modes = _two_atom_modes([0, 0, 0, 100, 150, 200])
    translations, _ = rigid_motion_bases(modes, dimensionality=3)
    t = translations[:, 0]
    internal = modes.eigenvectors[3].real.reshape(-1)
    assert abs(t @ internal) < 1e-12
    dynamical = np.outer(internal, internal) + 0.5 * (np.outer(t, internal) + np.outer(internal, t))
    masses = np.repeat(np.sqrt(modes.masses_amu), 3)
    hessian = masses[:, None] * dynamical * masses[None, :]
    q = np.eye(6) - np.tile(np.eye(3), (2, 1)) @ np.tile(np.eye(3), (2, 1)).T / 2
    projected = q @ hessian @ q
    to_tensor = lambda h: h.reshape(2, 3, 2, 3).transpose(0, 2, 1, 3)
    report = gamma_force_diagnostics(modes, to_tensor(hessian), to_tensor(projected), dimensionality=3)
    assert report['raw']['rigid_internal_coupling_frobenius'] == pytest.approx(0.5)
    assert report['raw']['internal_block_min_eigenvalue'] >= -1e-12
    assert np.linalg.eigvalsh(dynamical)[0] < 0
    assert report['projection_relative_frobenius'] > 0
    assert 'do not alone establish' in report['interpretation']


def test_phonon_inspect_writes_audit_without_rejecting_unstable_modes(tmp_path):
    modes = _two_atom_modes([-3.0, 0.0, 0.0, -2.0, 150.0, 200.0])
    points = [
        {"symbol": symbol, "mass": float(mass), "coordinates": position.tolist()}
        for symbol, mass, position in zip(
            modes.symbols, modes.masses_amu, modes.positions_fractional
        )
    ]
    bands = [
        {
            "frequency": float(frequency),
            "eigenvector": [
                [[float(value.real), float(value.imag)] for value in atom]
                for atom in vector
            ],
        }
        for frequency, vector in zip(modes.frequencies_thz, modes.eigenvectors)
    ]
    source = tmp_path / "qpoints.yaml"
    source.write_text(
        yaml.safe_dump({
            "primitive_cell": {"lattice": modes.lattice_angstrom.tolist(), "points": points},
            "phonon": [{"q-position": [0, 0, 0], "band": bands}],
        }),
        encoding="utf-8",
    )
    output = tmp_path / "audit.json"
    stream = io.StringIO()
    with redirect_stdout(stream):
        assert handle_canonical_cli(
            ["phonon", "inspect", "--qpoints", str(source), "--json", str(output)],
            lambda _: None,
        )
    assert "REVIEW" in stream.getvalue()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["flagged_mode_numbers"] == [4]
    assert report["modes"][0]["classification"] == "translation"


def test_phonon_inspect_one_dimensional_force_report(tmp_path, monkeypatch, capsys):
    from phonopy.file_IO import write_FORCE_CONSTANTS

    modes = _two_atom_modes([0, 0, 0, 100, 150, 200])
    modes = GammaModes(modes.frequencies_thz, modes.eigenvectors, modes.masses_amu,
                       modes.lattice_angstrom, modes.symbols,
                       np.array([[0.45, 0.5, 0.5], [0.55, 0.5, 0.5]]))
    monkeypatch.setattr('zstar.spectra.load_gamma_modes', lambda _: modes)
    fc = tmp_path / 'FORCE_CONSTANTS.raw'
    write_FORCE_CONSTANTS(np.zeros((2, 2, 3, 3)), filename=str(fc))
    output = tmp_path / 'audit.json'
    assert handle_canonical_cli(['phonon', 'inspect', '--dim', '1', '--qpoints', 'ignored',
                                 '--force-constants', str(fc), '--json', str(output)], lambda _: None)
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['force_constants']['rigid_basis']['rotations'] == 1
    assert report['force_constants']['projected'] is None
    assert report['force_constants']['raw']['reciprocity_max_eV_A2'] == 0
    text = capsys.readouterr().out
    assert 'Rotation' in text and 'axial-rotation-candidate' in text
