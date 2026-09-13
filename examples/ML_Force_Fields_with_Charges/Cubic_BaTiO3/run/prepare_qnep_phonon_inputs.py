"""Create GPUMD model.xyz inputs from a completed Phonopy displacement archive.

This helper only prepares calculator-neutral inputs. It does not run GPUMD and
does not assume that an external NAC can be added to a native long-range qNEP
force constant. The output directory is suitable for a controlled Level 2
smoke run on a GPU host.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from phonopy import load


BOHR_ANGSTROM = 0.529177210903


def _prepare_yaml(source: Path, target: Path) -> Path:
    """Create an Angstrom copy of an ABACUS archive recorded in Bohr."""
    import yaml

    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    length = str(payload.get("physical_unit", {}).get("length", "angstrom")).lower()
    if length not in {"au", "bohr", "a.u."}:
        return source
    for section in ("primitive_cell", "unit_cell", "supercell"):
        for row in payload.get(section, {}).get("lattice", []):
            for index in range(len(row)):
                row[index] = float(row[index]) * BOHR_ANGSTROM
    for item in payload.get("displacements", []):
        item["displacement"] = [float(value) * BOHR_ANGSTROM for value in item["displacement"]]
    payload.setdefault("physical_unit", {})["length"] = "angstrom"
    payload.setdefault("phonopy", {})["frequency_unit_conversion_factor"] = 15.633302
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8", newline="\n")
    return target


def write_model_xyz(cell, symbols, positions, output: Path) -> None:
    lattice = " ".join(f"{float(value):.12g}" for row in np.asarray(cell) for value in row)
    lines = [
        str(len(symbols)),
        f'Lattice="{lattice}" Properties=species:S:1:pos:R:3:force:R:3 energy=0.0 pbc="T T T"',
    ]
    for symbol, position in zip(symbols, np.asarray(positions)):
        values = " ".join(f"{float(value):.12g}" for value in position)
        lines.append(f"{symbol} {values} 0 0 0")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phonopy-yaml", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(args.phonopy_yaml).resolve()
    target = Path(args.output).resolve()
    target.mkdir(parents=True, exist_ok=True)
    normalized = _prepare_yaml(source, target / "phonopy_disp_angstrom.yaml")
    phonon = load(phonopy_yaml=str(normalized), produce_fc=False)
    write_model_xyz(phonon.supercell.cell, phonon.supercell.symbols, phonon.supercell.positions, target / "equilibrium.xyz")
    entries = []
    for index, structure in enumerate(phonon.supercells_with_displacements, start=1):
        name = f"disp-{index:03d}.xyz"
        write_model_xyz(structure.cell, structure.symbols, structure.positions, target / name)
        entries.append({"index": index, "file": name, "natoms": len(structure), "displacement": phonon.displacements[index - 1]})
    manifest = {
        "schema": "zstar-qnep-phonon-inputs",
        "source": str(source),
        "normalized_source": str(normalized),
        "calculator": "gpumd-qnep",
        "supercell_atoms": len(phonon.supercell),
        "equilibrium": "equilibrium.xyz",
        "displacements": entries,
        "next": "Run one GPUMD force smoke test per disp-*.xyz, then collect forces into FORCE_SETS.",
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
