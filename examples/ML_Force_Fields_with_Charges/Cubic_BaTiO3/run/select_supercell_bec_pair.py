"""Select two deterministic 40-atom supplement frames for BEC workflows.

The selected structures are deliberately kept as 2x2x2 (40-atom) cells.  They
are not reduced to the primitive five-atom cell: the purpose of this small
pair is to test that a charge-response workflow can annotate genuinely large
force-field configurations.  Selection is explicit and reproducible so the
pair cannot silently change when the 50-frame supplement is regenerated.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from zstar.charge_aware_dataset import read_charge_dataset, write_charge_dataset


DEFAULT_IDS = ("supp_003", "supp_005")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--frame-id", action="append", dest="frame_ids")
    args = parser.parse_args()

    requested = tuple(args.frame_ids or DEFAULT_IDS)
    if len(requested) != 2 or len(set(requested)) != 2:
        raise ValueError("exactly two distinct --frame-id values are required")
    frames = read_charge_dataset(args.input)
    by_id = {frame.frame_id: frame for frame in frames}
    missing = [frame_id for frame_id in requested if frame_id not in by_id]
    if missing:
        raise ValueError(f"selected frames are absent from {args.input}: {missing}")
    selected = [by_id[frame_id] for frame_id in requested]
    for frame in selected:
        if len(frame.chemical_symbols) != 40:
            raise ValueError(f"{frame.frame_id} has {len(frame.chemical_symbols)} atoms; expected 40")
        if frame.phase_label != "cubic":
            raise ValueError(f"{frame.frame_id} is not labeled cubic")
        frame.metadata = dict(frame.metadata or {})
        frame.metadata.update({
            "bec_selection": "deterministic_two_frame_supercell_pair",
            "bec_selection_role": "40_atom_nonprimitive_supplement",
            "bec_requested": True,
            "bec_units": "e",
            "bec_coordinate_convention": "cartesian_A; atom order from source extxyz",
            "supercell": [2, 2, 2],
        })
        frame.born_effective_charges = None
        frame.born_effective_charges_available = False
        frame.validation_status = "selected_for_bec"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_charge_dataset(selected, args.output)
    try:
        source_label = str(args.input.resolve().relative_to(REPO_ROOT))
    except ValueError:
        source_label = str(args.input)
    manifest = {
        "schema": "zstar-cubic-bto-supercell-bec-pair",
        "source": source_label,
        "selected_frame_ids": list(requested),
        "natoms": 40,
        "supercell": [2, 2, 2],
        "phase_label": "cubic",
        "selection_policy": (
            "fixed pair supp_003 (0.985 lattice scale plus random perturbation) and "
            "supp_005 (1.015 lattice scale plus random perturbation); both have "
            "space-group P1 at the selection tolerance and remain unreduced "
            "40-atom structures"
        ),
        "calculation_policy": {
            "exchange_correlation": "PBEsol",
            "kspacing_inv_bohr": 0.1,
            "primitive_kpoint_convention": "ABACUS automatic mesh from kspacing=0.1",
            "supercell_kpoint_convention": "ABACUS automatic mesh from kspacing=0.1; cell-dependent",
            "bec_method": "existing ZStar ABACUS+PYATB workflow",
        },
        "status": "candidates_selected; DFT BEC pending",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
