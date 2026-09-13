"""Prepare ABACUS SCF/force inputs for the 50-frame cubic-BTO supplement.

This script only writes inputs.  It does not run ABACUS or submit a scheduler
job.  ABACUS derives the cell-dependent k-point mesh from ``kspacing=0.1``
in the generated INPUT; no fixed primitive-cell KPT is copied.
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


def _rewrite_input(source: Path, target: Path, kspacing: float) -> None:
    lines = source.read_text(encoding="utf-8").splitlines()
    replacements = {
        "calculation": "scf",
        "cal_force": "1",
        "cal_stress": "1",
        "suffix": "SCF",
        "dft_functional": "pbesol",
        "kspacing": f"{kspacing:.12g}",
        "stru_file": "STRU",
    }
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        match = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s+", line)
        if match and match.group(2) in replacements:
            key = match.group(2)
            output.append(f"{key:<20} {replacements[key]}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in replacements.items():
        if key not in seen:
            output.append(f"{key:<20} {value}")
    target.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path, help="reviewed ABACUS INPUT template")
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--kspacing", type=float, default=0.1)
    args = parser.parse_args()
    frames = read_extxyz(args.geometry)
    if len(frames) != 50:
        raise ValueError(f"expected exactly 50 geometry frames, got {len(frames)}")
    if any(len(frame.symbols) != 40 for frame in frames):
        raise ValueError("all supplement frames must contain 40 atoms")
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for frame in frames:
        frame_dir = args.output / f"frame-{frame.frame_id}"
        frame_dir.mkdir(parents=True, exist_ok=True)
        _rewrite_input(args.baseline, frame_dir / "INPUT", args.kspacing)
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
        records.append(
            {
                "frame_id": frame.frame_id,
                "parent_frame_id": frame.parent_frame_id or frame.frame_id,
                "directory": str(frame_dir),
                "natoms": len(frame.symbols),
                "phase_label": "cubic",
                "exchange_correlation": "PBEsol",
                "kspacing_inv_bohr": args.kspacing,
                "labels": ["energy", "forces", "stress"],
            }
        )
    manifest = {
        "schema": "zstar-cubic-bto-abacus-force-batch",
        "status": "inputs_only",
        "frames": len(records),
        "natoms": 40,
        "supercell": [2, 2, 2],
        "exchange_correlation": "PBEsol",
        "kpoint_policy": "abacus_automatic_kspacing",
        "kspacing_inv_bohr": args.kspacing,
        "kpt_file_policy": "no KPT file; ABACUS automatic mesh from INPUT kspacing",
        "records": records,
        "next": "run a small static input audit and then submit reviewed SCF/force jobs",
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": len(records), "kspacing": args.kspacing}, indent=2))


if __name__ == "__main__":
    main()
