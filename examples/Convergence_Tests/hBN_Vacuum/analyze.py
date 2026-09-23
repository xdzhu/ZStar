#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def read_bec(path: Path) -> np.ndarray:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        rows.append([float(value) for value in line.split()[-9:]])
    return np.asarray(rows, dtype=float).reshape(-1, 3, 3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, default=Path(__file__).parent / "work")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()

    points = []
    tensors = {}
    for height in (15, 20, 30, 40):
        tensors[height] = read_bec(args.work / f"Lz{height}" / "BEC.dat")
    reference = tensors[40]
    for height, tensor in sorted(tensors.items()):
        points.append({
            "cell_height_A": height,
            "B_Z_inplane_e": float((tensor[1, 0, 0] + tensor[1, 1, 1]) / 2.0),
            "B_Z_out_of_plane_e": float(tensor[1, 2, 2]),
            "max_abs_delta_from_40A_e": float(np.max(np.abs(tensor - reference))),
        })

    args.output.mkdir(parents=True, exist_ok=True)
    csv_path = args.output / "hBN_vacuum_convergence.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(points[0]))
        writer.writeheader()
        writer.writerows({
            "cell_height_A": str(item["cell_height_A"]),
            "B_Z_inplane_e": f'{item["B_Z_inplane_e"]:.8f}',
            "B_Z_out_of_plane_e": f'{item["B_Z_out_of_plane_e"]:.8f}',
            "max_abs_delta_from_40A_e":
                f'{item["max_abs_delta_from_40A_e"]:.8f}',
        } for item in points)
    summary = {
        "schema": "zstar-convergence-result",
        "system": "monolayer hBN",
        "scan": "out_of_plane_cell_height",
        "units": {"cell_height": "angstrom", "bec": "e"},
        "reference_cell_height_A": 40,
        "points": points,
        "bec_tensors": {
            str(height): tensor.tolist()
            for height, tensor in sorted(tensors.items())
        },
        "B_inplane_spread_e": float(np.ptp([
            item["B_Z_inplane_e"] for item in points
        ])),
        "B_out_of_plane_spread_e": float(np.ptp([
            item["B_Z_out_of_plane_e"] for item in points
        ])),
    }
    (args.output / "hBN_vacuum_convergence.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    x = [item["cell_height_A"] for item in points]
    in_plane = np.asarray([item["B_Z_inplane_e"] for item in points])
    out_of_plane = np.asarray([item["B_Z_out_of_plane_e"] for item in points])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharex=True)
    axes[0].plot(x, (in_plane - in_plane[-1]) * 1e5, "o-",
                 color="#b7423c", linewidth=1.6, markersize=4.5)
    axes[0].axhline(0, color="0.65", linewidth=0.8, zorder=0)
    axes[0].set_ylabel(r"In-plane $\Delta Z^*$ ($10^{-5}$ e)")
    axes[1].plot(x, out_of_plane, "s--", color="#d98b35",
                 linewidth=1.6, markersize=4.2)
    axes[1].set_ylabel(r"Out-of-plane $Z^*$ (e)")
    for axis in axes:
        axis.set_xlabel("Cell height (Angstrom)")
        axis.tick_params(direction="in", top=True, right=True)
        axis.margins(x=0.04)
    fig.tight_layout()
    for suffix in ("pdf", "png"):
        fig.savefig(args.output / f"hBN_vacuum_convergence.{suffix}", dpi=300)
    print(csv_path)


if __name__ == "__main__":
    main()
