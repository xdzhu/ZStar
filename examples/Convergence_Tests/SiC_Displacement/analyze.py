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
    for displacement in (0.005, 0.010, 0.015, 0.020, 0.025, 0.030):
        case = args.work / f"d{displacement:.3f}".replace(".", "p")
        tensors[displacement] = read_bec(case / "BEC.dat")
    reference = tensors[0.010]
    for displacement, tensor in sorted(tensors.items()):
        points.append({
            "displacement_A": displacement,
            "Si_Zdiag_mean_e": float(np.trace(tensor[0]) / 3.0),
            "C_Zdiag_mean_e": float(np.trace(tensor[1]) / 3.0),
            "max_abs_delta_from_0.010A_e": float(np.max(np.abs(tensor - reference))),
        })

    args.output.mkdir(parents=True, exist_ok=True)
    csv_path = args.output / "SiC_displacement_convergence.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(points[0]))
        writer.writeheader()
        writer.writerows({
            "displacement_A": f'{item["displacement_A"]:.3f}',
            "Si_Zdiag_mean_e": f'{item["Si_Zdiag_mean_e"]:.8f}',
            "C_Zdiag_mean_e": f'{item["C_Zdiag_mean_e"]:.8f}',
            "max_abs_delta_from_0.010A_e":
                f'{item["max_abs_delta_from_0.010A_e"]:.8f}',
        } for item in points)
    summary = {
        "schema": "zstar-convergence-result",
        "system": "3C-SiC",
        "scan": "finite_displacement_magnitude",
        "units": {"displacement": "angstrom", "bec": "e"},
        "reference_displacement_A": 0.010,
        "points": points,
        "bec_tensors": {
            f"{displacement:.3f}": tensor.tolist()
            for displacement, tensor in sorted(tensors.items())
        },
        "max_tensor_spread_e": float(np.max([
            np.max(np.abs(left - right))
            for left in tensors.values() for right in tensors.values()
        ])),
    }
    (args.output / "SiC_displacement_convergence.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    x = [item["displacement_A"] for item in points]
    y = [item["Si_Zdiag_mean_e"] for item in points]
    fig, axis = plt.subplots(figsize=(5.0, 3.5))
    axis.plot(x, y, "o-", color="#b7423c", linewidth=1.6, markersize=4.5)
    axis.set(xlabel="Displacement (Angstrom)", ylabel="Si mean diagonal BEC (e)")
    axis.tick_params(direction="in", top=True, right=True)
    axis.margins(x=0.04)
    fig.tight_layout()
    for suffix in ("pdf", "png"):
        fig.savefig(args.output / f"SiC_displacement_convergence.{suffix}", dpi=300)
    print(csv_path)


if __name__ == "__main__":
    main()
