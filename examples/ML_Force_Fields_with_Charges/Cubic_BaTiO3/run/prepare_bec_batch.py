"""Prepare per-frame ZStar/PYATB BEC workflows from a selected JSONL set.

This is an input generator only.  It deliberately does not launch ABACUS or
PYATB; a scheduler-specific driver can run the generated frame directories.
Shared pseudopotential/orbital assets are symlinked when possible so a batch
archive does not duplicate the large immutable files.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


def write_stru(frame: dict, output: Path) -> None:
    symbols = list(frame["chemical_symbols"])
    cell = np.asarray(frame["cell"], dtype=float)
    positions = np.asarray(frame["positions"], dtype=float)
    frac = positions @ np.linalg.inv(cell)
    lines = [
        "ATOMIC_SPECIES",
        "Ba 137.3300 Ba.upf upf201",
        "Ti 47.8670 Ti.upf upf201",
        "O 15.9990 O.upf upf201",
        "",
        "NUMERICAL_ORBITAL",
        "Ba_gga_10au_100Ry_4s2p1d.orb",
        "Ti_gga_10au_100Ry_4s2p2d1f.orb",
        "O_gga_10au_100Ry_2s2p1d.orb",
        "",
        "LATTICE_CONSTANT",
        "1.8897260000",
        "",
        "LATTICE_VECTORS",
    ]
    lines.extend("        " + "        ".join(f"{x:.12f}" for x in row) for row in cell)
    lines.extend(["", "ATOMIC_POSITIONS", "Direct"])
    for symbol in ("Ba", "Ti", "O"):
        indices = [i for i, item in enumerate(symbols) if item == symbol]
        if not indices:
            continue
        lines.extend([f"{symbol} #label", "0.0000 #magnetism", f"{len(indices)} #number of atoms"])
        lines.extend(
            "        " + "        ".join(f"{x:.12f}" for x in frac[i]) + " m 1 1 1"
            for i in indices
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_kpt_from_kspacing(cell: np.ndarray, kspacing: float, output: Path) -> list[int]:
    """Write a Gamma-centered ABACUS KPT preserving a reciprocal-space spacing.

    This helper is retained for legacy callers that explicitly request a
    serialized KPT mesh.  The production BTO workflow does not call it:
    ABACUS receives ``kspacing`` (in 1/bohr) in INPUT and generates the
    cell-dependent mesh itself.
    """
    if kspacing <= 0:
        raise ValueError("kspacing must be positive")
    volume = float(abs(np.linalg.det(cell)))
    if volume <= 0:
        raise ValueError("cell volume must be positive")
    reciprocal = 2.0 * np.pi * np.linalg.inv(cell).T
    mesh = [max(1, int(np.ceil(np.linalg.norm(reciprocal[index]) / kspacing))) for index in range(3)]
    output.write_text(
        "K_POINTS\n0\nGamma\n" + " ".join(str(value) for value in mesh) + " 0 0 0\n",
        encoding="utf-8",
        newline="\n",
    )
    return mesh


def link_or_copy(source: Path, target: Path) -> None:
    if target.exists() or target.is_symlink():
        # ``--resume`` may revisit a frame directory that was interrupted
        # after its assets were created.  Preserve a valid existing link/file
        # and only replace a stale target pointing elsewhere.
        try:
            if target.resolve() == source.resolve():
                return
        except OSError:
            pass
        target.unlink()
    try:
        target.symlink_to(source.resolve())
    except (OSError, NotImplementedError):
        shutil.copy2(source, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frame-id", action="append", dest="frame_ids", help="prepare only these frame IDs")
    parser.add_argument("--zstar-root", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--kspacing", type=float, default=0.1, help="ABACUS reciprocal-space spacing in 1/bohr")
    parser.add_argument(
        "--method",
        choices=("forward", "central"),
        default="forward",
        help="finite-difference displacement policy; forward is the default and creates one displacement per DOF",
    )
    parser.add_argument("--resume", action="store_true", help="skip frame directories with an existing .zstar/bec.json")
    args = parser.parse_args()
    frames = [json.loads(line) for line in args.selected.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.frame_ids:
        requested = set(args.frame_ids)
        frames = [frame for frame in frames if str(frame["frame_id"]) in requested]
        missing = requested.difference(str(frame["frame_id"]) for frame in frames)
        if missing:
            raise ValueError(f"requested frame IDs are absent from {args.selected}: {sorted(missing)}")
    if args.limit:
        frames = frames[: args.limit]
    args.output = args.output.resolve()
    args.baseline = args.baseline.resolve()
    args.assets = args.assets.resolve()
    args.selected = args.selected.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    for frame in frames:
        frame_dir = args.output / f"frame-{frame['frame_id']}"
        if args.resume and (frame_dir / ".zstar" / "bec.json").is_file():
            continue
        frame_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.baseline / "INPUT", frame_dir / "INPUT")
        write_stru(frame, frame_dir / "STRU")
        # Let ABACUS derive the mesh from the actual cell.  A fixed KPT would
        # incorrectly reuse the primitive-cell mesh for a 2x2x2 supercell.
        if args.kspacing is None:
            shutil.copy2(args.baseline / "KPT", frame_dir / "KPT")
        else:
            text = (frame_dir / "INPUT").read_text(encoding="utf-8")
            lines = []
            replaced = False
            for line in text.splitlines():
                if line.split("#", 1)[0].strip().lower().startswith("kspacing"):
                    lines.append(f"kspacing            {args.kspacing:.12g}")
                    replaced = True
                else:
                    lines.append(line)
            if not replaced:
                lines.append(f"kspacing            {args.kspacing:.12g}")
            (frame_dir / "INPUT").write_text("\n".join(lines) + "\n", encoding="utf-8")
        for asset in args.assets.iterdir():
            link_or_copy(asset, frame_dir / asset.name)
        command = [
            sys.executable,
            "-m",
            "zstar.cli",
            "bec",
            "pre",
            "--dim",
            "3",
            "--method",
            args.method,
            "--ensemble",
            "phonopy",
            "--input",
            "INPUT",
            "--stru",
            "STRU",
            "--pp",
            ".",
            "--orb",
            ".",
            "--pyatb",
        ]
        env = os.environ.copy()
        source_root = args.zstar_root or Path(__file__).resolve().parents[4]
        env["PYTHONPATH"] = str(source_root.resolve()) + os.pathsep + env.get("PYTHONPATH", "")
        subprocess.run(command, cwd=frame_dir, check=True, env=env)
    manifest = {
        "schema": "zstar-bec-batch-inputs",
        "frames": len(frames),
        "frame_ids": [str(frame["frame_id"]) for frame in frames],
        "source": str(args.selected.resolve()),
        "reference_settings": "same baseline INPUT/assets; PBEsol, 100 Ry, and ABACUS automatic kspacing",
        "kpoint_policy": "abacus_automatic_kspacing" if args.kspacing is not None else "baseline_KPT",
        "kspacing_inv_bohr": args.kspacing,
        "next": "run each frame directory with ABACUS/PYATB using a native Slurm driver",
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
