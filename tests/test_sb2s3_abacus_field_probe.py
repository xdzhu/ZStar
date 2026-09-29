"""Input and geometry gates for the isolated-wire electric-field probe."""

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples/IR_Raman_Spectra/Nanowire_Sb2S3"
SCRIPT = ROOT / "tools/research/sb2s3_abacus_field_probe.py"
SPEC = importlib.util.spec_from_file_location("sb2s3_abacus_field_probe", SCRIPT)
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def _prepare(tmp_path, **overrides):
    settings = dict(
        mode_numbers=[7], field_au=0.0005, amplitude=0.02,
        axis=1, ramp_start=0.85, ramp_width=0.10,
    )
    settings.update(overrides)
    return PROBE.prepare(CASE, tmp_path / "probe", **settings)


def test_prepared_field_probe_has_signed_fields_and_no_slab_correction(tmp_path):
    manifest = _prepare(tmp_path)
    assert len(manifest["stages"]) == 6
    assert {stage["geometry"] for stage in manifest["stages"]} == {
        "reference", "mode-0007/plus", "mode-0007/minus"
    }
    for stage in manifest["stages"]:
        root = tmp_path / "probe" / stage["relative_path"]
        text = (root / "INPUT").read_text()
        parameters = {
            fields[0]: fields[1]
            for line in text.splitlines()
            if (fields := line.split()) and len(fields) >= 2
        }
        assert parameters["efield_flag"] == "1"
        assert parameters["efield_dir"] == "1"
        assert parameters["dip_cor_flag"] == "0"
        assert parameters["symmetry"] == "0"
        assert parameters["out_mat_hs2"] == "1"
        assert any(line.split()[:3] == ["out_chg", "1", "12"] for line in text.splitlines())
        assert parameters["out_dipole"] == "1"
        assert (root / "STRU").is_file()
        assert len(list(root.glob("*.orb"))) == 2
        assert len(list(root.glob("*.upf"))) == 2
        assert float(parameters["efield_amp"]) == stage["field_au"]


@pytest.mark.parametrize("settings", [
    {"mode_numbers": []},
    {"mode_numbers": [7, 7]},
    {"axis": 2},
    {"amplitude": 0.0},
    {"ramp_start": 0.50},
    {"cube_digits": 3},
])
def test_invalid_probe_settings_fail_before_writing(tmp_path, settings):
    with pytest.raises(ValueError):
        _prepare(tmp_path, **settings)
    assert not (tmp_path / "probe").exists()


def test_probe_refuses_to_overwrite_existing_work(tmp_path):
    (tmp_path / "probe").mkdir()
    with pytest.raises(FileExistsError):
        _prepare(tmp_path)
