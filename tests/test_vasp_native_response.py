import json
from pathlib import Path

import numpy as np
import pytest

from zstar.spectra import GammaModes, load_gamma_modes, read_born_data
from zstar.vasp_bec import prepare_vasp_bec, render_incar, resolve_vasp_response_method
from zstar.vasp_response import parse_native_tensors, write_native_qpoints, write_vasp_born_for_phonopy


POSCAR = """SiC
1.0
0.0 2.18 2.18
2.18 0.0 2.18
2.18 2.18 0.0
Si C
1 1
Direct
0.0 0.0 0.0
0.25 0.25 0.25
"""


def inputs(tmp_path, incar="ENCUT = 500\n"):
    source = tmp_path / "input"
    source.mkdir()
    for name, text in {"INCAR": incar, "POSCAR": POSCAR, "KPOINTS": "Gamma\n0\nGamma\n4 4 4\n0 0 0\n", "POTCAR": "unit-test placeholder"}.items():
        (source / name).write_text(text)
    return source


def table(title, values, labels=None):
    lines = [title, "-----------------------"]
    for i, row in enumerate(values):
        label = "" if labels is None else labels[i] + " "
        lines.append(label + " ".join(str(x) for x in row))
    return "\n".join(lines) + "\n"


def test_auto_prefers_native_dfpt_and_handles_semicolon_and_comments():
    assert resolve_vasp_response_method("GGA = PS\n# LHFCALC=.TRUE.\n") == "dfpt"
    assert resolve_vasp_response_method("ENCUT=500; LHFCALC=.TRUE. ! hybrid\n") == "finite-field"
    assert resolve_vasp_response_method("METAGGA=SCAN\n") == "finite-field"
    with pytest.raises(ValueError, match="orbital-dependent"):
        resolve_vasp_response_method("LHFCALC=.TRUE.\n", "dfpt")


def test_incar_update_retains_unrelated_semicolon_tags():
    rendered = render_incar("ENCUT=500; LEPSILON=.FALSE.; GGA=PS\n", updates={"LEPSILON": ".TRUE."})
    assert "ENCUT=500" in rendered
    assert "GGA=PS" in rendered
    assert ".FALSE." not in rendered
    assert rendered.count("LEPSILON") == 1


def test_native_gamma_dfpt_preparation(tmp_path):
    root = prepare_vasp_bec(inputs(tmp_path), tmp_path / "response", phonons=True)
    incar = (root / "response/INCAR").read_text()
    assert "IBRION = 8" in incar
    assert "LEPSILON = .TRUE." in incar
    assert "NSW = 1" in incar
    assert "NCORE = 1" in incar
    assert "NPAR" not in incar
    assert "NCORE = 1" in (root / "reference/INCAR").read_text()
    assert "ISYM = 2" in incar
    assert "ISYM = 2" in (root / "reference/INCAR").read_text()
    assert "POTIM" not in incar
    data = json.loads((root / "vasp_bec_manifest.json").read_text())
    assert data["ionic_response_method"] == "dfpt"


def test_native_hybrid_uses_field_and_finite_difference_phonons(tmp_path):
    root = prepare_vasp_bec(inputs(tmp_path, "LHFCALC=.TRUE.\n"), tmp_path / "response", phonons=True)
    incar = (root / "response/INCAR").read_text()
    assert "LCALCEPS = .TRUE." in incar
    assert "LEPSILON" not in incar
    assert "IBRION = 6" in incar
    assert "NFREE = 2" in incar
    assert "NCORE = 1" in incar
    assert "NPAR" not in incar


def test_native_elastic_uses_strain_finite_differences_with_electric_dfpt(tmp_path):
    root = prepare_vasp_bec(inputs(tmp_path), tmp_path / "response", elastic=True)
    incar = (root / "response/INCAR").read_text()
    assert "IBRION = 6" in incar
    assert "ISIF = 3" in incar
    assert "LEPSILON = .TRUE." in incar
    assert "NCORE = 1" in incar
    assert "NPAR" not in incar


@pytest.mark.parametrize("incar,method,ibrion", [("GGA=PS\n", "dfpt", 8), ("LHFCALC=.TRUE.\n", "finite-field", 6)])
def test_piezo_requests_native_ionic_response_without_elastic_strain_jobs(tmp_path, incar, method, ibrion):
    root = prepare_vasp_bec(inputs(tmp_path, incar), tmp_path / "piezo", piezo=True)
    manifest = json.loads((root / "vasp_bec_manifest.json").read_text())
    response = (root / "response/INCAR").read_text()
    assert manifest["piezo"] is True
    assert manifest["phonons"] is True
    assert manifest["elastic"] is False
    assert manifest["method"] == method
    assert f"IBRION = {ibrion}" in response
    assert "ISIF = 2" in response
    assert [stage["name"] for stage in manifest["stages"]] == ["reference", "response"]


