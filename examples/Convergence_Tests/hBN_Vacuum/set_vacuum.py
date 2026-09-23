#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from pathlib import Path


BOHR_ANGSTROM = 0.529177210903


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("structure", type=Path)
    parser.add_argument("cell_height", type=float)
    parser.add_argument("--check", action="store_true",
                        help="verify the cell height without changing STRU")
    args = parser.parse_args()
    if args.cell_height <= 0:
        raise SystemExit("cell_height must be positive")

    lines = args.structure.read_text(encoding="utf-8").splitlines()
    try:
        constant_index = next(i for i, line in enumerate(lines)
                              if line.strip() == "LATTICE_CONSTANT")
        vector_index = next(i for i, line in enumerate(lines)
                            if line.strip() == "LATTICE_VECTORS")
    except StopIteration as exc:
        raise SystemExit("LATTICE_CONSTANT or LATTICE_VECTORS was not found") from exc
    lattice_constant_bohr = float(lines[constant_index + 1].split()[0])
    vector = [float(value) for value in lines[vector_index + 3].split()[:3]]
    norm = math.sqrt(sum(value * value for value in vector))
    actual_height = lattice_constant_bohr * BOHR_ANGSTROM * norm
    if args.check:
        if not math.isclose(actual_height, args.cell_height, abs_tol=1e-6):
            raise SystemExit(
                f"stale work directory: expected Lz={args.cell_height:.6f} Angstrom, "
                f"found {actual_height:.6f} Angstrom"
            )
        return
    scale = args.cell_height / (lattice_constant_bohr * BOHR_ANGSTROM * norm)
    lines[vector_index + 3] = " ".join(f"{value * scale:.10f}" for value in vector)
    args.structure.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
