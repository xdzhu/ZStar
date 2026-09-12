"""Homogeneous-strain planning and ABACUS structure preparation for v2."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Iterable

import numpy as np

from ..dimensions import DimensionSpec
from .ensemble import PerturbationStage, ResponseEnsemble, plan_central_stages
from .mechanical import strain_tensor_to_voigt, voigt_to_strain_tensor
from .structure import StructureSpec, analyze_space_group, symmetry_adapted_input_plan


def apply_strain(structure: StructureSpec, strain_voigt: Iterable[float]) -> StructureSpec:
    """Apply engineering strain to a structure while keeping fractional sites fixed."""

    strain = voigt_to_strain_tensor(strain_voigt)
    deformation = np.eye(3) + strain
    # StructureSpec stores lattice vectors as rows; F acts on column vectors.
    lattice = np.asarray(structure.lattice) @ deformation.T
    return StructureSpec(
        lattice=lattice,
        fractional_positions=structure.fractional_positions.copy(),
        symbols=structure.symbols,
        dimensionality=structure.dimensionality,
    )


def actual_strain(reference_lattice: np.ndarray, strained_lattice: np.ndarray) -> np.ndarray:
    """Recover the serialized small-strain Voigt vector from two cell matrices."""

    reference = np.asarray(reference_lattice, dtype=float)
    strained = np.asarray(strained_lattice, dtype=float)
    if reference.shape != (3, 3) or strained.shape != (3, 3):
        raise ValueError("reference_lattice and strained_lattice must have shape (3, 3)")
    deformation = strained.T @ np.linalg.inv(reference.T)
    return strain_tensor_to_voigt(0.5 * (deformation + deformation.T) - np.eye(3))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _input_hash(directory: Path) -> str:
    """Hash serialized inputs and copied ABACUS assets, excluding outputs.

    Relaxed-ion post-processing may replace ``STRU`` with ``STRU_ION_D``.  If
    ``STRU_INITIAL`` is present it is the immutable pre-relaxation input and is
    hashed instead, so provenance remains stable after PYATB preparation.
    """

    root = Path(directory)
    digest = hashlib.sha256()
    names = {"INPUT", "INPUT-scf", "KPT", "STRU"}
    candidates: list[Path] = []
    initial = root / "STRU_INITIAL"
    if initial.is_file():
        candidates.append(initial)
        names.discard("STRU")
    for candidate in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not candidate.is_file():
            continue
        if candidate.name in names or candidate.suffix.lower() in {".upf", ".orb", ".gz"}:
            candidates.append(candidate)
    if not candidates:
        raise ValueError(f"cannot compute v2 input hash: no serialized inputs in {root}")
    for candidate in sorted(set(candidates), key=lambda item: item.name.lower()):
        # ``STRU_INITIAL`` is a provenance-preserving alias for the original
        # serialized ``STRU``.  Use the logical input name in the digest so
        # post-processing may preserve the pre-relaxation structure without
        # invalidating an ensemble hash generated before the alias existed.
        logical_name = "STRU" if candidate.name == "STRU_INITIAL" else candidate.name
        digest.update(logical_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(candidate.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _report_dict(report) -> dict:
    return {
        "status": report.status,
        "symprec": report.symprec,
        "space_group": report.space_group,
        "hall_number": report.hall_number,
        "equivalent_atoms": list(report.equivalent_atoms),
        "representatives": list(report.representatives),
        "operation_count": report.operation_count,
        "diagnostics": report.diagnostics,
    }


def _set_input_parameter(path: Path, key: str, value: str) -> None:
    """Enable a required ABACUS observable in a private stage input copy."""

    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"(?m)^([ \t]*){re.escape(key)}(?:[ \t]+.*)?$")
    match = pattern.search(text)
    if match:
        text = pattern.sub(f"{match.group(1)}{key:<20}{value}", text, count=1)
    else:
        lines = text.splitlines()
        insert_at = 1 if lines and lines[0].strip() == "INPUT_PARAMETERS" else 0
        lines.insert(insert_at, f"{key:<20}{value}")
        text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    path.write_text(text, encoding="utf-8", newline="\n")


def _read_input_parameter(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("#", 1)[0].split()
        if len(fields) >= 2 and fields[0].lower() == key.lower():
            return fields[1]
    return None


def prepare_abacus_berry_stages(
    source_scf_stage: str | Path,
    output: str | Path,
    *,
    gdirs: Iterable[int] = (1, 2, 3),
    symmetry: str = "0",
) -> dict:
    """Prepare independent ABACUS Berry NSCF stages from one SCF stage.

    The source stage must contain ``INPUT``, ``STRU``, ``KPT`` and the charge
    restart referenced by its ``suffix`` (normally
    ``OUT.<suffix>/POLAR-CHARGE-DENSITY.restart``).  This function only copies
    inputs and writes a manifest; it never launches ABACUS.  Each generated
    stage is self-contained and uses the source restart through
    ``init_chg file``/``read_file_dir``.
    """

    source = Path(source_scf_stage).expanduser().resolve()
    target = Path(output).expanduser().resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"ABACUS SCF stage does not exist: {source}")
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"Berry stage output is not empty: {target}")
    input_source = source / "INPUT"
    structure_source = source / "STRU"
    kpt_source = source / "KPT"
    for required in (input_source, structure_source, kpt_source):
        if not required.is_file():
            raise FileNotFoundError(f"ABACUS Berry preparation requires {required}")
    if not str(symmetry).strip():
        raise ValueError("symmetry value must not be empty")
    directions = tuple(int(value) for value in gdirs)
    if len(directions) == 0 or len(set(directions)) != len(directions) or any(value not in {1, 2, 3} for value in directions):
        raise ValueError("gdirs must contain distinct values chosen from 1, 2, and 3")
    suffix = _read_input_parameter(input_source, "suffix")
    if suffix is None or not suffix.strip():
        candidates = sorted(source.glob("OUT.*/POLAR-CHARGE-DENSITY.restart"))
        if not candidates:
            raise FileNotFoundError(
                "ABACUS Berry preparation requires a source "
                "charge restart at OUT.<suffix>/POLAR-CHARGE-DENSITY.restart"
            )
        if len(candidates) != 1:
            raise ValueError("cannot identify a unique source OUT.<suffix>/POLAR-CHARGE-DENSITY.restart")
        out_dir = candidates[0].parent
        suffix = out_dir.name[4:] if out_dir.name.startswith("OUT.") else out_dir.name
    restart_source = source / f"OUT.{suffix}" / "POLAR-CHARGE-DENSITY.restart"
    if not restart_source.is_file():
        raise FileNotFoundError(
            "ABACUS Berry preparation requires charge restart "
            f"{restart_source}; complete the SCF stage with the matching suffix first"
        )

    target.mkdir(parents=True, exist_ok=True)
    prepared: dict[int, str] = {}
    for direction in directions:
        stage = target / f"gdir-{direction}"
        stage.mkdir()
        for source_file, destination_name in (
            (input_source, "INPUT"),
            (structure_source, "STRU"),
            (kpt_source, "KPT"),
        ):
            shutil.copy2(source_file, stage / destination_name)
        for asset in source.iterdir():
            if asset.is_file() and asset.name.lower().endswith((".upf", ".orb", ".upf.gz", ".orb.gz")):
                shutil.copy2(asset, stage / asset.name)
        output_dir = stage / f"OUT.{suffix}"
        output_dir.mkdir()
        shutil.copy2(restart_source, output_dir / restart_source.name)
        _set_input_parameter(stage / "INPUT", "calculation", "nscf")
        _set_input_parameter(stage / "INPUT", "init_chg", "file")
        _set_input_parameter(stage / "INPUT", "read_file_dir", f"OUT.{suffix}/")
        _set_input_parameter(stage / "INPUT", "berry_phase", "1")
        _set_input_parameter(stage / "INPUT", "gdir", str(direction))
        _set_input_parameter(stage / "INPUT", "symmetry", str(symmetry))
        prepared[direction] = str(stage)
    manifest = {
        "schema": "zstar-v2-abacus-berry-preparation",
        "schema_version": "0.1",
        "source_stage": source.name,
        "suffix": suffix,
        "gdirs": list(directions),
        "stages": {str(direction): f"gdir-{direction}" for direction in directions},
        "executed": False,
    }
    (target / "berry_ensemble.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"root": str(target), "stages": prepared, "suffix": suffix, "manifest": str(target / "berry_ensemble.json")}


def prepare_abacus_strain_ensemble(
    root: str | Path,
    *,
    structure: str | Path = "STRU",
    input_template: str | Path | None = None,
    kpt_template: str | Path | None = None,
    pp_dir: str | Path | None = None,
    orb_dir: str | Path | None = None,
    dimensionality: int = 3,
    strain_vectors: Iterable[Iterable[float]] | None = None,
    amplitude: float = 1.0e-3,
    symprec: float = 1.0e-3,
    ion_relaxation: str = "clamped-ion",
    force_thr_ev: float = 1.0e-3,
    scf_thr: float | None = None,
    symmetry_reduce: bool = False,
) -> dict:
    """Prepare a reference plus ± homogeneous-strain ABACUS folders.

    This is a dry-run/preparation API: it never executes ABACUS.  Each stage
    records the strain recovered from the serialized cell so later fitting
    cannot accidentally use the nominal requested amplitude.  ``clamped-ion``
    keeps the source SCF calculation unchanged; ``relaxed-ion`` switches only
    the ± strain stages to ``calculation relax`` and records the requested
    force threshold.  If ``scf_thr`` is provided, it is written to every
    copied INPUT (including the reference) so SCF force noise and ionic
    convergence can be audited as one reproducible ensemble.  The reference
    is always a single-point SCF on the
    supplied reference structure, which must already be the intended relaxed
    geometry when relaxed-ion response is requested.  With ``symmetry_reduce``
    enabled and no explicit ``strain_vectors``, a representation-rank plan
    selects the smallest canonical strain set that identifies polarization and
    stress responses (and internal displacement for relaxed-ion stages).
    """

    from ..shared_response import read_structure, write_structure
    from ..abacus_assets import prepare_stru_assets

    output = Path(root).resolve()
    source = Path(structure).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"ABACUS STRU does not exist: {source}")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"strain ensemble output is not empty: {output}")
    if not np.isfinite(float(amplitude)) or float(amplitude) <= 0.0:
        raise ValueError("amplitude must be finite and positive")
    if not np.isfinite(float(symprec)) or float(symprec) <= 0.0:
        raise ValueError("symprec must be finite and positive")
    relaxation = str(ion_relaxation).strip().lower()
    if relaxation not in {"clamped-ion", "relaxed-ion"}:
        raise ValueError("ion_relaxation must be 'clamped-ion' or 'relaxed-ion'")
    threshold = float(force_thr_ev)
    if not np.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("force_thr_ev must be finite and positive")
    if not isinstance(symmetry_reduce, (bool, np.bool_)):
        raise TypeError("symmetry_reduce must be a bool")
    scf_threshold: float | None = None
    if scf_thr is not None:
        scf_threshold = float(scf_thr)
        if not np.isfinite(scf_threshold) or scf_threshold <= 0.0:
            raise ValueError("scf_thr must be finite and positive when provided")
    atoms = read_structure(source)
    spec = StructureSpec(
        lattice=np.asarray(atoms.cell, dtype=float),
        fractional_positions=np.asarray(atoms.scaled_positions, dtype=float),
        symbols=tuple(str(symbol) for symbol in atoms.symbols),
        dimensionality=DimensionSpec(int(dimensionality)),
    )
    report = analyze_space_group(spec, symprec_grid=(float(symprec),))
    symmetry_plan = None
    if symmetry_reduce:
        if strain_vectors is not None:
            raise ValueError(
                "symmetry_reduce=True cannot be combined with explicit strain_vectors; "
                "choose one deterministic perturbation plan"
            )
        output_kinds = ("polarization", "strain")
        if relaxation == "relaxed-ion":
            output_kinds += ("displacement",)
        symmetry_plan = symmetry_adapted_input_plan(
            report,
            input_kind="strain",
            output_kinds=output_kinds,
        )
        if not symmetry_plan.complete:
            raise ValueError(
                "symmetry-adapted strain plan is rank-deficient: identified "
                f"{symmetry_plan.identified_rank} of {sum(symmetry_plan.allowed_ranks.values())} "
                "response coefficients; use explicit strain_vectors or review symmetry"
            )
        strain_vectors = (
            float(amplitude) * vector for vector in symmetry_plan.vectors
        )
    elif strain_vectors is None:
        strain_vectors = (float(amplitude) * np.eye(6)[index] for index in range(6))
    expected_outputs = ["polarization", "forces", "stress"]
    if relaxation == "relaxed-ion":
        expected_outputs.append("relaxed_structure")
    stages = plan_central_stages(
        strain_vectors,
        kind="strain",
        unit="engineering_strain",
        expected_outputs=tuple(expected_outputs),
        prefix="strain",
    )
    reference_hash = _sha256(source)
    ensemble = ResponseEnsemble(
        reference_hash=reference_hash,
        stages=stages,
        dimensionality=int(dimensionality),
        metadata={
            "preparation": "abacus",
            "symprec": float(symprec),
            "ion_relaxation": relaxation,
            "force_thr_ev": threshold,
            "symmetry_reduce": bool(symmetry_reduce),
            "symmetry_input_plan": None if symmetry_plan is None else symmetry_plan.to_dict(),
        },
    )
    output.mkdir(parents=True, exist_ok=True)
    reference_dir = output / "reference"
    reference_dir.mkdir()
    write_structure(source, reference_dir / "STRU", atoms)
    input_source = Path(input_template).expanduser().resolve() if input_template else next(
        (candidate for candidate in (source.parent / "INPUT-scf", source.parent / "INPUT") if candidate.is_file()),
        None,
    )
    input_name = "INPUT" if input_source is not None and input_source.name.upper() == "INPUT" else "INPUT-scf"
    kpt_source = Path(kpt_template).expanduser().resolve() if kpt_template else (source.parent / "KPT")
    for candidate, destination in ((input_source, reference_dir / input_name), (kpt_source, reference_dir / "KPT")):
        if candidate is not None and candidate.is_file():
            shutil.copy2(candidate, destination)
    if (reference_dir / input_name).is_file():
        _set_input_parameter(reference_dir / input_name, "cal_force", "1")
        _set_input_parameter(reference_dir / input_name, "cal_stress", "1")
        if scf_threshold is not None:
            _set_input_parameter(reference_dir / input_name, "scf_thr", f"{scf_threshold:.16g}")
    prepared = prepare_stru_assets(
        reference_dir / "STRU",
        pp_dir=pp_dir,
        orb_dir=orb_dir,
        output_dir=reference_dir / ".zstar-assets",
    )
    if prepared.changed:
        shutil.copy2(prepared.path, reference_dir / "STRU")
    for asset in prepared.assets:
        shutil.copy2(asset, reference_dir / asset.name)

    actual_stages: list[PerturbationStage] = []
    for stage in ensemble.stages:
        stage_dir = output / stage.stage_id
        stage_dir.mkdir()
        eta = np.asarray(stage.requested_vector, dtype=float)
        strained_atoms = atoms.copy()
        strained_atoms.cell = np.asarray(atoms.cell) @ (np.eye(3) + voigt_to_strain_tensor(eta)).T
        write_structure(source, stage_dir / "STRU", strained_atoms)
        if input_source is not None and input_source.is_file():
            shutil.copy2(input_source, stage_dir / input_name)
        if (stage_dir / input_name).is_file():
            _set_input_parameter(stage_dir / input_name, "cal_force", "1")
            _set_input_parameter(stage_dir / input_name, "cal_stress", "1")
            if scf_threshold is not None:
                _set_input_parameter(stage_dir / input_name, "scf_thr", f"{scf_threshold:.16g}")
            if relaxation == "relaxed-ion":
                _set_input_parameter(stage_dir / input_name, "calculation", "relax")
                _set_input_parameter(stage_dir / input_name, "force_thr_ev", f"{threshold:.16g}")
        if kpt_source.is_file():
            shutil.copy2(kpt_source, stage_dir / "KPT")
        prepared = prepare_stru_assets(
            stage_dir / "STRU",
            pp_dir=pp_dir,
            orb_dir=orb_dir,
            output_dir=stage_dir / ".zstar-assets",
        )
        if prepared.changed:
            shutil.copy2(prepared.path, stage_dir / "STRU")
        for asset in prepared.assets:
            shutil.copy2(asset, stage_dir / asset.name)
        serialized = read_structure(stage_dir / "STRU")
        actual = actual_strain(atoms.cell, serialized.cell)
        actual_stages.append(
            replace(
                stage,
                actual_vector=tuple(actual),
                input_hash=_input_hash(stage_dir),
                metadata={
                    "directory": stage.stage_id,
                    "ion_relaxation": relaxation,
                    "force_thr_ev": threshold,
                },
            )
        )
    final_ensemble = replace(
        ensemble,
        stages=tuple(actual_stages),
        metadata={
            **ensemble.metadata,
            "reference_input_hash": _input_hash(reference_dir),
            "scf_thr": (
                scf_threshold
                if scf_threshold is not None
                else _read_input_parameter(reference_dir / input_name, "scf_thr")
            ),
        },
    )
    final_ensemble.write(output / "ensemble.json")
    (output / "symmetry.json").write_text(json.dumps(_report_dict(report), indent=2) + "\n", encoding="utf-8")
    return {
        "ensemble": final_ensemble,
        "symmetry": report,
        "reference": str(reference_dir),
        "root": str(output),
    }
