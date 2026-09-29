"""Numerical and branch checks for the isolated-wire field-response audit."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "tools/research/analyze_sb2s3_field_raman.py"
SPEC = importlib.util.spec_from_file_location("sb2s3_field_raman_analysis", SCRIPT)
assert SPEC and SPEC.loader
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
from zstar import raman_local_field as LOCAL_FIELD
from zstar.raman_local_field import dipole_line_polarizability_a2


def test_polarization_branch_unwrap():
    assert ANALYSIS.unwrap_difference(-0.49, 0.49, 1.0) == pytest.approx(0.02)
    with pytest.raises(ValueError, match="half a quantum"):
        ANALYSIS.unwrap_difference(0.49, 0.0, 1.0)


def test_mixed_derivative_recovers_synthetic_mode_tensor():
    field = 0.0005
    mode_q = 0.02
    volume = 30.46 * 24.76 * 3.7857
    length = 3.7857
    factor = (
        volume * 1.0e-30 / (ANALYSIS.ELEMENTARY_CHARGE * ANALYSIS.BOHR_M)
        * ANALYSIS.BOHR_ANGSTROM**3 / length
    )
    target = 0.24
    background = 1.1
    polarization = lambda q, e: (background + q * target) * e / factor
    positive_q = (polarization(mode_q, field), polarization(mode_q, -field), 1.0)
    negative_q = (polarization(-mode_q, field), polarization(-mode_q, -field), 1.0)
    result = ANALYSIS.mode_raman_component(
        positive_q, negative_q, field_au=field,
        amplitude_a_sqrt_amu=mode_q, volume_a3=volume, length_a=length,
    )
    assert result["raman_zy_a_per_sqrt_amu"] == pytest.approx(target)


def test_invalid_finite_difference_input_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        ANALYSIS.line_polarizability_a2(0, 0, 1, field_au=0, volume_a3=1, length_a=1)
    with pytest.raises(ValueError, match="Mode amplitude"):
        ANALYSIS.mode_raman_component(
            (0, 0, 1), (0, 0, 1), field_au=0.1,
            amplitude_a_sqrt_amu=0, volume_a3=1, length_a=1,
        )
    with pytest.raises(ValueError, match="transverse"):
        ANALYSIS.mode_raman_component(
            (0, 0, 1), (0, 0, 1), field_au=0.1,
            amplitude_a_sqrt_amu=0.1, volume_a3=1, length_a=1,
            field_axis="z",
        )


def test_x_field_labels_zx_component():
    result = ANALYSIS.mode_raman_component(
        (1e-7, -1e-7, 1.0), (-1e-7, 1e-7, 1.0),
        field_au=0.0005, amplitude_a_sqrt_amu=0.02,
        volume_a3=2800, length_a=3.8, field_axis="x",
    )
    assert "raman_zx_a_per_sqrt_amu" in result
    assert "raman_zy_a_per_sqrt_amu" not in result


def test_transverse_dipole_conversion_recovers_reference_alpha_xx():
    result = dipole_line_polarizability_a2(
        0.16192921409947303,
        -0.15664969907402337,
        field_au=0.0005,
        length_a=3.7857153231483736,
    )
    assert result == pytest.approx(12.470172820725727)


def test_tensor_assembly_enforces_reciprocity_but_keeps_axial_source():
    tensor, residual = LOCAL_FIELD.assemble_screened_line_tensor(
        np.array([[1.0, 4.0], [2.0, 5.0], [3.0, 6.0]]), axial_zz=-0.8
    )
    np.testing.assert_allclose(
        tensor, [[1.0, 3.0, 3.0], [3.0, 5.0, 6.0], [3.0, 6.0, -0.8]]
    )
    assert residual == pytest.approx(2.0)


def test_screened_collector_matches_mode_and_marks_axial_limit(tmp_path, monkeypatch):
    for axis in ("x", "y"):
        root = tmp_path / axis
        root.mkdir()
        (root / "manifest.json").write_text(json.dumps({
            "field_axis": axis,
            "field_au": 0.0005,
            "mode_amplitude_A_sqrt_amu": 0.02,
            "cube_digits": 12,
            "stages": [{"geometry": "mode-0018/plus"}],
        }), encoding="utf-8")
    monkeypatch.setattr(
        LOCAL_FIELD, "read_structure",
        lambda path: SimpleNamespace(cell=np.diag([30.0, 25.0, 4.0])),
    )
    monkeypatch.setattr(LOCAL_FIELD, "find_charge_cube", lambda path: Path("unused.cube"))
    monkeypatch.setattr(LOCAL_FIELD, "require_cube_precision", lambda path, digits: None)
    monkeypatch.setattr(
        LOCAL_FIELD, "integrate_transverse_dipole",
        lambda cube, axis: SimpleNamespace(unwrap_center_bohr=10.0),
    )

    def fake_alpha(root, geometry, **kwargs):
        derivative = np.array([1.0, 2.0, 3.0]) if root.name == "x" else np.array([4.0, 5.0, 6.0])
        sign = 1.0 if geometry.endswith("/plus") else -1.0
        return sign * 0.02 * derivative

    monkeypatch.setattr(LOCAL_FIELD, "_field_alpha", fake_alpha)
    bare = np.zeros((1, 3, 3))
    bare[0, 2, 2] = -0.8
    tensors, metadata = LOCAL_FIELD.collect_screened_1d_raman_tensors(
        tmp_path / "x", tmp_path / "y", tmp_path / "STRU", np.array([18]), bare
    )
    np.testing.assert_allclose(
        tensors[0], [[1.0, 3.0, 3.0], [3.0, 5.0, 6.0], [3.0, 6.0, -0.8]]
    )
    assert metadata["axial_zz_component"].startswith("original zero-field")
    assert metadata["xy_reciprocity_residual_A_per_sqrt_amu"]["18"] == pytest.approx(2.0)


def test_cube_precision_gate_reads_actual_density_digits(tmp_path):
    cube = tmp_path / "rho.cube"
    cube.write_text(
        "title\ncomment\n1 0 0 0\n1 1 0 0\n1 0 1 0\n1 0 0 1\n1 1 0 0 0\n"
        "1.234567890123e-02\n",
        encoding="utf-8",
    )
    assert LOCAL_FIELD.cube_mantissa_digits(cube) == 12
    LOCAL_FIELD.require_cube_precision(cube)
    cube.write_text(cube.read_text().replace("1.234567890123", "1.234"), encoding="utf-8")
    with pytest.raises(ValueError, match="only 3 mantissa digits"):
        LOCAL_FIELD.require_cube_precision(cube)


def test_screened_tensor_export_preserves_mode_ids_and_axial_provenance(tmp_path):
    source = tmp_path / "bare.csv"
    columns = ["mode", *[f"R{a}{b}" for a in "xyz" for b in "xyz"]]
    source.write_text(
        ",".join(columns) + "\n"
        + ",".join(["18", *[str(i) for i in range(9)]]) + "\n",
        encoding="utf-8",
    )
    numbers, bare = LOCAL_FIELD.load_bare_raman_csv(source, [18])
    assert numbers.tolist() == [18]
    assert bare[0, 2, 2] == 8.0
    output = LOCAL_FIELD.write_screened_1d_raman_outputs(
        tmp_path / "screened", numbers, bare,
        {"axial_zz_component": "original zero-field PYATB response; not field-screened"},
    )
    payload = json.loads((output / "raman_tensors.json").read_text(encoding="utf-8"))
    assert payload["mode_numbers"] == [18]
    assert "axial zz" in payload["tensor_kind"]
    assert payload["tensors"][0][2][2] == 8.0
    with pytest.raises(FileExistsError, match="must be empty"):
        LOCAL_FIELD.write_screened_1d_raman_outputs(output, numbers, bare, {})


def test_bare_raman_csv_rejects_duplicate_modes(tmp_path):
    source = tmp_path / "bare.csv"
    columns = ["mode", *[f"R{a}{b}" for a in "xyz" for b in "xyz"]]
    row = ",".join(["18", *["0"] * 9])
    source.write_text(",".join(columns) + "\n" + row + "\n" + row + "\n")
    with pytest.raises(ValueError, match="Duplicate"):
        LOCAL_FIELD.load_bare_raman_csv(source)


def test_raman_screen_1d_cli_collects_without_requiring_qpoints(tmp_path, monkeypatch):
    from zstar.cli import zstar_cli

    source = tmp_path / "bare.csv"
    columns = ["mode", *[f"R{a}{b}" for a in "xyz" for b in "xyz"]]
    source.write_text(
        ",".join(columns) + "\n"
        + ",".join(["18", *["0"] * 8, "1"]) + "\n",
        encoding="utf-8",
    )

    def collect(x_probe, y_probe, structure, numbers, bare):
        assert numbers.tolist() == [18]
        assert bare.shape == (1, 3, 3)
        return bare, {"axial_zz_component": "original zero-field PYATB response"}

    monkeypatch.setattr(LOCAL_FIELD, "collect_screened_1d_raman_tensors", collect)
    output = tmp_path / "screened"
    zstar_cli([
        "raman", "screen-1d", "--x-probe", str(tmp_path / "x"),
        "--y-probe", str(tmp_path / "y"), "--stru", str(tmp_path / "STRU"),
        "--bare-csv", str(source), "--outdir", str(output),
    ], _canonical=False)
    assert (output / "raman_tensors.json").is_file()