def test_canonical_piezo_cli_prepares_native_workflow(tmp_path):
    from zstar.cli import zstar_cli

    root = tmp_path / "response"
    zstar_cli(["bec", "pre", "--calculator", "vasp", "--input-dir", str(inputs(tmp_path)),
               "--root", str(root), "--piezo"])
    assert json.loads((root / "vasp_bec_manifest.json").read_text())["piezo"] is True
    assert "IBRION = 8" in (root / "response/INCAR").read_text()


def test_requested_piezo_missing_ionic_block_is_rejected(tmp_path):
    from zstar.vasp_response import collect_native_response

    (tmp_path / "response").mkdir()
    (tmp_path / "response/OUTCAR").write_text(
        table("MACROSCOPIC STATIC DIELECTRIC TENSOR IONIC CONTRIBUTION", np.eye(3)))
    with pytest.raises(ValueError, match="piezoelectric response is incomplete"):
        collect_native_response(tmp_path, {"piezo": True}, np.eye(3), np.zeros((2, 3, 3)))


def test_native_preparation_removes_user_npar_from_both_stages(tmp_path):
    root = prepare_vasp_bec(inputs(tmp_path, "ENCUT=500; NCORE=1; NPAR=1\n"), tmp_path / "response", phonons=True)
    for stage in ("reference", "response"):
        text = (root / stage / "INCAR").read_text()
        assert "NCORE = 1" in text
        assert "NPAR" not in text
        assert "ENCUT=500" in text


@pytest.mark.parametrize("source_isym", [0, -1])
def test_native_ionic_response_replaces_disabled_symmetry(tmp_path, source_isym):
    root = prepare_vasp_bec(
        inputs(tmp_path, f"ISYM={source_isym}\nNCORE=4\n"),
        tmp_path / "response",
        elastic=True,
    )
    manifest = json.loads((root / "vasp_bec_manifest.json").read_text())
    for stage in ("reference", "response"):
        text = (root / stage / "INCAR").read_text()
        assert "ISYM = 2" in text
        assert "NCORE = 1" in text
    assert manifest["source_isym"] == source_isym
    assert manifest["native_isym"] == 2
    assert manifest["symmetry_policy"] == "native-enabled"
    assert "replaced by ISYM=2" in manifest["symmetry_override"]
    assert "replaced by NCORE=1" in manifest["parallelization_override"]


def test_native_ionic_response_preserves_enabled_source_symmetry(tmp_path):
    root = prepare_vasp_bec(
        inputs(tmp_path, "ISYM=1\nNCORE=4\n"),
        tmp_path / "response",
        piezo=True,
    )
    manifest = json.loads((root / "vasp_bec_manifest.json").read_text())
    assert "ISYM = 1" in (root / "response/INCAR").read_text()
    assert "NCORE = 1" in (root / "response/INCAR").read_text()
    assert manifest["source_isym"] == 1
    assert manifest["native_isym"] == 1
    assert manifest["symmetry_override"] is None


def test_native_ionic_response_caps_loose_vasp_symprec_without_changing_structural_symprec(tmp_path):
    root = prepare_vasp_bec(
        inputs(tmp_path, "ISYM=2\nSYMPREC=1e-3\n"),
        tmp_path / "response",
        elastic=True,
    )
    manifest = json.loads((root / "vasp_bec_manifest.json").read_text())
    for stage in ("reference", "response"):
        text = (root / stage / "INCAR").read_text()
        assert "SYMPREC = 1E-4" in text
        assert "SYMPREC=1e-3" not in text
    assert manifest["source_vasp_symprec"] == pytest.approx(1e-3)
    assert manifest["native_vasp_symprec"] == pytest.approx(1e-4)
    assert "separate structural tolerance" in manifest["vasp_symprec_override"]


@pytest.mark.parametrize("source", ["", "SYMPREC=1e-5\n"])
def test_native_ionic_response_keeps_vasp_default_or_tighter_symprec(tmp_path, source):
    root = prepare_vasp_bec(inputs(tmp_path, source), tmp_path / "response", elastic=True)
    manifest = json.loads((root / "vasp_bec_manifest.json").read_text())
    response = (root / "response/INCAR").read_text()
    if source:
        assert "SYMPREC=1e-5" in response
        assert manifest["native_vasp_symprec"] == pytest.approx(1e-5)
    else:
        assert "SYMPREC" not in response
        assert manifest["native_vasp_symprec"] is None
    assert manifest["vasp_symprec_override"] is None


@pytest.mark.parametrize("source", ["SYMPREC=bad\n", "SYMPREC=0\n", "SYMPREC=-1e-5\n"])
def test_native_preparation_rejects_invalid_vasp_symprec(tmp_path, source):
    with pytest.raises(ValueError, match="SYMPREC must be"):
        prepare_vasp_bec(inputs(tmp_path, source), tmp_path / "response", elastic=True)


