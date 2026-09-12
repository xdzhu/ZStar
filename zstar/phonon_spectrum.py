"""Phonon dispersion, density of states, and bulk NAC comparison tools.

The finite-q force calculations are prepared separately from this module.  A
completed Phonopy ``phonopy.yaml`` is then sufficient to produce band and DOS
data without another electronic calculation; the archive contains the force
constants and the primitive-to-supercell mapping.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


def parse_supercell(value: str | Sequence[int]) -> tuple[int, int, int]:
    """Return a positive diagonal supercell from text or a three-item sequence."""

    if isinstance(value, str):
        tokens = value.replace(",", " ").split()
        if len(tokens) != 3:
            raise ValueError("supercell must contain exactly three integers")
        values = tuple(int(token) for token in tokens)
    else:
        if len(value) != 3:
            raise ValueError("supercell must contain exactly three integers")
        values = tuple(int(item) for item in value)
    if any(item < 1 for item in values):
        raise ValueError("supercell entries must be positive integers")
    return values


def parse_periodic_axes(value: str | Iterable[int] | None, dimensionality: int = 3) -> tuple[bool, bool, bool]:
    """Parse periodic axes, using x/y/z, an index list, or dimensionality defaults."""

    if value is None:
        if dimensionality == 3:
            return True, True, True
        if dimensionality == 2:
            return True, True, False
        if dimensionality == 1:
            return False, False, True
        if dimensionality == 0:
            return False, False, False
        raise ValueError("dimensionality must be one of 0, 1, 2, or 3")
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return parse_periodic_axes(None, dimensionality)
        if all(char in "xyz, \t" for char in text):
            selected = {"xyz".index(char) for char in text if char in "xyz"}
        else:
            tokens = text.replace(",", " ").split()
            selected = {int(token) for token in tokens}
    else:
        selected = {int(item) for item in value}
    if any(index not in {0, 1, 2} for index in selected):
        raise ValueError("periodic axes must be x/y/z or indices 0, 1, and 2")
    return tuple(index in selected for index in range(3))


def infer_supercell(
    cell: Sequence[Sequence[float]],
    *,
    dimensionality: int = 3,
    periodic_axes: str | Iterable[int] | None = None,
    minimum_length: float = 10.0,
) -> tuple[int, int, int]:
    """Choose diagonal repeats whose periodic vectors exceed ``minimum_length``.

    The strict ``>`` convention is intentional: a vector whose length is
    exactly 10 Angstrom is repeated once more.  Nonperiodic axes remain 1.
    """

    if minimum_length <= 0:
        raise ValueError("minimum_length must be positive")
    vectors = np.asarray(cell, dtype=float)
    if vectors.shape != (3, 3) or not np.all(np.isfinite(vectors)):
        raise ValueError("cell must be a finite 3x3 array")
    lengths = np.linalg.norm(vectors, axis=1)
    if np.any(lengths <= 0):
        raise ValueError("cell vectors must have nonzero lengths")
    axes = parse_periodic_axes(periodic_axes, dimensionality)
    repeats = []
    for length, is_periodic in zip(lengths, axes):
        repeats.append(max(1, math.floor(minimum_length / length) + 1) if is_periodic else 1)
    return tuple(repeats)  # type: ignore[return-value]


def _primitive_dataset(phonon):
    """Return a spglib dataset while accepting old and new spglib APIs."""

    import spglib

    dataset = spglib.get_symmetry_dataset(phonon.primitive.totuple())
    return dataset


def _dataset_value(dataset, key: str):
    if dataset is None:
        return None
    try:
        return getattr(dataset, key)
    except AttributeError:
        try:
            return dataset[key]
        except (KeyError, TypeError):
            return None


def automatic_band_path(
    phonon, npoints: int = 101, *, omit_disconnected_tail: bool = False
):
    """Build a standardized path, optionally omitting a disconnected tail."""

    if npoints < 2:
        raise ValueError("npoints must be at least 2")
    from phonopy.phonon.band_structure import get_band_qpoints_by_seekpath

    qpoints, labels, connections = get_band_qpoints_by_seekpath(
        phonon.primitive, npoints
    )
    if omit_disconnected_tail:
        # Seekpath can append a second, disconnected branch (for example the
        # R-M tail in cubic perovskites). Keep the main path and its labels,
        # while preserving the full automatic path by default.
        first_break = next(
            (index for index, connected in enumerate(connections) if not connected),
            None,
        )
        if first_break is not None and first_break + 1 < len(qpoints):
            keep = first_break + 1
            qpoints = qpoints[:keep]
            labels = labels[: keep + 1]
            connections = connections[:keep]
    dataset = _primitive_dataset(phonon)
    number = _dataset_value(dataset, "number")
    international = _dataset_value(dataset, "international")
    return {
        "qpoints": qpoints,
        "labels": labels,
        "connections": connections,
        "space_group_number": None if number is None else int(number),
        "space_group_symbol": None if international is None else str(international),
        "omitted_disconnected_tail": bool(omit_disconnected_tail),
        "generator": "Seekpath backed by spglib standardization",
    }


def _load_phonon(root: Path, *, nac: bool, born: Path | None, calculator: str):
    from phonopy import load

    yaml_path = root / "phonopy.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Phonopy force-constant archive not found: {yaml_path}")
    kwargs = {
        "phonopy_yaml": str(yaml_path),
        "calculator": calculator,
        "produce_fc": True,
        "is_nac": bool(nac),
    }
    # Phonopy YAML files produced by different versions may either embed the
    # force constants or keep the response in FORCE_CONSTANTS/FORCE_SETS.
    # Select the explicit archive when present so a clean results directory
    # remains independently usable.
    force_constants = root / "FORCE_CONSTANTS"
    force_sets = root / "FORCE_SETS"
    if force_constants.is_file() and force_constants.stat().st_size > 0:
        kwargs["force_constants_filename"] = str(force_constants)
    elif force_sets.is_file() and force_sets.stat().st_size > 0:
        kwargs["force_sets_filename"] = str(force_sets)
    if born is not None:
        kwargs["born_filename"] = str(born)
    return load(**kwargs)


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _continuous_distances(qpoints, connections=None):
    """Convert Phonopy's per-segment q points to one continuous x axis."""

    # Keep disconnected Seekpath segments visually distinct without changing
    # the distances within any physical segment.
    disconnected_gap = 0.25
    result = []
    offset = 0.0
    for index, segment in enumerate(qpoints):
        if index and connections is not None and not connections[index - 1]:
            offset += disconnected_gap
        points = np.asarray(segment, dtype=float)
        local = np.zeros(len(points), dtype=float)
        if len(points) > 1:
            local[1:] = np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))
        result.append(local + offset)
        if len(local):
            offset = float(result[-1][-1])
    return result


