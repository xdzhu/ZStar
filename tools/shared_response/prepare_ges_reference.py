"""Build a fixed-cell, inversion-symmetric GeS potential control, without DFT."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from phonopy.interface.abacus import read_abacus, write_abacus
import spglib


def prepare(source: Path, output: Path) -> dict:
    atoms, pps, orbitals, abfs = read_abacus(source / "STRU")
    if atoms.symbols != ["Ge", "Ge", "S", "S"]:
        raise ValueError("This provenance-specific control requires Ge, Ge, S, S ordering.")
    p = np.asarray(atoms.scaled_positions)
    # The inspected polar cell has the same x branch for the first Ge/S pair.
    # Inversion exchanges equal-species partners (0,1) and (2,3).
    shifts = p[[1, 3]] - p[[0, 2]]
    if not np.allclose(shifts[:, 0], [0.5, -0.5], atol=2e-5):
        raise ValueError("Unexpected periodic atom mapping; do not average this structure.")
    x_center = float((p[0, 0] + p[2, 0]) / 2)
    q = p.copy()
    q[:, 0] = [x_center, (x_center + .5) % 1, x_center, (x_center + .5) % 1]
    q[:, 1] = [.5, 0, .5, 0]
    for i, j in ((0, 1), (2, 3)):
        half = (p[i, 2] - p[j, 2]) / 2
        q[i, 2], q[j, 2] = .5 + half, .5 - half
    inversion_center = np.array([(x_center + .25) % 1, .25, .5])
    permutation = [1, 0, 3, 2]
    residual = q[permutation] + q - 2 * inversion_center
    residual -= np.rint(residual)
    assert np.max(np.abs(residual)) < 1e-12
    reference = atoms.copy()
    reference.scaled_positions = q
    def symmetry(cell):
        data = spglib.get_symmetry_dataset(
            (cell.cell, cell.scaled_positions, cell.numbers), symprec=1e-4
        )
        return {"international": data.international, "number": int(data.number),
                "pointgroup": data.pointgroup, "operations": len(data.rotations)}
    output.mkdir(parents=True, exist_ok=False)
    write_abacus(output / "STRU", reference, pps, orbitals, abfs)
    for name in ("INPUT", "KPT", "run.sh"):
        shutil.copy2(source / name, output / name)
    evidence = {
        "source": str(source), "source_stru_sha256": hashlib.sha256((source / "STRU").read_bytes()).hexdigest(),
        "construction": "Remove relative armchair Ge/S offset at fixed cell; restore equal-species inversion pairs.",
        "inversion_center_fractional": inversion_center.tolist(),
        "inversion_permutation_zero_based": permutation,
        "maximum_inversion_residual_fractional": float(np.max(np.abs(residual))),
        "polar_symmetry": symmetry(atoms), "reference_symmetry": symmetry(reference),
        "polar_fractional_positions": p.tolist(), "reference_fractional_positions": q.tolist(),
        "reference_status": "Fixed-ion nonpolar reference; not an optimized saddle point.",
        "primary_reference": "https://doi.org/10.1103/PhysRevLett.117.097601",
        "primary_location": "Fig. 1(b), zero tilting and inversion-symmetric phase A",
    }
    (output / "reference_construction.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), indent=2))
