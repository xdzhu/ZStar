import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

from zstar.charge_aware_dataset import (
    ChargeAwareFrame,
    annotate_bec_dataset,
    dataset_manifest,
    export_qnep_xyz,
    read_abacus_dataset,
    read_deepmd_dataset,
    read_charge_dataset,
    select_charge_frames,
    validate_charge_dataset,
    write_charge_dataset,
)
from zstar.qnep_dataset import check_qnep_dataset


def frame(i: int, *, bec: bool = False, phase: str = "cubic", temperature: float = 300.0):
    return ChargeAwareFrame(
        frame_id=f"f{i:03d}", structure_id="bto-cubic", chemical_symbols=["Ba", "Ti", "O", "O", "O"],
        cell=[[4.0, 0, 0], [0, 4.0, 0], [0, 0, 4.0]], positions=[[0, 0, 0], [2, 2, 2], [2, 0, 0], [0, 2, 0], [0, 0, 2]],
        pbc=[True, True, True], energy=-10.0 + i * 0.01, forces=[[0.0, 0.0, 0.0]] * 5,
        stress=[0.0] * 6, temperature=temperature, phase_label=phase,
        born_effective_charges=([[[float(i + 1), 0, 0], [0, 1, 0], [0, 0, 1]]] * 5 if bec else None),
        born_effective_charges_available=bec,
    )


