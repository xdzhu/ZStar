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
