"""Analyze a transverse finite-field Raman probe for a z-periodic wire."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from zstar.polarization_2d import _parse_pyatb_polarization
from zstar.raman_local_field import (
    BOHR_M,
    ELEMENTARY_CHARGE,
    BOHR_ANGSTROM,
    line_polarizability_a2,
    mode_raman_component,
    unwrap_difference,
)
from zstar.shared_response import read_structure


def _field_pair(root: Path, geometry: str) -> tuple[float, float, float]:
    values = []
    quanta = []
    for sign in ("plus", "minus"):
        path = (
            root / "states" / geometry / f"field_{sign}"
            / "pyatb-field-polar/Out/Polarization/polarization.dat"
        )
        polarization, quantum = _parse_pyatb_polarization(path)
        values.append(float(polarization[2]))
        quanta.append(float(quantum[2]))
    if not np.isclose(quanta[0], quanta[1], rtol=1.0e-4, atol=0.0):
        raise ValueError(f"Polarization quanta disagree for {geometry}")
    return values[0], values[1], 0.5 * sum(quanta)


def analyze(root: Path, structure: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("field_axis") not in {"x", "y"}:
        raise ValueError("Only transverse x/y fields are supported")
    field = float(manifest["field_au"])
    amplitude = float(manifest["mode_amplitude_A_sqrt_amu"])
    cell = np.asarray(read_structure(structure).cell, dtype=float)
    if not np.allclose(cell, np.diag(np.diag(cell)), atol=1.0e-6) or np.any(np.diag(cell) <= 0):
        raise ValueError("Analysis requires a positive orthorhombic z-periodic cell")
    volume = float(abs(np.linalg.det(cell)))
    length = float(cell[2, 2])
    reference = _field_pair(root, "reference")
    modes = sorted({
        int(stage["geometry"].split("/")[0].split("-")[1])
        for stage in manifest["stages"]
        if stage["geometry"].startswith("mode-")
    })
    output = {
        "field_axis": manifest["field_axis"],
        "field_au": field,
        "mode_amplitude_a_sqrt_amu": amplitude,
        "volume_a3": volume,
        "periodic_length_a": length,
        f"reference_alpha_z{manifest['field_axis']}_a2": line_polarizability_a2(
            *reference, field_au=field, volume_a3=volume, length_a=length,
        ),
        "modes": {},
    }
    for mode in modes:
        result = mode_raman_component(
            _field_pair(root, f"mode-{mode:04d}/plus"),
            _field_pair(root, f"mode-{mode:04d}/minus"),
            field_au=field, amplitude_a_sqrt_amu=amplitude,
            volume_a3=volume, length_a=length,
            field_axis=manifest["field_axis"],
        )
        output["modes"][str(mode)] = result
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--stru", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.probe, args.stru)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
