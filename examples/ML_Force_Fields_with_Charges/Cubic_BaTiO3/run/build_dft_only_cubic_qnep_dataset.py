"""Build the cubic-only qNEP input from completed raw DFT outputs.

The public qNEP excerpt is deliberately not an input to this script.  The
force labels come from completed Wuzhen ABACUS/PBEsol SCF logs and the 2x2x2
supplement.  Energies are copied as stored; no reference shift or
normalization is performed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from zstar.charge_aware_dataset import ChargeAwareFrame, export_qnep_xyz, write_charge_dataset


def _rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _reorder_forces(parent: dict, force: dict) -> list[list[float]]:
    used = set()
    result = []
    source_symbols = list(force["chemical_symbols"])
    source_positions = np.asarray(force["positions"], dtype=float)
    source_forces = np.asarray(force["forces"], dtype=float)
    for symbol, position in zip(parent["chemical_symbols"], parent["positions"]):
        candidates = [
            i for i, (current, current_position) in enumerate(zip(source_symbols, source_positions))
            if i not in used and current == symbol and np.linalg.norm(current_position - position) < 1e-4
        ]
        if len(candidates) != 1:
            raise ValueError("cannot match force atom %s at %s for %s" % (symbol, position, parent["frame_id"]))
        used.add(candidates[0])
        result.append(source_forces[candidates[0]].tolist())
    return result


def _frame(mapping: dict) -> ChargeAwareFrame:
    return ChargeAwareFrame.from_mapping(mapping)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-force-jsonl", required=True, type=Path)
    parser.add_argument("--candidate-jsonl", required=True, type=Path)
    parser.add_argument("--supplement-extxyz", required=True, type=Path)
    parser.add_argument(
        "--bec-annotated-jsonl", required=True, type=Path, action="append",
        help="One or more sparse-BEC annotation JSONL files; unlabeled rows are retained as missing.",
    )
    parser.add_argument("--bec-force-jsonl", required=True, type=Path)
    parser.add_argument("--output-jsonl", required=True, type=Path)
    parser.add_argument("--output-extxyz", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    candidate_rows = _rows(args.candidate_jsonl)
    phase_by_id = {str(row["frame_id"]): row.get("phase_label") for row in candidate_rows}
    cubic_ids = {frame_id for frame_id, phase in phase_by_id.items() if phase == "cubic"}

    raw = []
    for row in _rows(args.raw_force_jsonl):
        parent_id = str(row.get("metadata", {}).get("parent_frame_id", ""))
        if parent_id not in cubic_ids:
            continue
        row = dict(row)
        row["phase_label"] = "cubic"
        row["metadata"] = dict(row.get("metadata") or {})
        row["metadata"]["energy_policy"] = "copied verbatim from ABACUS FINAL_ETOT_IS; no shift or normalization"
        if str(row.get("kpoints") or "").strip().lower() == "gamma 9x9x9":
            row["metadata"]["kpoint_policy"] = "ABACUS automatic kspacing=0.1 (Gamma 9x9x9 equivalent for primitive BTO)"
        raw.append(_frame(row))

    from zstar.charge_aware_dataset import read_charge_dataset

    supplement = read_charge_dataset(args.supplement_extxyz)
    if any(frame.phase_label not in {None, "cubic"} for frame in supplement):
        raise ValueError("supplement contains a non-cubic phase")
    for frame in supplement:
        frame.phase_label = "cubic"
        frame.validation_status = "imported_raw_dft"
        frame.calculator = "ABACUS"
        frame.exchange_correlation = "PBEsol"
        frame.pseudopotential = "Wuzhen baseline UPF"
        frame.orbital = "Wuzhen baseline numerical orbital"
        # Preserve the collector's actual cell-dependent mesh.  The DFT
        # standard is kspacing=0.1 in INPUT, not a fixed primitive-cell KPT.
        if not frame.kpoints:
            frame.kpoints = "ABACUS automatic kspacing=0.1"
        frame.metadata = dict(frame.metadata or {})
        frame.metadata["kpoint_policy"] = "ABACUS automatic kspacing=0.1"
        frame.ecut = 100.0
        frame.metadata.update(
            energy_policy="copied verbatim from ABACUS force collector",
            source_label_status="completed_raw_dft",
        )

    bec_rows = {}
    for annotation_path in args.bec_annotated_jsonl:
        for row in _rows(annotation_path):
            frame_id = str(row["frame_id"])
            # Non-cubic phase labels are useful for the campaign report but
            # must never enter the cubic-only qNEP training set.
            if row.get("phase_label") not in {None, "cubic"}:
                continue
            if not row.get("born_effective_charges_available"):
                continue
            if frame_id in bec_rows:
                previous = np.asarray(bec_rows[frame_id]["born_effective_charges"], dtype=float)
                current = np.asarray(row["born_effective_charges"], dtype=float)
                if not np.allclose(previous, current, atol=1e-8, rtol=0):
                    raise ValueError(f"conflicting BEC annotations for {frame_id}")
                continue
            bec_rows[frame_id] = row
    force_rows = {str(row["frame_id"]): row for row in _rows(args.bec_force_jsonl)}
    bec_frames = []
    for frame_id, parent in sorted(bec_rows.items()):
        force_id = frame_id + "::0.no-move"
        if force_id in force_rows:
            force = force_rows[force_id]
            mapping = dict(parent)
            mapping.update({
                "energy": force["energy"],
                "forces": _reorder_forces(parent, force),
                "calculator": "ABACUS",
                "pseudopotential": "Wuzhen baseline UPF",
                "orbital": "Wuzhen baseline numerical orbital",
                "kpoints": force.get("kpoints"),
                "ecut": force.get("ecut"),
                "source_directory": force.get("source_directory"),
                "source_manifest": force.get("source_manifest"),
                "validation_status": "imported_raw_dft_bec_annotated",
                "metadata": dict(parent.get("metadata") or {},
                                  raw_force_frame_id=force_id,
                                  energy_policy="copied verbatim from ABACUS FINAL_ETOT_IS; no shift or normalization"),
            })
        elif parent.get("energy") is not None and parent.get("forces") is not None:
            # A supplement BEC annotation is generated directly from the
            # already-collected 40-atom force frame.  It therefore carries
            # its own immutable DFT energy/force labels and needs no separate
            # primitive-family force-only row.
            mapping = dict(parent)
            mapping["validation_status"] = "imported_raw_dft_bec_annotated"
            mapping["metadata"] = dict(parent.get("metadata") or {},
                                        energy_policy="copied verbatim from ABACUS/PBEsol force dataset")
        else:
            raise ValueError("missing raw DFT no-move labels for %s" % frame_id)
        bec_frames.append(_frame(mapping))

    # Attach BEC tensors to the existing force/energy frame whenever the
    # geometry is already present.  This is essential for the 40-atom pair:
    # adding a second record with the same geometry would otherwise let the
    # duplicate filter discard the BEC-bearing record.
    def _geometry_key(frame: ChargeAwareFrame):
        return (
            tuple(frame.chemical_symbols),
            tuple(round(value, 9) for row in frame.cell for value in row),
            tuple(round(value, 9) for row in frame.positions for value in row),
        )

    def _reorder_bec(source: ChargeAwareFrame, target: ChargeAwareFrame) -> list[list[list[float]]]:
        """Reorder atom-indexed BEC tensors onto the force-frame atom order."""
        tensors = np.asarray(source.born_effective_charges, dtype=float)
        used = set()
        ordered = []
        source_positions = np.asarray(source.positions, dtype=float)
        target_positions = np.asarray(target.positions, dtype=float)
        for symbol, position in zip(target.chemical_symbols, target_positions):
            candidates = [
                i for i, (current_symbol, current_position) in enumerate(
                    zip(source.chemical_symbols, source_positions)
                )
                if i not in used and current_symbol == symbol
                and np.linalg.norm(current_position - position) < 1e-4
            ]
            if len(candidates) != 1:
                raise ValueError(f"cannot match BEC atom {symbol} at {position} for {source.frame_id}")
            used.add(candidates[0])
            ordered.append(tensors[candidates[0]].tolist())
        return ordered

    base_frames = raw + supplement
    base_by_id = {frame.frame_id: frame for frame in base_frames}
    base_by_geometry = {_geometry_key(frame): frame for frame in base_frames}
    unattached_bec = []
    attached_bec_ids = []
    for bec_frame in bec_frames:
        target = (
            base_by_id.get(bec_frame.frame_id)
            or base_by_id.get(f"{bec_frame.frame_id}::0.no-move")
            or base_by_geometry.get(_geometry_key(bec_frame))
        )
        if target is None:
            unattached_bec.append(bec_frame)
            continue
        if len(target.chemical_symbols) != len(bec_frame.chemical_symbols):
            raise ValueError(f"BEC atom count mismatch while attaching {bec_frame.frame_id}")
        target.born_effective_charges = _reorder_bec(bec_frame, target)
        target.born_effective_charges_available = True
        target.metadata = dict(target.metadata or {}, **(bec_frame.metadata or {}), bec_annotation_frame_id=bec_frame.frame_id)
        target.validation_status = "imported_raw_dft_bec_annotated"
        attached_bec_ids.append(bec_frame.frame_id)

    frames = base_frames + unattached_bec
    # Identical finite-displacement geometries can occur in two selected
    # parent families.  Keep one raw-DTF record, but reject any disagreement
    # before dropping the duplicate so this cannot hide a label conflict.
    unique = []
    seen = {}
    duplicate_ids = []
    for frame in frames:
        key = (
            tuple(frame.chemical_symbols),
            tuple(round(value, 9) for row in frame.cell for value in row),
            tuple(round(value, 9) for row in frame.positions for value in row),
        )
        if key in seen:
            previous = seen[key]
            if abs(float(previous.energy) - float(frame.energy)) > 1e-7 or not np.allclose(
                np.asarray(previous.forces), np.asarray(frame.forces), atol=1e-7, rtol=0
            ):
                raise ValueError("duplicate geometry has inconsistent DFT labels: %s vs %s" % (previous.frame_id, frame.frame_id))
            if frame.born_effective_charges_available:
                if previous.born_effective_charges_available and not np.allclose(
                    np.asarray(previous.born_effective_charges),
                    np.asarray(frame.born_effective_charges),
                    atol=1e-8,
                    rtol=0,
                ):
                    raise ValueError("duplicate geometry has conflicting BEC labels: %s vs %s" % (previous.frame_id, frame.frame_id))
                if not previous.born_effective_charges_available:
                    previous.born_effective_charges = frame.born_effective_charges
                    previous.born_effective_charges_available = True
                    previous.metadata = dict(previous.metadata or {},
                                             bec_deduplicated_from=frame.frame_id,
                                             **(frame.metadata or {}))
                    previous.validation_status = "imported_raw_dft_bec_annotated"
            duplicate_ids.append(frame.frame_id)
            continue
        seen[key] = frame
        unique.append(frame)
    frames = unique
    ids = [frame.frame_id for frame in frames]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate frame_id in DFT-only dataset")
    if any(frame.exchange_correlation not in {None, "PBEsol"} for frame in frames):
        raise ValueError("non-PBEsol frame in DFT-only dataset")
    write_charge_dataset(frames, args.output_jsonl)
    export_summary = export_qnep_xyz(args.output_jsonl, args.output_extxyz)
    manifest = {
        "schema": "zstar-dft-only-cubic-qnep-dataset",
        "frames": len(frames),
        "raw_cubic_bec_family_rows": len(raw),
        "supercell_supplement_rows": len(supplement),
        "bec_annotation_rows": len(bec_frames),
        "bec_attached_to_existing_frames": len(attached_bec_ids),
        "bec_unattached_rows": len(unattached_bec),
        "atoms": dict(Counter(len(frame.chemical_symbols) for frame in frames)),
        "bec_labeled_frames": sum(frame.born_effective_charges_available for frame in frames),
        "duplicate_geometry_frames_removed": duplicate_ids,
        "phase_counts": dict(Counter(frame.phase_label for frame in frames)),
        "energy_policy": "all energy values copied from completed ABACUS/PBEsol outputs; no shifts, offsets, normalization, or replacement",
        "excluded_sources": ["public qNEP force-pool excerpt", "mixed-source training outputs"],
        "sources": {
            "raw_force_jsonl": str(args.raw_force_jsonl.resolve()),
            "candidate_jsonl": str(args.candidate_jsonl.resolve()),
            "supplement_extxyz": str(args.supplement_extxyz.resolve()),
            "bec_annotated_jsonl": [str(path.resolve()) for path in args.bec_annotated_jsonl],
            "bec_force_jsonl": str(args.bec_force_jsonl.resolve()),
        },
        "export": export_summary,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
