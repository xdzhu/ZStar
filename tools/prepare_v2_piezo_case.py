#!/usr/bin/env python3
"""Prepare a full 3-D central finite-strain ensemble for a v2 case.

This helper only serializes inputs and provenance.  It never launches ABACUS
or PYATB; the remote drivers are separate, scheduler-specific scripts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zstar.v2.strain import V2_SYMPREC, prepare_abacus_strain_ensemble


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="directory containing inputs/STRU")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pseudopotential-dir", type=Path, required=True)
    parser.add_argument("--orbital-dir", type=Path, required=True)
    parser.add_argument("--amplitude", type=float, default=5.0e-3)
    parser.add_argument("--profile", choices=("production", "verification"), default="production")
    parser.add_argument(
        "--symprec",
        type=float,
        default=V2_SYMPREC,
        help="fixed v2 symmetry tolerance (must be 1e-3 Angstrom)",
    )
    parser.add_argument(
        "--force-thr-ev",
        type=float,
        default=None,
        help="override the selected profile only with an equal-or-tighter force threshold",
    )
    parser.add_argument(
        "--scf-thr",
        type=float,
        default=None,
        help="override the selected profile only with an equal-or-tighter SCF threshold",
    )
    parser.add_argument("--relax-nmax", type=int, default=100)
    parser.add_argument("--ion-relaxation", choices=("clamped-ion", "relaxed-ion"), default="relaxed-ion")
    args = parser.parse_args()
    if args.symprec != V2_SYMPREC:
        raise SystemExit(
            f"v2 requires --symprec {V2_SYMPREC:g}; refusing {args.symprec:g}"
        )
    source = args.source.resolve()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"output is not empty: {output}")
    result = prepare_abacus_strain_ensemble(
        output,
        structure=source / "STRU",
        input_template=source / "INPUT",
        kpt_template=source / "KPT",
        pp_dir=args.pseudopotential_dir,
        orb_dir=args.orbital_dir,
        dimensionality=3,
        amplitude=args.amplitude,
        symprec=args.symprec,
        ion_relaxation=args.ion_relaxation,
        profile=args.profile,
        force_thr_ev=args.force_thr_ev,
        scf_thr=args.scf_thr,
        relax_nmax=args.relax_nmax,
        symmetry_reduce=False,
    )
    metadata = {
        "schema": "zstar-v2-piezo-case-preparation",
        "status": "inputs_prepared",
        "source": str(source),
        "ensemble": "ensemble.json",
        "symmetry": "symmetry.json",
        "amplitude_engineering_strain": args.amplitude,
        "convergence_profile": args.profile,
        "scf_thr": result["ensemble"].metadata["scf_thr"],
        "ion_relaxation": args.ion_relaxation,
        "force_thr_ev": result["ensemble"].metadata["force_thr_ev"],
        "relax_nmax": args.relax_nmax,
        "backend": "ABACUS + PYATB",
        "note": "No calculator was launched by this helper.",
    }
    (output / "preparation.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"root": str(output), "stages": len(result["ensemble"].stages) + 1, "symmetry": result["symmetry"].space_group}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
