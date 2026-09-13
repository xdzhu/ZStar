from pathlib import Path

import numpy as np
import pytest

from zstar.v2 import parse_vasp_outcar_observations


def _outcar(with_forces: bool = True) -> str:
    blocks = ""
    if with_forces:
        blocks = """
 POSITION                                       TOTAL-FORCE (eV/Angst)
 -----------------------------------------------------------------------------------
 0.000000 0.000000 0.000000     0.100000 0.200000 0.300000
 1.000000 1.000000 1.000000    -0.100000 -0.200000 -0.300000
 POSITION                                       TOTAL-FORCE (eV/Angst)
 -----------------------------------------------------------------------------------
 0.000000 0.000000 0.000000     0.010000 0.020000 0.030000
 1.000000 1.000000 1.000000    -0.010000 -0.020000 -0.030000
"""
    return f"""
 ions per type =  1  1
 direct lattice vectors                 reciprocal lattice vectors
   3.0 0.0 0.0   1.0 0.0 0.0
   0.0 3.1 0.0   0.0 1.0 0.0
   0.0 0.0 3.2   0.0 0.0 1.0
 FORCE on cell =-STRESS in cart. coord.  units (eV)
  Direction    XX          YY          ZZ          XY          YZ          ZX
  in kB       10.0        20.0        30.0         1.0         2.0         3.0
 free  energy   TOTEN  =       -12.34567890 eV
{blocks}
 General timing and accounting informations for this job
"""


def test_parse_vasp_observations_preserves_raw_stress_and_all_force_blocks(tmp_path: Path):
    source = tmp_path / "OUTCAR"
    source.write_text(_outcar(), encoding="utf-8")
    result = parse_vasp_outcar_observations(source, require_forces=True)
    assert result.natoms == 2
    assert result.energy == -12.34567890
    np.testing.assert_allclose(result.stress, [[10, 1, 3], [1, 20, 2], [3, 2, 30]])
    assert result.stress_unit == "kbar"
    assert result.stress_sign == "vasp-raw"
    assert len(result.force_blocks) == 2
    np.testing.assert_allclose(result.forces_initial[0], [0.1, 0.2, 0.3])
    np.testing.assert_allclose(result.forces_final[1], [-0.01, -0.02, -0.03])
    np.testing.assert_allclose(result.lattice_angstrom, np.diag([3.0, 3.1, 3.2]))


def test_parse_vasp_observations_allows_missing_forces_for_stress_energy(tmp_path: Path):
    source = tmp_path / "OUTCAR"
    source.write_text(_outcar(with_forces=False), encoding="utf-8")
    result = parse_vasp_outcar_observations(source)
    assert result.force_blocks == ()
    assert "force_parse_error" in result.provenance
    with pytest.raises(ValueError, match="TOTAL-FORCE"):
        parse_vasp_outcar_observations(source, require_forces=True)


def test_parse_vasp_observations_requires_energy_stress_lattice(tmp_path: Path):
    source = tmp_path / "OUTCAR"
    source.write_text("ions per type = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stress"):
        parse_vasp_outcar_observations(source)
