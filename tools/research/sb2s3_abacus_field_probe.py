"""Prepare an isolated-wire finite-field response probe without running DFT."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from zstar.shared_response import read_structure
from zstar.spectra import load_gamma_modes, prepare_raman_displacements
from zstar.workflow import _set_abacus_parameter


def _check_drop_in_vacuum(structure: Path, axis: int, start: float, width: float) -> None:
    fractional = read_structure(structure).scaled_positions[:, axis] % 1.0
    # Keep the potential's steep return ramp away from every ionic center.
    for position in fractional:
        distance = (float(position) - start) % 1.0
        if distance < width + 0.05 or distance > 0.95:
            raise ValueError(
                f"The field return ramp is too close to an atom in {structure}: "
                f"fractional coordinate {position:.4f}"
            )


def prepare(
    case: Path,
    output: Path,
    *,
    mode_numbers: list[int],
    field_au: float,
    amplitude: float,
    axis: int,
    ramp_start: float,
    ramp_width: float,
    cube_digits: int = 12,
    out_dipole: bool = True,
) -> dict:
    if not 0 < field_au <= 0.002:
        raise ValueError("field_au must be in (0, 0.002]")
    if not mode_numbers or len(mode_numbers) != len(set(mode_numbers)):
        raise ValueError("Specify at least one distinct mode number")
    if amplitude <= 0:
        raise ValueError("amplitude must be positive")
    if axis not in (0, 1):
        raise ValueError("The sawtooth field is restricted to an open x/y direction")
    if not 0 < ramp_start < 1 or not 0 < ramp_width < 1 - ramp_start:
        raise ValueError("The return ramp must fit within the transverse vacuum")
    if not 6 <= cube_digits <= 16:
        raise ValueError("cube_digits must be between 6 and 16")
    if output.exists():
        raise FileExistsError(f"Choose a fresh probe directory: {output}")

    source = case / "run"
    _check_drop_in_vacuum(source / "STRU", axis, ramp_start, ramp_width)
    assets = [source / "KPT", *sorted(source.glob("*.upf")), *sorted(source.glob("*.orb"))]
    if len(assets) < 5 or any(not path.is_file() for path in assets):
        raise FileNotFoundError("Missing KPT, pseudopotentials, or orbitals in case/run")
    modes = load_gamma_modes(case / "results/qpoints.yaml")
    output.mkdir(parents=True)
    displaced = prepare_raman_displacements(
        source / "STRU", modes, output / "seed_modes",
        amplitude=amplitude, mode_numbers=mode_numbers,
    )
    geometries = [("reference", source / "STRU")]
    for entry in displaced["modes"]:
        for sign in ("plus", "minus"):
            geometries.append(
                (f"mode-{entry['mode']:04d}/{sign}", Path(entry[sign]) / "STRU")
            )

    input_text = (source / "INPUT").read_text(encoding="utf-8")
    parameters = {
        "calculation": "scf",
        "cal_force": "0",
        "cal_stress": "0",
        "init_chg": "auto",
        "symmetry": "0",
        "efield_flag": "1",
        "dip_cor_flag": "0",
        "efield_dir": str(axis),
        "efield_pos_max": f"{ramp_start:.12g}",
        "efield_pos_dec": f"{ramp_width:.12g}",
        "out_chg": f"1 {cube_digits}",
        "out_dipole": "1" if out_dipole else "0",
        "out_mat_hs2": "1",
        "out_mat_r": "1",
    }
    for key, value in parameters.items():
        input_text = _set_abacus_parameter(input_text, key, value)

    stages = []
    for name, stru in geometries:
        _check_drop_in_vacuum(stru, axis, ramp_start, ramp_width)
        for sign, signed_field in (("plus", field_au), ("minus", -field_au)):
            stage = output / "states" / name / f"field_{sign}"
            stage.mkdir(parents=True)
            shutil.copy2(stru, stage / "STRU")
            for asset in assets:
                shutil.copy2(asset, stage / asset.name)
            (stage / "INPUT").write_text(
                _set_abacus_parameter(input_text, "efield_amp", f"{signed_field:.12g}"),
                encoding="utf-8",
            )
            stages.append({
                "geometry": name,
                "field_sign": sign,
                "field_au": signed_field,
                "relative_path": str(stage.relative_to(output)).replace("\\", "/"),
            })
    manifest = {
        "schema": 1,
        "purpose": "Sb2S3 transverse finite-field SCF and periodic-z polarization probe",
        "case": str(case.resolve()),
        "field_axis": "xy"[axis],
        "field_au": field_au,
        "mode_amplitude_A_sqrt_amu": amplitude,
        "ramp_start_fractional": ramp_start,
        "ramp_width_fractional": ramp_width,
        "dipole_correction": False,
        "cube_digits": cube_digits,
        "out_dipole": out_dipole,
        "stages": stages,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", type=int, action="append", default=[])
    parser.add_argument(
        "--all-optical", action="store_true",
        help="Select every Gamma mode above the acoustic cutoff instead of --mode.",
    )
    parser.add_argument("--acoustic-cutoff", type=float, default=5.0)
    parser.add_argument("--field-au", type=float, default=0.0005)
    parser.add_argument("--amplitude", type=float, default=0.02)
    parser.add_argument("--axis", choices=("x", "y"), default="y")
    parser.add_argument("--ramp-start", type=float, default=0.85)
    parser.add_argument("--ramp-width", type=float, default=0.10)
    parser.add_argument("--cube-digits", type=int, default=12)
    parser.add_argument("--no-out-dipole", action="store_true")
    args = parser.parse_args()
    if args.all_optical and args.mode:
        parser.error("--all-optical and --mode cannot be combined")
    selected_modes = args.mode
    if args.all_optical:
        modes = load_gamma_modes(args.case / "results/qpoints.yaml")
        selected_modes = [
            index + 1
            for index, frequency in enumerate(modes.frequencies_cm1)
            if frequency > args.acoustic_cutoff
        ]
    result = prepare(
        args.case.resolve(), args.output.resolve(),
        mode_numbers=selected_modes, field_au=args.field_au,
        amplitude=args.amplitude, axis="xy".index(args.axis),
        ramp_start=args.ramp_start, ramp_width=args.ramp_width,
        cube_digits=args.cube_digits, out_dipole=not args.no_out_dipole,
    )
    print(f"Prepared {len(result['stages'])} finite-field SCF stages")


if __name__ == "__main__":
    main()
