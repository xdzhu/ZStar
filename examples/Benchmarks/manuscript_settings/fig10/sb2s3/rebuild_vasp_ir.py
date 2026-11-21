"""Rebuild the Sb2S3 VASP infrared curve from archived harmonic modes and BECs."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from zstar.spectra import GammaModes, mode_effective_charges


def rebuild(mode_archive, bec_csv):
    data = json.loads(Path(mode_archive).read_text(encoding="utf-8"))
    modes = GammaModes(
        frequencies_thz=np.asarray(data["frequencies_thz"]),
        eigenvectors=np.asarray(data["eigenvectors"]),
        masses_amu=np.asarray(data["masses_amu"]),
        lattice_angstrom=np.asarray(data["lattice_angstrom"]),
        symbols=tuple(data["symbols"]),
        positions_fractional=np.asarray(data["positions_fractional"]),
    )
    with Path(bec_csv).open(encoding="utf-8", newline="") as handle:
        atoms = list(csv.DictReader(handle))
    if [int(row["atom"]) for row in atoms] != list(range(1, len(modes.symbols) + 1)):
        raise ValueError("BEC records must follow the archived VASP atom order")
    if tuple(row["site"].split("(")[0] for row in atoms) != modes.symbols:
        raise ValueError("BEC sites and archived VASP species differ")
    tensors = np.array([
        [[float(row[f"Z_{a}{b}_e"]) for b in "xyz"] for a in "xyz"]
        for row in atoms
    ])
    selected = modes.frequencies_cm1 > 5.0
    frequency = modes.frequencies_cm1[selected]
    if len(frequency) != 26:
        raise ValueError("Expected the 26 optical modes of the archived calculation")
    intensities = mode_effective_charges(modes, tensors)[selected] ** 2
    grid_spec = data["wavenumber_grid_cm1"]
    grid = np.linspace(grid_spec["start"], grid_spec["stop"], grid_spec["count"])
    half_width = 4.0
    kernel = (half_width / np.pi) / ((grid[:, None] - frequency[None, :]) ** 2 + half_width ** 2)
    polarized = kernel @ intensities
    return np.column_stack((grid, polarized, polarized.sum(axis=1))), frequency, intensities


def main():
    case = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    curve, _, _ = rebuild(
        case / "vasp_gamma_modes.json",
        case.parents[1] / "sb2s3_vasp_fd/results/BEC_all_atoms.csv",
    )
    np.savetxt(args.output, curve, header="frequency_cm-1 intensity_x intensity_y intensity_z intensity_total")


if __name__ == "__main__":
    main()
