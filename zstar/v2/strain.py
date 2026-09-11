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
from .structure import StructureSpec, analyze_space_group


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
) -> dict:
    """Prepare a reference plus ± homogeneous-strain ABACUS folders.

    This is a dry-run/preparation API: it never executes ABACUS.  Each stage
    records the strain recovered from the serialized cell so later fitting
    cannot accidentally use the nominal requested amplitude.
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
    atoms = read_structure(source)
    spec = StructureSpec(
        lattice=np.asarray(atoms.cell, dtype=float),
        fractional_positions=np.asarray(atoms.scaled_positions, dtype=float),
        symbols=tuple(str(symbol) for symbol in atoms.symbols),
        dimensionality=DimensionSpec(int(dimensionality)),
    )
    report = analyze_space_group(spec, symprec_grid=(float(symprec),))
    if strain_vectors is None:
        strain_vectors = (float(amplitude) * np.eye(6)[index] for index in range(6))
    stages = plan_central_stages(
        strain_vectors,
        kind="strain",
        unit="engineering_strain",
        expected_outputs=("polarization", "forces", "stress"),
        prefix="strain",
    )
    reference_hash = _sha256(source)
    ensemble = ResponseEnsemble(
        reference_hash=reference_hash,
        stages=stages,
        dimensionality=int(dimensionality),
        metadata={"preparation": "abacus", "symprec": float(symprec)},
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
        actual_stages.append(replace(stage, actual_vector=tuple(actual), metadata={"directory": stage.stage_id}))
    final_ensemble = replace(ensemble, stages=tuple(actual_stages))
    final_ensemble.write(output / "ensemble.json")
    (output / "symmetry.json").write_text(json.dumps(_report_dict(report), indent=2) + "\n", encoding="utf-8")
    return {
        "ensemble": final_ensemble,
        "symmetry": report,
        "reference": str(reference_dir),
        "root": str(output),
    }
