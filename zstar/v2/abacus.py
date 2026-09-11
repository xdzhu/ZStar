"""ABACUS output collection for the calculator-neutral v2 response layer."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import numpy as np

from ..dimensions import DimensionSpec
from ..shared_response import read_structure
from .ensemble import ResponseEnsemble
from .model import BoundaryConditions, ResponseDocument, TensorQuantity


def _single_log(stage: Path) -> Path:
    logs = sorted(stage.glob("OUT.*/running_scf.log"))
    if len(logs) != 1:
        raise ValueError(f"Expected exactly one ABACUS running_scf.log in {stage}; found {len(logs)}")
    return logs[0]


def _float_triplet(fields: list[str]) -> list[float] | None:
    if len(fields) < 3:
        return None
    try:
        values = [float(value.replace("D", "E").replace("d", "e")) for value in fields[-3:]]
    except ValueError:
        return None
    return values if all(np.isfinite(values)) else None


def _parse_forces(text: str, natoms: int) -> np.ndarray:
    marker = "TOTAL-FORCE (eV/Angstrom)"
    if marker not in text:
        raise ValueError("ABACUS output does not contain TOTAL-FORCE (eV/Angstrom)")
    rows: list[list[float]] = []
    for line in text.rsplit(marker, 1)[1].splitlines():
        values = _float_triplet(line.split())
        if values is None:
            continue
        rows.append(values)
        if len(rows) == natoms:
            return np.asarray(rows, dtype=float)
    raise ValueError(f"Expected {natoms} force rows after the final TOTAL-FORCE block; found {len(rows)}")


def _parse_stress(text: str) -> np.ndarray:
    matches = list(re.finditer(r"TOTAL-STRESS\s*\(KBAR\)", text, flags=re.IGNORECASE))
    if not matches:
        raise ValueError("ABACUS output does not contain TOTAL-STRESS (KBAR)")
    rows: list[list[float]] = []
    for line in text[matches[-1].end() :].splitlines():
        values = _float_triplet(line.split())
        if values is None:
            if rows:
                break
            continue
        rows.append(values)
        if len(rows) == 3:
            return np.asarray(rows, dtype=float)
    raise ValueError(f"Expected a 3x3 stress block after TOTAL-STRESS (KBAR); found {len(rows)} rows")


def _parse_energy(text: str) -> float | None:
    """Return the final total energy when ABACUS emitted it."""

    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
    matches = re.findall(rf"!?FINAL_ETOT_IS\s+({number})\s+eV", text, flags=re.IGNORECASE)
    if not matches:
        return None
    value = float(matches[-1].replace("D", "E").replace("d", "e"))
    if not np.isfinite(value):
        raise ValueError("ABACUS final energy is not finite")
    return value


def _input_parameters(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    parameters: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("#", 1)[0].split()
        if len(fields) >= 2:
            parameters[fields[0].lower()] = fields[1]
    return parameters


def collect_abacus_stage(stage: str | Path, *, natoms: int | None = None) -> dict[str, Any]:
    """Parse one completed ABACUS stage without applying a stress-sign convention."""

    directory = Path(stage).resolve()
    log = _single_log(directory)
    text = log.read_text(encoding="utf-8", errors="replace")
    if "charge density convergence is achieved" not in text:
        raise ValueError(f"ABACUS SCF is not marked converged in {log}")
    structure = read_structure(directory / "STRU")
    count = structure.natoms if natoms is None and hasattr(structure, "natoms") else natoms
    if count is None:
        count = len(structure)
    forces = _parse_forces(text, int(count))
    stress = _parse_stress(text)
    energy = _parse_energy(text)
    timing: dict[str, Any] = {}
    timing_path = directory / "time.json"
    if timing_path.is_file():
        try:
            timing = json.loads(timing_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid ABACUS time.json: {timing_path}") from exc
    return {
        "stage": directory.name,
        "forces": forces,
        "stress": stress,
        "stress_unit": "kbar",
        "force_unit": "eV/angstrom",
        "energy": energy,
        "energy_unit": "eV",
        "scf_converged": True,
        "scf_iterations": int(text.count("E_Harris")),
        "timing": timing,
        "input_parameters": _input_parameters(directory / "INPUT"),
        "log": str(log),
    }


def collect_abacus_strain_response(root: str | Path) -> ResponseDocument:
    """Collect reference and strain stages into a v2 response document."""

    base = Path(root).resolve()
    ensemble = ResponseEnsemble.read(base / "ensemble.json")
    reference = base / "reference"
    reference_structure = read_structure(reference / "STRU")
    natoms = len(reference_structure)
    records = [collect_abacus_stage(reference, natoms=natoms)]
    stage_vectors = [np.zeros(6, dtype=float)]
    stage_names = ["reference"]
    for stage in ensemble.stages:
        records.append(collect_abacus_stage(base / stage.stage_id, natoms=natoms))
        if stage.actual_vector is None:
            raise ValueError(f"Stage {stage.stage_id} has no actual serialized strain vector")
        stage_vectors.append(np.asarray(stage.actual_vector, dtype=float))
        stage_names.append(stage.stage_id)
    dimensions = DimensionSpec(ensemble.dimensionality)
    stress_boundary = BoundaryConditions(electric="E", mechanical="strain", stress_sign="backend-raw")
    quantities = [
        TensorQuantity(
            name="strain_vector",
            values=np.asarray(stage_vectors),
            unit="engineering_strain",
            axes=("stage", "voigt_engineering"),
            voigt_convention=("xx", "yy", "zz", "2yz", "2xz", "2xy"),
            boundary_conditions=stress_boundary,
            periodic_axes=dimensions.periodic_axes,
            normalization="dimensionless",
            source="serialized_structure",
            backend="abacus",
            provenance={"stage_names": stage_names},
        ),
        TensorQuantity(
            name="forces",
            values=np.asarray([record["forces"] for record in records]),
            unit="eV/angstrom",
            axes=("stage", "atom", "cartesian"),
            boundary_conditions=stress_boundary,
            periodic_axes=dimensions.periodic_axes,
            normalization="per_atom",
            source="abacus_output",
            backend="abacus",
            provenance={"stage_names": stage_names},
        ),
        TensorQuantity(
            name="stress_raw",
            values=np.asarray([record["stress"] for record in records]),
            unit="kbar",
            axes=("stage", "stress_row_cartesian", "stress_column_cartesian"),
            boundary_conditions=stress_boundary,
            periodic_axes=dimensions.periodic_axes,
            normalization="cell_volume",
            source="abacus_output",
            backend="abacus",
            provenance={"stage_names": stage_names, "sign_convention": "backend-raw"},
        ),
    ]
    energies = [record["energy"] for record in records]
    if all(value is not None for value in energies):
        quantities.append(
            TensorQuantity(
                name="energy",
                values=np.asarray(energies, dtype=float),
                unit="eV",
                axes=("stage",),
                boundary_conditions=stress_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization="total_cell",
                source="abacus_output",
                backend="abacus",
                provenance={"stage_names": stage_names},
            )
        )
    first_parameters = records[0]["input_parameters"]
    provenance = {
        "reference_hash": ensemble.reference_hash,
        "stage_names": stage_names,
        "stages": [
            {
                "name": name,
                "log": record["log"],
                "scf_converged": record["scf_converged"],
                "scf_iterations": record["scf_iterations"],
                "energy": record["energy"],
                "timing": record["timing"],
            }
            for name, record in zip(stage_names, records)
        ],
    }
    return ResponseDocument(
        backend="abacus",
        dimensionality=dimensions,
        quantities=tuple(quantities),
        provenance=provenance,
        structure={
            "lattice_angstrom": reference_structure.cell.tolist(),
            "fractional_positions": reference_structure.scaled_positions.tolist(),
            "symbols": list(reference_structure.symbols),
        },
        symmetry={},
        functional=first_parameters.get("dft_functional", ""),
        convergence={key: value for key, value in first_parameters.items() if key in {"scf_thr", "scf_nmax"}},
        restart_state={"ensemble": str(base / "ensemble.json")},
        metadata={
            "stage_count": len(records),
            "polarization_collected": False,
            "energy_collected": all(value is not None for value in energies),
        },
    )
