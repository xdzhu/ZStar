"""Static bulk electro-optic response from matched optical-mode data."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .raman_response import internal_mode_indices
from .spectra import (
    ATOMIC_MASS_UNIT,
    ELEMENTARY_CHARGE,
    VACUUM_PERMITTIVITY,
    load_gamma_modes,
    mode_effective_charges,
    read_born_data,
)


def _array(value, shape, name):
    values = np.asarray(value, dtype=float)
    if values.shape != shape or not np.isfinite(values).all():
        raise ValueError(f"{name} must contain finite values with shape {shape}")
    return values


def _dielectric(value):
    dielectric = _array(value, (3, 3), "electronic relative permittivity")
    if not np.allclose(dielectric, dielectric.T, rtol=0, atol=2e-5):
        raise ValueError("Electronic relative permittivity must be symmetric")
    dielectric = (dielectric + dielectric.T) / 2
    if np.linalg.eigvalsh(dielectric).min() <= 0:
        raise ValueError("Electronic relative permittivity must be positive definite")
    return dielectric


def _mode_inputs(frequencies_thz, mode_charges, raman):
    frequencies = np.asarray(frequencies_thz, dtype=float)
    if (frequencies.ndim != 1 or not frequencies.size
            or not np.isfinite(frequencies).all() or np.any(frequencies <= 0)):
        raise ValueError("Provide positive Gamma optical frequencies in THz")
    charges = _array(mode_charges, (len(frequencies), 3), "mode charges")
    tensors = _array(raman, (len(frequencies), 3, 3), "bulk Raman tensors")
    if not np.allclose(tensors, tensors.swapaxes(1, 2), rtol=0, atol=2e-5):
        raise ValueError("Bulk Raman tensors must be symmetric")
    return frequencies, charges, (tensors + tensors.swapaxes(1, 2)) / 2


def _chi2_pm_per_v(value):
    chi2 = _array(value, (3, 3, 3), "static electronic chi2")
    if not all(np.allclose(chi2, other, rtol=1e-8, atol=1e-10)
               for other in (chi2.swapaxes(0, 1), chi2.swapaxes(1, 2))):
        raise ValueError("Static electronic chi2 must have permutation symmetry")
    return chi2


def electrooptic(frequencies_thz, mode_charges, raman, epsilon, *,
                 chi2_pm_v=None, photoelastic=None, piezoelectric_pm_v=None):
    """Return inverse-permittivity derivatives with axes (i, j, field), pm/V.

    Inputs use Z in e/sqrt(amu), Raman d epsilon / dQ in
    1/(angstrom sqrt(amu)), and the static SI convention P(2) = epsilon_0 chi2 E E.
    Photoelastic axes are (i, j, engineering Voigt strain). The piezoelectric
    coefficient maps static electric field to the matching six strain components.
    """
    frequencies, charges, tensors = _mode_inputs(frequencies_thz, mode_charges, raman)
    inverse = np.linalg.inv(_dielectric(epsilon))
    angular = 2 * np.pi * 1e12 * frequencies
    scale = 1e12 * ELEMENTARY_CHARGE / (1e-10 * ATOMIC_MASS_UNIT)
    optical_derivative = scale * np.einsum("mij,mk,m->ijk", tensors, charges, angular**-2)
    ionic = -np.einsum("ia,abk,bj->ijk", inverse, optical_derivative, inverse)
    result = {"ionic_fixed_strain": ionic}
    if chi2_pm_v is not None:
        chi2 = _chi2_pm_per_v(chi2_pm_v)
        electronic = -2 * np.einsum("ia,abk,bj->ijk", inverse, chi2, inverse)
        result.update(electronic_clamped_ion=electronic, total_fixed_strain=electronic + ionic)
    if photoelastic is not None or piezoelectric_pm_v is not None:
        if photoelastic is None or piezoelectric_pm_v is None:
            raise ValueError("Relaxed-stress response requires both photoelastic and piezoelectric tensors")
        if chi2_pm_v is None:
            raise ValueError("Relaxed-stress total requires the electronic chi2")
        p = _array(photoelastic, (3, 3, 6), "relaxed-ion photoelastic tensor")
        d = _array(piezoelectric_pm_v, (6, 3), "piezoelectric strain tensor")
        strain = np.einsum("ijv,vk->ijk", p, d)
        result.update(piezoelectric_relaxation=strain,
                      total_relaxed_stress=result["total_fixed_strain"] + strain)
    return result


def longitudinal_raman(frequencies_thz, mode_charges, raman, epsilon,
                       volume_angstrom3, direction, chi2_pm_v):
    """Return the bulk long-wavelength directional optical spectrum.

    Diagonalize the dipole-dipole dynamical correction in the zero-field
    optical-mode basis. Apply the macroscopic field correction to the Raman
    tensors in the same basis before rotating them to the new modes.
    """
    frequencies, charges, tensors = _mode_inputs(frequencies_thz, mode_charges, raman)
    dielectric = _dielectric(epsilon)
    chi2 = _chi2_pm_per_v(chi2_pm_v)
    direction = _array(direction, (3,), "Cartesian propagation direction")
    norm = np.linalg.norm(direction)
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("Propagation direction must have finite nonzero length")
    if not np.isfinite(volume_angstrom3) or volume_angstrom3 <= 0:
        raise ValueError("Cell volume must be positive in cubic angstroms")
    axis = direction / norm
    projections = charges @ axis
    electrostatic = VACUUM_PERMITTIVITY * volume_angstrom3 * 1e-30 * (axis @ dielectric @ axis)
    dynamical_scale = ELEMENTARY_CHARGE**2 / (electrostatic * ATOMIC_MASS_UNIT * (2 * np.pi * 1e12)**2)
    eigenvalues, rotation = np.linalg.eigh(
        np.diag(frequencies**2) + dynamical_scale * np.outer(projections, projections)
    )
    field = -ELEMENTARY_CHARGE * 1e-10 * projections / electrostatic
    delta = np.einsum("ijk,k,m->mij", 2e-12 * chi2, axis, field)
    return {
        "frequencies_THz": np.sqrt(eigenvalues),
        "mode_charges_e_sqrt_amu": rotation.T @ charges,
        "raman_derivatives": np.einsum("mn,mij->nij", rotation, tensors + delta),
        "mode_rotation_columns": rotation,
    }


def _read_mode_raman(path, modes, selected):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    by_mode = {int(row["mode"]): row for row in rows}
    if len(by_mode) != len(rows) or set(by_mode) != set(selected + 1):
        raise ValueError("Raman mode IDs must match the full Gamma optical mode list")
    frequencies = np.array([float(by_mode[i]["frequency_cm-1"]) for i in selected + 1])
    if not np.allclose(frequencies, modes.frequencies_cm1[selected], atol=0.1, rtol=0):
        raise ValueError("Raman frequencies do not match the supplied Gamma modes")
    keys = [f"R{i}{j}" for i in "xyz" for j in "xyz"]
    return np.array([[float(by_mode[i][key]) for key in keys]
                     for i in selected + 1]).reshape(-1, 3, 3)


def run_electrooptic_cli(argv):
    parser = argparse.ArgumentParser(prog="zstar dielectric electrooptic", description=__doc__)
    parser.add_argument("--qpoints", type=Path, required=True, help="Bulk Gamma TO mode file")
    parser.add_argument("--born", type=Path, required=True, help="Matched BECs and electronic permittivity")
    parser.add_argument("--raman", type=Path, required=True, help="Matched bulk Raman mode CSV in 1/(angstrom sqrt(amu))")
    parser.add_argument("--chi2", type=Path, help="Static electronic chi2 JSON, pm/V, P(2) = epsilon_0 chi2 E E")
    parser.add_argument("--photoelastic", type=Path, help="Relaxed-ion inverse permittivity derivative vs Voigt strain")
    parser.add_argument("--piezoelectric", type=Path, help="Engineering Voigt strain by Cartesian field in pm/V")
    parser.add_argument("--direction", type=float, nargs=3, help="Also calculate bulk LO Raman for this Cartesian direction")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.direction is not None and args.chi2 is None:
        parser.error("--direction requires --chi2")

    def read(path):
        return json.loads(path.read_text(encoding="utf-8-sig")) if path is not None else None

    modes = load_gamma_modes(args.qpoints)
    selected, _ = internal_mode_indices(modes, 3)
    born = read_born_data(args.born, natoms=len(modes.masses_amu))
    if born.electronic_dielectric is None:
        parser.error("--born must include the electronic dielectric tensor")
    frequency = modes.frequencies_thz[selected]
    charges = mode_effective_charges(modes, born.tensors)[selected]
    raman = _read_mode_raman(args.raman, modes, selected)
    chi2 = read(args.chi2)
    tensors = electrooptic(
        frequency, charges, raman, born.electronic_dielectric, chi2_pm_v=chi2,
        photoelastic=read(args.photoelastic), piezoelectric_pm_v=read(args.piezoelectric),
    )
    result = {
        "mode_ids": (selected + 1).tolist(),
        "electrooptic_axes": ["optical_row", "optical_column", "static_field"],
        "electrooptic_unit": "pm/V",
        "electrooptic": {name: values.tolist() for name, values in tensors.items()},
    }
    if args.direction is not None:
        longitudinal = longitudinal_raman(
            frequency, charges, raman, born.electronic_dielectric,
            modes.volume_angstrom3, args.direction, chi2,
        )
        result["directional_raman"] = {
            "direction_cartesian": args.direction,
            "raman_derivative_unit": "1/(angstrom sqrt(amu))",
            **{name: values.tolist() for name, values in longitudinal.items()},
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"[OUT] {args.output}")


def finite_field_chi2(field_step_v_m, directions, zero_c_m2, plus_c_m2, minus_c_m2):
    """Fit the static SI susceptibility from pairs of clamped-ion polarizations.

    A direction v gives fields +field_step*v and -field_step*v. Leave all
    polarizations on a continuous branch. Output is chi2 in pm/V for
    P(2)_i = epsilon_0 * sum_jk chi2_ijk E_j E_k.
    """
    step = float(field_step_v_m)
    if not np.isfinite(step) or step <= 0:
        raise ValueError("The field step must be positive and finite")
    axes = np.asarray(directions, dtype=float)
    if axes.ndim != 2 or axes.shape[1] != 3 or not np.isfinite(axes).all():
        raise ValueError("Field directions must have shape (n, 3) and be finite")
    x, y, z = axes.T
    design = np.column_stack((x*x, y*y, z*z, 2*y*z, 2*x*z, 2*x*y))
    zero = _array(zero_c_m2, (3,), "zero-field polarization")
    plus = _array(plus_c_m2, axes.shape, "positive-field polarizations")
    minus = _array(minus_c_m2, axes.shape, "negative-field polarizations")
    even = (plus - zero) + (minus - zero)
    scale = 2 * VACUUM_PERMITTIVITY * step**2
    coefficients, _, rank, _ = np.linalg.lstsq(design, even, rcond=None)
    if rank != 6:
        raise ValueError("Field directions do not span the six symmetric quadratic terms")
    fit = (coefficients.T / scale) * 1e12
    raw = fit[:, [[0, 5, 4], [5, 1, 3], [4, 3, 2]]]
    # Static lossless response is symmetric in all three Cartesian indices.
    chi2 = (raw + raw.transpose(1, 0, 2) + raw.transpose(1, 2, 0)) / 3
    diagnostic = {
        "maximum_permutation_correction_pm_V": float(np.max(abs(chi2 - raw))),
        "maximum_even_polarization_fit_residual_C_m2": float(np.max(abs(design @ coefficients - even))),
    }
    return chi2, diagnostic


def run_chi2_cli(argv):
    parser = argparse.ArgumentParser(prog="zstar dielectric chi2",
                                     description="Get static electronic chi2 from finite-field polarization.")
    parser.add_argument("--input", type=Path, required=True, help="JSON containing paired field polarizations")
    parser.add_argument("--output", type=Path, required=True, help="Write the 3×3×3 chi2 tensor in pm/V")
    args = parser.parse_args(argv)
    data = json.loads(args.input.read_text(encoding="utf-8-sig"))
    tensor, diagnostic = finite_field_chi2(
        data["field_step_V_m"], data["directions"], data["zero_C_m2"],
        data["plus_C_m2"], data["minus_C_m2"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(tensor.tolist(), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(diagnostic, allow_nan=False))
    print(f"[OUT] {args.output}")
