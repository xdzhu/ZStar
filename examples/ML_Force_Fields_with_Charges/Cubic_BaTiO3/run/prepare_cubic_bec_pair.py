"""Create two primitive cubic-BTO BEC candidates linked to the supplement.

The structures are deliberately small and deterministic.  Their DFT/PYATB
labels are generated later with the same PBEsol settings and ABACUS
``kspacing=0.1`` policy used by the existing BEC workflow.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--a", type=float, default=4.04849223)
    args = parser.parse_args()
    a = args.a
    base = [
        ("Ba", (0.0, 0.0, 0.0)),
        ("O", (a / 2, a / 2, 0.0)),
        ("O", (a / 2, 0.0, a / 2)),
        ("O", (0.0, a / 2, a / 2)),
        ("Ti", (a / 2, a / 2, a / 2)),
    ]
    soft = []
    for symbol, position in base:
        dz = 0.06 if symbol == "Ti" else -0.02 if symbol == "O" else 0.0
        soft.append((symbol, (position[0], position[1], (position[2] + dz) % a)))
    records = []
    for frame_id, atoms, tag in [
        ("bec_parent_equilibrium", base, "equilibrium"),
        ("bec_parent_soft_z", soft, "soft_mode_[001]"),
    ]:
        records.append(
            {
                "frame_id": frame_id,
                "structure_id": frame_id,
                "chemical_symbols": [symbol for symbol, _ in atoms],
                "cell": [[a, 0.0, 0.0], [0.0, a, 0.0], [0.0, 0.0, a]],
                "positions": [list(position) for _, position in atoms],
                "pbc": [True, True, True],
                "total_charge": 0.0,
                "temperature": None,
                "phase_label": "cubic",
                "sampling_tag": tag,
                "parent_frame_id": f"primitive_parent_{tag}",
                "exchange_correlation": "PBEsol",
                "kpoint_policy": "abacus_automatic_kspacing_0.1",
                "bec_required": True,
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": len(records), "natoms": 5}, indent=2))


if __name__ == "__main__":
    main()
