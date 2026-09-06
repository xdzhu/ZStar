import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from zstar.artifacts import LEGACY_NAMES, resolve_artifact
from zstar.agent_skill import preflight_report
from zstar.bec_database import read_zborn
from zstar.calc_kappa import read_and_extract_matrices
from zstar.qnep_dataset import read_bec_data
from zstar.response_schema import ResponseRecord, response_record_from_bec_result
from zstar.spectra import read_born_data
from zstar.verify_born_symmetry import load_born_all, load_born_reduced
from zstar.spectra_frontend import run_spectra_cli


class ArtifactNamesTests(unittest.TestCase):
    def test_every_alias_resolves_both_ways_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, (old, new) in enumerate(LEGACY_NAMES.items()):
                with self.subTest(old=old):
                    directory = root / str(index)
                    directory.mkdir()
                    legacy = directory / old
                    legacy.write_bytes(b"original evidence\r\n")
                    original_names = [p.name for p in directory.iterdir()]
                    before = hashlib.sha256(legacy.read_bytes()).hexdigest()
                    self.assertEqual(resolve_artifact(directory / new), legacy)
                    self.assertEqual([p.name for p in directory.iterdir()], original_names)
                    self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(), before)
                    canonical = directory / new
                    legacy.rename(canonical)
                    self.assertEqual(resolve_artifact(directory / old), canonical)
                    self.assertEqual(resolve_artifact(canonical), canonical)

    def test_explicit_existing_path_wins_and_typos_are_not_substituted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new = root / "Z-BORN-symm.out", root / "bec.dat"
            old.write_text("old", encoding="utf-8")
            new.write_text("new", encoding="utf-8")
            self.assertEqual(resolve_artifact(old), old)
            self.assertEqual(resolve_artifact(new), new)
            self.assertEqual(resolve_artifact(root / "my_bec.dat"), root / "my_bec.dat")

    def test_legacy_tensor_reaches_all_readers_without_axis_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tensor = np.arange(1.0, 10.0).reshape(3, 3)
            legacy = root / "Z-BORN-symm.out"
            legacy.write_text("# atom species Z[displacement,polarization]; units e\n"
                              "* 1 H 1 2 3 4 5 6 7 8 9\n", encoding="utf-8")
            path = root / "bec.dat"
            np.testing.assert_array_equal(read_born_data(path, natoms=1).tensors[0], tensor)
            np.testing.assert_array_equal(read_zborn(path)[0], tensor)
            np.testing.assert_array_equal(read_bec_data(path).tensors[0], tensor)
            np.testing.assert_array_equal(read_and_extract_matrices(path)[0], tensor)
            np.testing.assert_array_equal(load_born_all(str(path))[0][1], tensor)
            np.testing.assert_array_equal(load_born_reduced(str(path))[1][1], tensor)
            self.assertFalse(path.exists())

    def test_legacy_full_tensor_expands_phonopy_representatives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "BORN").write_text(
                "# ZStar shared response: Z[polarization,displacement]; units e\n"
                "5 0 0 0 5 0 0 0 5\n1 0 0 0 1 0 0 0 1\n", encoding="utf-8")
            (root / "Z-BORN-symm.out").write_text(
                "# full cell\n1 H 1 2 0 3 1 0 0 0 1\n2 H -1 -2 0 -3 -1 0 0 0 -1\n",
                encoding="utf-8")
            data = read_born_data(root / "BORN", natoms=2)
            self.assertEqual(data.tensors.shape, (2, 3, 3))
            self.assertEqual(data.tensors[0, 0, 1], 2)
            self.assertEqual(data.tensors[0, 1, 0], 3)

    def test_legacy_response_schema_and_agent_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = response_record_from_bec_result({
                "backend": "abacus", "atoms": [{"label": "H", "tensor": np.eye(3).tolist()}],
                "epsilon_infinity": (np.eye(3)*5).tolist()}, dimensionality=3)
            record.write(root / "zstar_response.json")
            restored = ResponseRecord.read(root / "response.json")
            self.assertEqual(restored.backend, "abacus")
            (root / "Z-BORN-symm.out").write_text("legacy", encoding="utf-8")
            (root / "qpoints.yaml").write_text("placeholder", encoding="utf-8")
            report = preflight_report(root, lane="dielectric")
            self.assertTrue(report["ready"])
            self.assertEqual(report["artifacts"]["BEC.dat"]["path"], "Z-BORN-symm.out")
            self.assertFalse((root / "response.json").exists())

    def test_discovery_rejects_conflicting_aliases_but_explicit_input_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "BEC.dat"
            old = root / "Z-BORN-symm.out"
            current.write_text("new result", encoding="utf-8")
            old.write_text("old result", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Conflicting result aliases.*explicit input"):
                resolve_artifact(current, explicit=False)
            self.assertEqual(resolve_artifact(old), old)
            self.assertEqual(resolve_artifact(current), current)

    def test_equal_aliases_prefer_current_without_removing_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current, old = root / "BEC.raw.dat", root / "Z-BORN-all.out"
            for path in (current, old):
                path.write_bytes(b"equal evidence\n")
            self.assertEqual(resolve_artifact(old, explicit=False), current)
            self.assertEqual(len(list(root.iterdir())), 2)

    def test_lowercase_archive_resolves_uppercase_default_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "bec.dat"
            old.write_text("* 1 H 1 2 3 4 5 6 7 8 9\n", encoding="utf-8")
            np.testing.assert_array_equal(read_born_data(root / "BEC.dat").tensors[0],
                                          np.arange(1., 10.).reshape(3, 3))
            self.assertEqual([p.name for p in root.iterdir()], ["bec.dat"])

    def test_spectra_manifest_default_checks_aliases_and_explicit_override_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current, old = root / 'BEC.dat', root / 'Z-BORN-symm.out'
            current.write_text('current')
            old.write_text('historical')
            saved = ('abacus', 'ir', 3, {'born': str(current), 'born_explicit': False})
            calls = []
            with patch('zstar.spectra_frontend._saved', return_value=saved):
                with self.assertRaisesRegex(ValueError, 'Conflicting result aliases'):
                    run_spectra_cli(['post', '--root', str(root)], calls.append)
                run_spectra_cli(['post', '--root', str(root), '--born', str(old)], calls.append)
            self.assertEqual(calls[0][calls[0].index('--born') + 1], str(old))
