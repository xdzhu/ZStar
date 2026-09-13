"""Summarize GPUMD qNEP energy/force/BEC validation outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _bec_metrics(path: Path) -> dict:
    rows = np.asarray([[float(x) for x in line.split()] for line in path.read_text().splitlines() if line.strip()])
    if not rows.size:
        return {"labeled_atom_rows": 0}
    if rows.ndim != 2 or rows.shape[1] != 18:
        raise ValueError(f"{path} must contain 18 columns")
    labeled = np.any(np.abs(rows[:, 9:]) > 1e-10, axis=1)
    error = rows[labeled, :9] - rows[labeled, 9:]
    if not len(error):
        return {"labeled_atom_rows": 0}
    ss_tot = np.sum((rows[labeled, 9:] - rows[labeled, 9:].mean()) ** 2)
    return {
        "labeled_atom_rows": int(len(error)),
        "mae_e": float(np.abs(error).mean()),
        "rmse_e": float(np.sqrt(np.mean(error**2))),
        "max_abs_e": float(np.abs(error).max()),
        "r2": float(1.0 - np.sum(error**2) / ss_tot) if ss_tot > 0 else None,
    }


def _parity_metrics(path: Path, n_components: int, units: str, *, sentinel_limit: float | None = None) -> dict:
    if not path.exists() or not path.read_text().strip():
        return {"rows": 0, "units": units}
    rows = np.loadtxt(path, ndmin=2)
    if rows.shape[1] != 2 * n_components:
        raise ValueError(f"{path} must contain {2 * n_components} columns")
    if sentinel_limit is not None:
        valid = np.all(np.abs(rows) < sentinel_limit, axis=1)
        rows = rows[valid]
        if not len(rows):
            return {"rows": 0, "units": units, "filtered_sentinel_rows": int(np.sum(~valid))}
    else:
        valid = np.ones(len(rows), dtype=bool)
    error = rows[:, :n_components] - rows[:, n_components:]
    flat = error.ravel()
    target = rows[:, n_components:].ravel()
    ss_tot = np.sum((target - target.mean()) ** 2)
    return {
        "rows": int(len(rows)),
        "mae": float(np.abs(flat).mean()),
        "rmse": float(np.sqrt(np.mean(flat**2))),
        "max_abs": float(np.abs(flat).max()),
        "r2": float(1.0 - np.sum(flat**2) / ss_tot) if ss_tot > 0 else None,
        "units": units,
        "filtered_sentinel_rows": int(np.sum(~valid)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.run_dir).resolve()
    result = {
        "schema": "zstar-qnep-training-validation",
        "run_dir": str(root),
        "training_scope": "cubic BaTiO3 only; small compatibility model",
        "gpumd_version": "5.7",
        "charge_mode": 1,
        "parity": {
            "train_energy": _parity_metrics(root / "energy_train.out", 1, "eV/atom"),
            "test_energy": _parity_metrics(root / "energy_test.out", 1, "eV/atom"),
            "train_force": _parity_metrics(root / "force_train.out", 3, "eV/Angstrom"),
            "test_force": _parity_metrics(root / "force_test.out", 3, "eV/Angstrom"),
            "train_stress": _parity_metrics(root / "stress_train.out", 6, "eV/Angstrom^3", sentinel_limit=1e5),
            "test_stress": _parity_metrics(root / "stress_test.out", 6, "eV/Angstrom^3", sentinel_limit=1e5),
            "train_virial": _parity_metrics(root / "virial_train.out", 6, "eV/atom", sentinel_limit=1e5),
            "test_virial": _parity_metrics(root / "virial_test.out", 6, "eV/atom", sentinel_limit=1e5),
        },
        "train_bec": _bec_metrics(root / "bec_train.out"),
        "test_bec": _bec_metrics(root / "bec_test.out"),
        "loss_log": "loss.out",
        "model": "nep.txt",
        "note": "BEC output contains zero target rows for frames without a BEC label; metrics use only nonzero target rows.",
    }
    target = Path(args.output).resolve()
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
