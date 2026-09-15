import csv
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from zstar.qnep_dataset import (
    augment_qnep_dataset,
    check_qnep_dataset,
    compose_qnep_dataset,
    export_qnep_jsonl_dataset,
    score_qnep_predictions,
    write_qnep_input,
)


FRAME = """2
Lattice="5 0 0 0 5 0 0 0 5" energy=-10 Properties=species:S:1:pos:R:3:force:R:3
Na 0 0 0 0.1 0.2 0.3
Cl 2.5 2.5 2.5 -0.1 -0.2 -0.3
"""


ZBORN = """No. Atom xx xy xz yx yy yz zx zy zz
 1 Na 1 2 3 4 5 6 7 8 9
 2 Cl -1 -2 -3 -4 -5 -6 -7 -8 -9
"""


class QnepDatasetTests(unittest.TestCase):
    @staticmethod
    def _record(frame_id, symbols, positions, *, phase=None, bec=None, available=False):
        return {
            "frame_id": frame_id,
            "structure_id": frame_id,
            "chemical_symbols": symbols,
            "cell": [[5, 0, 0], [0, 5, 0], [0, 0, 5]],
            "positions": positions,
            "forces": [[0.1, 0.2, 0.3], [-0.1, -0.2, -0.3]],
            "energy": -10.0,
            "total_charge": 0.0,
            "phase_label": phase,
            "born_effective_charges_available": available,
            "born_effective_charges": bec,
            "metadata": {"bec_convention": "zstar"},
        }

    def test_jsonl_export_inherits_phase_and_reorders_sparse_bec(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw.jsonl"
            annotation = root / "annotation.jsonl"
            raw_records = [
                self._record("alpha::0.no-move", ["Na", "Cl"], [[0, 0, 0], [2.5, 2.5, 2.5]]),
                self._record("alpha::disp-001", ["Na", "Cl"], [[0.01, 0, 0], [2.5, 2.5, 2.5]]),
            ]
            bec = [
                [[-1, -2, -3], [-4, -5, -6], [-7, -8, -9]],
                [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            ]
            annotated = self._record(
                "alpha", ["Cl", "Na"], [[2.5, 2.5, 2.5], [0, 0, 0]],
                phase="tetragonal", bec=bec, available=True,
            )
            raw.write_text("\n".join(json.dumps(item) for item in raw_records) + "\n", encoding="utf-8")
            annotation.write_text(json.dumps(annotated) + "\n", encoding="utf-8")
            output = root / "out.xyz"
            summary = export_qnep_jsonl_dataset(raw, output, annotations_jsonl=annotation)
            self.assertEqual(summary["frames"], 2)
            self.assertEqual(summary["labeled_frames"], 1)
            self.assertEqual(summary["phase_counts"], {"tetragonal": 2})
            lines = output.read_text().splitlines()
            self.assertIn("phase_label=tetragonal", lines[1])
            self.assertEqual(
                lines[2].split()[-9:],
                ["1.0000000000", "4.0000000000", "7.0000000000", "2.0000000000", "5.0000000000", "8.0000000000", "3.0000000000", "6.0000000000", "9.0000000000"],
            )
            self.assertEqual(check_qnep_dataset(output)["labeled_frames"], 1)

    def test_jsonl_export_rejects_zero_bec_as_missing_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = self._record(
                "zero", ["Na", "Cl"], [[0, 0, 0], [2.5, 2.5, 2.5]],
                bec=[[[0, 0, 0]] * 3, [[0, 0, 0]] * 3], available=True,
            )
            source = root / "zero.jsonl"
            source.write_text(json.dumps(record) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "all-zero BEC"):
                export_qnep_jsonl_dataset(source, root / "out.xyz")

    def test_compose_selects_phase_with_a_reproducible_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.xyz"
            base.write_text(FRAME.replace("energy=-10", "energy=-10 frame_id=base phase_label=cubic"), encoding="utf-8")
            addition = root / "addition.xyz"
            addition.write_text(
                FRAME.replace("energy=-10", "energy=-11 frame_id=t1 phase_label=tetragonal")
                + FRAME.replace("energy=-10", "energy=-12 frame_id=t2 phase_label=tetragonal"),
                encoding="utf-8",
            )
            summary = compose_qnep_dataset(
                base, addition, root / "composed.xyz", phases=["tetragonal"], max_per_phase=1, seed=7
            )
            self.assertEqual(summary["frames"], 2)
            self.assertEqual(summary["selected_counts"], {"tetragonal": 1})
            self.assertEqual(summary["phase_counts"]["cubic"], 1)

    def test_score_uses_explicit_bec_mask_not_zero_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "test.xyz"
            labeled_header = (
                'Lattice="5 0 0 0 5 0 0 0 5" energy=-10 '
                'Properties=species:S:1:pos:R:3:force:R:3:bec:R:9'
            )
            labeled = "\n".join([
                "2", labeled_header,
                "Na 0 0 0 0.1 0.2 0.3 1 1 1 1 1 1 1 1 1",
                "Cl 2.5 2.5 2.5 -0.1 -0.2 -0.3 -1 -1 -1 -1 -1 -1 -1 -1 -1",
            ]) + "\n"
            source.write_text(labeled + FRAME, encoding="utf-8")
            np.savetxt(root / "energy_test.out", [[-5, -4], [-5, -6]])
            np.savetxt(root / "force_test.out", np.zeros((4, 6)))
            bec = np.zeros((4, 18))
            bec[:2, :9] = 1.0
            bec[:2, 9:] = 2.0
            bec[2:, 9:] = 999.0
            np.savetxt(root / "bec_test.out", bec)
            summary = score_qnep_predictions(source, root)
            self.assertEqual(summary["bec"]["labeled_atom_rows"], 2)
            self.assertAlmostEqual(summary["bec"]["mae"], 1.0)

    def test_augment_transposes_zstar_tensor_for_qnep(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "train.xyz"
            source.write_text(FRAME, encoding="utf-8")
            bec = root / "BEC.raw.dat"
            bec.write_text(ZBORN, encoding="utf-8")
            output = root / "train_qnep.xyz"
            summary = augment_qnep_dataset(source, output, bec=bec)
            lines = output.read_text().splitlines()
            self.assertIn(":bec:R:9", lines[1])
            self.assertEqual(
                lines[2].split()[-9:],
                [
                    "1.0000000000", "4.0000000000", "7.0000000000",
                    "2.0000000000", "5.0000000000", "8.0000000000",
                    "3.0000000000", "6.0000000000", "9.0000000000",
                ],
            )
            self.assertEqual(summary["labeled_frames"], 1)
            self.assertTrue(Path(summary["audit_output"]).is_file())

    def test_partial_labels_from_frame_map_are_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "train.xyz"
            source.write_text(FRAME + FRAME, encoding="utf-8")
            bec = root / "BEC.raw.dat"
            bec.write_text(ZBORN, encoding="utf-8")
            mapping = root / "map.csv"
            with mapping.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["frame", "bec"])
                writer.writerow([1, bec.name])
            output = root / "qnep.xyz"
            summary = augment_qnep_dataset(source, output, bec_map=mapping)
            self.assertEqual(summary["labeled_frames"], 1)
            self.assertEqual(summary["unlabeled_frames"], 1)
            checked = check_qnep_dataset(output)
            self.assertEqual(checked["labeled_frames"], 1)

    def test_atom_order_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "train.xyz"
            source.write_text(FRAME, encoding="utf-8")
            data = {
                "tensor_convention": "rows=atomic displacement/force; columns=polarization/electric field",
                "atoms": [
                    {"label": "Cl", "tensor": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
                    {"label": "Na", "tensor": [[-1, 0, 0], [0, -1, 0], [0, 0, -1]]},
                ],
            }
            bec = root / "bec.json"
            bec.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Atom order mismatch"):
                augment_qnep_dataset(source, root / "out.xyz", bec=bec)

    def test_minimal_qnep_input_uses_dataset_elements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "train.xyz"
            source.write_text(FRAME, encoding="utf-8")
            bec = root / "BEC.raw.dat"
            bec.write_text(ZBORN, encoding="utf-8")
            labeled = root / "qnep.xyz"
            augment_qnep_dataset(source, labeled, bec=bec)
            nep = write_qnep_input(labeled, root / "nep.in", charge_mode=2)
            text = nep.read_text()
            self.assertIn("type 2 Cl Na", text)
            self.assertIn("charge_mode 2", text)
            self.assertIn("lambda_z 0.5", text)


if __name__ == "__main__":
    unittest.main()
