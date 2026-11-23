import json

import pytest

from zstar.pyatb_hamiltonian import prepare_pyatb_hamiltonian


def _fixture(tmp_path):
    structure = tmp_path/"POSCAR"
    structure.write_text("Test\n1\n3 0 0\n0 3 0\n0 0 3\nH\n1\nDirect\n0.2 0.3 0.4\n")
    for tag in "HSr":
        (tmp_path/f"{tag}.csr").write_text(f"STEP: 0\nMatrix Dimension of {tag}(R): 2\n")
    infile = tmp_path/"Input"
    infile.write_text("""INPUT_PARAMETERS
{
 package ABACUS
 nspin 1
 HR_route old.csr
 SR_route S.csr
 rR_route r.csr
 HR_unit Ry
 fermi_energy_unit eV
 fermi_energy 1.0
}
LATTICE
{
 lattice_constant 3
 lattice_constant_unit Angstrom
 lattice_vector
   1 0 0
   0 1 0
   0 0 1
}
POLARIZATION
{
 stru_file POSCAR
}
""")
    return infile, tmp_path/"H.csr", structure


@pytest.mark.parametrize("model", ("hamgnn", "deeph", "nextham"))
def test_exported_hamiltonian_keeps_matrix_partners(tmp_path, model):
    infile, hamiltonian, structure = _fixture(tmp_path)
    output = prepare_pyatb_hamiltonian(infile, hamiltonian, structure, structure,
                                      model=model, fermi_energy_ev=1.5,
                                      output_dir=tmp_path/model)
    text = (output/"Input").read_text()
    assert "fermi_energy 1.5" in text
    assert hamiltonian.as_posix() in text and "old.csr" not in text
    assert (tmp_path/"S.csr").as_posix() in text
    assert (tmp_path/"r.csr").as_posix() in text
    assert (output/"hamiltonian_source.json").is_file()
    assert "old.csr" in infile.read_text()


def test_geometry_mismatch_does_not_write_prepared_input(tmp_path):
    infile, hamiltonian, structure = _fixture(tmp_path)
    other = tmp_path/"different.vasp"
    other.write_text(structure.read_text().replace("0.2 0.3 0.4", "0.1 0.3 0.4"))
    with pytest.raises(ValueError, match="different atomic positions"):
        prepare_pyatb_hamiltonian(infile, hamiltonian, structure, other,
                                  model="hamgnn", fermi_energy_ev=1.5,
                                  output_dir=tmp_path/"export")
    assert not (tmp_path/"export").exists()


def test_nextham_spinor_export_keeps_spinor_template(tmp_path):
    infile, hamiltonian, structure = _fixture(tmp_path)
    infile.write_text(infile.read_text().replace("nspin 1", "nspin 4"))
    output = prepare_pyatb_hamiltonian(infile, hamiltonian, structure, structure,
                                      model="nextham", fermi_energy_ev=1.5,
                                      output_dir=tmp_path/"nextham-spinor")
    assert "nspin 4" in (output/"Input").read_text()
    assert json.loads((output/"hamiltonian_source.json").read_text())["nspin"] == 4
    with pytest.raises(ValueError, match="deeph requires an ABACUS template with nspin 1"):
        prepare_pyatb_hamiltonian(infile, hamiltonian, structure, structure,
                                  model="deeph", fermi_energy_ev=1.5,
                                  output_dir=tmp_path/"deeph-spinor")


@pytest.mark.parametrize("unit_line", (" lattice_constant_unit Bohr\n", ""))
def test_template_cell_accepts_equivalent_bohr(tmp_path, unit_line):
    infile, hamiltonian, structure = _fixture(tmp_path)
    original = infile.read_text()
    infile.write_text(original.replace(
        " lattice_constant 3\n lattice_constant_unit Angstrom\n",
        " lattice_constant 5.66917837387731\n" + unit_line,
    ))
    output = prepare_pyatb_hamiltonian(infile, hamiltonian, structure, structure,
                                      model="nextham", fermi_energy_ev=1.5,
                                      output_dir=tmp_path/"bohr")
    assert "lattice_constant 5.66917837387731" in (output/"Input").read_text()


def test_wrong_template_lattice_does_not_prepare_input(tmp_path):
    infile, hamiltonian, structure = _fixture(tmp_path)
    infile.write_text(infile.read_text().replace(" lattice_constant 3", " lattice_constant 4"))
    output = tmp_path/"export"
    with pytest.raises(ValueError, match="PYATB LATTICE differs"):
        prepare_pyatb_hamiltonian(infile, hamiltonian, structure, structure,
                                  model="deeph", fermi_energy_ev=1.5, output_dir=output)
    assert not output.exists()


