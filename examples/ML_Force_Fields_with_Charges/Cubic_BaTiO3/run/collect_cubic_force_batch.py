"""Collect completed 40-atom ABACUS force/stress frames into qNEP extxyz.

The collector is scheduler-neutral and intentionally refuses incomplete frames.
It consumes the geometry-only extxyz plus a copied Wuzhen batch root after the
Slurm jobs finish.  Missing stress is reported explicitly instead of filled
with zeros.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

from prepare_cubic_supercell_supplement import read_extxyz


ENERGY_RE = re.compile(r"FINAL_ETOT_IS\s+([-+0-9.]+(?:[eE][-+0-9]+)?)\s*eV", re.I)


def _read_energy(log: Path) -> float:
    matches = ENERGY_RE.findall(log.read_text(encoding="utf-8", errors="replace"))
    if not matches:
        raise ValueError(f"no FINAL_ETOT_IS in {log}")
    return float(matches[-1])


def _read_stress(log: Path) -> list[float] | None:
    text = log.read_text(encoding="utf-8", errors="replace")
    marker = "TOTAL-STRESS (KBAR)"
    if marker not in text:
        return None
    block = text.rsplit(marker, 1)[1].split("TOTAL-PRESSURE", 1)[0]
    rows = []
    for line in block.splitlines():
        values = line.split()
        if len(values) >= 3:
            try:
                row = [float(value) for value in values[-3:]]
            except ValueError:
                continue
            rows.append(row)
            if len(rows) == 3:
                # ABACUS reports kbar; qNEP extxyz stress is recorded here in
                # eV/Angstrom^3, retaining the conversion in provenance.
                return [value / 1602.176634 for row in rows for value in row]
    return None


def _read_forces(log: Path, natoms: int) -> list[list[float]]:
    text = log.read_text(encoding="utf-8", errors="replace")
    marker = "TOTAL-FORCE (eV/Angstrom)"
    if marker not in text:
        raise ValueError(f"no TOTAL-FORCE block in {log}")
    rows = []
    for line in text.rsplit(marker, 1)[1].splitlines():
        values = line.split()
        if len(values) < 3:
            continue
        try:
            row = [float(value) for value in values[-3:]]
        except ValueError:
            continue
        rows.append(row)
        if len(rows) == natoms:
            return rows
    raise ValueError(f"expected {natoms} force rows in {log}, found {len(rows)}")


def _properties(stress_available: bool) -> str:
    return "species:S:1:pos:R:3:force:R:3" + (":stress:R:9" if stress_available else "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", required=True, type=Path)
    parser.add_argument("--batch-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--exclude-frame-id",
        action="append",
        default=[],
        help=(
            "Frame ID to leave out of this force-label collection. Repeat for "
            "already-labelled phonon frames; they are reported as reused rather "
            "than silently recalculated."
        ),
    )
    parser.add_argument(
        "--reuse-frame-id",
        action="append",
        default=[],
        help=(
            "Already-computed frame ID to collect for dataset completeness. "
            "The output is marked reused_existing rather than new; this does "
            "not authorize a recalculation."
        ),
    )
    args = parser.parse_args()
    frames = read_extxyz(args.geometry)
    excluded = set(args.exclude_frame_id)
    reused_ids = set(args.reuse_frame_id)
    overlap = excluded & reused_ids
    if overlap:
        raise SystemExit(f"frame IDs cannot be both excluded and reused: {sorted(overlap)}")
    output: list[str] = []
    records = []
    failed = {}
    reused = []
    for frame in frames:
        frame_id = frame.frame_id
        if frame_id in excluded:
            reused.append(frame_id)
            continue
        frame_dir = args.batch_root / f"frame-{frame_id}"
        logs = sorted(frame_dir.glob("OUT.*/running_scf.log"))
        if len(logs) != 1:
            failed[frame_id] = f"expected one running_scf.log, found {len(logs)}"
            continue
        try:
            energy = _read_energy(logs[0])
            forces = _read_forces(logs[0], len(frame.symbols))
            stress = _read_stress(logs[0])
        except (OSError, ValueError) as exc:
            failed[frame_id] = str(exc)
            continue
        stress_text = "" if stress is None else " stress=\"" + " ".join(f"{v:.12g}" for v in stress) + "\""
        lattice = " ".join(
            f"{value:.12g}" if index in (0, 4, 8) else "0"
            for index, value in enumerate(
                (frame.lattice[0], 0.0, 0.0, 0.0, frame.lattice[1], 0.0, 0.0, 0.0, frame.lattice[2])
            )
        )
        output.extend([
            str(len(frame.symbols)),
            f'Lattice="{lattice}" Properties={_properties(stress is not None)} '
            f'energy={energy:.12g} frame_id={frame_id} parent_frame_id={frame.parent_frame_id or frame_id} '
            f'phase_label=cubic calculator=ABACUS exchange_correlation=PBEsol '
            'kpoint_convention=ABACUS_automatic_kspacing_0.1 '
            f'stress_unit=eV/angstrom^3 stress_available={str(stress is not None).lower()}{stress_text}',
        ])
        for symbol, position, force in zip(frame.symbols, frame.positions, forces):
            row = [symbol, *position, *force]
            if stress is not None:
                row.extend(stress)
            output.append(" ".join(f"{value:.12g}" if isinstance(value, float) else str(value) for value in row))
        records.append({
            "frame_id": frame_id,
            "energy_eV": energy,
            "stress_available": stress is not None,
            "source": str(logs[0]),
            "label_status": "reused_existing" if frame_id in reused_ids else "new",
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(output) + ("\n" if output else ""), encoding="utf-8")
    report = {
        "schema": "zstar-cubic-bto-force-batch-collection",
        "requested_frames": len(frames),
        "excluded_reused_frames": reused,
        "collected_reused_frames": [record["frame_id"] for record in records if record["label_status"] == "reused_existing"],
        "new_label_frames_requested": len(frames) - len(reused) - len(reused_ids),
        "collected_frames": len(records),
        "new_label_frames_collected": sum(record["label_status"] == "new" for record in records),
        "failed_frames": failed,
        "stress_unit": "eV/angstrom^3",
        "stress_conversion": "ABACUS kbar / 1602.176634",
        "records": records,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
