"""Calculator-neutral observations parsed from a VASP OUTCAR.

This module intentionally stops at observation parsing.  VASP's stress sign is
kept as ``vasp-raw`` and must be declared explicitly when fitting an elastic
response; no sign or boundary condition is inferred here.  The parser is
therefore usable for an independent backend audit without making VASP a
dependency of the v2 response algebra.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import numpy as np

from ..dimensions import DimensionSpec
from ..structure_io import read_structure
from .ensemble import ResponseEnsemble
from .model import BoundaryConditions, ResponseDocument, TensorQuantity
from .strain import actual_strain


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
_NUMBER_RE = re.compile(_NUMBER)


def _float(token: str) -> float:
    return float(token.replace("D", "E").replace("d", "e"))


def _numbers(line: str) -> list[float]:
    return [_float(value) for value in _NUMBER_RE.findall(line)]


def _parse_energy(text: str) -> float:
    matches = re.findall(rf"free\s+energy\s+TOTEN\s*=\s*({_NUMBER})\s+eV", text, re.I)
    if not matches:
        raise ValueError("VASP OUTCAR does not contain a free-energy TOTEN line")
    value = _float(matches[-1])
    if not np.isfinite(value):
        raise ValueError("VASP total energy is not finite")
    return value


def _parse_stress(text: str) -> np.ndarray:
    matches = list(re.finditer(r"^\s*in\s+kB\s+", text, re.I | re.M))
    if not matches:
        raise ValueError("VASP OUTCAR does not contain an 'in kB' stress row")
    values = _numbers(text[matches[-1].end() :].splitlines()[0])
    if len(values) < 6:
        raise ValueError(
            "VASP OUTCAR 'in kB' stress row must contain xx yy zz xy yz zx"
        )
    xx, yy, zz, xy, yz, zx = values[:6]
    stress = np.array(
        [[xx, xy, zx], [xy, yy, yz], [zx, yz, zz]], dtype=float
    )
    if not np.all(np.isfinite(stress)):
        raise ValueError("VASP stress contains non-finite values")
    return stress


def _infer_natoms(text: str) -> int | None:
    matches = re.findall(r"ions\s+per\s+type\s*=\s*([^\n]+)", text, re.I)
    if not matches:
        return None
    values = _numbers(matches[-1])
    if not values or any(value <= 0 or value != int(value) for value in values):
        return None
    return int(sum(values))


def _parse_force_blocks(text: str, natoms: int) -> tuple[np.ndarray, ...]:
    matches = list(
        re.finditer(r"TOTAL-FORCE\s*\(eV/Angst(?:rom)?\)", text, re.I)
    )
    if not matches:
        raise ValueError("VASP OUTCAR does not contain TOTAL-FORCE (eV/Angst) blocks")
    blocks: list[np.ndarray] = []
    for match in matches:
        rows: list[list[float]] = []
        for line in text[match.end() :].splitlines():
            values = _numbers(line)
            if len(values) >= 6:
                rows.append(values[-3:])
                if len(rows) == natoms:
                    break
            elif rows:
                break
        if len(rows) != natoms:
            raise ValueError(
                f"VASP TOTAL-FORCE block has {len(rows)} rows; expected {natoms}"
            )
        block = np.asarray(rows, dtype=float)
        if not np.all(np.isfinite(block)):
            raise ValueError("VASP force block contains non-finite values")
        blocks.append(block)
    return tuple(blocks)


def _parse_lattice(text: str) -> np.ndarray:
    matches = list(
        re.finditer(r"direct\s+lattice\s+vectors\s+reciprocal\s+lattice\s+vectors", text, re.I)
    )
    if not matches:
        raise ValueError("VASP OUTCAR does not contain direct lattice vectors")
    rows: list[list[float]] = []
    for line in text[matches[-1].end() :].splitlines():
        values = _numbers(line)
        if len(values) >= 6:
            rows.append(values[:3])
            if len(rows) == 3:
                break
        elif rows:
            break
    if len(rows) != 3:
        raise ValueError(
            "VASP direct lattice vector block must contain three rows of six values"
        )
    lattice = np.asarray(rows, dtype=float)
    if not np.all(np.isfinite(lattice)):
        raise ValueError("VASP lattice vectors contain non-finite values")
    return lattice


@dataclass(frozen=True)
class VaspObservations:
    """Parsed VASP observations before any v2 response fitting."""

    energy: float
    stress: np.ndarray
    force_blocks: tuple[np.ndarray, ...]
    lattice_angstrom: np.ndarray
    natoms: int
    stress_unit: str = "kbar"
    force_unit: str = "eV/angstrom"
    stress_sign: str = "vasp-raw"
    backend: str = "vasp"
    provenance: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        stress = np.asarray(self.stress, dtype=float)
        lattice = np.asarray(self.lattice_angstrom, dtype=float)
        if stress.shape != (3, 3) or not np.all(np.isfinite(stress)):
            raise ValueError("stress must be a finite 3x3 tensor")
        if lattice.shape != (3, 3) or not np.all(np.isfinite(lattice)):
            raise ValueError("lattice_angstrom must be a finite 3x3 matrix")
        if int(self.natoms) <= 0:
            raise ValueError("natoms must be positive")
        blocks = tuple(np.asarray(block, dtype=float) for block in self.force_blocks)
        if any(block.shape != (int(self.natoms), 3) for block in blocks):
            raise ValueError("each VASP force block must have shape (natoms, 3)")
        if any(not np.all(np.isfinite(block)) for block in blocks):
            raise ValueError("VASP force blocks must be finite")
        if self.stress_sign != "vasp-raw":
            raise ValueError("VaspObservations stress_sign is fixed to the explicit 'vasp-raw' label")
        object.__setattr__(self, "stress", stress)
        object.__setattr__(self, "lattice_angstrom", lattice)
        object.__setattr__(self, "force_blocks", blocks)
        object.__setattr__(self, "provenance", dict(self.provenance or {}))

    @property
    def forces_initial(self) -> np.ndarray | None:
        return self.force_blocks[0] if self.force_blocks else None

    @property
    def forces_final(self) -> np.ndarray | None:
        return self.force_blocks[-1] if self.force_blocks else None


def parse_vasp_outcar_observations(
    path: str | Path,
    *,
    natoms: int | None = None,
    require_forces: bool = False,
) -> VaspObservations:
    """Parse energy, stress, force blocks and lattice from one OUTCAR.

    ``natoms`` is required when the OUTCAR does not contain a parseable
    ``ions per type`` line.  Force blocks are optional for a clamped-ion
    stress/energy audit unless ``require_forces=True``.
    """

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"VASP OUTCAR does not exist: {source}")
    text = source.read_text(encoding="utf-8", errors="replace")
    count = _infer_natoms(text) if natoms is None else int(natoms)
    if count is None or count <= 0:
        raise ValueError("cannot determine positive VASP atom count; pass natoms explicitly")
    force_blocks: tuple[np.ndarray, ...] = ()
    force_error: Exception | None = None
    try:
        force_blocks = _parse_force_blocks(text, count)
    except ValueError as exc:
        force_error = exc
    if require_forces and force_error is not None:
        raise force_error
    return VaspObservations(
        energy=_parse_energy(text),
        stress=_parse_stress(text),
        force_blocks=force_blocks,
        lattice_angstrom=_parse_lattice(text),
        natoms=count,
        provenance={"source_file": str(source), "force_parse_error": None if force_error is None else str(force_error)},
    )


def _vasp_input_hash(directory: Path) -> str:
    """Hash the immutable VASP inputs when a manifest asks for verification."""

    import hashlib

    files = [directory / name for name in ("INCAR", "POSCAR", "KPOINTS", "POTCAR")]
    present = [path for path in files if path.is_file()]
    if not present:
        raise ValueError(f"cannot compute VASP input hash: no INCAR/POSCAR/KPOINTS/POTCAR in {directory}")
    digest = hashlib.sha256()
    for path in present:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _verify_vasp_input_hash(directory: Path, expected: str, label: str) -> None:
    if not expected:
        return
    actual = _vasp_input_hash(directory)
    if actual != expected:
        raise ValueError(
            f"VASP input hash mismatch for {label}: expected {expected}, got {actual}; "
            "restore INCAR/POSCAR/KPOINTS/POTCAR or regenerate the ensemble"
        )


def _stage_initial_structure(stage_path: Path):
    path = stage_path / "POSCAR"
    if not path.is_file():
        raise FileNotFoundError(f"VASP stage is missing POSCAR: {path}")
    return read_structure(path)


def collect_vasp_strain_response(root: str | Path) -> ResponseDocument:
    """Collect a VASP strain ensemble into the v2 response schema.

    The ensemble must contain ``reference`` plus completed ``strain`` stages
    with POSCAR/OUTCAR files.  The collector provides elastic, energy and force
    observations; it deliberately does not invent Berry polarization because
    this parser has no validated VASP polarization reader.  Stress remains
    ``vasp-raw`` until the caller supplies the sign to ``fit_response_document``.
    """

    base = Path(root).expanduser().resolve()
    ensemble_path = base / "ensemble.json"
    if not ensemble_path.is_file():
        raise FileNotFoundError(f"VASP strain ensemble is missing {ensemble_path}")
    ensemble = ResponseEnsemble.read(ensemble_path)
    if ensemble.dimensionality != 3:
        raise ValueError(
            "VASP strain collector currently requires dimensionality=3; "
            "2D/1D stress and open-direction boundary conditions are not defined here"
        )
    reference_path = base / "reference"
    reference_structure = _stage_initial_structure(reference_path)
    natoms = len(reference_structure.symbols)
    expected_reference_hash = str(ensemble.metadata.get("reference_input_hash", ""))
    _verify_vasp_input_hash(reference_path, expected_reference_hash, "reference")
    ion_relaxation = str(ensemble.metadata.get("ion_relaxation", "clamped-ion")).strip().lower()
    if ion_relaxation not in {"clamped-ion", "relaxed-ion"}:
        raise ValueError("VASP ensemble metadata ion_relaxation must be clamped-ion or relaxed-ion")
    if ion_relaxation == "relaxed-ion":
        try:
            force_threshold = float(ensemble.metadata["force_thr_ev"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "relaxed-ion VASP ensemble requires a positive force_thr_ev in metadata"
            ) from exc
        if not np.isfinite(force_threshold) or force_threshold <= 0.0:
            raise ValueError("relaxed-ion VASP ensemble force_thr_ev must be finite and positive")
    else:
        force_threshold = None

    paths = [reference_path]
    stage_names = ["reference"]
    for stage in ensemble.stages:
        if stage.kind != "strain":
            raise ValueError(f"VASP strain collector found non-strain stage {stage.stage_id!r}")
        if stage.status in {"failed", "skipped"}:
            action = "rerun the failed stage" if stage.status == "failed" else "remove the skipped stage or regenerate the ensemble"
            raise ValueError(f"cannot collect VASP stage {stage.stage_id}: manifest status is {stage.status!r}; {action}")
        if stage.status != "complete" or stage.actual_vector is None:
            raise ValueError(f"VASP stage {stage.stage_id} is not complete with an actual strain vector")
        path = base / stage.stage_id
        if not path.is_dir():
            raise FileNotFoundError(f"VASP stage directory does not exist: {path}")
        _verify_vasp_input_hash(path, stage.input_hash, stage.stage_id)
        initial = _stage_initial_structure(path)
        if initial.symbols != reference_structure.symbols:
            raise ValueError(f"VASP stage {stage.stage_id} atom ordering differs from reference")
        if not np.allclose(initial.positions_fractional, reference_structure.positions_fractional, atol=1.0e-8, rtol=0.0):
            raise ValueError(
                f"VASP stage {stage.stage_id} fractional positions differ from reference; "
                "use POSCAR for the common initial coordinates"
            )
        serialized = actual_strain(reference_structure.lattice_angstrom, initial.lattice_angstrom)
        if not np.allclose(serialized, np.asarray(stage.actual_vector), atol=1.0e-10, rtol=0.0):
            raise ValueError(f"VASP stage {stage.stage_id} actual strain disagrees with POSCAR cell")
        paths.append(path)
        stage_names.append(stage.stage_id)

    observations: list[VaspObservations] = []
    for name, path in zip(stage_names, paths):
        observation = parse_vasp_outcar_observations(path / "OUTCAR", natoms=natoms, require_forces=True)
        structure = _stage_initial_structure(path)
        if not np.allclose(
            observation.lattice_angstrom,
            structure.lattice_angstrom,
            atol=1.0e-7,
            rtol=0.0,
        ):
            raise ValueError(
                f"VASP stage {name} OUTCAR lattice differs from POSCAR; "
                "do not mix cell-relax output with a fixed-cell strain ensemble"
            )
        observations.append(observation)

    if ion_relaxation == "relaxed-ion":
        reference_force = observations[0].forces_final
        if reference_force is None:
            raise ValueError("relaxed-ion VASP reference has no converged force block")
        reference_force_max = float(np.max(np.linalg.norm(reference_force, axis=1)))
        if reference_force_max > float(force_threshold):
            raise ValueError(
                f"relaxed-ion VASP reference maximum force {reference_force_max:.6g} eV/angstrom "
                f"exceeds force_thr_ev {float(force_threshold):.6g}; relax the reference first"
            )
    else:
        reference_force_max = None

    dimensions = DimensionSpec(3, ensemble.periodic_axes)
    boundary = BoundaryConditions(electric="E", mechanical="strain", stress_sign="vasp-raw")
    strains = [np.zeros(6, dtype=float)] + [np.asarray(stage.actual_vector, dtype=float) for stage in ensemble.stages]
    quantities: list[TensorQuantity] = [
        TensorQuantity(
            name="strain_vector", values=np.asarray(strains), unit="engineering_strain",
            axes=("stage", "voigt_engineering"), voigt_convention=("xx", "yy", "zz", "2yz", "2xz", "2xy"),
            boundary_conditions=boundary, periodic_axes=dimensions.periodic_axes,
            normalization="dimensionless", source="serialized_structure", backend="vasp",
            ion_relaxation=ion_relaxation, provenance={"stage_names": stage_names},
        ),
        TensorQuantity(
            name="forces", values=np.asarray([item.forces_final for item in observations]), unit="eV/angstrom",
            axes=("stage", "atom", "cartesian"), boundary_conditions=boundary,
            periodic_axes=dimensions.periodic_axes, normalization="per_atom", source="vasp_outcar",
            backend="vasp", ion_relaxation=ion_relaxation, provenance={"stage_names": stage_names},
        ),
        TensorQuantity(
            name="stress_raw", values=np.asarray([item.stress for item in observations]), unit="kbar",
            axes=("stage", "stress_row_cartesian", "stress_column_cartesian"), boundary_conditions=boundary,
            periodic_axes=dimensions.periodic_axes, normalization="cell_volume", source="vasp_outcar",
            backend="vasp", ion_relaxation=ion_relaxation,
            provenance={"stage_names": stage_names, "sign_convention": "vasp-raw"},
        ),
        TensorQuantity(
            name="energy", values=np.asarray([item.energy for item in observations]), unit="eV",
            axes=("stage",), boundary_conditions=boundary, periodic_axes=dimensions.periodic_axes,
            normalization="total_cell", source="vasp_outcar", backend="vasp",
            ion_relaxation=ion_relaxation, provenance={"stage_names": stage_names},
        ),
    ]
    if ion_relaxation == "relaxed-ion":
        quantities.append(
            TensorQuantity(
                name="forces_initial", values=np.asarray([item.forces_initial for item in observations]),
                unit="eV/angstrom", axes=("stage", "atom", "cartesian"), boundary_conditions=boundary,
                periodic_axes=dimensions.periodic_axes, normalization="per_atom",
                source="vasp_outcar_initial_force_block", backend="vasp", ion_relaxation="clamped-ion",
                provenance={"stage_names": stage_names, "definition": "first TOTAL-FORCE block"},
            )
        )
        displacement_rows = [np.zeros((natoms, 3), dtype=float)]
        final_paths = [""]
        for name, path in zip(stage_names[1:], paths[1:]):
            contcar = path / "CONTCAR"
            if not contcar.is_file():
                raise FileNotFoundError(f"relaxed-ion VASP stage {name} is missing CONTCAR")
            initial = _stage_initial_structure(path)
            final = read_structure(contcar)
            if final.symbols != initial.symbols or not np.allclose(final.lattice_angstrom, initial.lattice_angstrom, atol=1.0e-8, rtol=0.0):
                raise ValueError(f"relaxed-ion VASP stage {name} CONTCAR changes atom order or cell")
            delta = np.asarray(final.positions_fractional) - np.asarray(initial.positions_fractional)
            delta -= np.rint(delta)
            displacement_rows.append(delta @ np.asarray(initial.lattice_angstrom, dtype=float))
            final_paths.append(str(contcar))
        quantities.append(
            TensorQuantity(
                name="internal_displacement", values=np.asarray(displacement_rows), unit="angstrom",
                axes=("stage", "atom", "cartesian"), coordinate_system="cartesian_right_handed",
                boundary_conditions=boundary, periodic_axes=dimensions.periodic_axes, normalization="per_atom",
                source="vasp_contcar", backend="vasp", ion_relaxation="relaxed-ion",
                provenance={"stage_names": stage_names, "relaxed_structure_paths": final_paths,
                            "definition": "wrapped(final_fractional-initial_fractional) @ initial_cell",
                            "acoustic_gauge": "unfixed_raw_displacement"},
            )
        )

    provenance = {
        "stage_names": stage_names,
        "stages": [item.provenance for item in observations],
        "reference_force_max_eV_per_angstrom": reference_force_max,
        "stress_sign": "vasp-raw",
        "polarization_collected": False,
    }
    return ResponseDocument(
        backend="vasp", dimensionality=dimensions, quantities=tuple(quantities), provenance=provenance,
        structure={"lattice_angstrom": np.asarray(reference_structure.lattice_angstrom).tolist(),
                   "fractional_positions": np.asarray(reference_structure.positions_fractional).tolist(),
                   "symbols": list(reference_structure.symbols)},
        convergence={"force_thr_ev": force_threshold} if force_threshold is not None else {},
        restart_state={"ensemble": str(ensemble_path)},
        metadata={"stage_count": len(stage_names), "ion_relaxation": ion_relaxation,
                  "energy_collected": True, "polarization_collected": False},
    )
