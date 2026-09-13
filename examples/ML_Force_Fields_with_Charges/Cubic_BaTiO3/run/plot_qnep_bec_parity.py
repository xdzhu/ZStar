"""Plot target/predicted BEC components from GPUMD ``bec_test.out``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = np.asarray([[float(x) for x in line.split()] for line in Path(args.input).read_text().splitlines() if line.strip()])
    if rows.ndim != 2 or rows.shape[1] != 18:
        raise ValueError("GPUMD BEC output must have 18 columns")
    mask = np.any(np.abs(rows[:, 9:]) > 1e-10, axis=1)
    predicted = rows[mask, :9].ravel()
    target = rows[mask, 9:].ravel()
    mae = float(np.abs(predicted - target).mean())
    rmse = float(np.sqrt(np.mean((predicted - target) ** 2)))
    fig, ax = plt.subplots(figsize=(4.8, 4.4), constrained_layout=True)
    lo = float(min(predicted.min(), target.min()))
    hi = float(max(predicted.max(), target.max()))
    pad = 0.04 * (hi - lo or 1.0)
    ax.scatter(target, predicted, s=20, alpha=0.75, color="#c44e52", edgecolors="none")
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="black", lw=1)
    ax.set(xlim=(lo - pad, hi + pad), ylim=(lo - pad, hi + pad), xlabel="DFT BEC target (e)", ylabel="qNEP prediction (e)")
    ax.text(0.04, 0.95, f"MAE = {mae:.3f} e\nRMSE = {rmse:.3f} e\nN = {len(predicted)}", transform=ax.transAxes, va="top")
    target_path = Path(args.output).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target_path, dpi=220)
    fig.savefig(target_path.with_suffix(".pdf"))
    plt.close(fig)
    target_path.with_suffix(".json").write_text(json.dumps({"schema": "zstar-qnep-bec-parity", "mae_e": mae, "rmse_e": rmse, "components": len(predicted)}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
