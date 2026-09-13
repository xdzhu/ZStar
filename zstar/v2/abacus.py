"""ABACUS output collection for the calculator-neutral v2 response layer."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Mapping

import numpy as np

from ..dimensions import DimensionSpec
from ..shared_response import read_structure
from .ensemble import ResponseEnsemble
from .model import BoundaryConditions, ResponseDocument, TensorQuantity
from .normalization import normalize_polarization
from .polarization import (
    PolarizationSample,
    assemble_cartesian_polarization,
    collect_pyatb_polarization,
    collect_abacus_polarization_triplet,
    match_polarization_branch,
    pyatb_directional_to_cartesian,
)
from .strain import actual_strain


def _verify_input_hash(directory: Path, expected: str, *, label: str) -> None:
    """Reject changed v2 inputs before parsing calculator output."""

    if not expected:
        return
    from .strain import _input_hash

    try:
        actual = _input_hash(directory)
    except ValueError as exc:
        raise ValueError(f"cannot verify v2 input hash for {label}: {exc}") from exc
    if actual != expected:
        raise ValueError(
            f"v2 input hash mismatch for {label}: expected {expected}, got {actual}. "
            "Restore the serialized INPUT/STRU/KPT/assets or regenerate the ensemble "
            "before collecting results."
        )


def _single_log(stage: Path) -> Path:
    logs: list[Path] = []
    for pattern in (
        "OUT.*/running_scf.log",
        "OUT.*/running_relax.log",
        "OUT.*/running_cell-relax.log",
        "running_scf.log",
        "running_relax.log",
        "running_cell-relax.log",
    ):
        logs.extend(sorted(stage.glob(pattern)))
    logs = list(dict.fromkeys(logs))
    if len(logs) != 1:
        raise ValueError(
            "Expected exactly one ABACUS running_scf.log/running_relax.log/"
            f"running_cell-relax.log in {stage}; found {len(logs)}"
        )
    return logs[0]


def _float_triplet(fields: list[str]) -> list[float] | None:
    if len(fields) < 3:
        return None
    try:
        values = [float(value.replace("D", "E").replace("d", "e")) for value in fields[-3:]]
    except ValueError:
        return None
    return values if all(np.isfinite(values)) else None


def _parse_force_blocks(text: str, natoms: int) -> list[np.ndarray]:
    """Parse every ABACUS force block in chronological output order."""

    matches = list(re.finditer(r"TOTAL-FORCE\s*\(eV/Angstrom\)", text, flags=re.IGNORECASE))
    if not matches:
        raise ValueError("ABACUS output does not contain TOTAL-FORCE (eV/Angstrom)")
    blocks: list[np.ndarray] = []
    for match in matches:
        rows: list[list[float]] = []
        for line in text[match.end() :].splitlines():
            values = _float_triplet(line.split())
            if values is None:
                if rows:
                    break
                continue
            rows.append(values)
            if len(rows) == natoms:
                blocks.append(np.asarray(rows, dtype=float))
                break
        if len(rows) != natoms:
            raise ValueError(
                f"Expected {natoms} force rows after TOTAL-FORCE block; found {len(rows)}"
            )
    return blocks


def _parse_forces(text: str, natoms: int) -> np.ndarray:
    """Return the final ABACUS force block for convergence diagnostics."""

    return _parse_force_blocks(text, natoms)[-1]


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


def _relaxed_structure_path(stage: Path, log: Path) -> Path | None:
    """Locate the unique fixed-cell relaxation structure emitted by ABACUS."""

    candidates: list[Path] = []
    for candidate in (log.parent / "STRU_ION_D", stage / "STRU_ION_D"):
        if candidate.is_file():
            candidates.append(candidate)
    candidates.extend(sorted(stage.glob("OUT.*/STRU_ION_D")))
    candidates = list(dict.fromkeys(candidate.resolve() for candidate in candidates))
    if len(candidates) > 1:
        raise ValueError(
            "Expected at most one ABACUS relaxed structure STRU_ION_D in "
            f"{stage}; found {len(candidates)}"
        )
    return candidates[0] if candidates else None


def _input_structure_path(stage: Path) -> Path:
    """Return the pre-relaxation structure when PYATB uses the final ``STRU``."""

    preserved = stage / "STRU_INITIAL"
    return preserved if preserved.is_file() else stage / "STRU"


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
    charge_converged = "charge density convergence is achieved" in text
    ionic_converged = bool(re.search(r"relaxation is converged", text, flags=re.IGNORECASE))
    is_relax_log = "relax" in log.name.lower()
    if is_relax_log and not ionic_converged:
        raise ValueError(f"ABACUS ionic relaxation is not marked converged in {log}")
    if not charge_converged and not ionic_converged:
        raise ValueError(f"ABACUS SCF is not marked converged in {log}")
    input_structure_path = _input_structure_path(directory)
    structure = read_structure(input_structure_path)
    count = structure.natoms if natoms is None and hasattr(structure, "natoms") else natoms
    if count is None:
        count = len(structure)
    relaxed_path = _relaxed_structure_path(directory, log)
    relaxed_structure = None
    if relaxed_path is not None:
        relaxed_structure = read_structure(relaxed_path)
        if relaxed_structure.symbols != structure.symbols:
            raise ValueError(
                f"ABACUS relaxed structure atom ordering differs between {input_structure_path} "
                f"and {relaxed_path}"
            )
        if len(relaxed_structure) != int(count):
            raise ValueError(
                f"ABACUS relaxed structure has {len(relaxed_structure)} atoms; expected {int(count)}"
            )
    force_blocks = _parse_force_blocks(text, int(count))
    initial_forces = force_blocks[0]
    forces = force_blocks[-1]
    stress = _parse_stress(text)
    energy = _parse_energy(text)
    force_max = float(np.max(np.linalg.norm(forces, axis=1)))
    stress_max_abs = float(np.max(np.abs(stress)))
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
        "initial_forces": initial_forces,
        "force_blocks_count": len(force_blocks),
        "initial_force_max_eV_per_angstrom": float(np.max(np.linalg.norm(initial_forces, axis=1))),
        "force_max_eV_per_angstrom": force_max,
        "stress": stress,
        "stress_max_abs_kbar": stress_max_abs,
        "stress_unit": "kbar",
        "force_unit": "eV/angstrom",
        "energy": energy,
        "energy_unit": "eV",
        "scf_converged": charge_converged,
        "ionic_relaxation_converged": ionic_converged,
        "log_kind": log.name,
        "scf_iterations": int(text.count("E_Harris")),
        "timing": timing,
        "input_parameters": _input_parameters(directory / "INPUT"),
        "log": str(log),
        "relaxed_structure": relaxed_structure,
        "relaxed_structure_path": str(relaxed_path) if relaxed_path is not None else None,
        "input_structure_path": str(input_structure_path),
    }


def collect_abacus_strain_response(
    root: str | Path,
    *,
    polarization_stages: Mapping[str, Mapping[int | str, str | Path]] | None = None,
) -> ResponseDocument:
    """Collect reference and strain stages into a v2 response document.

    ``polarization_stages`` is an optional explicit map from each ensemble
    stage name to three ABACUS Berry ``gdir`` directories.  Keeping this map
    separate avoids assuming a backend-specific directory layout and prevents
    missing Berry data from being silently filled with zeros.
    """

    base = Path(root).resolve()
    ensemble = ResponseEnsemble.read(base / "ensemble.json")
    reference = base / "reference"
    _verify_input_hash(
        reference,
        str(ensemble.metadata.get("reference_input_hash", "")),
        label="reference",
    )
    # Verify every serialized input before parsing any calculator output.  A
    # changed later stage must fail deterministically even when the reference
    # output is absent or incomplete.
    for stage in ensemble.stages:
        _verify_input_hash(base / stage.stage_id, stage.input_hash, label=stage.stage_id)
    reference_structure = read_structure(reference / "STRU")
    natoms = len(reference_structure)
    records = [collect_abacus_stage(reference, natoms=natoms)]
    stage_vectors = [np.zeros(6, dtype=float)]
    stage_names = ["reference"]
    for stage in ensemble.stages:
        stage_path = base / stage.stage_id
        if stage.status in {"failed", "skipped"}:
            action = "rerun the failed stage" if stage.status == "failed" else "remove the skipped stage or regenerate the ensemble"
            raise ValueError(
                f"cannot collect stage {stage.stage_id}: manifest status is {stage.status!r}; "
                f"{action} before collecting a response"
            )
        # A strain response is defined from one common reference internal
        # coordinate set.  In particular, relaxed-ion stages must not carry
        # stale coordinates from a previous strain relaxation: that creates a
        # finite midpoint offset which can masquerade as a piezoelectric
        # signal.  ``STRU_INITIAL`` is the immutable serialized input when it
        # exists; compare wrapped fractional coordinates before fitting.
        records.append(collect_abacus_stage(stage_path, natoms=natoms))
        initial = read_structure(_input_structure_path(stage_path))
        if initial.symbols != reference_structure.symbols:
            raise ValueError(
                f"stage {stage.stage_id} atom ordering differs from reference; "
                "regenerate the ensemble from one reference structure"
            )
        delta_fractional = np.asarray(initial.scaled_positions, dtype=float) - np.asarray(
            reference_structure.scaled_positions, dtype=float
        )
        delta_fractional -= np.rint(delta_fractional)
        coordinate_error = float(np.max(np.abs(delta_fractional)))
        if coordinate_error > 1.0e-8:
            raise ValueError(
                f"stage {stage.stage_id} initial fractional coordinates differ from reference "
                f"by {coordinate_error:.6g}; regenerate the stage from the equilibrated "
                "reference structure before fitting"
            )
        if stage.actual_vector is None:
            raise ValueError(f"Stage {stage.stage_id} has no actual serialized strain vector")
        serialized_strain = actual_strain(reference_structure.cell, initial.cell)
        declared_strain = np.asarray(stage.actual_vector, dtype=float)
        if not np.allclose(serialized_strain, declared_strain, atol=1.0e-10, rtol=0.0):
            raise ValueError(
                f"stage {stage.stage_id} serialized cell strain differs from ensemble metadata; "
                "recompute actual_vector from the generated structure before fitting"
            )
        stage_vectors.append(np.asarray(stage.actual_vector, dtype=float))
        stage_names.append(stage.stage_id)
    dimensions = DimensionSpec(ensemble.dimensionality, ensemble.periodic_axes)
    ion_relaxation = str(ensemble.metadata.get("ion_relaxation", "clamped-ion")).strip().lower()
    if ion_relaxation not in {"clamped-ion", "relaxed-ion"}:
        raise ValueError(
            "ensemble metadata ion_relaxation must be 'clamped-ion' or 'relaxed-ion'; "
            f"got {ion_relaxation!r}"
        )
    reference_force_max: float | None = None
    if ion_relaxation == "relaxed-ion":
        # A relaxed-ion derivative is defined around an internally equilibrated
        # zero-strain state.  Do not let a single-point, high-force reference
        # masquerade as that state and contaminate every ±strain difference.
        threshold_value = ensemble.metadata.get("force_thr_ev")
        try:
            force_threshold = float(threshold_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "relaxed-ion ensemble metadata must provide a finite positive "
                "force_thr_ev for reference-equilibrium validation"
            ) from exc
        if not np.isfinite(force_threshold) or force_threshold <= 0.0:
            raise ValueError(
                "relaxed-ion ensemble metadata force_thr_ev must be finite and positive"
            )
        reference_force_max = float(np.max(np.linalg.norm(records[0]["forces"], axis=1)))
        if reference_force_max > force_threshold:
            raise ValueError(
                "relaxed-ion reference is not internally equilibrated: maximum force "
                f"{reference_force_max:.6g} eV/angstrom exceeds force_thr_ev "
                f"{force_threshold:.6g}; relax the reference structure before fitting"
            )
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
            ion_relaxation=ion_relaxation,
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
            ion_relaxation=ion_relaxation,
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
            ion_relaxation=ion_relaxation,
            provenance={"stage_names": stage_names, "sign_convention": "backend-raw"},
        ),
    ]
    if ion_relaxation == "relaxed-ion":
        quantities.append(
            TensorQuantity(
                name="forces_initial",
                values=np.asarray([record["initial_forces"] for record in records]),
                unit="eV/angstrom",
                axes=("stage", "atom", "cartesian"),
                boundary_conditions=stress_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization="per_atom",
                source="abacus_output_initial_force_block",
                backend="abacus",
                ion_relaxation="clamped-ion",
                provenance={
                    "stage_names": stage_names,
                    "definition": "first TOTAL-FORCE block in each relaxed-ion log",
                    "force_blocks_count": [record["force_blocks_count"] for record in records],
                },
            )
        )
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
                ion_relaxation=ion_relaxation,
                provenance={"stage_names": stage_names},
            )
        )

    internal_displacements: np.ndarray | None = None
    if ion_relaxation == "relaxed-ion":
        displacement_rows: list[np.ndarray] = []
        relaxed_paths: list[str] = []
        for name, stage_path, record in zip(stage_names, [reference] + [base / stage.stage_id for stage in ensemble.stages], records):
            if name == "reference":
                displacement_rows.append(np.zeros((natoms, 3), dtype=float))
                relaxed_paths.append("")
                continue
            initial = read_structure(_input_structure_path(stage_path))
            relaxed = record.get("relaxed_structure")
            relaxed_path = record.get("relaxed_structure_path")
            if relaxed is None or not relaxed_path:
                raise ValueError(
                    f"relaxed-ion stage {name} is missing OUT.*/STRU_ION_D; "
                    "complete the ionic relaxation before collecting internal strain"
                )
            if not np.allclose(relaxed.cell, initial.cell, atol=1.0e-8, rtol=0.0):
                raise ValueError(
                    f"relaxed-ion stage {name} changed the cell; use fixed-cell calculation relax "
                    "for internal-strain response, not cell-relax"
                )
            delta_fractional = np.asarray(relaxed.scaled_positions, dtype=float) - np.asarray(
                initial.scaled_positions, dtype=float
            )
            delta_fractional -= np.rint(delta_fractional)
            displacement_rows.append(delta_fractional @ np.asarray(initial.cell, dtype=float))
            relaxed_paths.append(str(relaxed_path))
        internal_displacements = np.asarray(displacement_rows, dtype=float)
        quantities.append(
            TensorQuantity(
                name="internal_displacement",
                values=internal_displacements,
                unit="angstrom",
                axes=("stage", "atom", "cartesian"),
                coordinate_system="cartesian_right_handed",
                boundary_conditions=stress_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization="per_atom",
                source="abacus_output",
                backend="abacus",
                ion_relaxation="relaxed-ion",
                provenance={
                    "stage_names": stage_names,
                    "relaxed_structure_paths": relaxed_paths,
                    "definition": "wrapped(final_fractional - initial_fractional) @ initial_cell",
                    "acoustic_gauge": "unfixed_raw_displacement",
                },
            )
        )
    polarization_samples: list[PolarizationSample] = []
    if polarization_stages is not None:
        if dimensions.value != 3:
            raise ValueError(
                "ABACUS Berry polarization collection currently requires "
                "dimensionality=3; for 2D/1D systems the raw C/m^2 output "
                "depends on the non-periodic cell length and must be converted "
                "to an explicit sheet/line normalization before collection"
            )
        missing = [name for name in stage_names if name not in polarization_stages]
        if missing:
            raise ValueError(
                "polarization_stages is missing mappings for ensemble stages: "
                + ", ".join(missing)
            )
        polarization_samples = [
            collect_abacus_polarization_triplet(polarization_stages[name])
            for name in stage_names
        ]
        polarization_boundary = BoundaryConditions(electric="E", mechanical="strain")
        quantities.append(
            TensorQuantity(
                name="polarization_gdir",
                values=np.asarray([sample.values for sample in polarization_samples]),
                unit="C/m^2",
                axes=("stage", "gdir"),
                coordinate_system="lattice_direction_scalar",
                boundary_conditions=polarization_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization="cell_volume",
                source="abacus_berry",
                backend="abacus",
                provenance={
                    "stage_names": stage_names,
                    "logs": [list(sample.logs) for sample in polarization_samples],
                    "raw_units": [list(sample.raw_units) for sample in polarization_samples],
                },
            )
        )
        quantities.append(
            TensorQuantity(
                name="polarization_quantum",
                values=np.asarray([sample.quanta for sample in polarization_samples]),
                unit="C/m^2",
                axes=("stage", "gdir"),
                coordinate_system="lattice_direction_scalar",
                boundary_conditions=polarization_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization="cell_volume",
                source="abacus_berry",
                backend="abacus",
                provenance={"stage_names": stage_names},
            )
        )
        if all(sample.cartesian_values is not None for sample in polarization_samples):
            quantities.append(
                TensorQuantity(
                    name="polarization_cartesian_directional",
                    values=np.asarray([sample.cartesian_values for sample in polarization_samples]),
                    unit="C/m^2",
                    axes=("stage", "gdir", "cartesian"),
                    coordinate_system="cartesian_right_handed",
                    boundary_conditions=polarization_boundary,
                    periodic_axes=dimensions.periodic_axes,
                    normalization="cell_volume",
                    source="abacus_berry",
                    backend="abacus",
                    provenance={"stage_names": stage_names},
                )
            )
            quantities.append(
                TensorQuantity(
                    name="polarization_cartesian",
                    values=np.asarray(
                        [assemble_cartesian_polarization(sample) for sample in polarization_samples]
                    ),
                    unit="C/m^2",
                    axes=("stage", "cartesian"),
                    coordinate_system="cartesian_right_handed",
                    boundary_conditions=polarization_boundary,
                    periodic_axes=dimensions.periodic_axes,
                    normalization="cell_volume",
                    source="abacus_berry_axis_sum",
                    backend="abacus",
                    provenance={
                        "stage_names": stage_names,
                        "assembly": "sum of three axis-resolved Cartesian tuples",
                    },
                )
            )
    first_parameters = records[0]["input_parameters"]
    provenance = {
        "reference_hash": ensemble.reference_hash,
        "stage_names": stage_names,
        "reference_force_max_eV_per_angstrom": reference_force_max,
        "stages": [
            {
                "name": name,
                "log": record["log"],
                "log_kind": record["log_kind"],
                "scf_converged": record["scf_converged"],
                "ionic_relaxation_converged": record["ionic_relaxation_converged"],
                "relaxed_structure_path": record["relaxed_structure_path"],
                "input_structure_path": record["input_structure_path"],
                "scf_iterations": record["scf_iterations"],
                "force_max_eV_per_angstrom": record["force_max_eV_per_angstrom"],
                "initial_force_max_eV_per_angstrom": record["initial_force_max_eV_per_angstrom"],
                "force_blocks_count": record["force_blocks_count"],
                "stress_max_abs_kbar": record["stress_max_abs_kbar"],
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
        convergence={
            **{key: value for key, value in first_parameters.items() if key in {"scf_thr", "scf_nmax"}},
            **(
                {"force_thr_ev": float(ensemble.metadata["force_thr_ev"])}
                if (
                    "force_thr_ev" in ensemble.metadata
                    and ion_relaxation == "relaxed-ion"
                )
                else {}
            ),
        },
        restart_state={"ensemble": str(base / "ensemble.json")},
        metadata={
            "stage_count": len(records),
            "polarization_collected": polarization_stages is not None,
            "polarization_cartesian_collected": bool(
                polarization_samples and all(sample.cartesian_values is not None for sample in polarization_samples)
            ),
            "energy_collected": all(value is not None for value in energies),
            "ion_relaxation": ion_relaxation,
            "reference_force_max_eV_per_angstrom": reference_force_max,
            "internal_displacement_collected": internal_displacements is not None,
        },
    )


def collect_pyatb_strain_response(
    root: str | Path,
    *,
    require_precision: bool = True,
    normalize_low_dimensional: bool = False,
) -> ResponseDocument:
    """Collect SCF force/stress data and one PYATB polarization run per stage.

    PYATB writes all three lattice-direction Berry values in one
    polarization.dat. Branch matching is performed in that directional basis
    with the stage-specific quanta, then each matched sample is converted to
    Cartesian coordinates using the stage lattice. This is the v1-compatible
    production path; the ABACUS gdir triplet collector remains an audit lane.
    Bulk (3D) collection is the default. For an explicitly declared 1D/2D
    ensemble, ``normalize_low_dimensional=True`` additionally stores an
    intrinsic line/sheet polarization after applying the documented geometric
    projection. It does not enable low-dimensional piezoelectric or elastic
    claims, and it rejects molecular (0D) bulk polarization.
    """

    base = Path(root).resolve()
    ensemble = ResponseEnsemble.read(base / "ensemble.json")
    if ensemble.metadata.get("insulating") is False:
        raise ValueError(
            "PYATB Berry polarization is not applicable to a metallic ensemble. "
            "Verify an insulating gap or use a separately validated metallic-response method "
            "before collecting piezoelectric data."
        )
    scf_document = collect_abacus_strain_response(base)
    stage_names = tuple(scf_document.provenance.get("stage_names", ()))
    if not stage_names:
        raise ValueError("SCF response document does not contain stage_names provenance")
    ion_relaxation = str(ensemble.metadata.get("ion_relaxation", "clamped-ion")).strip().lower()
    stage_paths = [base / "reference"] + [base / stage.stage_id for stage in ensemble.stages]
    if len(stage_paths) != len(stage_names):
        raise ValueError("SCF stage order does not match ensemble provenance")
    if not isinstance(normalize_low_dimensional, bool):
        raise TypeError("normalize_low_dimensional must be a bool")
    dimensions = scf_document.dimensionality
    if dimensions.value != 3 and not normalize_low_dimensional:
        raise ValueError(
            "PYATB bulk polarization collection currently requires dimensionality=3; "
            "set normalize_low_dimensional=True only after choosing an explicit sheet/line boundary"
        )
    if dimensions.value == 0 and normalize_low_dimensional:
        raise ValueError(
            "PYATB bulk polarization cannot be normalized for dimensionality=0; "
            "collect a molecular dipole instead"
        )

    if not isinstance(require_precision, bool):
        raise TypeError("require_precision must be a bool")
    precision_paths = [
        path / "pyatb" / "Out" / "Polarization" / "zstar_precision.json"
        for path in stage_paths
    ]
    missing_precision = [str(path) for path in precision_paths if not path.is_file()]
    if require_precision and missing_precision:
        raise ValueError(
            "PYATB precision writer metadata is missing for stage(s): "
            + ", ".join(missing_precision)
            + "; rerun with zstar.pyatb_precision or set require_precision=False "
            "for a qualitative audit only"
        )

    samples: list[PolarizationSample] = []
    lattices: list[np.ndarray] = []
    for path in stage_paths:
        sample, lattice = collect_pyatb_polarization(path)
        samples.append(sample)
        lattices.append(lattice)
    reference = samples[0]
    wrapped = np.asarray([sample.values for sample in samples], dtype=float)
    quanta = np.asarray([sample.quanta for sample in samples], dtype=float)
    matched_directional: list[np.ndarray] = []
    branch_shifts: list[np.ndarray] = []
    residuals: list[float] = []
    cartesian: list[np.ndarray] = []
    for sample, lattice in zip(samples, lattices):
        match = match_polarization_branch(
            reference.values,
            sample.values,
            np.diag(sample.quanta),
            periodic_axes=dimensions.periodic_axes,
        )
        matched_directional.append(match.matched)
        branch_shifts.append(match.branch_shift)
        residuals.append(match.residual)
        cartesian.append(pyatb_directional_to_cartesian(match.matched, lattice))

    polarization_boundary = BoundaryConditions(electric="E", mechanical="strain")
    quantities = list(scf_document.quantities)
    quantities.extend(
        (
            TensorQuantity(
                name="polarization_directional",
                values=wrapped,
                unit="C/m^2",
                axes=("stage", "lattice_direction"),
                coordinate_system="lattice_direction_scalar",
                boundary_conditions=polarization_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization="cell_volume",
                source="pyatb_berry",
                backend="pyatb",
                ion_relaxation=ion_relaxation,
                provenance={"stage_names": stage_names},
            ),
            TensorQuantity(
                name="polarization_quantum",
                values=quanta,
                unit="C/m^2",
                axes=("stage", "lattice_direction"),
                coordinate_system="lattice_direction_scalar",
                boundary_conditions=polarization_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization="cell_volume",
                source="pyatb_berry",
                backend="pyatb",
                ion_relaxation=ion_relaxation,
                provenance={"stage_names": stage_names},
            ),
            TensorQuantity(
                name="polarization_directional_matched",
                values=np.asarray(matched_directional),
                unit="C/m^2",
                axes=("stage", "lattice_direction"),
                coordinate_system="lattice_direction_scalar",
                boundary_conditions=polarization_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization="cell_volume",
                source="branch_matching",
                backend="pyatb",
                ion_relaxation=ion_relaxation,
                provenance={
                    "stage_names": stage_names,
                    "branch_shifts": np.asarray(branch_shifts).tolist(),
                    "residuals": residuals,
                },
            ),
            TensorQuantity(
                name="polarization_cartesian",
                values=np.asarray(cartesian),
                unit="C/m^2",
                axes=("stage", "cartesian"),
                coordinate_system="cartesian_right_handed",
                boundary_conditions=polarization_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization="cell_volume",
                source="pyatb_berry",
                backend="pyatb",
                ion_relaxation=ion_relaxation,
                provenance={
                    "stage_names": stage_names,
                    "lattice_vectors_angstrom": [lattice.tolist() for lattice in lattices],
                    "transformation": "solve normalized lattice-direction projections",
                },
            ),
        )
    )
    if normalize_low_dimensional:
        normalized = [
            normalize_polarization(
                value,
                lattice,
                dimensionality=dimensions.value,
                periodic_axes=dimensions.periodic_axes,
                boundary_condition="explicit_slab_or_wire",
            )
            for value, lattice in zip(cartesian, lattices)
        ]
        units = {item.unit for item in normalized}
        normalizations = {item.normalization for item in normalized}
        if len(units) != 1 or len(normalizations) != 1:
            raise ValueError("low-dimensional polarization stages produced inconsistent normalization")
        quantities.append(
            TensorQuantity(
                name="polarization_intrinsic",
                values=np.asarray([item.values for item in normalized]),
                unit=normalized[0].unit,
                axes=("stage", "cartesian"),
                coordinate_system="cartesian_right_handed",
                boundary_conditions=polarization_boundary,
                periodic_axes=dimensions.periodic_axes,
                normalization=normalized[0].normalization,
                source="explicit_low_dimensional_normalization",
                backend="zstar-v2",
                ion_relaxation=ion_relaxation,
                provenance={
                    "stage_names": stage_names,
                    "geometric_factors_si": [item.geometric_factor_si for item in normalized],
                    "geometric_factor_units": [item.geometric_factor_unit for item in normalized],
                    "projection": [item.projection for item in normalized],
                    "boundary_condition": [item.boundary_condition for item in normalized],
                },
            )
        )
    provenance = dict(scf_document.provenance)
    provenance.update(
        {
            "polarization_backend": "pyatb",
            "polarization_stage_names": list(stage_names),
            "polarization_logs": [
                sample.logs[0] for sample in samples
            ],
        }
    )
    metadata = dict(scf_document.metadata)
    metadata.update(
        {
            "polarization_collected": True,
            "polarization_backend": "pyatb",
            "pyatb_run_count": len(samples),
            "pyatb_precision_required": require_precision,
            "pyatb_precision_complete": not missing_precision,
            "low_dimensional_normalization": normalize_low_dimensional,
            "branch_shift_max": int(np.max(np.abs(np.asarray(branch_shifts)))),
            "branch_residual_max": float(max(residuals)),
        }
    )
    return ResponseDocument(
        backend="abacus+pyatb",
        dimensionality=scf_document.dimensionality,
        quantities=tuple(quantities),
        provenance=provenance,
        structure=scf_document.structure,
        symmetry=scf_document.symmetry,
        functional=scf_document.functional,
        pseudopotential=scf_document.pseudopotential,
        orbital=scf_document.orbital,
        convergence=scf_document.convergence,
        restart_state=scf_document.restart_state,
        metadata=metadata,
        created_at=scf_document.created_at,
    )
