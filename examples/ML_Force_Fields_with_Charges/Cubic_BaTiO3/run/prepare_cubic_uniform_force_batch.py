"""Prepare uniform ABACUS force/stress inputs for every cubic frame.

This is the source-consistency gate for the final qNEP benchmark.  It accepts
the merged geometry archive but writes only the requested phase, so old public
energy/force labels are never silently reused as DFT targets.  All selected
frames are regenerated with the reviewed ABACUS INPUT/KPT/assets.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import numpy as np

from prepare_bec_batch import write_stru
from prepare_cubic_supercell_supplement import read_extxyz
from prepare_cubic_force_batch import _rewrite_input


PHASE_RE = re.compile(r"(?:^|\s)phase_label=([^\s]+)")


def _phase(header: str) -> str:
    match = PHASE_RE.search(header)
    return match.group(1) if match else "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--phase", default="cubic")
    parser.add_argument("--kspacing", type=float, default=0.1)
    args = parser.parse_args()

    source = read_extxyz(args.geometry)
    frames = [frame for frame in source if _phase(frame.header) == args.phase]
    if not frames:
        raise ValueError(f"no frames found for phase {args.phase!r}")
    frame_ids = [frame.frame_id for frame in frames]
    if len(set(frame_ids)) != len(frame_ids):
        raise ValueError("duplicate frame_id in uniform force input selection")

    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for frame in frames:
        frame_dir = args.output / f"frame-{frame.frame_id}"
        frame_dir.mkdir(parents=True, exist_ok=True)
        _rewrite_input(args.baseline, frame_dir / "INPUT", args.kspacing)
        shutil.copy2(args.baseline.parent / "KPT", frame_dir / "KPT")
        frame_data = {
            "chemical_symbols": frame.symbols,
            "cell": np.diag(frame.lattice).tolist(),
            "positions": np.asarray(frame.positions, dtype=float).tolist(),
        }
        write_stru(frame_data, frame_dir / "STRU")
        for asset in args.assets.iterdir():
            destination = frame_dir / asset.name
            if destination.exists() or destination.is_symlink():
                destination.unlink()
            try:
                destination.symlink_to(asset.resolve())
            except (OSError, NotImplementedError):
                shutil.copy2(asset, destination)
        records.append({
            "frame_id": frame.frame_id,
            "natoms": len(frame.symbols),
            "phase_label": args.phase,
            "exchange_correlation": "PBEsol",
            "kspacing_inv_angstrom": args.kspacing,
            "labels": ["energy", "forces", "stress"],
            "source_header": frame.header,
        })

    manifest = {
        "schema": "zstar-cubic-bto-uniform-abacus-force-batch",
        "status": "inputs_only",
        "source_geometry": str(args.geometry.resolve()),
        "phase": args.phase,
        "frames": len(records),
        "natoms_counts": {str(n): sum(record["natoms"] == n for record in records) for n in sorted({record["natoms"] for record in records})},
        "exchange_correlation": "PBEsol",
        "kpoint_policy": "project_baseline_KPT",
        "kspacing_inv_angstrom": args.kspacing,
        "kpt_file_policy": "Gamma 9x9x9; validated project equivalent of kspacing=0.1",
        "all_selected_frames_recomputed": True,
        "records": records,
        "next": "run reviewed SCF/force/stress jobs; do not merge old energy/force labels",
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": len(records), "natoms_counts": manifest["natoms_counts"]}, indent=2))


if __name__ == "__main__":
    main()