def test_electronic_only_response_does_not_force_symmetry_or_ncore(tmp_path):
    root = prepare_vasp_bec(
        inputs(tmp_path, "ISYM=-1\nNCORE=4\n"),
        tmp_path / "response",
    )
    for stage in ("reference", "response"):
        text = (root / stage / "INCAR").read_text()
        assert "ISYM=-1" in text
        assert "NCORE=4" in text
    manifest = json.loads((root / "vasp_bec_manifest.json").read_text())
    assert manifest["symmetry_policy"] == "source-or-vasp-default"
    assert manifest["symmetry_override"] is None


def test_force_cannot_delete_original_vasp_inputs(tmp_path):
    source = inputs(tmp_path)
    with pytest.raises(ValueError, match="input directory"):
        prepare_vasp_bec(source, source, force=True)
    assert (source / "POSCAR").is_file()


def test_bulk_elastic_rejects_vacuum_supercell(tmp_path):
    with pytest.raises(ValueError, match="intrinsic low-dimensional"):
        prepare_vasp_bec(inputs(tmp_path), tmp_path / "response", elastic=True, dimensionality=2)
    assert not (tmp_path / "response").exists()


def test_tensor_reordering_units_and_derived_d(tmp_path):
    source = tmp_path / "OUTCAR"
    piezo = np.arange(18).reshape(3, 6)
    stiffness = np.diag([1000., 1100., 1200., 1300., 1400., 1500.])
    source.write_text(
        table("MACROSCOPIC STATIC DIELECTRIC TENSOR IONIC CONTRIBUTION", np.eye(3) * 2)
        + table("PIEZOELECTRIC TENSOR for field in x, y, z (C/m^2)", piezo, ["x", "y", "z"])
        + table("PIEZOELECTRIC TENSOR IONIC CONTR for field in x, y, z (C/m^2)", piezo * 0.1, ["x", "y", "z"])
        + table("TOTAL ELASTIC MODULI (kBar)", stiffness, ["XX", "YY", "ZZ", "XY", "YZ", "ZX"])
        + table("INTERNAL STRAIN TENSOR FOR ION 1 (eV/Angst)", np.ones((3, 6)), ["x", "y", "z"])
        + table("INTERNAL STRAIN TENSOR FOR ION 2 (eV/Angst)", -np.ones((3, 6)), ["x", "y", "z"])
    )
    data = parse_native_tensors(source)
    order = [0, 1, 2, 4, 5, 3]
    np.testing.assert_allclose(data["piezoelectric_clamped_C_m2"], piezo[:, order])
    np.testing.assert_allclose(data["elastic_relaxed_GPa"], stiffness[np.ix_(order, order)] * 0.1)
    expected = piezo[:, order] * 1.1 @ np.linalg.inv(stiffness[np.ix_(order, order)] * 0.1) * 1000
    np.testing.assert_allclose(data["piezoelectric_d_pm_V"], expected)


@pytest.mark.parametrize("problem", ["missing-internal-strain", "inconsistent-total", "missing-ionic"])
def test_unchecked_or_inconsistent_native_data_do_not_emit_d(tmp_path, problem):
    source = tmp_path / "OUTCAR"
    text = table("PIEZOELECTRIC TENSOR (C/m^2)", np.ones((3, 6)))
    if problem != "missing-ionic":
        text += table("PIEZOELECTRIC TENSOR IONIC CONTR (C/m^2)", np.zeros((3, 6)))
    text += table("TOTAL PIEZOELECTRIC TENSOR (C/m^2)", np.ones((3, 6)) * (2 if problem == "inconsistent-total" else 1))
    text += table("TOTAL ELASTIC MODULI (kBar)", np.eye(6) * 1000)
    if problem != "missing-internal-strain":
        for atom, sign in [(1, 1), (2, -1)]:
            text += table(f"INTERNAL STRAIN TENSOR FOR ION {atom} (eV/Angst)", np.ones((3, 6)) * sign)
    source.write_text(text)
    data = parse_native_tensors(source)
    assert "piezoelectric_d_pm_V" not in data
    assert "d_rejected_reason" in data
    assert "piezoelectric_total_C_m2" in data


def test_unstable_elastic_d_is_not_emitted(tmp_path):
    source = tmp_path / "OUTCAR"
    source.write_text(table("PIEZOELECTRIC TENSOR (C/m^2)", np.ones((3, 6)))
                      + table("PIEZOELECTRIC TENSOR IONIC CONTR (C/m^2)", np.zeros((3, 6)))
                      + table("TOTAL ELASTIC MODULI (kBar)", np.diag([-1., 2., 2., 2., 2., 2.])))
    data = parse_native_tensors(source)
    assert "piezoelectric_d_pm_V" not in data
    assert "d_rejected_reason" in data


def test_incomplete_tensor_is_rejected(tmp_path):
    source = tmp_path / "OUTCAR"
    source.write_text(table("PIEZOELECTRIC TENSOR (C/m^2)", np.ones((2, 6))))
    with pytest.raises(ValueError, match="Incomplete"):
        parse_native_tensors(source)


