"""Merge the 40-atom force supplement and sparse primitive BEC labels.

The existing cubic qNEP export contains five-atom force/BEC frames.  The
supplement contributes 2x2x2 (40-atom) force/stress frames, while the two
primitive BEC workflows contribute optional BEC labels.  This bridge keeps
those sources explicit and transposes ZStar's displacement-row convention to
qNEP's ``bec:R:9`` convention.  It does not fill missing BEC labels with zeros.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from zstar.qnep_dataset import read_extxyz


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _match_force_row(parent: dict, force_rows: list[dict]) -> dict:
    matches = [
        row
        for row in force_rows
        if row.get("frame_id") == f"{parent['frame_id']}::0.no-move"
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one no-move force row for {parent['frame_id']}, found {len(matches)}")
    return matches[0]


def _reorder_rows(source: dict, target: dict) -> tuple[list[str], np.ndarray]:
    """Match duplicate O atoms by Cartesian position, preserving target order."""
    source_symbols = list(source["chemical_symbols"])
    source_positions = np.asarray(source["positions"], dtype=float)
    source_forces = np.asarray(source["forces"], dtype=float)
    used: set[int] = set()
    order: list[int] = []
    for symbol, position in zip(target["chemical_symbols"], target["positions"]):
        candidates = [
            index
            for index, (current, current_position) in enumerate(zip(source_symbols, source_positions))
            if index not in used and current == symbol and np.linalg.norm(current_position - position) < 1e-5
        ]
        if len(candidates) != 1:
            raise ValueError(f"cannot match atom {symbol} at {position} between BEC and force rows")
        used.add(candidates[0])
        order.append(candidates[0])
    return [source_symbols[index] for index in order], source_forces[order]


def _lattice(cell: list[list[float]]) -> str:
    values = np.asarray(cell, dtype=float).reshape(9)
    return " ".join(f"{value:.12g}" for value in values)


def _bec_frame(parent: dict, force: dict) -> str:
    symbols, forces = _reorder_rows(force, parent)
    bec = np.asarray(parent["born_effective_charges"], dtype=float)
    if bec.shape != (len(symbols), 3, 3):
        raise ValueError(f"BEC shape for {parent['frame_id']} is {bec.shape}, expected ({len(symbols)},3,3)")
    qnep_bec = np.transpose(bec, (0, 2, 1))
    positions = np.asarray(parent["positions"], dtype=float)
    kpoint_convention = str(force.get("kpoints", "unknown")).replace(" ", "_")
    lines = [
        str(len(symbols)),
        f'Lattice="{_lattice(parent["cell"])}" '
        'Properties=species:S:1:pos:R:3:force:R:3:bec:R:9 '
        f'energy={float(force["energy"]):.12g} frame_id={parent["frame_id"]} '
        f'structure_id={parent["structure_id"]} total_charge={float(parent.get("total_charge", 0.0)):.12g} '
        f'phase_label={parent.get("phase_label", "cubic")} calculator=ABACUS '
        'exchange_correlation=PBEsol '
        f'kpoint_convention={kpoint_convention}_equivalent_kspacing_0.1 '
        'bec_unit=e bec_convention=qnep_electric_rows',
    ]
    for symbol, position, force_row, tensor in zip(symbols, positions, forces, qnep_bec):
        values = [*position, *force_row, *tensor.reshape(9)]
        lines.append(symbol + " " + " ".join(f"{float(value):.12g}" for value in values))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--supplement", required=True, type=Path)
    parser.add_argument("--bec-annotated", required=True, type=Path)
    parser.add_argument("--bec-force-only", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    base = read_extxyz(args.base)
    supplement = read_extxyz(args.supplement)
    annotated = {row["frame_id"]: row for row in _load_jsonl(args.bec_annotated)}
    force_rows = _load_jsonl(args.bec_force_only)
    bec_blocks = [_bec_frame(row, _match_force_row(row, force_rows)) for row in annotated.values()]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for frame in base + supplement:
            handle.write(f"{frame.natoms}\n{frame.header}\n")
            handle.write("\n".join(frame.atoms) + "\n")
        for block in bec_blocks:
            handle.write(block)

    payload = {
        "schema": "zstar-cubic-bto-qnep-merged-dataset",
        "base_frames": len(base),
        "supplement_force_frames": len(supplement),
        "bec_frames_added": len(bec_blocks),
        "total_frames": len(base) + len(supplement) + len(bec_blocks),
        "supplement_atoms": sorted({frame.natoms for frame in supplement}),
        "bec_atoms": sorted({json.loads(block.splitlines()[0]) for block in bec_blocks}),
        "bec_is_optional_per_frame": True,
        "bec_missing_is_not_zero": True,
        "qnep_bec_convention": "electric-row form; transpose of ZStar displacement-row tensors",
        "sources": {
            "base": str(args.base.resolve()),
            "supplement": str(args.supplement.resolve()),
            "bec_annotated": str(args.bec_annotated.resolve()),
            "bec_force_only": str(args.bec_force_only.resolve()),
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
