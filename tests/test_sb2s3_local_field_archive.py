"""Regression checks for the archived Sb2S3 transverse local-field result."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from zstar.spectra import load_raman_tensors


ARCHIVE = (
    Path(__file__).resolve().parents[1]
    / "examples/IR_Raman_Spectra/Nanowire_Sb2S3/results/local_field_screened"
)


def test_archived_mode_tensors_are_complete_and_reciprocal():
    data = json.loads((ARCHIVE / "raman_tensors.json").read_text(encoding="utf-8"))
    numbers, tensors, kind = load_raman_tensors(ARCHIVE / "raman_tensors.json")
    assert numbers.tolist() == list(range(5, 31))
    assert tensors.shape == (26, 3, 3)
    assert np.all(np.isfinite(tensors))
    np.testing.assert_allclose(tensors, tensors.swapaxes(1, 2), atol=1e-12)
    assert "axial zz" in kind
    assert "not field-screened" in data["axial_zz_component"]
    assert data["minimum_cube_mantissa_digits"] >= 10
    residuals = data["xy_reciprocity_residual_A_per_sqrt_amu"]
    assert set(residuals) == {str(mode) for mode in numbers}
    assert max(abs(value) for value in residuals.values()) < 1e-3


def test_archived_screened_spectra_match_the_independent_weak_yz_physics():
    data = json.loads((ARCHIVE / "comparison.json").read_text(encoding="utf-8"))
    ratios = data["crossed_to_axial_peak_height"]
    bare = ratios["ZStar (ABACUS), zero-field"]
    corrected = ratios["ZStar (ABACUS), screened"]
    vasp = ratios["ZStar (VASP)"]
    reference = ratios["CRYSTAL reference"]
    assert bare == pytest.approx(0.3973683673, abs=1e-8)
    assert corrected == pytest.approx(0.0064161703, abs=1e-8)
    assert vasp == pytest.approx(0.0075640742, abs=1e-8)
    assert reference == pytest.approx(0.0183556367, abs=1e-8)
    assert corrected < 0.02 * bare
    assert abs(corrected - vasp) < 0.002
    for component in ("xx", "xy", "xz", "yy", "yz", "zz"):
        channels = data["all_channel_peak_height_relative_to_axial"][component]
        assert all(value >= 0 for value in channels.values())
        assert len(channels) == 3
