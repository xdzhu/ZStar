"""Collect VASP-native responses without imposing the ABACUS sampling method."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
import re

import numpy as np
import yaml


VASP_VOIGT = ("xx", "yy", "zz", "xy", "yz", "zx")
ENGINEERING_VOIGT = ("xx", "yy", "zz", "yz", "xz", "xy")
_ORDER = (0, 1, 2, 4, 5, 3)


def append_native_quantities(path: str | Path, native: dict) -> None:
    """Enrich the common response record, retaining explicit native conventions."""
    from .response_schema import ResponseQuantity, ResponseRecord

    record = ResponseRecord.read(path)
    bulk = record.dimensionality.value == 3
    normalization = "bulk_cell_volume" if bulk else "periodic_supercell_volume"
    specifications = {
        "epsilon_ph": ("phonon_dielectric", "1", ("polarization", "field")),
        "epsilon_static": ("static_dielectric", "1", ("polarization", "field")),
        "piezoelectric_clamped_C_m2": ("piezoelectric_clamped", "C/m^2", ("polarization", "voigt_engineering")),
        "piezoelectric_ionic_C_m2": ("piezoelectric_internal", "C/m^2", ("polarization", "voigt_engineering")),
        "piezoelectric_total_C_m2": ("piezoelectric_relaxed", "C/m^2", ("polarization", "voigt_engineering")),
        "elastic_clamped_GPa": ("elastic", "GPa", ("stress_voigt", "voigt_engineering")),
        "elastic_ionic_GPa": ("elastic_internal_contribution", "GPa", ("stress_voigt", "voigt_engineering")),
        "elastic_relaxed_GPa": ("elastic_relaxed", "GPa", ("stress_voigt", "voigt_engineering")),
        "piezoelectric_d_pm_V": ("piezoelectric_d", "pm/V", ("polarization", "stress_voigt")),
        "internal_strain_eV_per_A": ("native_internal_strain", "eV/angstrom", ("atom", "displacement", "voigt_engineering")),
        "internal_strain_from_strained_cells_eV_per_A": ("native_internal_strain_from_strained_cells", "eV/angstrom", ("atom", "displacement", "voigt_engineering")),
    }
    additional = []
    for key, (name, unit, axes) in specifications.items():
        if key not in native["tensors"]:
            continue
        mechanical_boundary = (
            "prescribed stress; internal ions relaxed" if key == "piezoelectric_d_pm_V"
            else "prescribed strain; ions clamped" if "clamped" in key
            else "fixed strain" if key.startswith("epsilon_")
            else "ions clamped; mixed displacement/strain derivative" if key.startswith("internal_strain_")
            else "prescribed strain; internal ionic contribution" if "ionic" in key
            else "prescribed strain; internal ions relaxed"
        )
        additional.append(ResponseQuantity(
            name=name if bulk else f"supercell_{name}", values=native["tensors"][key],
            unit=unit, normalization="none" if key.startswith("internal_strain_") or key == "piezoelectric_d_pm_V" else normalization,
            axes=axes, source=native["source"],
            convention="native VASP; engineering Voigt xx,yy,zz,yz,xz,xy; no improper-to-proper recorrection",
            metadata={
                "electric_boundary": native["electric_boundary"],
                "mechanical_boundary": mechanical_boundary,
                "intrinsic_low_dimensional_response_required": not bulk,
                "voigt_convention": list(ENGINEERING_VOIGT),
                "solver_provenance": native.get("solver_provenance", {}),
                **({"derivation": "d = e C^-1 using native relaxed-ion tensors; GPa to Pa conversion"}
                   if key == "piezoelectric_d_pm_V" else {}),
                **({"derivative_kind": "native force-strain coupling, not relaxed displacement per strain"}
                   if key.startswith("internal_strain_") else {}),
            },
        ))
    # A newly rejected derivative must not survive from an earlier collection.
    names = {name for name, _, _ in specifications.values()}
    names |= {f"supercell_{name}" for name in names}
    quantities = tuple(quantity for quantity in record.quantities if quantity.name not in names) + tuple(additional)
    replace(record, quantities=quantities,
            metadata={**record.metadata, "native_response_diagnostics": native["diagnostics"]}).write(path)


def write_vasp_born_for_phonopy(poscar: Path, epsilon: np.ndarray, born: np.ndarray, destination: Path) -> None:
    from phonopy.structure.atoms import PhonopyAtoms
    from phonopy.structure.symmetry import Symmetry
    from .structure_io import read_structure

    structure = read_structure(poscar)
    cell = PhonopyAtoms(symbols=structure.symbols, cell=structure.lattice_angstrom,
                        scaled_positions=structure.positions_fractional)
    independent = Symmetry(cell, symprec=1e-5).get_independent_atoms()
    rows = ["# ZStar native VASP response: Z[polarization,displacement]; units e"]
    rows.append(" ".join(f"{value:.10f}" for value in epsilon.ravel()))
    rows.extend(" ".join(f"{value:.10f}" for value in born[i].T.ravel()) for i in independent)
    destination.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _table(lines: list[str], start: int, rows: int, columns: int) -> np.ndarray:
    values = []
    for line in lines[start + 1:start + 18]:
        fields = line.split()
        if len(fields) == columns + 1 and fields[0].lower() in {"x", "y", "z", *VASP_VOIGT}:
            fields = fields[1:]
        if len(fields) != columns:
            continue
        try:
            row = [float(x.replace("D", "E").replace("d", "e")) for x in fields]
        except ValueError:
            continue
        values.append(row)
        if len(values) == rows:
            matrix = np.asarray(values)
            if not np.all(np.isfinite(matrix)):
                raise ValueError(f"Non-finite VASP response below {lines[start].strip()}")
            return matrix
    raise ValueError(f"Incomplete VASP response table below {lines[start].strip()}")


def parse_native_tensors(path: str | Path) -> dict:
    """Read native ionic dielectric, piezoelectric and elastic output blocks.

    Piezoelectric rows are electric-field directions. Columns are reordered
    from VASP's xx,yy,zz,xy,yz,zx to engineering xx,yy,zz,yz,xz,xy.
    Native piezoelectric output is not corrected a second time as an improper
    finite-polarization derivative.
    """
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    result = {}
    internal_strains = {}
    strain_source = "displaced_atoms"
    for i, line in enumerate(lines):
        title = line.upper()
        if "INTERNAL STRAIN TENSORS FROM STRAINED CELLS" in title:
            strain_source = "strained_cells"
        elif "INTERNAL STRAIN TENSORS FROM DISPLACED ATOMS" in title:
            strain_source = "displaced_atoms"
        if "MACROSCOPIC STATIC DIELECTRIC TENSOR" in title and "IONIC CONTRIBUTION" in title:
            result["epsilon_ph"] = _table(lines, i, 3, 3)
        if "PIEZOELECTRIC TENSOR" in title and "FIELD DIRECTION" not in title and re.search(r"C\s*/\s*M\s*\^?\s*2", title):
            kind = "ionic" if "IONIC" in title else "total" if "TOTAL" in title else "clamped"
            result[f"piezoelectric_{kind}_C_m2"] = _table(lines, i, 3, 6)[:, _ORDER]
        if "ELASTIC MODULI" in title and "KBAR" in title:
            kind = (
                "relaxed" if "TOTAL" in title else "ionic" if "IONIC" in title
                else "clamped" if "SYMMETRIZED" in title else None
            )
            if kind:
                result[f"elastic_{kind}_GPa"] = _table(lines, i, 6, 6)[np.ix_(_ORDER, _ORDER)] * 0.1
        atom = re.search(r"INTERNAL STRAIN TENSOR FOR ION\s+(\d+)", title)
        if atom:
            internal_strains.setdefault(strain_source, {})[int(atom.group(1))] = _table(lines, i, 3, 6)[:, _ORDER]
    parsed_strains = {}
    for source, atoms in internal_strains.items():
        indices = sorted(atoms)
        if indices != list(range(1, len(indices) + 1)):
            raise ValueError("Incomplete VASP internal-strain atom sequence")
        parsed_strains[source] = np.asarray([atoms[index] for index in indices])
    if parsed_strains:
        # Native ionic e/C contractions use the stress derivative from displaced
        # atoms. Do not substitute a better-balanced strain-force derivative.
        source = "displaced_atoms" if "displaced_atoms" in parsed_strains else "strained_cells"
        tensor = parsed_strains[source]
        result["internal_strain_source"] = source
        residual = float(np.max(np.abs(np.sum(tensor, axis=0))))
        relative = residual / max(float(np.max(np.abs(tensor))), 1e-12)
        result["internal_strain_eV_per_A"] = tensor
        result["internal_strain_translation_max_eV_per_A"] = residual
        result["internal_strain_translation_relative"] = relative
        if "strained_cells" in parsed_strains:
            strained = parsed_strains["strained_cells"]
            result["internal_strain_from_strained_cells_eV_per_A"] = strained
            result["strained_cell_internal_strain_translation_max_eV_per_A"] = float(np.max(np.abs(strained.sum(axis=0))))
            if strained.shape != tensor.shape:
                raise ValueError("VASP internal-strain routes have different atom counts")
            result["internal_strain_reciprocity_max_eV_per_A"] = float(np.max(np.abs(strained - tensor)))
        if relative > 1e-3:
            result["electromechanical_warning"] = (
                "Native internal-strain tensor violates translational force balance; "
                "ionic piezoelectric/elastic contributions need convergence checks. "
                "Compare with --elastic native strain finite differences before use."
            )
    if "piezoelectric_clamped_C_m2" in result and "piezoelectric_ionic_C_m2" in result:
        summed = result["piezoelectric_clamped_C_m2"] + result["piezoelectric_ionic_C_m2"]
        if "piezoelectric_total_C_m2" in result:
            result["piezoelectric_closure_max_C_m2"] = float(np.max(np.abs(summed - result["piezoelectric_total_C_m2"])))
        else:
            result["piezoelectric_total_C_m2"] = summed
    if "elastic_relaxed_GPa" in result and "piezoelectric_total_C_m2" in result:
        elastic = result["elastic_relaxed_GPa"]
        antisymmetry = float(np.max(np.abs(elastic - elastic.T)))
        result["elastic_antisymmetry_max_GPa"] = antisymmetry
        result["elastic_eigenvalues_GPa"] = np.linalg.eigvalsh(0.5 * (elastic + elastic.T))
        result["elastic_condition_number"] = float(np.linalg.cond(elastic))
        failures = []
        if antisymmetry > 1e-3 * max(1.0, float(np.max(np.abs(elastic)))):
            failures.append("elastic major symmetry failed")
        if np.min(result["elastic_eigenvalues_GPa"]) <= 0.0:
            failures.append("elastic stability failed")
        if not {"piezoelectric_clamped_C_m2", "piezoelectric_ionic_C_m2"} <= result.keys():
            failures.append("electronic or ionic piezoelectric contribution missing")
        if result.get("piezoelectric_closure_max_C_m2", 0.0) > 1e-4:
            failures.append("piezoelectric electronic + ionic closure failed")
        if not failures:
            # Solve rather than explicitly forming the compliance inverse.
            result["piezoelectric_d_pm_V"] = np.linalg.solve(elastic.T, result["piezoelectric_total_C_m2"].T).T * 1000.0
            reconstructed_e = result["piezoelectric_d_pm_V"] @ elastic / 1000.0
            result["piezoelectric_d_ec_closure_max_C_m2"] = float(
                np.max(np.abs(reconstructed_e - result["piezoelectric_total_C_m2"]))
            )
        else:
            result["d_rejected_reason"] = "; ".join(failures) + "; no d tensor emitted"
    return result


def write_native_qpoints(modes, destination: str | Path) -> Path:
    """Export the native Gamma eigensystem in the existing ZStar input format."""
    if modes.eigenvectors.shape != (3 * len(modes.symbols), len(modes.symbols), 3):
        raise ValueError("Native Gamma eigensystem must contain all 3N modes")
    order = np.argsort(modes.frequencies_thz, kind="stable")
    data = {
        "physical_unit": {"length": "angstrom", "frequency": "THz"},
        "primitive_cell": {
            "lattice": modes.lattice_angstrom.tolist(),
            "points": [
                {"symbol": symbol, "mass": float(mass), "coordinates": position.tolist()}
                for symbol, mass, position in zip(modes.symbols, modes.masses_amu, modes.positions_fractional)
            ],
        },
        "phonon": [{"q-position": [0.0, 0.0, 0.0], "band": [
            {
                "frequency": float(modes.frequencies_thz[i]),
                "eigenvector": np.stack([modes.eigenvectors[i].real, modes.eigenvectors[i].imag], axis=-1).tolist(),
            } for i in order
        ]}],
    }
    target = Path(destination)
    target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return target


def write_native_phonopy(modes, force_constants: np.ndarray, root: Path) -> None:
    """Keep native force constants reusable by the existing phonon/irrep tools."""
    from phonopy import Phonopy
    from phonopy.structure.atoms import PhonopyAtoms

    cell = PhonopyAtoms(symbols=modes.symbols, masses=modes.masses_amu,
                        cell=modes.lattice_angstrom, scaled_positions=modes.positions_fractional)
    phonon = Phonopy(cell, np.eye(3, dtype=int), primitive_matrix=np.eye(3), calculator="vasp")
    phonon.force_constants = force_constants
    phonon.save(filename=str(root / "phonopy.yaml"), settings={"force_constants": True})
    run_irreps = getattr(phonon, "run_irreps", None) or phonon.set_irreps
    run_irreps([0, 0, 0], degeneracy_tolerance=0.02)
    previous = Path.cwd()
    try:
        os.chdir(root)
        phonon.write_yaml_irreps()
    finally:
        os.chdir(previous)


def collect_native_response(root: Path, manifest: dict, epsilon: np.ndarray, born: np.ndarray) -> dict:
    """Export native modes and tensors for reuse by dielectric/IR workflows."""
    from phonopy.file_IO import write_FORCE_CONSTANTS
    from phonopy.interface.vasp import parse_force_constants

    from .spectroscopy_backends import load_vasp_gamma_modes
    from .spectra import GammaModes

    source = root / "response"
    native = parse_native_tensors(source / "OUTCAR")
    if "epsilon_ph" not in native:
        raise ValueError("Native phonon response is incomplete: ionic dielectric tensor missing from OUTCAR")
    if manifest.get("elastic") and "elastic_relaxed_GPa" not in native:
        raise ValueError("Requested native elastic response is missing TOTAL ELASTIC MODULI")
    if manifest.get("piezo") and not {"piezoelectric_clamped_C_m2", "piezoelectric_ionic_C_m2"} <= native.keys():
        raise ValueError("Requested native piezoelectric response is incomplete: electronic or ionic contribution missing from OUTCAR")
    modes = load_vasp_gamma_modes(source / "vasprun.xml")
    order = np.argsort(modes.frequencies_thz, kind="stable")
    modes = GammaModes(modes.frequencies_thz[order], modes.eigenvectors[order], modes.masses_amu,
                       modes.lattice_angstrom, modes.symbols, modes.positions_fractional)
    if "internal_strain_eV_per_A" in native and len(native["internal_strain_eV_per_A"]) != len(born):
        raise ValueError("Native internal-strain atom count does not match BEC data")
    write_native_qpoints(modes, root / "qpoints.yaml")
    parsed = parse_force_constants(str(source / "vasprun.xml"))
    if parsed is None:
        raise ValueError("Native phonon response is incomplete: force constants missing from vasprun.xml")
    force_constants, _elements = parsed
    if np.shape(force_constants) != (len(born), len(born), 3, 3):
        raise ValueError("Native force-constant atom count does not match BEC data")
    write_FORCE_CONSTANTS(force_constants, filename=str(root / "FORCE_CONSTANTS"))
    write_native_phonopy(modes, force_constants, root)
    native["epsilon_static"] = epsilon + native["epsilon_ph"]
    native["frequencies_thz"] = modes.frequencies_thz
    diagnostics = {"irreps_degeneracy_tolerance_thz": 0.02}
    for key in ("internal_strain_translation_max_eV_per_A", "internal_strain_translation_relative",
                "electromechanical_warning", "d_rejected_reason", "internal_strain_source",
                "strained_cell_internal_strain_translation_max_eV_per_A",
                "internal_strain_reciprocity_max_eV_per_A", "piezoelectric_closure_max_C_m2",
                "piezoelectric_d_ec_closure_max_C_m2", "elastic_antisymmetry_max_GPa",
                "elastic_condition_number"):
        if key in native:
            diagnostics[key] = native[key]
    if manifest.get("dimensionality", 3) == 3:
        from .spectra import BornData, calculate_ir_spectrum, write_ir_outputs

        try:
            ir = calculate_ir_spectrum(modes, BornData(born, epsilon, "native VASP"))
            write_ir_outputs(root / "ir_spectrum", ir, plot=False)
            diagnostics["static_dielectric_max_abs"] = float(np.max(np.abs(ir.response_real[0] - native["epsilon_static"])))
        except ValueError as exc:
            # Preserve valid native tensors even when soft modes forbid a
            # stable harmonic dielectric interpretation.
            diagnostics["ir_rejected_reason"] = str(exc)
    result = {
        "schema_version": 1,
        "backend": "vasp",
        "electronic_response_method": manifest["method"],
        "ionic_response_method": manifest["ionic_response_method"],
        "solver_provenance": {
            "electronic_dielectric_bec_clamped_piezoelectric": "VASP native " + manifest["method"],
            "gamma_force_constants_internal_strain_ionic_response": "VASP native " + manifest["ionic_response_method"],
            "elastic": "VASP native strain finite differences" if manifest.get("elastic") else "not requested",
            "piezoelectric_d": "ZStar algebraic conversion of native e and C; no extra DFT" if "piezoelectric_d_pm_V" in native else "not emitted",
            "ir": "ZStar post-processing of native BEC and Gamma modes; no extra DFT" if "static_dielectric_max_abs" in diagnostics else "not emitted",
            "raman": "not computed here; additional native dielectric derivatives required",
        },
        "dimensionality": manifest.get("dimensionality", 3),
        "normalization": "bulk" if manifest.get("dimensionality", 3) == 3 else "periodic-supercell; intrinsic low-dimensional conversion required",
        "voigt_convention": list(ENGINEERING_VOIGT),
        "electric_boundary": "fixed macroscopic E",
        "mechanical_boundary": "fixed strain for dielectric; internal ions relaxed in ionic piezoelectric and elastic contributions",
        "gamma_boundary_condition": "native Gamma modes; no directional nonanalytic correction applied",
        "mode_index_convention": "frequency-ascending",
        "native_mode_numbers": (order + 1).tolist(),
        "epsilon_infinity": epsilon.tolist(),
        "tensors": {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in native.items()},
        "diagnostics": diagnostics,
        "files": {"qpoints": "qpoints.yaml", "force_constants": "FORCE_CONSTANTS", "modes_source": "response/vasprun.xml",
                  "phonopy": "phonopy.yaml", "irreps": "irreps.yaml"},
        "source": str(source / "OUTCAR"),
    }
    (root / "vasp_native_response.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
