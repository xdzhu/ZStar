"""Finite-field line-polarizability derivatives for a z-periodic wire.

The transverse field is applied self-consistently in the DFT calculation.
Its response is read from the periodic Berry polarization or from transverse
real-space dipoles, never from a bare zero-field optical tensor.
"""

from __future__ import annotations

import math
import json
import csv
from pathlib import Path

import numpy as np

from .polarization_1d import integrate_transverse_dipole
from .polarization_2d import (
    BOHR_M,
    ELEMENTARY_CHARGE,
    _parse_pyatb_polarization,
    find_charge_cube,
)
from .shared_response import BOHR_ANGSTROM, read_structure


def unwrap_difference(plus: float, minus: float, quantum: float) -> float:
    """Shortest field-induced polarization difference in C/m^2."""
    if not all(math.isfinite(value) for value in (plus, minus, quantum)) or quantum <= 0:
        raise ValueError("Polarization values and quantum must be finite; quantum > 0")
    delta = plus - minus
    delta -= round(delta / quantum) * quantum
    if abs(delta) >= 0.45 * quantum:
        raise ValueError("Field polarization difference approaches half a quantum")
    return delta


def line_polarizability_a2(
    plus: float,
    minus: float,
    quantum: float,
    *,
    field_au: float,
    volume_a3: float,
    length_a: float,
) -> float:
    """Convert dP_z/dE_transverse to line polarizability in Angstrom^2."""
    if not all(math.isfinite(value) and value > 0 for value in (
        field_au, volume_a3, length_a,
    )):
        raise ValueError("Field, cell volume, and periodic length must be positive")
    delta_p = unwrap_difference(plus, minus, quantum)
    # P_z V / e is a dipole length; atomic field units then yield bohr^3.
    return (
        delta_p / (2.0 * field_au)
        * volume_a3 * 1.0e-30 / (ELEMENTARY_CHARGE * BOHR_M)
        * BOHR_ANGSTROM**3 / length_a
    )


def dipole_line_polarizability_a2(
    plus_e_bohr: float,
    minus_e_bohr: float,
    *,
    field_au: float,
    length_a: float,
) -> float:
    """Convert d(mu_transverse)/dE to line polarizability in Angstrom^2."""
    if not all(math.isfinite(value) for value in (plus_e_bohr, minus_e_bohr)):
        raise ValueError("Dipoles must be finite")
    if not all(math.isfinite(value) and value > 0 for value in (field_au, length_a)):
        raise ValueError("Field and periodic length must be positive")
    return (
        (plus_e_bohr - minus_e_bohr) / (2.0 * field_au)
        * BOHR_ANGSTROM**3 / length_a
    )


def mode_raman_component(
    plus_geometry: tuple[float, float, float],
    minus_geometry: tuple[float, float, float],
    *,
    field_au: float,
    amplitude_a_sqrt_amu: float,
    volume_a3: float,
    length_a: float,
    field_axis: str = "y",
) -> dict[str, float]:
    """Four-point mixed derivative from Berry P_z at E=+/- and Q=+/-."""
    if field_axis not in {"x", "y"}:
        raise ValueError("Field axis must be transverse x or y")
    if not math.isfinite(amplitude_a_sqrt_amu) or amplitude_a_sqrt_amu <= 0:
        raise ValueError("Mode amplitude must be positive")
    alpha_plus = line_polarizability_a2(
        *plus_geometry, field_au=field_au,
        volume_a3=volume_a3, length_a=length_a,
    )
    alpha_minus = line_polarizability_a2(
        *minus_geometry, field_au=field_au,
        volume_a3=volume_a3, length_a=length_a,
    )
    return {
        "alpha_mode_plus_a2": alpha_plus,
        "alpha_mode_minus_a2": alpha_minus,
        f"raman_z{field_axis}_a_per_sqrt_amu": (
            alpha_plus - alpha_minus
        ) / (2.0 * amplitude_a_sqrt_amu),
    }


def assemble_screened_line_tensor(
    field_derivatives: np.ndarray,
    *,
    axial_zz: float,
) -> tuple[np.ndarray, float]:
    """Assemble d(alpha_line)/dQ from x/y field columns and an axial zz value.

    ``field_derivatives[response_axis, field_axis]`` has shape (3, 2).
    Reciprocal off-diagonal components are averaged for xy and copied for xz/yz.
    The axial zz value retains its separately supplied response approximation.
    """
    raw = np.asarray(field_derivatives, dtype=float)
    if raw.shape != (3, 2) or not np.all(np.isfinite(raw)):
        raise ValueError("Finite-field derivatives must be a finite (3, 2) array")
    if not math.isfinite(axial_zz):
        raise ValueError("The axial zz Raman derivative must be finite")
    tensor = np.zeros((3, 3), dtype=float)
    tensor[:, :2] = raw
    xy_residual = float(raw[0, 1] - raw[1, 0])
    tensor[0, 1] = tensor[1, 0] = 0.5 * (raw[0, 1] + raw[1, 0])
    tensor[0, 2] = raw[2, 0]
    tensor[1, 2] = raw[2, 1]
    tensor[2, 2] = float(axial_zz)
    return tensor, xy_residual