def test_native_parser_ignores_intermediate_field_direction_blocks(tmp_path):
    source = tmp_path / "OUTCAR"
    source.write_text(table("PIEZOELECTRIC TENSOR FIELD DIRECTION 1 (C/m^2)", np.eye(3))
                      + table("PIEZOELECTRIC TENSOR for field in x, y, z (C/m^2)", np.ones((3, 6)), ["x", "y", "z"]))
    np.testing.assert_allclose(parse_native_tensors(source)["piezoelectric_clamped_C_m2"], np.ones((3, 6)))


def test_internal_strain_force_balance_warns_and_gates_derived_d(tmp_path):
    source = tmp_path / "OUTCAR"
    source.write_text(table("PIEZOELECTRIC TENSOR (C/m^2)", np.ones((3, 6)), ["x", "y", "z"])
                      + table("PIEZOELECTRIC TENSOR IONIC CONTR (C/m^2)", np.zeros((3, 6)), ["x", "y", "z"])
                      + table("TOTAL ELASTIC MODULI (kBar)", np.eye(6) * 1000, ["XX", "YY", "ZZ", "XY", "YZ", "ZX"])
                      + table("INTERNAL STRAIN TENSOR FOR ION 1 (eV/Angst)", np.ones((3, 6)), ["x", "y", "z"])
                      + table("INTERNAL STRAIN TENSOR FOR ION 2 (eV/Angst)", -np.ones((3, 6)) * .5, ["x", "y", "z"]))
    result = parse_native_tensors(source)
    assert result["internal_strain_translation_relative"] == .5
    assert "electromechanical_warning" in result
    assert "piezoelectric_d_pm_V" not in result
    assert "d_rejected_reason" in result


def test_vasp_mode_masses_use_actual_atom_types_and_pomass(tmp_path):
    from zstar.spectroscopy_backends import _vasp_masses

    xml = tmp_path / "vasprun.xml"
    xml.write_text('''<modeling><atominfo>
<array name="atomtypes"><field>atomspertype</field><field>element</field><field>mass</field><set>
<rc><c>1</c><c>H</c><c>1.008</c></rc><rc><c>1</c><c>H</c><c>2.014</c></rc></set></array>
<array name="atoms"><field>element</field><field>atomtype</field><set>
<rc><c>H</c><c>2</c></rc><rc><c>H</c><c>1</c></rc></set></array>
</atominfo></modeling>''')
    np.testing.assert_allclose(_vasp_masses(xml, None), [2.014, 1.008])
    np.testing.assert_allclose(_vasp_masses(xml, [1., 3.]), [3., 1.])
    with pytest.raises(ValueError, match="positive"):
        _vasp_masses(xml, [-1., 2.])


def test_vasp_frequency_unit_conversion_is_version_aware(tmp_path):
    from phonopy.units import VaspToTHz
    from zstar.spectroscopy_backends import _vasp_frequency_factor

    xml = tmp_path / "vasprun.xml"
    xml.write_text('<modeling><dynmat><i name="unit">THz^2 </i></dynmat></modeling>')
    assert _vasp_frequency_factor(xml) == 1.
    xml.write_text('<modeling><dynmat/></modeling>')
    assert _vasp_frequency_factor(xml) == VaspToTHz
    xml.write_text('<modeling><dynmat><i name="unit">eV/amu/Angstrom^2</i></dynmat></modeling>')
    assert _vasp_frequency_factor(xml) == VaspToTHz
    xml.write_text('<modeling><dynmat><i name="unit">unknown</i></dynmat></modeling>')
    with pytest.raises(ValueError, match="frequency unit"):
        _vasp_frequency_factor(xml)