def _hotham_files(tmp_path):
    infile, hamiltonian, structure = _fixture(tmp_path)
    # Opposite translations carry distinct row/column indices.
    blocks = ("0 0 0 2\n1 1\n0 1\n0 1 2\n"
              "1 -2 0 1\n0.125\n1\n0 1 1\n"
              "-1 2 0 1\n0.125\n0\n0 0 1\n")
    overlap = tmp_path / "olp.csr"
    for kind, path in [("S", overlap), ("S", tmp_path / "S.csr"), ("H", hamiltonian)]:
        header = f"STEP: 0\nMatrix Dimension of {kind}(R): 2\nMatrix number of {kind}(R): 3\n"
        path.write_text(header + (blocks.replace("0.125", "-0.75") if kind == "H" else blocks))
    return infile, hamiltonian, structure, overlap


def test_hotham_cli_keeps_native_ry_and_matrix_partners(tmp_path):
    from hashlib import sha256
    from zstar.cli import zstar_cli

    infile, hamiltonian, structure, overlap = _hotham_files(tmp_path)
    output = tmp_path / "prepared"
    zstar_cli(["response", "pyatb-hamiltonian", "--model", "hotham",
               "--input", str(infile), "--hamiltonian", str(hamiltonian),
               "--model-overlap", str(overlap), "--structure", str(structure),
               "--prediction-structure", str(structure), "--fermi-energy", "0.1",
               "--output-dir", str(output)])
    text = (output / "Input").read_text()
    for path in [hamiltonian, tmp_path / "S.csr", tmp_path / "r.csr"]:
        assert path.as_posix() in text
    receipt = json.loads((output / "hamiltonian_source.json").read_text())
    assert receipt["source_files"]["model_overlap"]["sha256"] == sha256(overlap.read_bytes()).hexdigest()
    assert receipt["model"] == "hotham"


@pytest.mark.parametrize("fault, message", [
    ("shift", "overlap differs"), ("orbital", "overlap differs"), ("complex", "real CSR"),
    ("unpaired", r"H\(-R\)"), ("spin", "nspin 1"), ("missing", "--model-overlap"),
])
def test_hotham_rejects_incompatible_exports(tmp_path, fault, message):
    infile, hamiltonian, structure, overlap = _hotham_files(tmp_path)
    if fault == "shift":
        overlap.write_text(overlap.read_text().replace("1 -2 0 1", "0 -2 0 1"))
    elif fault == "orbital":
        overlap.write_text(overlap.read_text().replace("0.125\n1", "0.125\n0"))
    elif fault == "complex":
        hamiltonian.write_text(hamiltonian.read_text().replace("-0.75", "(-0.75,0)"))
    elif fault == "unpaired":
        hamiltonian.write_text(hamiltonian.read_text().replace("-0.75", "-0.25", 1))
    elif fault == "spin":
        infile.write_text(infile.read_text().replace("nspin 1", "nspin 2"))
    elif fault == "missing":
        overlap = None
    with pytest.raises(ValueError, match=message):
        prepare_pyatb_hamiltonian(infile, hamiltonian, structure, structure,
                                  model="hotham", model_overlap=overlap,
                                  fermi_energy_ev=0.1, output_dir=tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_hotham_inference_xyz_selects_one_matching_frame(tmp_path):
    pytest.importorskip("ase")
    infile, hamiltonian, structure, overlap = _hotham_files(tmp_path)
    xyz = tmp_path / "model.xyz"
    frame = '1\nLattice="3 0 0 0 3 0 0 0 3" Properties=species:S:1:pos:R:3\nH 0.6 0.9 1.2\n'

    def prepare():
        return prepare_pyatb_hamiltonian(infile, hamiltonian, structure, xyz, model="hotham",
                                         model_overlap=overlap, fermi_energy_ev=0.1,
                                         output_dir=tmp_path / "out")

    xyz.write_text(frame * 2)
    with pytest.raises(ValueError, match="one prediction frame"):
        prepare()
    xyz.write_text(frame.replace("0.6 0.9", "0.9 0.6"))
    with pytest.raises(ValueError, match="different atomic positions"):
        prepare()
    xyz.write_text(frame)
    assert (prepare() / "Input").is_file()
