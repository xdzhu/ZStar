import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pytest

from zstar.density_adapters import (
    cp2k_density_cube_block,
    qe_pp_cube_input,
    vasp_chgcar_to_cube,
    write_cube_sidecar,
    write_qe_cube_sidecar,
)
from zstar.polarization_2d import integrate_slab_dipole


def write_nuclear_charge_cube(path: Path) -> None:
    values = [0.0] * 32
    values[4] = 1.0
    lines = [
        "test", "positive electron density",
        "1 0 0 0", "2 1 0 0", "2 0 1 0", "8 0 0 1",
        "6 6.0 0 0 4.0",
    ]
    for start in range(0, len(values), 6):
        lines.append(" ".join(str(value) for value in values[start:start + 6]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class DensityAdapterTests(unittest.TestCase):
    def test_vasp_chgcar_cube_has_physical_electron_density(self):
        pytest.importorskip("pymatgen")
        from pymatgen.core import Structure
        from pymatgen.io.vasp.outputs import Chgcar

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            structure = Structure(np.eye(3) * 10.0, ["H"], [[0.5, 0.5, 0.5]])
            source = root / "CHGCAR"
            Chgcar(structure, {"total": np.ones((4, 4, 4))}).write_file(source)
            cube = vasp_chgcar_to_cube(source, root / "density.cube")
            dipole = integrate_slab_dipole(cube, ionic_valence_charges=[1.0])
            self.assertAlmostEqual(dipole.electron_count_raw, 1.0, places=5)
            self.assertAlmostEqual(dipole.ionic_charge, 1.0)

    def test_sidecar_overrides_nuclear_charge_with_valence_charge(self):
        with tempfile.TemporaryDirectory() as tmp:
            cube = Path(tmp) / "charge-density.cube"
            write_nuclear_charge_cube(cube)
            with self.assertRaisesRegex(ValueError, "neutrality"):
                integrate_slab_dipole(cube)
            sidecar = write_cube_sidecar(cube, [1.0], backend="test")
            self.assertTrue(sidecar.is_file())
            result = integrate_slab_dipole(cube)
            self.assertAlmostEqual(result.ionic_charge, 1.0)

    def test_qe_export_input_uses_total_density_cube(self):
        text = qe_pp_cube_input(prefix="hbn", outdir="../scratch")
        self.assertIn("plot_num = 0", text)
        self.assertIn("output_format = 6", text)
        self.assertIn("charge-density.cube", text)

    def test_qe_sidecar_reads_upf_valence_in_atom_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "B.UPF").write_text('<PP_HEADER z_valence="3.0"/>', encoding="utf-8")
            (root / "N.UPF").write_text('<PP_HEADER z_valence="5.0"/>', encoding="utf-8")
            pw = root / "pw.in"
            pw.write_text(
                "ATOMIC_SPECIES\nB 10.81 B.UPF\nN 14.01 N.UPF\n"
                "ATOMIC_POSITIONS crystal\nN 0 0 0\nB 0.3 0.3 0\n",
                encoding="utf-8",
            )
            cube = root / "density.cube"
            cube.write_text("placeholder", encoding="utf-8")
            sidecar = write_qe_cube_sidecar(cube, pw, pseudo_dir=root)
            data = json.loads(sidecar.read_text())
            self.assertEqual(data["ionic_valence_charges"], [5.0, 3.0])

    def test_cp2k_cube_block_is_explicit(self):
        self.assertEqual(
            cp2k_density_cube_block(stride=(2, 2, 1)),
            "&E_DENSITY_CUBE\n  STRIDE 2 2 1\n&END E_DENSITY_CUBE\n",
        )


if __name__ == "__main__":
    unittest.main()