def cube_mantissa_digits(path: str | Path) -> int:
    """Count printed fractional digits in an ABACUS charge-density cube."""
    with Path(path).open(encoding="utf-8", errors="replace") as stream:
        next(stream)
        next(stream)
        natoms = int(next(stream).split()[0])
        if natoms <= 0:
            raise ValueError(f"Expected a standard positive-atom-count cube: {path}")
        for _ in range(3 + natoms):
            next(stream)
        token = next(stream).split()[0]
    mantissa = token.lower().split("e", 1)[0]
    if "." not in mantissa:
        raise ValueError(f"Cube density is not printed as a decimal: {path}")
    return len(mantissa.split(".", 1)[1])


def require_cube_precision(path: str | Path, minimum_digits: int = 10) -> None:
    digits = cube_mantissa_digits(path)
    if digits < minimum_digits:
        raise ValueError(
            f"Charge-density cube has only {digits} mantissa digits; "
            f"at least {minimum_digits} are required for finite-field Raman: {path}"
        )


def _field_pair_berry(stage_root: Path, geometry: str) -> tuple[float, float, float]:
    values: list[float] = []
    quanta: list[float] = []
    for sign in ("plus", "minus"):
        path = (
            stage_root / "states" / geometry / f"field_{sign}"
            / "pyatb-field-polar/Out/Polarization/polarization.dat"
        )
        polarization, quantum = _parse_pyatb_polarization(path)
        values.append(float(polarization[2]))
        quanta.append(float(quantum[2]))
    if not np.isclose(quanta[0], quanta[1], rtol=1.0e-4, atol=0.0):
        raise ValueError(f"Polarization quanta disagree for {geometry}")
    return values[0], values[1], 0.5 * sum(quanta)


def _field_alpha(
    root: Path,
    geometry: str,
    *,
    field_au: float,
    volume_a3: float,
    length_a: float,
    unwrap_centers_bohr: dict[str, float],
    minimum_cube_digits: int,
) -> np.ndarray:
    field_stages = [root / "states" / geometry / f"field_{sign}" for sign in ("plus", "minus")]
    cubes = [find_charge_cube(stage) for stage in field_stages]
    for cube in cubes:
        require_cube_precision(cube, minimum_cube_digits)
    alpha = np.zeros(3, dtype=float)
    for index, axis in enumerate(("x", "y")):
        dipoles = [
            integrate_transverse_dipole(
                cube, axis, unwrap_center_bohr=unwrap_centers_bohr[axis]
            ).dipole_e_bohr
            for cube in cubes
        ]
        alpha[index] = dipole_line_polarizability_a2(
            dipoles[0], dipoles[1], field_au=field_au, length_a=length_a
        )
    alpha[2] = line_polarizability_a2(
        *_field_pair_berry(root, geometry), field_au=field_au,
        volume_a3=volume_a3, length_a=length_a,
    )
    return alpha


