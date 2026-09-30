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
