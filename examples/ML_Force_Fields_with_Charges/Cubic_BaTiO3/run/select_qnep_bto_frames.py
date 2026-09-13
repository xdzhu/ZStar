"""Select a small, phase-stratified BTO subset from a qNEP extended-XYZ file.

The public qNEP structure archive does not encode an MD temperature for every
configuration.  This helper therefore records space-group phase labels and
leaves ``temperature`` empty rather than inventing temperatures. By default it
also keeps only primitive five-atom structures and excludes displacement
snapshots/supercells, so a BEC campaign remains tractable; both filters can be
relaxed explicitly. The public primitive archive has fewer than 20 structures
for some phases, so ``--allow-phase-shortfall`` records that fact instead of
duplicating a geometry. If supercells are enabled, the manifest retains the
atom count because a 120-atom cell creates hundreds of phonopy displacements
and should not be sent to a routine BEC queue without an explicit decision.
The generic ZStar selector can then be reused once a source-specific
temperature sidecar is available.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import numpy as np

from zstar.charge_aware_dataset import (
    dataset_manifest,
    read_charge_dataset,
    select_charge_frames,
    write_charge_dataset,
)
from zstar.qnep_dataset import read_extxyz


PHASES = {
    "38": "orthorhombic",
    "99": "tetragonal",
    "160": "rhombohedral",
    "221": "cubic",
}


def write_metadata(
    source: Path,
    output: Path,
    *,
    include_displacements: bool,
    include_supercells: bool,
) -> dict[str, int]:
    rows: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    for index, frame in enumerate(read_extxyz(source)):
        match = re.search(r"BaTiO3-spg(\d+)", frame.header)
        is_displacement = "displ" in frame.header
        phase = PHASES.get(match.group(1), "other") if match else "other"
        if is_displacement and not include_displacements:
            phase = "other"
        if len(frame.atoms) != 5 and not include_supercells:
            phase = "other"
        rows.append({"frame_id": str(index), "phase_label": phase})
        counts[phase] = counts.get(phase, 0) + 1
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["frame_id", "phase_label"])
        writer.writeheader()
        writer.writerows(rows)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument(
        "--per-phase",
        type=int,
        default=None,
        help="select up to this many frames for each recognized phase",
    )
    parser.add_argument(
        "--exclude-frame-ids",
        type=Path,
        default=None,
        help="newline-delimited frame IDs to exclude (useful for an additive batch)",
    )
    parser.add_argument(
        "--allow-phase-shortfall",
        action="store_true",
        help="take all available frames when a phase has fewer than --per-phase",
    )
    parser.add_argument("--seed", type=int, default=20260912)
    parser.add_argument(
        "--include-displacements",
        action="store_true",
        help="allow source frames whose name contains 'displ'; excluded by default",
    )
    parser.add_argument(
        "--include-supercells",
        action="store_true",
        help="allow non-primitive BTO supercells; expensive for BEC workflows",
    )
    args = parser.parse_args()
    counts = write_metadata(
        args.input,
        args.metadata,
        include_displacements=args.include_displacements,
        include_supercells=args.include_supercells,
    )
    excluded = set()
    if args.exclude_frame_ids:
        excluded = {
            line.strip()
            for line in args.exclude_frame_ids.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    if args.per_phase is not None:
        if args.per_phase < 1:
            raise ValueError("--per-phase must be positive")
        frames = [
            frame
            for frame in read_charge_dataset(args.input, metadata=args.metadata)
            if frame.frame_id not in excluded and frame.phase_label in PHASES.values()
        ]
        rng = np.random.default_rng(args.seed)
        chosen = []
        for phase in ("orthorhombic", "tetragonal", "rhombohedral", "cubic"):
            candidates = [frame for frame in frames if frame.phase_label == phase]
            if len(candidates) < args.per_phase:
                if not args.allow_phase_shortfall:
                    raise ValueError(
                        f"phase {phase} has {len(candidates)} eligible frames, "
                        f"cannot select {args.per_phase}"
                    )
            take = min(len(candidates), args.per_phase)
            # Prefer primitive cells so a phase shortfall is not hidden by an
            # unnecessary supercell. If a phase has fewer primitive frames,
            # use the smallest available supercells and record that choice in
            # the selected frame's atom count.
            candidates.sort(key=lambda frame: len(frame.chemical_symbols))
            selected_phase = []
            cursor = 0
            while len(selected_phase) < take:
                natoms = len(candidates[cursor].chemical_symbols)
                block = [frame for frame in candidates if len(frame.chemical_symbols) == natoms]
                remaining = take - len(selected_phase)
                order = rng.permutation(len(block))[:remaining]
                selected_phase.extend(block[int(index)] for index in order)
                candidates = [frame for frame in candidates if len(frame.chemical_symbols) != natoms]
                cursor = 0
            chosen.extend(selected_phase)
        chosen.sort(key=lambda frame: (frame.phase_label or "", frame.frame_id))
        write_charge_dataset(chosen, args.output)
        manifest = dataset_manifest(chosen, args.output) | {
            "selection_seed": args.seed,
            "selected_from": str(args.input.resolve()),
            "selected_frame_ids": [frame.frame_id for frame in chosen],
            "selection_mode": "exact_per_phase",
            "per_phase": args.per_phase,
            "phase_target_shortfall_allowed": args.allow_phase_shortfall,
            "selected_phase_counts": {
                phase: sum(frame.phase_label == phase for frame in chosen)
                for phase in ("orthorhombic", "tetragonal", "rhombohedral", "cubic")
            },
            "excluded_frame_ids": sorted(excluded),
        }
    else:
        if excluded:
            source_frames = [
                frame
                for frame in read_charge_dataset(args.input, metadata=args.metadata)
                if frame.frame_id not in excluded
            ]
            temporary = args.output.with_suffix(args.output.suffix + ".eligible.jsonl")
            write_charge_dataset(source_frames, temporary)
            manifest = select_charge_frames(
                temporary,
                args.output,
                count=args.count,
                seed=args.seed,
                phases=["orthorhombic", "tetragonal", "rhombohedral", "cubic"],
            )
            temporary.unlink(missing_ok=True)
        else:
            manifest = select_charge_frames(
                args.input,
                args.output,
                count=args.count,
                seed=args.seed,
                phases=["orthorhombic", "tetragonal", "rhombohedral", "cubic"],
                metadata=args.metadata,
            )
    digest = hashlib.sha256(args.input.read_bytes()).hexdigest()
    manifest.update({
        "source_phase_counts": counts,
        "temperature_metadata": "not present in public XYZ archive",
        "source_sha256": digest,
    })
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
