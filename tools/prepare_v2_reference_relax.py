#!/usr/bin/env python3
"""Prepare a production or verification reference cell relaxation for v2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zstar.v2.strain import V2_SYMPREC, prepare_abacus_reference_relaxation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="directory containing STRU, INPUT, and KPT")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pseudopotential-dir", type=Path, required=True)
    parser.add_argument("--orbital-dir", type=Path, required=True)
    parser.add_argument("--profile", choices=("production", "verification"), default="production")
    parser.add_argument("--force-thr-ev", type=float, default=None)
    parser.add_argument("--stress-thr-kbar", type=float, default=None)
    parser.add_argument("--scf-thr", type=float, default=None)
    parser.add_argument("--relax-nmax", type=int, default=100)
    args = parser.parse_args()
    result = prepare_abacus_reference_relaxation(
        args.output,
        structure=args.source / "STRU",
        input_template=args.source / "INPUT",
        kpt_template=args.source / "KPT",
        pp_dir=args.pseudopotential_dir,
        orb_dir=args.orbital_dir,
        profile=args.profile,
        symprec=V2_SYMPREC,
        force_thr_ev=args.force_thr_ev,
        stress_thr_kbar=args.stress_thr_kbar,
        scf_thr=args.scf_thr,
        relax_nmax=args.relax_nmax,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
