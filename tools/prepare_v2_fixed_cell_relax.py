#!/usr/bin/env python3
"""Prepare the v2 R2r fixed-cell internal-relaxation stage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zstar.v2.strain import prepare_abacus_fixed_cell_relaxation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="directory with promoted R1 STRU, INPUT, KPT")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pseudopotential-dir", type=Path, required=True)
    parser.add_argument("--orbital-dir", type=Path, required=True)
    parser.add_argument("--profile", choices=("production", "verification"), default="production")
    parser.add_argument("--relax-nmax", type=int, default=100)
    args = parser.parse_args()
    result = prepare_abacus_fixed_cell_relaxation(
        args.output,
        structure=args.source / "STRU",
        input_template=args.source / "INPUT",
        kpt_template=args.source / "KPT",
        pp_dir=args.pseudopotential_dir,
        orb_dir=args.orbital_dir,
        profile=args.profile,
        relax_nmax=args.relax_nmax,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
