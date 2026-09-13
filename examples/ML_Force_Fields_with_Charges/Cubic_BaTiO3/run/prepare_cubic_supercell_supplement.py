"""Prepare a compact 2x2x2 cubic-BaTiO3 force-data supplement.

The supplement deliberately contains geometries only.  DFT energies, forces,
and stresses must be collected by the selected calculator before the resulting
frames are exported to qNEP.  The existing Phonopy equilibrium and disp-*
geometries are reused, and the remaining frames are deterministic lattice,
random-displacement, and soft-mode perturbations of the same 40-atom cell.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Frame:
    symbols: list[str]
    positions: list[tuple[float, float, float]]
    lattice: tuple[float, float, float]
    frame_id: str
    source: str
    parent_frame_id: str | None = None
    header: str = ""


def _quoted_value(header: str, key: str) -> str | None:
    marker = f'{key}="'
    start = header.find(marker)
    if start < 0:
        return None
    start += len(marker)
    end = header.find('"', start)
    return header[start:end] if end >= 0 else None


def _token_value(header: str, key: str) -> str | None:
    marker = f"{key}="
    start = header.find(marker)
    if start < 0:
        return None
    start += len(marker)
    end = start
    while end < len(header) and not header[end].isspace():
        end += 1
    return header[start:end].strip('"') or None


def read_extxyz(path: Path) -> list[Frame]:
    lines = path.read_text(encoding="utf-8").splitlines()
    frames: list[Frame] = []
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        natoms = int(lines[i].strip())
        header = lines[i + 1]
        lattice_text = _quoted_value(header, "Lattice")
        if lattice_text is None:
            raise ValueError(f"missing Lattice in {path}")
        lattice_values = [float(value) for value in lattice_text.split()]
        if len(lattice_values) != 9:
            raise ValueError(f"expected 9 lattice values in {path}")
        lattice = tuple(
            math.sqrt(sum(lattice_values[row + 3 * column] ** 2 for row in range(3)))
            for column in range(3)
        )
        symbols: list[str] = []
        positions: list[tuple[float, float, float]] = []
        for row in lines[i + 2 : i + 2 + natoms]:
            fields = row.split()
            symbols.append(fields[0])
            positions.append(tuple(float(value) for value in fields[1:4]))
        frames.append(
            Frame(
                symbols,
                positions,
                lattice,
                _token_value(header, "frame_id") or "",
                str(path),
                _token_value(header, "parent_frame_id"),
                header,
            )
        )
        i += natoms + 2
    return frames


def _wrap(value: float, period: float) -> float:
    return value % period


def _normalised(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return tuple(value / norm for value in vector)


def _soft_coefficients(symbols: list[str]) -> list[float]:
    # A simple Ti/O relative-displacement pattern.  This is a data-diversity
    # generator, not a claim to be the normalized phonon eigenvector.
    return [1.0 if symbol == "Ti" else -0.35 if symbol == "O" else 0.0 for symbol in symbols]


def _perturb(
    base: Frame,
    *,
    scale: float,
    rng: random.Random,
    random_amplitude: float = 0.0,
    soft_direction: tuple[float, float, float] | None = None,
    soft_amplitude: float = 0.0,
) -> Frame:
    lattice = tuple(value * scale for value in base.lattice)
    coefficients = _soft_coefficients(base.symbols)
    direction = _normalised(soft_direction) if soft_direction else (0.0, 0.0, 0.0)
    positions: list[tuple[float, float, float]] = []
    random_vectors: list[tuple[float, float, float]] = []
    for _ in base.positions:
        random_vectors.append(
            tuple(rng.uniform(-random_amplitude, random_amplitude) for _ in range(3))
        )
    if random_vectors:
        mean = tuple(sum(vector[index] for vector in random_vectors) / len(random_vectors) for index in range(3))
    else:
        mean = (0.0, 0.0, 0.0)
    for index, position in enumerate(base.positions):
        random_shift = tuple(random_vectors[index][axis] - mean[axis] for axis in range(3))
        soft_shift = tuple(coefficients[index] * soft_amplitude * direction[axis] for axis in range(3))
        shifted = tuple(position[axis] * scale + random_shift[axis] + soft_shift[axis] for axis in range(3))
        positions.append(tuple(_wrap(shifted[axis], lattice[axis]) for axis in range(3)))
    return Frame(base.symbols.copy(), positions, lattice, "", "generated", None)


def write_extxyz(frames: list[Frame], path: Path) -> None:
    lines: list[str] = []
    for frame in frames:
        lattice = " ".join(
            f"{value:.12g}" if index in (0, 4, 8) else "0"
            for index, value in enumerate(
                (frame.lattice[0], 0.0, 0.0, 0.0, frame.lattice[1], 0.0, 0.0, 0.0, frame.lattice[2])
            )
        )
        lines.append(str(len(frame.symbols)))
        lines.append(
            f'Lattice="{lattice}" Properties=species:S:1:pos:R:3 '
            f'frame_id={frame.frame_id} parent_frame_id={frame.parent_frame_id or frame.frame_id} '
            'phase_label=cubic units=angstrom pbc="T T T" labels_pending=true'
        )
        lines.extend(
            f"{symbol} {position[0]:.12g} {position[1]:.12g} {position[2]:.12g}"
            for symbol, position in zip(frame.symbols, frame.positions)
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_supplement(source_dir: Path, output_dir: Path, seed: int, target_count: int) -> dict:
    equilibrium_path = source_dir / "equilibrium.xyz"
    source_frames = read_extxyz(equilibrium_path)
    if len(source_frames) != 1 or len(source_frames[0].symbols) != 40:
        raise ValueError("equilibrium.xyz must contain one 40-atom frame")
    base = source_frames[0]
    selected: list[Frame] = []
    for filename, frame_id in [
        ("equilibrium.xyz", "phonon_equilibrium"),
        ("disp-001.xyz", "phonon_disp_001"),
        ("disp-002.xyz", "phonon_disp_002"),
        ("disp-003.xyz", "phonon_disp_003"),
    ]:
        frames = read_extxyz(source_dir / filename)
        if len(frames) != 1 or len(frames[0].symbols) != 40:
            raise ValueError(f"{filename} must contain one 40-atom frame")
        frame = frames[0]
        frame.frame_id = frame_id
        frame.source = str(source_dir / filename)
        frame.parent_frame_id = frame_id
        selected.append(frame)
    if target_count < len(selected):
        raise ValueError(f"target_count must be at least {len(selected)}")

    rng = random.Random(seed)
    recipes: list[dict] = []
    recipes.extend({"kind": "lattice_random", "scale": scale, "random_amplitude": amplitude}
                   for scale, amplitude in [
                       (0.97, 0.03), (0.97, 0.06), (0.985, 0.03), (0.985, 0.06),
                       (1.015, 0.03), (1.015, 0.06), (1.03, 0.03), (1.03, 0.06),
                       (0.995, 0.10), (1.005, 0.10)])
    recipes.extend({"kind": "random", "scale": 1.0, "random_amplitude": amplitude}
                   for amplitude in [0.02, 0.04, 0.06, 0.08] * 4)
    recipes.extend({"kind": "random", "scale": 1.0, "random_amplitude": amplitude}
                   for amplitude in [0.10, 0.12] * 5)
    recipes.extend({"kind": "soft_mode", "scale": scale, "soft_direction": direction, "soft_amplitude": amplitude}
                   for direction in [(0.0, 0.0, 1.0), (1.0, 1.0, 0.0), (1.0, 1.0, 1.0)]
                   for scale, amplitude in [(1.0, 0.06), (1.0, 0.10), (0.985, 0.08), (1.015, 0.08)])
    recipes.extend([
        {"kind": "mixed", "scale": 0.98, "random_amplitude": 0.06, "soft_direction": (0.0, 0.0, 1.0), "soft_amplitude": 0.06},
        {"kind": "mixed", "scale": 1.02, "random_amplitude": 0.06, "soft_direction": (1.0, 1.0, 1.0), "soft_amplitude": 0.06},
    ])
    needed = target_count - len(selected)
    if len(recipes) < needed:
        raise ValueError(f"recipe table has only {len(recipes)} entries for {needed} generated frames")

    records: list[dict] = []
    for frame in selected:
        records.append({"frame_id": frame.frame_id, "source": frame.source, "kind": "existing_phonon", "natoms": 40})
    for index, recipe in enumerate(recipes[:needed], start=1):
        frame = _perturb(base, rng=rng, **{key: value for key, value in recipe.items() if key != "kind"})
        frame.frame_id = f"supp_{index:03d}"
        frame.parent_frame_id = f"primitive_parent_{index:03d}"
        frame.source = "generated_from_phonon_equilibrium"
        selected.append(frame)
        records.append({"frame_id": frame.frame_id, "parent_frame_id": frame.parent_frame_id, "source": frame.source, "natoms": 40, **recipe})

    output_dir.mkdir(parents=True, exist_ok=True)
    write_extxyz(selected, output_dir / "geometry_candidates.xyz")
    manifest = {
        "schema": "zstar-cubic-bto-qnep-supercell-supplement",
        "status": "geometry_only_labels_pending",
        "exchange_correlation": "PBEsol",
        "kpoint_policy": "kspacing",
        "kspacing_inv_bohr": 0.1,
        "seed": seed,
        "target_frames": target_count,
        "new_force_label_frames": sum(record["kind"] != "existing_phonon" for record in records),
        "reused_existing_phonon_frames": sum(record["kind"] == "existing_phonon" for record in records),
        "actual_frames": len(selected),
        "supercell": [2, 2, 2],
        "natoms": 40,
        "phase_label": "cubic",
        "bec_frames": [],
        "geometry_reuse_policy": "reuse_existing_phonon_geometry_and_labels; calculate only supp_*",
        "kpoint_convention": "ABACUS automatic cell-dependent mesh from kspacing=0.1",
        "source_phonopy_inputs": str(source_dir),
        "records": records,
        "next": "run consistent DFT energy/force/stress calculations before qNEP export",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260913)
    parser.add_argument("--target-count", type=int, default=50)
    args = parser.parse_args()
    manifest = build_supplement(args.source_dir, args.output_dir, args.seed, args.target_count)
    print(json.dumps({"output_dir": str(args.output_dir), "actual_frames": manifest["actual_frames"]}, indent=2))


if __name__ == "__main__":
    main()