def collect_screened_1d_raman_tensors(
    x_probe: str | Path,
    y_probe: str | Path,
    structure: str | Path,
    mode_numbers: np.ndarray,
    zero_field_tensors: np.ndarray,
    *,
    minimum_cube_digits: int = 10,
) -> tuple[np.ndarray, dict]:
    """Replace transverse Raman responses with self-consistent field derivatives.

    The wire must be periodic along positive Cartesian z with orthorhombic
    vacuum directions. The supplied zero-field tensors contribute only zz;
    this routine does not claim a screened axial response.
    """
    roots = {"x": Path(x_probe), "y": Path(y_probe)}
    manifests = {
        axis: json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for axis, root in roots.items()
    }
    for axis in ("x", "y"):
        if manifests[axis].get("field_axis") != axis:
            raise ValueError(f"Expected a {axis}-field manifest in {roots[axis]}")
        digits = int(manifests[axis].get("cube_digits", 0))
        if digits < minimum_cube_digits:
            raise ValueError(
                f"{axis}-field manifest specifies {digits} cube digits; "
                f"at least {minimum_cube_digits} are required"
            )
    field_au = float(manifests["x"]["field_au"])
    amplitude = float(manifests["x"]["mode_amplitude_A_sqrt_amu"])
    for key in ("field_au", "mode_amplitude_A_sqrt_amu"):
        if not np.isclose(float(manifests["x"][key]), float(manifests["y"][key]), rtol=1e-8):
            raise ValueError(f"x/y finite-field manifests disagree on {key}")
    if not math.isfinite(amplitude) or amplitude <= 0:
        raise ValueError("Mode amplitude must be positive")
    if not math.isfinite(field_au) or field_au <= 0:
        raise ValueError("Field magnitude must be positive")
    cell = np.asarray(read_structure(structure).cell, dtype=float)
    if not np.allclose(cell, np.diag(np.diag(cell)), atol=1e-6) or np.any(np.diag(cell) <= 0):
        raise ValueError("Screened 1D Raman requires a positive orthorhombic z-periodic cell")
    volume_a3 = float(abs(np.linalg.det(cell)))
    length_a = float(cell[2, 2])
    numbers = np.asarray(mode_numbers, dtype=int)
    original = np.asarray(zero_field_tensors, dtype=float)
    if original.shape != (len(numbers), 3, 3) or len(set(numbers)) != len(numbers):
        raise ValueError("Mode numbers and zero-field tensor shapes are inconsistent")
    manifest_numbers = {
        axis: {
            int(stage["geometry"].split("/")[0].split("-")[1])
            for stage in manifest["stages"]
            if stage["geometry"].startswith("mode-")
        }
        for axis, manifest in manifests.items()
    }
    for axis, available in manifest_numbers.items():
        missing = set(numbers) - available
        if missing:
            raise ValueError(f"{axis}-field manifest lacks modes {sorted(missing)}")
    reference_cube = find_charge_cube(roots["x"] / "states/reference/field_plus")
    require_cube_precision(reference_cube, minimum_cube_digits)
    centers = {
        axis: integrate_transverse_dipole(reference_cube, axis).unwrap_center_bohr
        for axis in ("x", "y")
    }
    tensors = np.zeros_like(original)
    xy_residuals: dict[str, float] = {}
    for position, mode in enumerate(numbers):
        derivative = np.zeros((3, 2), dtype=float)
        for field_index, axis in enumerate(("x", "y")):
            values = [
                _field_alpha(
                    roots[axis], f"mode-{mode:04d}/{sign}",
                    field_au=field_au, volume_a3=volume_a3,
                    length_a=length_a, unwrap_centers_bohr=centers,
                    minimum_cube_digits=minimum_cube_digits,
                )
                for sign in ("plus", "minus")
            ]
            derivative[:, field_index] = (values[0] - values[1]) / (2.0 * amplitude)
        tensors[position], xy_residual = assemble_screened_line_tensor(
            derivative, axial_zz=float(original[position, 2, 2])
        )
        xy_residuals[str(mode)] = xy_residual
    metadata = {
        "method": "self-consistent transverse finite field plus Berry/real-space response",
        "dimensionality": 1,
        "periodic_axis": "z",
        "transverse_components": "screened finite-field ABACUS response",
        "axial_zz_component": "original zero-field PYATB response; not field-screened",
        "field_au": field_au,
        "mode_amplitude_A_sqrt_amu": amplitude,
        "minimum_cube_mantissa_digits": minimum_cube_digits,
        "mode_numbers": numbers.tolist(),
        "xy_reciprocity_residual_A_per_sqrt_amu": xy_residuals,
    }
    return tensors, metadata


def load_bare_raman_csv(
    path: str | Path, selected_modes: list[int] | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Read the zero-field Raman table used for the axial 1D component."""
    with Path(path).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    by_mode: dict[int, np.ndarray] = {}
    for row in rows:
        mode = int(row["mode"])
        if mode in by_mode:
            raise ValueError(f"Duplicate zero-field Raman mode {mode}")
        by_mode[mode] = np.asarray([
            [float(row[f"R{first}{second}"]) for second in "xyz"]
            for first in "xyz"
        ], dtype=float)
    numbers = selected_modes if selected_modes is not None else sorted(by_mode)
    if not numbers or len(set(numbers)) != len(numbers):
        raise ValueError("Select at least one distinct Raman mode")
    missing = set(numbers) - by_mode.keys()
    if missing:
        raise ValueError(f"Zero-field Raman CSV lacks modes {sorted(missing)}")
    tensors = np.asarray([by_mode[mode] for mode in numbers], dtype=float)
    if not np.all(np.isfinite(tensors)):
        raise ValueError("Zero-field Raman tensors must be finite")
    return np.asarray(numbers, dtype=int), tensors


def write_screened_1d_raman_outputs(
    output_dir: str | Path,
    mode_numbers: np.ndarray,
    tensors: np.ndarray,
    metadata: dict,
) -> Path:
    """Write mode-indexed tensors for the existing ``zstar raman spectrum`` path."""
    output = Path(output_dir).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory must be empty: {output}")
    numbers = np.asarray(mode_numbers, dtype=int)
    values = np.asarray(tensors, dtype=float)
    if values.shape != (len(numbers), 3, 3) or not np.all(np.isfinite(values)):
        raise ValueError("Screened Raman tensors must be finite 3x3 mode tensors")
    output.mkdir(parents=True, exist_ok=True)
    document = dict(metadata)
    document["mode_numbers"] = numbers.tolist()
    document["tensor_kind"] = "1D transverse screened Raman; axial zz from zero-field PYATB"
    document["tensors"] = values.tolist()
    (output / "raman_tensors.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    np.save(output / "raman_tensors.npy", values)
    fieldnames = ["mode", *[f"R{first}{second}" for first in "xyz" for second in "xyz"]]
    with (output / "raman_tensors.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for mode, tensor in zip(numbers, values):
            row = {"mode": int(mode)}
            row.update({
                f"R{first}{second}": float(tensor[i, j])
                for i, first in enumerate("xyz")
                for j, second in enumerate("xyz")
            })
            writer.writerow(row)
    return output
