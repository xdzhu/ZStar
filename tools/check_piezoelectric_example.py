#!/usr/bin/env python3
"""Validate a curated piezoelectric example and its archived tensors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    case = args.case.resolve()
    metadata = json.loads((case / "case.json").read_text(encoding="utf-8"))

    missing = [name for name in metadata["required_run_files"] if not (case / "run" / name).is_file()]
    if missing:
        raise SystemExit("missing run files: " + ", ".join(missing))

    for stage in ("reference", "response"):
        incar = (case / "run" / "vasp" / stage / "INCAR").read_text(encoding="utf-8")
        normalized = incar.upper().replace(" ", "")
        if "NCORE=4" not in normalized or "NPAR=" in normalized:
            raise SystemExit(f"VASP {stage} INCAR must use NCORE=4 without NPAR")

    summary = json.loads((case / "results" / "abacus_pbe_summary.json").read_text(encoding="utf-8"))
    native = json.loads((case / "results" / "vasp_pbe_native_response.json").read_text(encoding="utf-8"))
    if str(summary.get("functional", "")).lower() != "pbe":
        raise SystemExit("archived ABACUS result is not labelled PBE")
    if int(summary.get("stage_count", 0)) != 13 or int(summary.get("pyatb_run_count", 0)) != 13:
        raise SystemExit("archived ABACUS result does not contain the complete 13-stage ensemble")
    if not summary.get("mechanical_stable_positive_definite"):
        raise SystemExit("archived elastic tensor is not positive definite")

    abacus_e = np.asarray(summary["piezoelectric_proper_C_per_m2"], dtype=float)
    abacus_d = np.asarray(summary["piezoelectric_d_pm_per_V"], dtype=float)
    vasp_e = np.asarray(native["tensors"]["piezoelectric_total_C_m2"], dtype=float)
    vasp_d = np.asarray(native["tensors"]["piezoelectric_d_pm_V"], dtype=float)
    expected = metadata["expected"]
    checks = {
        "abacus_e31": abacus_e[2, 0],
        "abacus_e33": abacus_e[2, 2],
        "abacus_e15": abacus_e[0, 4],
        "abacus_d33": abacus_d[2, 2],
        "vasp_e31": vasp_e[2, 0],
        "vasp_e33": vasp_e[2, 2],
        "vasp_e15": vasp_e[0, 4],
        "vasp_d33": vasp_d[2, 2],
    }
    for name, actual in checks.items():
        if not np.isclose(actual, float(expected[name]), atol=5.0e-6, rtol=0.0):
            raise SystemExit(f"{name} mismatch: expected {expected[name]}, found {actual}")
    print(json.dumps({"case": metadata["material"], "status": "validated", **checks}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
