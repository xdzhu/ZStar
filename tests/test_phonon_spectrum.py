import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from zstar.phonon_spectrum import (
    _axis_ticks,
    _continuous_distances,
    infer_supercell,
    parse_periodic_axes,
    parse_supercell,
    run_phonon_spectrum,
)
from zstar.phonon_gen import run_phonopy_and_process_files


class PhononSpectrumTests(unittest.TestCase):
    def test_auto_supercell_exceeds_threshold_only_on_periodic_axes(self):
        repeats = infer_supercell(
            np.diag([3.0, 5.0, 12.0]), dimensionality=2, minimum_length=10.0
        )
        self.assertEqual(repeats, (4, 3, 1))

    def test_strict_threshold_repeats_exact_ten_angstrom_vector(self):
        self.assertEqual(
            infer_supercell(np.diag([10.0, 11.0, 11.0]), minimum_length=10.0),
            (2, 1, 1),
        )

    def test_axis_parser_supports_named_axes(self):
        self.assertEqual(parse_periodic_axes("z", 3), (False, False, True))
        self.assertEqual(parse_periodic_axes(None, 2), (True, True, False))
        self.assertEqual(parse_supercell("2, 3 4"), (2, 3, 4))

    def test_custom_abacus_input_is_staged_as_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "STRU").write_text(
                "ATOMIC_SPECIES\nSi 28.0 Si.upf\n"
                "LATTICE_CONSTANT\n1.0\nLATTICE_VECTORS\n"
                "3 0 0\n0 3 0\n0 0 3\n"
                "ATOMIC_POSITIONS\nDirect\nSi\n0\n0 0 0 1 1 1\n",
                encoding="utf-8",
            )
            (root / "INPUT-GPU").write_text(
                "INPUT_PARAMETERS\ncal_force 1\nks_solver cusolver\n",
                encoding="utf-8",
            )
            (root / "KPT").write_text("K_POINTS\n0\nGamma\n1 1 1 0 0 0\n", encoding="utf-8")
            (root / "Si.upf").write_text("placeholder", encoding="utf-8")
            with patch("zstar.phonon_gen._phonopy_displacements") as generate:
                displaced = root / "STRU-001"
                displaced.write_text((root / "STRU").read_text(), encoding="utf-8")
                generate.side_effect = lambda *args, **kwargs: None
                with patch.object(Path, "glob", side_effect=[ [displaced], [] ]):
                    with patch("zstar.phonon_gen._referenced_abacus_assets", return_value=[]):
                        with patch("zstar.phonon_gen._copy_optional_script"):
                            with patch("zstar.phonon_gen.create_symlink") as link:
                                with patch("os.getcwd", return_value=str(root)):
                                    previous = Path.cwd()
                                    try:
                                        import os
                                        os.chdir(root)
                                        run_phonopy_and_process_files(
                                            f_stru="STRU", input_file="INPUT-GPU", abacus_sub=None
                                        )
                                    finally:
                                        os.chdir(previous)
            link.assert_any_call(root / "INPUT-GPU", root / "disp-001" / "INPUT")

    def test_disconnected_band_segments_have_distinct_tick_positions(self):
        segments = [
            np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]]),
            np.array([[0.0, 0.5, 0.0], [0.0, 0.0, 0.0]]),
        ]
        distances = _continuous_distances(segments, [False])
        ticks, labels = _axis_ticks(
            distances, ["X", "R", "X", "M"], [False]
        )
        self.assertGreater(distances[1][0] - distances[0][-1], 0.1)
        self.assertEqual(labels, ["X", "R", "X", "M"])
        self.assertEqual(len(ticks), 4)

    def test_shared_endpoint_keeps_one_continuous_label(self):
        distances = [
            np.array([0.0, 0.5]),
            np.array([0.5, 1.0]),
        ]
        ticks, labels = _axis_ticks(
            distances, ["Gamma", "X", "M", "R"], [False]
        )
        self.assertEqual(ticks, [0.0, 0.5, 1.0])
        self.assertEqual(labels, ["Gamma", "X", "R"])

    def test_missing_force_archive_is_actionable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError, "complete `zstar phonon post`"):
                run_phonon_spectrum(tmp)

    def test_spectrum_cli_writes_three_outputs_from_archived_data(self):
        source = Path("examples/3D_Bulk/cubic_BaTiO3/results/unified")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("phonopy.yaml", "FORCE_CONSTANTS", "BORN"):
                (root / name).write_bytes((source / name).read_bytes())
            result = run_phonon_spectrum(root, npoints=7, mesh=(4, 4, 4))
            self.assertTrue(result["nac_available"])
            self.assertEqual(len(result["outputs"]), 6)
            for name in result["outputs"]:
                self.assertTrue((root / name).is_file(), name)
            saved = json.loads((root / "phonon_spectrum_result.json").read_text())
            self.assertIn("$\\Gamma$", saved["labels"])
            self.assertEqual(saved["frequency_unit"], "THz")

    def test_spectrum_loads_force_sets_archive_without_force_constants(self):
        source = Path("examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/results")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("phonopy.yaml", "FORCE_SETS", "BORN"):
                (root / name).write_bytes((source / name).read_bytes())
            result = run_phonon_spectrum(root, npoints=5, mesh=(2, 2, 2))
            self.assertTrue(result["nac_available"])
            self.assertTrue((root / "phonon_band_dos_nac_comparison.pdf").is_file())

    def test_spectrum_can_write_band_only_comparison(self):
        source = Path("examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/results")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("phonopy.yaml", "FORCE_SETS", "BORN"):
                (root / name).write_bytes((source / name).read_bytes())
            result = run_phonon_spectrum(
                root, npoints=5, mesh=(2, 2, 2), band_only=True
            )
            self.assertIn("phonon_band_nac_comparison.pdf", result["outputs"])
            self.assertTrue((root / "phonon_band_nac_comparison.pdf").is_file())
            self.assertTrue((root / "phonon_band_nac_comparison.png").is_file())

    def test_band_only_requires_born(self):
        source = Path("examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/results")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("phonopy.yaml", "FORCE_SETS"):
                (root / name).write_bytes((source / name).read_bytes())
            with self.assertRaisesRegex(FileNotFoundError, "--band-only requires"):
                run_phonon_spectrum(root, band_only=True)

    def test_can_omit_disconnected_path_tail(self):
        source = Path("examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/results")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("phonopy.yaml", "FORCE_SETS", "BORN"):
                (root / name).write_bytes((source / name).read_bytes())
            result = run_phonon_spectrum(
                root,
                npoints=5,
                mesh=(2, 2, 2),
                band_only=True,
                omit_disconnected_tail=True,
            )
            self.assertEqual(
                result["labels"],
                ["$\\Gamma$", "$\\mathrm{X}$", "$\\mathrm{M}$", "$\\Gamma$", "$\\mathrm{R}$", "$\\mathrm{X}$"],
            )
            self.assertEqual(len(result["wo_nac"]["distances"]), 5)


if __name__ == "__main__":
    unittest.main()
