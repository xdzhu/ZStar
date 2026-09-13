"""Create a small cubic-BTO Phonopy displacement archive for GPUMD forces."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from phonopy import Phonopy
from phonopy.structure.atoms import PhonopyAtoms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--a", type=float, default=4.04849223)
    parser.add_argument("--distance", type=float, default=0.01)
    args = parser.parse_args()
    target = Path(args.output).resolve()
    target.mkdir(parents=True, exist_ok=True)
    a = args.a
    cell = PhonopyAtoms(
        symbols=["Ba", "O", "O", "O", "Ti"],
        cell=np.eye(3) * a,
        scaled_positions=[[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5], [0.5, 0.5, 0.5]],
    )
    phonon = Phonopy(cell, np.diag([2, 2, 2]))
    phonon.generate_displacements(distance=args.distance)
    phonon.save(filename=str(target / "phonopy.yaml"), settings={"force_constants": False})
    # The displacement archive is read by the existing GPUMD dump collector.
    phonon.save(filename=str(target / "phonopy_disp.yaml"), settings={"force_constants": False})
    (target / "manifest.json").write_text(
        "{\n"
        '  "schema": "zstar-cubic-bto-qnep-phonopy-archive",\n'
        f'  "lattice_A": {a:.12g},\n'
        f'  "supercell": [2, 2, 2],\n'
        f'  "supercell_atoms": {len(phonon.supercell)},\n'
        f'  "displacement_A": {args.distance:.12g}\n'
        "}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