def _axis_ticks(distances, labels, connections=None):
    ticks: list[float] = []
    texts: list[str] = []
    label_index = 0
    for index, distance in enumerate(distances):
        if label_index + 1 >= len(labels):
            break
        for position, label in (
            (distance[0], labels[label_index]),
            (distance[-1], labels[label_index + 1]),
        ):
            if ticks and abs(position - ticks[-1]) < 1.0e-9:
                # A connected path shares one endpoint.  Keep one label at
                # that coordinate; joining aliases with ``|`` obscures the
                # continuous high-symmetry path.
                continue
            else:
                ticks.append(float(position))
                texts.append(str(label))
        if connections is not None and index < len(connections) and not connections[index]:
            label_index += 2
        else:
            label_index += 1
    return ticks, texts


def _plot_one(data, path, output: Path, *, color: str, label: str):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    distances = [np.asarray(item) for item in data["distances"]]
    frequencies = [np.asarray(item) for item in data["frequencies"]]
    fig = plt.figure(figsize=(7.2, 4.5))
    grid = fig.add_gridspec(1, 2, width_ratios=(4.1, 1.25), wspace=0.05)
    ax = fig.add_subplot(grid[0, 0])
    dos_ax = fig.add_subplot(grid[0, 1], sharey=ax)
    for distance, freq in zip(distances, frequencies):
        for band_index in range(freq.shape[1]):
            ax.plot(distance, freq[:, band_index], color=color, linewidth=1.1)
    ticks, texts = _axis_ticks(distances, path["labels"], path["connections"])
    ax.set_xticks(ticks)
    ax.set_xticklabels(texts)
    ax.set_ylabel("Frequency (THz)")
    ax.set_xlabel("Wave vector")
    ax.set_ylim(-8.0, 25.0)
    ax.set_xlim(float(distances[0][0]), float(distances[-1][-1]))
    ax.grid(axis="y", color="0.88", linewidth=0.5)
    ax.set_title(label)
    dos_ax.plot(data["total_dos"], data["frequency_points"], color=color, linewidth=1.1)
    dos_ax.set_xlabel("DOS")
    dos_ax.tick_params(labelleft=False)
    dos_ax.set_xlim(left=0)
    for position in ticks:
        ax.axvline(position, color="0.78", linewidth=0.45, zorder=0)
    fig.savefig(output, bbox_inches="tight")
    fig.savefig(output.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_comparison(wo_nac, with_nac, path, output: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    distances = [np.asarray(item) for item in wo_nac["distances"]]
    fig = plt.figure(figsize=(7.2, 4.5))
    grid = fig.add_gridspec(1, 2, width_ratios=(4.1, 1.25), wspace=0.05)
    ax = fig.add_subplot(grid[0, 0])
    dos_ax = fig.add_subplot(grid[0, 1], sharey=ax)
    for data, color, name in (
        (wo_nac, "#3976b5", "without NAC"),
        (with_nac, "#c94c4c", "with NAC"),
    ):
        for path_index, (distance, freq) in enumerate(zip(distances, data["frequencies"])):
            for band_index in range(np.asarray(freq).shape[1]):
                ax.plot(
                    distance,
                    np.asarray(freq)[:, band_index],
                    color=color,
                    linewidth=1.1,
                    label=name if path_index == 0 and band_index == 0 else None,
                )
        dos_ax.plot(data["total_dos"], data["frequency_points"], color=color, linewidth=1.1, label=name)
    ticks, texts = _axis_ticks(distances, path["labels"], path["connections"])
    ax.set_xticks(ticks)
    ax.set_xticklabels(texts)
    ax.set_ylabel("Frequency (THz)")
    ax.set_xlabel("Wave vector")
    ax.set_ylim(-8.0, 25.0)
    ax.set_xlim(float(distances[0][0]), float(distances[-1][-1]))
    ax.grid(axis="y", color="0.88", linewidth=0.5)
    ax.legend(frameon=False, loc="upper left")
    dos_ax.set_xlabel("DOS")
    dos_ax.tick_params(labelleft=False)
    dos_ax.set_xlim(left=0)
    dos_ax.legend(frameon=False, loc="upper right")
    for position in ticks:
        ax.axvline(position, color="0.78", linewidth=0.45, zorder=0)
    fig.savefig(output, bbox_inches="tight")
    fig.savefig(output.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_comparison_band_only(wo_nac, with_nac, path, output: Path):
    """Write a compact NAC comparison containing phonon bands only."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    distances = [np.asarray(item) for item in wo_nac["distances"]]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for data, color, name in (
        (wo_nac, "#3976b5", "without NAC"),
        (with_nac, "#c94c4c", "with NAC"),
    ):
        for path_index, (distance, freq) in enumerate(
            zip(distances, data["frequencies"])
        ):
            freq = np.asarray(freq)
            for band_index in range(freq.shape[1]):
                ax.plot(
                    distance,
                    freq[:, band_index],
                    color=color,
                    linewidth=1.1,
                    label=name if path_index == 0 and band_index == 0 else None,
                )
    ticks, texts = _axis_ticks(distances, path["labels"], path["connections"])
    ax.set_xticks(ticks)
    ax.set_xticklabels(texts)
    ax.set_ylabel("Frequency (THz)")
    ax.set_xlabel("Wave vector")
    ax.set_ylim(-8.0, 25.0)
    ax.set_xlim(float(distances[0][0]), float(distances[-1][-1]))
    ax.grid(axis="y", color="0.88", linewidth=0.5)
    ax.legend(frameon=False, loc="upper left")
    for position in ticks:
        ax.axvline(position, color="0.78", linewidth=0.45, zorder=0)
    fig.savefig(output, bbox_inches="tight")
    fig.savefig(output.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def prepare_phonon_spectrum(
    root: str | Path = ".",
    *,
    structure: str | Path = "STRU",
    supercell: str | Sequence[int] | None = None,
    dimensionality: int = 3,
    periodic_axes: str | Iterable[int] | None = None,
    minimum_length: float = 10.0,
    symm_tol: float = 1.0e-3,
    input_file: str | Path = "INPUT",
    calculator: str = "abacus",
) -> dict:
    """Generate finite-q displacement folders and record the chosen repeat."""

    from .phonon_gen import run_phonopy_and_process_files
    from .shared_response import read_structure

    root_path = Path(root).resolve()
    structure_path = Path(structure)
    if not structure_path.is_absolute():
        structure_path = root_path / structure_path
    atoms = read_structure(structure_path)
    repeats = parse_supercell(supercell) if supercell is not None else infer_supercell(
        atoms.cell,
        dimensionality=dimensionality,
        periodic_axes=periodic_axes,
        minimum_length=minimum_length,
    )
    previous = Path.cwd()
    try:
        import os

        os.chdir(root_path)
        folders = run_phonopy_and_process_files(
            f_stru=str(structure_path),
            symm_tol=symm_tol,
            dim=" ".join(str(item) for item in repeats),
            input_file=input_file,
        )
    finally:
        os.chdir(previous)
    metadata = {
        "schema": "zstar-phonon-spectrum",
        "calculator": calculator,
        "structure": str(structure_path),
        "input_file": str(Path(input_file)),
        "supercell": list(repeats),
        "supercell_source": "user" if supercell is not None else "automatic",
        "minimum_periodic_length_A": minimum_length,
        "periodic_axes": list(parse_periodic_axes(periodic_axes, dimensionality)),
        "symmetry_tolerance": symm_tol,
        "displacement_folders": [str(Path(folder).name) for folder in folders],
        "next": "Run zstar phonon run, then zstar phonon post, then zstar phonon spectrum.",
    }
    (root_path / "phonon_spectrum.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return metadata


def run_phonon_spectrum(
    root: str | Path = ".",
    *,
    calculator: str = "abacus",
    born: str | Path | None = None,
    npoints: int = 101,
    mesh: Sequence[int] = (20, 20, 20),
    require_nac: bool = False,
    no_nac: bool = False,
    band_only: bool = False,
    omit_disconnected_tail: bool = False,
) -> dict:
    """Write band/DOS plots and an optional compact NAC band comparison."""

    root_path = Path(root).resolve()
    yaml_path = root_path / "phonopy.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(
            f"{yaml_path} is missing; complete `zstar phonon post` first"
        )
    if len(mesh) != 3 or any(int(item) < 1 for item in mesh):
        raise ValueError("mesh must contain three positive integers")
    if band_only and no_nac:
        raise ValueError("--band-only requires NAC; do not combine it with --no-nac")
    born_path = Path(born) if born is not None else root_path / "BORN"
    if not born_path.is_absolute():
        born_path = root_path / born_path
    has_born = born_path.is_file() and born_path.stat().st_size > 0
    if require_nac and not has_born:
        raise FileNotFoundError(
            f"NAC was requested but no non-empty BORN file was found at {born_path}"
        )
    if band_only and not has_born:
        raise FileNotFoundError(
            f"--band-only requires a non-empty BORN file at {born_path}"
        )
    phonon_wo = _load_phonon(root_path, nac=False, born=None, calculator=calculator)
    path = automatic_band_path(
        phonon_wo,
        npoints=npoints,
        omit_disconnected_tail=omit_disconnected_tail,
    )
    # Keep the requested DOS mesh explicit rather than hiding it in a CLI call.
    def calculate(phonon):
        phonon.run_band_structure(
            path["qpoints"],
            path_connections=path["connections"],
            labels=path["labels"],
        )
        band = phonon.get_band_structure_dict()
        distances = _continuous_distances(band["qpoints"], path["connections"])
        phonon.init_mesh(list(mesh))
        phonon.run_total_dos()
        dos = phonon.get_total_dos_dict()
        return {
            "distances": distances,
            "frequencies": band["frequencies"],
            "qpoints": band["qpoints"],
            "frequency_points": dos["frequency_points"],
            "total_dos": dos["total_dos"],
        }

    data_wo = calculate(phonon_wo)
    _plot_one(
        data_wo,
        path,
        root_path / "phonon_band_dos_wo_nac.pdf",
        color="#3976b5",
        label="w/o NAC",
    )
    data_with = None
    if has_born and not no_nac:
        phonon_with = _load_phonon(
            root_path, nac=True, born=born_path, calculator=calculator
        )
        data_with = calculate(phonon_with)
        _plot_one(
            data_with,
            path,
            root_path / "phonon_band_dos_with_nac.pdf",
            color="#c94c4c",
            label="with NAC",
        )
        _plot_comparison(
            data_wo,
            data_with,
            path,
            root_path / "phonon_band_dos_nac_comparison.pdf",
        )
        if band_only:
            _plot_comparison_band_only(
                data_wo,
                data_with,
                path,
                root_path / "phonon_band_nac_comparison.pdf",
            )
    elif not no_nac:
        print(f"[WARN] BORN not found at {born_path}; only w/o NAC output was generated.")

    result = {
        "schema": "zstar-phonon-spectrum-result",
        "calculator": calculator,
        "frequency_unit": "THz",
        "nac_available": data_with is not None,
        "nac_source": str(born_path) if data_with is not None else None,
        "npoints": npoints,
        "mesh": list(mesh),
        "band_only": band_only,
        "omit_disconnected_tail": omit_disconnected_tail,
        "space_group_number": path["space_group_number"],
        "space_group_symbol": path["space_group_symbol"],
        "path_generator": path["generator"],
        "labels": path["labels"],
        "wo_nac": data_wo,
        "with_nac": data_with,
        "outputs": [
            "phonon_band_dos_wo_nac.pdf",
            "phonon_band_dos_wo_nac.png",
        ] + (
            [
                "phonon_band_dos_with_nac.pdf",
                "phonon_band_dos_with_nac.png",
                "phonon_band_dos_nac_comparison.pdf",
                "phonon_band_dos_nac_comparison.png",
            ]
            + (
                [
                    "phonon_band_nac_comparison.pdf",
                    "phonon_band_nac_comparison.png",
                ]
                if band_only
                else []
            )
            if data_with is not None
            else []
        ),
    }
    (root_path / "phonon_spectrum_result.json").write_text(
        json.dumps(_jsonable(result), indent=2), encoding="utf-8"
    )
    return result