class ChargeAwareDatasetTests(unittest.TestCase):
    def test_missing_bec_is_explicit_and_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.jsonl"
            write_charge_dataset([frame(0), frame(1, bec=True)], path)
            loaded = read_charge_dataset(path)
            self.assertFalse(loaded[0].born_effective_charges_available)
            self.assertIsNone(loaded[0].born_effective_charges)
            self.assertTrue(loaded[1].born_effective_charges_available)
            self.assertEqual(len(loaded[1].born_effective_charges), 5)

    def test_round_trip_and_export_keep_frame_ids_and_partial_bec(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "d.jsonl"
            labeled = frame(1, bec=True)
            labeled.total_charge = 1.0
            labeled.split = "validation"
            write_charge_dataset([frame(0), labeled], source)
            xyz = root / "train.xyz"
            result = export_qnep_xyz(source, xyz)
            checked = check_qnep_dataset(xyz)
            self.assertEqual(result["labeled_frames"], 1)
            self.assertEqual(checked["labeled_frames"], 1)
            self.assertIn("frame_id=f001", xyz.read_text())
            imported = read_charge_dataset(xyz)
            self.assertEqual([f.frame_id for f in imported], ["f000", "f001"])
            self.assertTrue(imported[1].born_effective_charges_available)
            self.assertEqual(imported[1].total_charge, 1.0)
            self.assertEqual(imported[1].split, "validation")

    def test_manifest_reports_split_counts(self):
        rows = [frame(0), frame(1)]
        rows[0].split = "train"
        rows[1].split = "test"
        self.assertEqual(dataset_manifest(rows)["split_counts"], {"train": 1, "test": 1})

    def test_selection_is_seeded_and_temperature_phase_stratified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "d.jsonl"
            rows = [frame(i, phase=("cubic" if i % 2 else "tetragonal"), temperature=100.0 + i * 100) for i in range(8)]
            write_charge_dataset(rows, source)
            a = root / "a.jsonl"
            b = root / "b.jsonl"
            select_charge_frames(source, a, count=4, seed=17, temperature_bins=[300, 600])
            select_charge_frames(source, b, count=4, seed=17, temperature_bins=[300, 600])
            self.assertEqual(a.read_text(), b.read_text())

    def test_validation_catches_mixed_settings_and_duplicate_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = frame(0)
            b = frame(1)
            b.exchange_correlation = "PBEsol"
            write_charge_dataset([a, b], root / "d.jsonl")
            report = validate_charge_dataset(root / "d.jsonl")
            self.assertFalse(report["valid"])
            self.assertTrue(any("mixed" in issue for issue in report["issues"]))
            self.assertTrue(any("duplicate structure" in issue for issue in report["issues"]))

    def test_validation_accepts_explicit_equivalent_kpoint_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = frame(0)
            a.kpoints = "Gamma 9x9x9"
            a.metadata = {"kpoint_policy": "ABACUS automatic kspacing=0.1 (Gamma 9x9x9 equivalent for primitive BTO)"}
            b = frame(1)
            b.kpoints = "ABACUS automatic kspacing=0.1"
            b.metadata = {"kpoint_policy": "ABACUS automatic kspacing=0.1"}
            # The geometries differ only enough to avoid the duplicate check.
            b.positions = [[0.001, 0, 0], [2, 2, 2], [2, 0, 0], [0, 2, 0], [0, 0, 2]]
            path = Path(tmp) / "d.jsonl"
            write_charge_dataset([a, b], path)
            report = validate_charge_dataset(path)
            self.assertTrue(report["valid"])

    def test_validation_flags_labeled_zero_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zero = frame(0, bec=True)
            zero.born_effective_charges = [[[0.0, 0.0, 0.0]] * 3] * 5
            write_charge_dataset([zero], root / "d.jsonl")
            report = validate_charge_dataset(root / "d.jsonl")
            self.assertFalse(report["valid"])
            self.assertTrue(any("all-zero" in issue for issue in report["issues"]))

    def test_validation_catches_parent_frame_split_leakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            train = frame(0)
            train.frame_id = "parent::disp-001"
            train.metadata = {"parent_frame_id": "parent"}
            train.split = "train"
            test = frame(1)
            test.frame_id = "parent::disp-002"
            test.metadata = {"parent_frame_id": "parent"}
            test.split = "test"
            report_path = root / "d.jsonl"
            write_charge_dataset([train, test], report_path)
            report = validate_charge_dataset(report_path)
            self.assertFalse(report["valid"])
            self.assertTrue(any("split across" in issue for issue in report["issues"]))

    def test_bec_annotation_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "d.jsonl"
            write_charge_dataset([frame(0), frame(1)], source)
            bec = root / "BEC.json"
            bec.write_text(json.dumps({"tensor_convention": "zstar", "atoms": [{"label": x, "tensor": [[1,0,0],[0,1,0],[0,0,1]]} for x in ["Ba", "Ti", "O", "O", "O"]]}))
            mapping = root / "map.csv"
            mapping.write_text(f"frame_id,bec\nf001,{bec}\n")
            output = root / "out.jsonl"
            result = annotate_bec_dataset(source, output, mapping)
            self.assertEqual(result["bec_labeled_frames"], 1)
            self.assertFalse(read_charge_dataset(output)[0].born_effective_charges_available)

    def test_bec_annotation_reorders_species_blocks_and_records_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "d.jsonl"
            target = frame(0)
            target.chemical_symbols = ["Ba", "O", "O", "O", "Ti"]
            target.atom_order = list(target.chemical_symbols)
            write_charge_dataset([target], source)
            bec = root / "BEC.json"
            bec.write_text(json.dumps({
                "tensor_convention": "zstar",
                "atoms": [
                    {"label": "Ba", "tensor": [[1,0,0],[0,1,0],[0,0,1]]},
                    {"label": "Ti", "tensor": [[2,0,0],[0,2,0],[0,0,2]]},
                    {"label": "O", "tensor": [[3,0,0],[0,3,0],[0,0,3]]},
                    {"label": "O", "tensor": [[4,0,0],[0,4,0],[0,0,4]]},
                    {"label": "O", "tensor": [[5,0,0],[0,5,0],[0,0,5]]},
                ],
            }))
            mapping = root / "map.csv"
            mapping.write_text(f"frame_id,bec\n{target.frame_id},{bec}\n")
            output = root / "out.jsonl"
            annotate_bec_dataset(source, output, mapping)
            result = read_charge_dataset(output)[0]
            self.assertTrue(result.born_effective_charges_available)
            self.assertEqual([row[0][0] for row in result.born_effective_charges], [1, 3, 4, 5, 2])
            self.assertTrue(result.metadata["bec_reordered_to_frame_atom_order"])

    def test_deepmd_npy_reader_supports_metadata_and_selection(self):
        import numpy as np

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "deepmd"
            (root / "set.000").mkdir(parents=True)
            np.save(root / "set.000" / "coord.npy", np.arange(2 * 15, dtype=float).reshape(2, 15))
            np.save(root / "set.000" / "box.npy", np.tile(np.eye(3).reshape(1, 9), (2, 1)) * 4.0)
            np.save(root / "set.000" / "energy.npy", np.asarray([-1.0, -0.9]))
            np.save(root / "set.000" / "force.npy", np.zeros((2, 15)))
            (root / "type.raw").write_text("0 1 2 2 2\n")
            (root / "type_map.raw").write_text("Ba Ti O\n")
            metadata = root / "metadata.csv"
            metadata.write_text("frame_id,temperature,phase_label,total_charge,split\n0,300,cubic,0.0,train\n1,500,cubic,1.0,validation\n")
            rows = read_deepmd_dataset(root)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].chemical_symbols, ["Ba", "Ti", "O", "O", "O"])
            self.assertEqual(rows[1].temperature, 500.0)
            self.assertEqual(rows[1].total_charge, 1.0)
            self.assertEqual(rows[1].split, "validation")
            self.assertFalse(rows[0].born_effective_charges_available)

    def test_generic_extxyz_reader_supports_mace_style_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mace"
            root.mkdir()
            (root / "data.extxyz").write_text(
                "5\n"
                "Lattice=\"4 0 0 0 4 0 0 0 4\" Properties=species:S:1:pos:R:3:REF_forces:R:3 "
                "REF_energy=-10.5 frame_id=m0\n"
                "Ba 0 0 0 0 0 0\nTi 2 2 2 0 0 0\nO 2 0 0 0 0 0\nO 0 2 0 0 0 0\nO 0 0 2 0 0 0\n"
            )
            rows = read_charge_dataset(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].frame_id, "m0")
            self.assertEqual(rows[0].calculator, "extxyz")
            self.assertEqual(rows[0].energy, -10.5)
            self.assertEqual(len(rows[0].forces), 5)
            self.assertFalse(rows[0].born_effective_charges_available)

    def test_abacus_directory_adapter_normalizes_optional_dpdata_arrays(self):
        import numpy as np

        class FakeSystem:
            fmt = "abacus/scf"
            data = {
                "coords": np.zeros((1, 5, 3)),
                "cells": np.tile(np.eye(3)[None, :, :] * 4.0, (1, 1, 1)),
                "atom_names": ["Ba", "Ti", "O"],
                "atom_types": np.asarray([0, 1, 2, 2, 2]),
                "energies": np.asarray([-10.0]),
                "forces": np.zeros((1, 5, 3)),
                "virials": np.zeros((1, 3, 3)),
            }

            def __len__(self):
                return 1

        fake_dpdata = SimpleNamespace(LabeledSystem=lambda *_args, **_kwargs: FakeSystem())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "STRU").write_text("placeholder\n")
            (root / "OUT.POLAR").mkdir()
            old = sys.modules.get("dpdata")
            sys.modules["dpdata"] = fake_dpdata
            try:
                rows = read_abacus_dataset(root)
            finally:
                if old is None:
                    sys.modules.pop("dpdata", None)
                else:
                    sys.modules["dpdata"] = old
            self.assertEqual(rows[0].calculator, "abacus-dpdata")
            self.assertEqual(rows[0].chemical_symbols, ["Ba", "Ti", "O", "O", "O"])
            self.assertEqual(rows[0].forces[0], [0.0, 0.0, 0.0])
            self.assertFalse(rows[0].born_effective_charges_available)


if __name__ == "__main__":
    unittest.main()