def test_native_modes_use_equilibrium_not_last_displaced_structure(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from pymatgen.core import Lattice, Structure
    from pymatgen.io.vasp import outputs
    from zstar.spectroscopy_backends import load_vasp_gamma_modes

    equilibrium = Structure(Lattice.cubic(4), ["Si", "C"], [[0, 0, 0], [.25, .25, .25]])
    displaced = equilibrium.copy()
    displaced.translate_sites([1], [0, 0, .0025])
    run = SimpleNamespace(initial_structure=equilibrium, final_structure=displaced,
                          normalmode_eigenvals=-np.arange(6.),
                          normalmode_eigenvecs=np.eye(6).reshape(6, 2, 3), parameters={})
    monkeypatch.setattr(outputs, "Vasprun", lambda *args, **kwargs: run)
    monkeypatch.setattr("zstar.spectroscopy_backends._vasp_masses", lambda *args: np.array([28., 12.]))
    monkeypatch.setattr("zstar.spectroscopy_backends._vasp_frequency_factor", lambda *args: 1.)
    modes = load_vasp_gamma_modes(tmp_path / "vasprun.xml")
    np.testing.assert_allclose(modes.positions_fractional, equilibrium.frac_coords)
    assert not np.allclose(modes.positions_fractional, displaced.frac_coords)


def test_qpoints_roundtrip_preserves_full_eigensystem_and_sorts_frequencies(tmp_path):
    modes = GammaModes(np.array([6., 5., 4., 0., 0., 0.]), np.eye(6).reshape(6, 2, 3).astype(complex),
                       np.array([28., 12.]), np.eye(3) * 4, ("Si", "C"), np.array([[0., 0., 0.], [.25, .25, .25]]))
    target = write_native_qpoints(modes, tmp_path / "qpoints.yaml")
    restored = load_gamma_modes(target)
    order = np.argsort(modes.frequencies_thz)
    np.testing.assert_allclose(restored.frequencies_thz, modes.frequencies_thz[order])
    np.testing.assert_allclose(restored.eigenvectors, modes.eigenvectors[order])


def test_born_is_phonopy_format_and_zstar_reader_retains_tensor_axes(tmp_path):
    from phonopy.file_IO import parse_BORN
    from phonopy.structure.atoms import PhonopyAtoms
    from zstar.structure_io import read_structure

    poscar = tmp_path / "POSCAR"
    poscar.write_text(POSCAR)
    born = np.arange(18).reshape(2, 3, 3).astype(float)
    target = tmp_path / "BORN"
    write_vasp_born_for_phonopy(poscar, np.eye(3) * 5., born, target)
    structure = read_structure(poscar)
    cell = PhonopyAtoms(symbols=structure.symbols, cell=structure.lattice_angstrom,
                        scaled_positions=structure.positions_fractional)
    parsed = parse_BORN(cell, filename=str(target))
    assert parsed is not None
    # Native tensors remain raw. Phonopy may symmetry-project their expansion.
    np.testing.assert_allclose(parsed["dielectric"], np.eye(3) * 5.)
    loaded = read_born_data(target, natoms=2)
    np.testing.assert_allclose(loaded.tensors, born)


def native_cache(tmp_path):
    source = inputs(tmp_path)
    root = prepare_vasp_bec(source, tmp_path / "native", phonons=True)
    response = root / "response"
    (response / "OUTCAR").write_text("General timing and accounting informations for this job\n")
    (response / "vasprun.xml").write_text("mock XML adapter input")
    return root


def test_native_manifest_without_canonical_metadata_routes_to_vasp(tmp_path):
    from zstar.cli_frontend import _run_bec

    cache = native_cache(tmp_path)
    calls = []
    _run_bec(["post", "--root", str(cache)], lambda arguments: calls.append(arguments))
    assert calls[0][:2] == ["vasp-bec", "collect"]
    assert "--root" in calls[0]


def test_retained_sic_native_response_and_raman_pass_delivery_checks():
    import importlib.util

    case = Path(__file__).resolve().parents[1] / "examples/VASP_Native_Response/3C_SiC"
    spec = importlib.util.spec_from_file_location("sic_verifier", case / "verify_results.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.validate(case)
    assert report["passed"]
    assert "electromechanical_warning" in report["DFPT_diagnostics"]


def mock_gamma_modes():
    return GammaModes(np.array([0., 0., 0., 10., 10., 10.]),
                      np.eye(6).reshape(6, 2, 3).astype(complex), np.array([28., 12.]),
                      np.eye(3) * 4., ("Si", "C"), np.array([[0., 0., 0.], [.25, .25, .25]]))


def test_ir_only_cache_needs_no_wavefunctions_and_generates_no_displacements(tmp_path, monkeypatch):
    from zstar.spectroscopy_backends import prepare_vasp_spectra, run_calculator_spectra

    cache = native_cache(tmp_path)
    monkeypatch.setattr("zstar.spectroscopy_backends.load_vasp_gamma_modes", lambda _: mock_gamma_modes())
    root = prepare_vasp_spectra(tmp_path / "unused", None, tmp_path / "ir", kind="ir", native_response_root=cache)
    manifest = json.loads((root / "spectra_manifest.json").read_text())
    assert manifest["kind"] == "ir"
    assert len(manifest["stages"]) == 1
    assert len(manifest["modes"]) == 3
    assert not list(root.glob("mode-*"))
    assert (root / "reference/OUTCAR").read_bytes() == (cache / "response/OUTCAR").read_bytes()
    assert not (root / "reference/OUTCAR").is_symlink()
    monkeypatch.setattr("zstar.spectroscopy_backends.parse_vasp_gap", lambda _: 1.5)
    calls = []
    monkeypatch.setattr("zstar.spectroscopy_backends.subprocess.run", lambda *args, **kwargs: calls.append(args))
    states = run_calculator_spectra(root, command="must-not-run")
    assert [state.status for state in states] == ["completed"]
    assert calls == []


def test_raman_cache_requires_restart_files_before_creating_target(tmp_path, monkeypatch):
    from zstar.spectroscopy_backends import prepare_vasp_spectra

    cache = native_cache(tmp_path)
    monkeypatch.setattr("zstar.spectroscopy_backends.load_vasp_gamma_modes", lambda _: mock_gamma_modes())
    target = tmp_path / "raman"
    with pytest.raises(FileNotFoundError, match="CHGCAR"):
        prepare_vasp_spectra(tmp_path / "unused", None, target, native_response_root=cache)
    assert not target.exists()
    for name in ("WAVECAR", "CHGCAR"):
        (cache / "response" / name).write_bytes(b"restart fixture")
    root = prepare_vasp_spectra(tmp_path / "unused", None, target, native_response_root=cache)
    manifest = json.loads((root / "spectra_manifest.json").read_text())
    assert len(manifest["stages"]) == 7
    assert (root / "reference/CHGCAR").read_bytes() == b"restart fixture"
    assert "ISTART = 0" in (root / "mode-0004/plus/INCAR").read_text()
    assert "NCORE = 4" in (root / "mode-0004/plus/INCAR").read_text()
    assert "NPAR" not in (root / "mode-0004/plus/INCAR").read_text()


def test_raman_preserves_tighter_native_convergence_setting(tmp_path, monkeypatch):
    from zstar.spectroscopy_backends import prepare_vasp_spectra

    cache = native_cache(tmp_path)
    (cache / "response/INCAR").write_text("EDIFF = 1E-9\nLEPSILON=.TRUE.\n")
    (cache / "response/CHGCAR").write_bytes(b"charge density")
    monkeypatch.setattr("zstar.spectroscopy_backends.load_vasp_gamma_modes", lambda _: mock_gamma_modes())
    root = prepare_vasp_spectra(tmp_path / "unused", None, tmp_path / "raman", native_response_root=cache)
    assert "EDIFF = 1E-9" in (root / "mode-0004/plus/INCAR").read_text()


def test_native_internal_strain_keeps_both_routes_without_substitution(tmp_path):
    clamped = np.zeros((3, 6))
    displaced = np.zeros((3, 6))
    displaced[0, 0] = 1
    content = "INTERNAL STRAIN TENSORS FROM DISPLACED ATOMS\n"
    content += table("INTERNAL STRAIN TENSOR FOR ION 1", displaced, ["x", "y", "z"])
    content += table("INTERNAL STRAIN TENSOR FOR ION 2", -displaced * 0.9, ["x", "y", "z"])
    content += "INTERNAL STRAIN TENSORS FROM STRAINED CELLS\n"
    content += table("INTERNAL STRAIN TENSOR FOR ION 1", clamped, ["x", "y", "z"])
    content += table("INTERNAL STRAIN TENSOR FOR ION 2", clamped, ["x", "y", "z"])
    path = tmp_path / "OUTCAR"
    path.write_text(content)
    result = parse_native_tensors(path)
    assert result["internal_strain_source"] == "displaced_atoms"
    assert result["internal_strain_translation_relative"] == pytest.approx(0.1)
    assert result["strained_cell_internal_strain_translation_max_eV_per_A"] == 0
    assert result["internal_strain_reciprocity_max_eV_per_A"] == 1
    assert "electromechanical_warning" in result


def test_native_force_strain_quantity_is_not_volume_normalized(tmp_path):
    from zstar.response_schema import ResponseRecord, response_record_from_bec_result
    from zstar.vasp_response import append_native_quantities

    path = tmp_path / "response.json"
    response_record_from_bec_result({"backend": "vasp", "atoms": [{"label": "Si", "tensor": np.eye(3)}]},
                                    dimensionality=3).write(path)
    native = {"tensors": {"internal_strain_eV_per_A": np.zeros((1, 3, 6)).tolist()},
              "source": "OUTCAR", "electric_boundary": "fixed E", "diagnostics": {}}
    append_native_quantities(path, native)
    quantity = ResponseRecord.read(path).quantity("native_internal_strain")
    assert quantity.normalization == "none"
    assert "not relaxed displacement per strain" in quantity.metadata["derivative_kind"]


def test_rejected_native_d_does_not_survive_recollection(tmp_path):
    from zstar.response_schema import ResponseRecord, response_record_from_bec_result
    from zstar.vasp_response import append_native_quantities

    path = tmp_path / "response.json"
    response_record_from_bec_result({"backend": "vasp", "atoms": [{"label": "Si", "tensor": np.eye(3)}]},
                                    dimensionality=3).write(path)
    native = {"tensors": {"piezoelectric_d_pm_V": np.ones((3, 6)).tolist()},
              "source": "OUTCAR", "electric_boundary": "fixed E", "diagnostics": {}}
    append_native_quantities(path, native)
    assert ResponseRecord.read(path).quantity("piezoelectric_d").unit == "pm/V"
    assert ResponseRecord.read(path).quantity("piezoelectric_d").normalization == "none"
    native["tensors"] = {}
    native["diagnostics"] = {"d_rejected_reason": "Native force balance failed"}
    append_native_quantities(path, native)
    with pytest.raises(KeyError):
        ResponseRecord.read(path).quantity("piezoelectric_d")


def test_native_force_constants_export_phonopy_and_cubic_irreps(tmp_path):
    from zstar.vasp_response import write_native_phonopy
    from zstar.read_irrep import read_irreps_yaml

    modes = mock_gamma_modes()
    modes.lattice_angstrom[:] = np.asarray([[0, 2.18, 2.18], [2.18, 0, 2.18], [2.18, 2.18, 0]])
    force_constants = np.empty((2, 2, 3, 3))
    force_constants[0, 0] = force_constants[1, 1] = np.eye(3) * 20
    force_constants[0, 1] = force_constants[1, 0] = -np.eye(3) * 20
    previous = Path.cwd()
    write_native_phonopy(modes, force_constants, tmp_path)
    assert Path.cwd() == previous
    assert (tmp_path / "phonopy.yaml").is_file()
    group, branches = read_irreps_yaml(tmp_path / "irreps.yaml")
    assert group == "-43m"
    assert len(branches) == 2
    assert all(label == "T2" for label, _, _ in branches)


def test_native_raman_export_matches_ascending_gamma_ids(tmp_path, monkeypatch):
    from zstar.spectroscopy_backends import _collect_vasp_spectra
    from zstar.spectra import load_raman_tensors, calculate_raman_spectrum

    modes = mock_gamma_modes()
    native_order = np.asarray([5, 0, 3, 1, 4, 2])
    frequencies = np.asarray([0., 0., 0., 8., 9., 10.])
    native = GammaModes(frequencies[native_order], modes.eigenvectors[native_order],
                        modes.masses_amu, modes.lattice_angstrom,
                        modes.symbols, modes.positions_fractional)
    monkeypatch.setattr("zstar.spectroscopy_backends.load_vasp_gamma_modes", lambda _: native)
    born = np.asarray([np.eye(3), -np.eye(3)])
    def response(path):
        value = 4. if path.parent.name == "reference" else (5. if path.parent.name == "plus" else 3.)
        return np.eye(3) * value, born
    monkeypatch.setattr("zstar.spectroscopy_backends.parse_vasp_outcar", response)
    manifest = {"modes_source": "native.xml", "dimensionality": 3,
                "amplitude_A_sqrt_amu": 0.01,
                "modes": [{"mode": i, "plus": f"mode-{i}/plus", "minus": f"mode-{i}/minus"}
                          for i in [1, 3, 5]]}
    from zstar.spectroscopy_backends import _write_vasp_poscar
    (tmp_path / "reference").mkdir()
    _write_vasp_poscar(tmp_path / "reference/POSCAR", native)
    result = _collect_vasp_spectra(tmp_path, manifest, broadening_cm1=5., laser_nm=532.,
                                  temperature_K=300., points=101, plot=False,
                                  imaginary_tolerance_cm1=5., allow_imaginary=False)
    assert result["native_mode_numbers"] == [1, 3, 5]
    assert result["mode_numbers"] == [6, 4, 5]
    assert [source["native_mode"] for source in result["raman_sources"]] == [1, 3, 5]
    exported = load_gamma_modes(tmp_path / "qpoints.yaml")
    numbers, tensors, kind = load_raman_tensors(tmp_path / "spectra_results.json")
    np.testing.assert_allclose(exported.frequencies_cm1[numbers - 1], result["frequencies_cm-1"])
    roundtrip = calculate_raman_spectrum(exported, numbers, tensors, tensor_kind=kind,
                                        points=101, broadening_cm1=5.)
    np.testing.assert_allclose(roundtrip.frequencies_cm1, result["frequencies_cm-1"])


def test_legacy_native_raman_ids_are_rejected_with_regeneration_guidance(tmp_path):
    from zstar.spectra import load_raman_tensors

    path = tmp_path / "spectra_results.json"
    path.write_text(json.dumps({"calculator": "vasp", "mode_numbers": [1],
                                "raman_tensors": [np.eye(3).tolist()]}))
    with pytest.raises(ValueError, match="zstar spectra post"):
        load_raman_tensors(path)


def test_wrong_reference_geometry_is_rejected_before_spectra_collection(tmp_path):
    from zstar.spectroscopy_backends import _validate_vasp_mode_geometry, _write_vasp_poscar

    (tmp_path / "reference").mkdir()
    modes = mock_gamma_modes()
    displacement = np.zeros((2, 3))
    displacement[1, 2] = .01
    _write_vasp_poscar(tmp_path / "reference/POSCAR", modes, displacement)
    with pytest.raises(ValueError, match="initial equilibrium"):
        _validate_vasp_mode_geometry(tmp_path, modes)


def test_native_cache_rejects_competing_mode_source(tmp_path):
    from zstar.spectroscopy_backends import prepare_vasp_spectra

    cache = native_cache(tmp_path)
    with pytest.raises(ValueError, match="same native response"):
        prepare_vasp_spectra(tmp_path / "unused", tmp_path / "different.xml", tmp_path / "ir", native_response_root=cache)


def test_force_cannot_delete_reused_native_cache(tmp_path, monkeypatch):
    from zstar.spectroscopy_backends import prepare_vasp_spectra

    cache = native_cache(tmp_path)
    monkeypatch.setattr("zstar.spectroscopy_backends.load_vasp_gamma_modes", lambda _: mock_gamma_modes())
    with pytest.raises(ValueError, match="cached response"):
        prepare_vasp_spectra(tmp_path / "unused", None, cache, kind="ir", native_response_root=cache, force=True)
    assert (cache / "response/OUTCAR").is_file()


@pytest.mark.parametrize("dim", [2, 3])
def test_native_common_record_preserves_units_and_low_dimensional_label(tmp_path, dim):
    from zstar.response_schema import ResponseRecord, response_record_from_bec_result
    from zstar.vasp_response import append_native_quantities

    path = tmp_path / "response.json"
    response_record_from_bec_result({"backend": "vasp", "atoms": [{"label": "Si", "tensor": np.eye(3)}]},
                                    dimensionality=dim).write(path)
    native = {"tensors": {"epsilon_ph": (np.eye(3) * 2).tolist(),
                           "piezoelectric_total_C_m2": np.ones((3, 6)).tolist()},
              "source": "OUTCAR", "electric_boundary": "fixed E", "mechanical_boundary": "fixed strain",
              "diagnostics": {"static_dielectric_max_abs": 0.0001}}
    append_native_quantities(path, native)
    append_native_quantities(path, native)
    record = ResponseRecord.read(path)
    name = "piezoelectric_relaxed" if dim == 3 else "supercell_piezoelectric_relaxed"
    quantity = record.quantity(name)
    assert quantity.unit == "C/m^2"
    assert quantity.metadata["intrinsic_low_dimensional_response_required"] == (dim < 3)
    assert len(record.quantities) == 3


def test_vasp_cli_returns_failure_exit_code_for_failed_native_stage(monkeypatch):
    from zstar.cli import zstar_cli
    from zstar.vasp_bec import VaspStageState

    monkeypatch.setattr("zstar.vasp_bec.run_vasp_bec", lambda *args, **kwargs: [VaspStageState("response", "response", status="failed")])
    with pytest.raises(SystemExit) as error:
        zstar_cli(["vasp-bec", "run", "--root", "native"], _canonical=False)
    assert error.value.code == 1


def test_vasp_cli_surfaces_native_quality_warnings(monkeypatch, capsys):
    from zstar.cli import zstar_cli

    result = {"output": "BEC.raw.dat", "born_output": "BORN", "json_output": "vasp_bec.json",
              "response_output": "response.json", "acoustic_sum_tensor": np.zeros((3, 3)),
              "native_response": {"diagnostics": {
                  "electromechanical_warning": "Native force balance failed",
                  "d_rejected_reason": "No reliable d tensor emitted"}}}
    monkeypatch.setattr("zstar.vasp_bec.collect_vasp_bec", lambda *args, **kwargs: result)
    zstar_cli(["vasp-bec", "collect", "--root", "native"], _canonical=False)
    output = capsys.readouterr().out
    assert "[WARN] Native force balance failed" in output
    assert "[WARN] No reliable d tensor emitted" in output


def test_slurm_spectra_driver_respects_specified_vasp_launcher(tmp_path):
    from zstar.spectra_frontend import _write_driver

    root = tmp_path / "spectra"
    (root / ".zstar").mkdir(parents=True)
    script = _write_driver(str(root), system="slurm", output=None, job_name="native", nodes=1,
                           tasks=64, cpus_per_task=1, walltime="00:30:00", queue=None,
                           account=None, env_script=None, dry_run=False, calculator="vasp",
                           calculator_command="mpirun -np 64 vasp_std")
    text = script.read_text()
    assert "--command 'mpirun -np 64 vasp_std'" in text
    assert "srun" not in text
    assert "--exclusive" not in text
    assert "#SBATCH --ntasks=64" in text


def test_spectra_restart_only_requires_wavefunctions_when_istart_requests_them(tmp_path):
    from zstar.spectroscopy_backends import _copy_vasp_restart

    reference = tmp_path / "reference"
    target = tmp_path / "displaced"
    reference.mkdir()
    target.mkdir()
    (reference / "CHGCAR").write_bytes(b"charge density")
    (target / "INCAR").write_text("ISTART=0; ICHARG=1\n")
    _copy_vasp_restart(reference, target)
    assert (target / "CHGCAR").read_bytes() == b"charge density"
    assert not (target / "WAVECAR").exists()
    (target / "INCAR").write_text("ISTART=1\n")
    with pytest.raises(FileNotFoundError, match="WAVECAR"):
        _copy_vasp_restart(reference, target)
