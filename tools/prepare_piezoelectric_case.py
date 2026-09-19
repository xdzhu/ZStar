#!/usr/bin/env python3
"""Prepare a three-dimensional finite-strain ensemble (central default).

This helper only serializes inputs and provenance.  It never launches ABACUS
or PYATB; the remote drivers are separate, scheduler-specific scripts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zstar.v2.strain import V2_SYMPREC
from zstar.piezoelectric import prepare_abacus_strain_ensemble


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="directory containing INPUT, KPT, and STRU",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--pp", "--pseudopotential-dir", dest="pseudopotential_dir", type=Path, required=True
    )
    parser.add_argument("--orb", "--orbital-dir", dest="orbital_dir", type=Path, required=True)
    parser.add_argument(
        "--amplitude",
        type=float,
        default=5.0e-3,
        help="production is fixed at 0.005; verification accepts the two internal audit values",
    )
    parser.add_argument("--profile", choices=("production", "verification"), default="production")
    parser.add_argument("--method", choices=("central", "forward"), default="central",
                        help="central (recommended): O(h^2); forward: O(h) truncation error")
    parser.add_argument(
        "--symprec",
        type=float,
        default=V2_SYMPREC,
        help="fixed response symmetry tolerance (must be 1e-3 Angstrom)",
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
            f"piezoelectric response requires --symprec {V2_SYMPREC:g}; refusing {args.symprec:g}"
        )
    if args.profile == "production" and args.amplitude != 5.0e-3:
        raise SystemExit("production profile has fixed engineering strain amplitude 0.005")
    if args.profile == "verification" and args.amplitude not in {5.0e-3, 1.0e-2}:
        raise SystemExit(
            "verification amplitude is developer-only and must be either 0.005 or 0.01"
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
        method=args.method,
    )
    metadata = {
        "schema": "zstar-piezo-case-preparation",
        "status": "inputs_prepared",
        "source": str(source),
        "ensemble": "ensemble.json",
        "symmetry": "symmetry.json",
        "amplitude_engineering_strain": args.amplitude,
        "convergence_profile": args.profile,
        "finite_difference": result["ensemble"].metadata["finite_difference"],
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
