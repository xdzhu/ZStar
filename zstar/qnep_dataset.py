"""Prepare and audit GPUMD qNEP extended-XYZ datasets with BEC labels."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Iterable

import numpy as np

from .bec_database import read_born, read_zborn


_PROPERTIES_RE = re.compile(r"(?i)(\bproperties\s*=\s*)(\"[^\"]*\"|\S+)")
_KEY_RE_TEMPLATE = r"(?i)(?:^|\s){key}\s*="
_HEADER_VALUE_RE_TEMPLATE = r"(?:^|\s){key}=([^\s]+)"
QNEP_BEC_OUTPUT_PRECISION = 10


@dataclass(frozen=True)
class ExtxyzFrame:
    natoms: int
    header: str
    atoms: tuple[str, ...]


@dataclass(frozen=True)
class BecData:
    tensors: np.ndarray
    labels: tuple[str, ...] = ()
    convention: str = "zstar"


def _read_jsonl_records(path: str | Path) -> list[dict]:
    """Read a ZStar charge-aware JSONL dataset without changing its labels."""

    source = Path(path)
    records: list[dict] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL record at {source}:{line_number}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"JSONL record at {source}:{line_number} is not an object")
        records.append(record)
    if not records:
        raise ValueError(f"No records found in {source}")
    return records


def _jsonl_bec_in_qnep_order(record: dict) -> np.ndarray | None:
    """Return an optional JSONL BEC tensor in qNEP component convention."""

    available = record.get("born_effective_charges_available")
    tensors = record.get("born_effective_charges")
    if available is False or tensors is None:
        return None
    if available is not True:
        raise ValueError(
            "born_effective_charges_available must be explicitly true or false; "
            "a missing BEC is never encoded as a zero tensor"
        )
    array = np.asarray(tensors, dtype=float)
    natoms = len(record.get("chemical_symbols", []))
    if array.shape != (natoms, 3, 3):
        raise ValueError(
            f"Frame {record.get('frame_id', '<unknown>')} has BEC shape {array.shape}; "
            f"expected ({natoms}, 3, 3)"
        )
    if np.allclose(array, 0.0):
        raise ValueError(
            f"Frame {record.get('frame_id', '<unknown>')} has an all-zero BEC tensor; "
            "use born_effective_charges_available=false for a missing label"
        )
    convention = str(record.get("metadata", {}).get("bec_convention", "zstar")).lower()
    if convention == "zstar" or "rows=atomic displacement" in convention:
        return np.transpose(array, (0, 2, 1))
    if convention == "qnep" or "rows=electric" in convention:
        return array
    raise ValueError(f"Unknown BEC convention for frame {record.get('frame_id')}: {convention}")


def _match_annotation_atom_order(target: dict, annotation: dict) -> np.ndarray:
    """Map annotation atoms to a target frame using species and periodic positions.

    BEC campaign records can preserve a source extxyz ordering while ABACUS
    writes a different order.  A species-only reorder is unsafe for the three
    oxygen sites, so use minimum-image Cartesian positions and reject
    non-unique or inconsistent matches.
    """

    target_symbols = tuple(target.get("chemical_symbols", []))
    source_symbols = tuple(annotation.get("chemical_symbols", []))
    if len(target_symbols) != len(source_symbols) or sorted(target_symbols) != sorted(source_symbols):
        raise ValueError(
            f"Atom species mismatch between {target.get('frame_id')} and annotation "
            f"{annotation.get('frame_id')}"
        )
    target_cell = np.asarray(target.get("cell"), dtype=float)
    source_cell = np.asarray(annotation.get("cell"), dtype=float)
    target_pos = np.asarray(target.get("positions"), dtype=float)
    source_pos = np.asarray(annotation.get("positions"), dtype=float)
    if target_cell.shape != (3, 3) or source_cell.shape != (3, 3):
        raise ValueError("JSONL qNEP export requires a (3, 3) cell")
    if target_pos.shape != (len(target_symbols), 3) or source_pos.shape != target_pos.shape:
        raise ValueError("JSONL qNEP export requires one Cartesian position per atom")
    if not np.allclose(target_cell, source_cell, atol=5.0e-5, rtol=0.0):
        raise ValueError(
            f"Cell mismatch between {target.get('frame_id')} and annotation {annotation.get('frame_id')}"
        )

    inverse = np.linalg.inv(target_cell)
    target_fractional = target_pos @ inverse
    source_fractional = source_pos @ inverse
    order = np.empty(len(target_symbols), dtype=int)
    for species in sorted(set(target_symbols)):
        targets = [index for index, value in enumerate(target_symbols) if value == species]
        sources = [index for index, value in enumerate(source_symbols) if value == species]
        remaining = set(sources)
        for target_index in targets:
            distances: list[tuple[float, int]] = []
            for source_index in remaining:
                delta = target_fractional[target_index] - source_fractional[source_index]
                delta -= np.round(delta)
                distances.append((float(np.linalg.norm(delta @ target_cell)), source_index))
            distances.sort()
            if not distances or distances[0][0] > 2.0e-4:
                raise ValueError(
                    f"Could not position-match {species} in {target.get('frame_id')} to its BEC annotation"
                )
            if len(distances) > 1 and abs(distances[1][0] - distances[0][0]) < 1.0e-10:
                raise ValueError(
                    f"Ambiguous {species} atom order while matching {target.get('frame_id')}"
                )
            order[target_index] = distances[0][1]
            remaining.remove(distances[0][1])
    return order


def export_qnep_jsonl_dataset(
    input_jsonl: str | Path,
    output_xyz: str | Path,
    *,
    annotations_jsonl: str | Path | None = None,
    parent_separator: str = "::",
    neutral_suffix: str = "0.no-move",
    audit_output: str | Path | None = None,
) -> dict:
    """Export a traceable ZStar JSONL dataset to qNEP extended XYZ.

    Labels are copied verbatim.  If ``annotations_jsonl`` is supplied, its
    phase labels are inherited by children with ``parent_separator`` in their
    frame ID; BECs are attached only to the matching neutral parent frame.
    This is intended for sparse BEC campaigns where every finite-displacement
    SCF calculation is also a valid force-field E/F sample.
    """

    records = _read_jsonl_records(input_jsonl)
    annotations = _read_jsonl_records(annotations_jsonl) if annotations_jsonl else []
    annotation_by_id = {str(item.get("frame_id")): item for item in annotations}
    if len(annotation_by_id) != len(annotations):
        raise ValueError("Duplicate frame_id values in BEC annotation JSONL")

    output_lines: list[str] = []
    details: list[dict] = []
    phase_counts: dict[str, int] = {}
    for record in records:
        frame_id = str(record.get("frame_id", ""))
        symbols = tuple(str(item) for item in record.get("chemical_symbols", []))
        positions = np.asarray(record.get("positions"), dtype=float)
        forces = np.asarray(record.get("forces"), dtype=float)
        cell = np.asarray(record.get("cell"), dtype=float)
        if not frame_id or not symbols or positions.shape != (len(symbols), 3):
            raise ValueError(f"Frame {frame_id or '<unknown>'} has invalid symbols or positions")
        if forces.shape != positions.shape:
            raise ValueError(f"Frame {frame_id} forces do not match positions")
        if cell.shape != (3, 3) or record.get("energy") is None:
            raise ValueError(f"Frame {frame_id} lacks a (3, 3) cell or energy")

        parent = frame_id.split(parent_separator, 1)[0] if parent_separator in frame_id else frame_id
        annotation = annotation_by_id.get(parent)
        phase = record.get("phase_label")
        if phase in {None, "", "None"} and annotation is not None:
            phase = annotation.get("phase_label")
        phase = str(phase) if phase not in {None, "", "None"} else "unlabeled"
        phase_counts[phase] = phase_counts.get(phase, 0) + 1

        bec: np.ndarray | None = None
        bec_source: str | None = None
        own_bec = _jsonl_bec_in_qnep_order(record)
        if own_bec is not None:
            bec = own_bec
            bec_source = frame_id
        elif annotation is not None and frame_id.endswith(f"{parent_separator}{neutral_suffix}"):
            annotated_bec = _jsonl_bec_in_qnep_order(annotation)
            if annotated_bec is not None:
                order = _match_annotation_atom_order(record, annotation)
                bec = annotated_bec[order]
                bec_source = str(annotation.get("frame_id"))

        property_text = "species:S:1:pos:R:3:force:R:3" + (":bec:R:9" if bec is not None else "")
        lattice = " ".join(f"{value:.11g}" for value in cell.reshape(-1))
        header = (
            f'Lattice="{lattice}" Properties={property_text} energy={float(record["energy"]):.11g} '
            f"frame_id={frame_id} structure_id={record.get('structure_id', frame_id)} "
            f"total_charge={float(record.get('total_charge', 0.0)):.11g} phase_label={phase}"
        )
        stress = record.get("stress")
        if stress is not None:
            stress_array = np.asarray(stress, dtype=float).reshape(-1)
            if stress_array.size != 9:
                raise ValueError(f"Frame {frame_id} stress must have 9 components")
            header += ' stress="' + " ".join(f"{value:.11g}" for value in stress_array) + '"'
        output_lines.extend([str(len(symbols)), header])
        for index, symbol in enumerate(symbols):
            values = [*positions[index], *forces[index]]
            atom_line = f"{symbol} " + " ".join(f"{value:.10f}" for value in values)
            if bec is not None:
                atom_line += " " + " ".join(f"{value:.10f}" for value in bec[index].reshape(-1))
            output_lines.append(atom_line)
        details.append({"frame_id": frame_id, "phase_label": phase, "has_bec": bec is not None, "bec_source": bec_source})

    target = Path(output_xyz).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(output_lines) + "\n", encoding="utf-8", newline="\n")
    summary = {
        "schema_version": 1,
        "format": "gpumd-qnep-extxyz",
        "input": str(Path(input_jsonl).resolve()),
        "annotations": str(Path(annotations_jsonl).resolve()) if annotations_jsonl else None,
        "output": str(target),
        "frames": len(records),
        "labeled_frames": sum(item["has_bec"] for item in details),
        "unlabeled_frames": sum(not item["has_bec"] for item in details),
        "phase_counts": phase_counts,
        "bec_unit": "elementary_charge_e",
        "raw_labels_modified": False,
        "frames_detail": details,
    }
    audit = Path(audit_output).resolve() if audit_output else target.with_suffix(target.suffix + ".audit.json")
    audit.write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")
    summary["audit_output"] = str(audit)
    return summary


def read_extxyz(path: str | Path) -> list[ExtxyzFrame]:
    source = Path(path)
    lines = source.read_text(encoding="utf-8", errors="strict").splitlines()
    frames: list[ExtxyzFrame] = []
    cursor = 0
    while cursor < len(lines):
        if not lines[cursor].strip():
            cursor += 1
            continue
        try:
            natoms = int(lines[cursor].strip())
        except ValueError as exc:
            raise ValueError(f"Invalid atom count at {source}:{cursor + 1}") from exc
        if natoms < 1 or cursor + natoms + 1 >= len(lines):
            raise ValueError(f"Truncated extxyz frame at {source}:{cursor + 1}")
        frames.append(
            ExtxyzFrame(
                natoms=natoms,
                header=lines[cursor + 1],
                atoms=tuple(lines[cursor + 2:cursor + 2 + natoms]),
            )
        )
        cursor += natoms + 2
    if not frames:
        raise ValueError(f"No extxyz frames found in {source}")
    return frames


def _header_value(header: str, key: str) -> str | None:
    match = re.search(_HEADER_VALUE_RE_TEMPLATE.format(key=re.escape(key)), header)
    return match.group(1) if match else None


def compose_qnep_dataset(
    base_xyz: str | Path,
    addition_xyz: str | Path,
    output_xyz: str | Path,
    *,
    phases: Iterable[str],
    max_per_phase: int | None = None,
    seed: int = 0,
    audit_output: str | Path | None = None,
) -> dict:
    """Append selected phase-labelled qNEP frames to a fixed base dataset.

    The base frames are retained byte-for-byte.  Additions are selected by
    ``phase_label`` with a reproducible per-phase cap and de-duplicated by
    ``frame_id``.  This makes a fixed cubic benchmark and a multiphase training
    context auditable without rewriting any reference energy, force, or BEC.
    """

    wanted = tuple(str(phase) for phase in phases)
    if not wanted:
        raise ValueError("At least one phase must be requested")
    if max_per_phase is not None and max_per_phase < 1:
        raise ValueError("max_per_phase must be positive when supplied")
    base = read_extxyz(base_xyz)
    additions = read_extxyz(addition_xyz)
    base_ids = {_header_value(frame.header, "frame_id") for frame in base}
    base_ids.discard(None)
    rng = np.random.default_rng(seed)
    selected: list[ExtxyzFrame] = []
    selected_counts: dict[str, int] = {}
    skipped_duplicate = 0
    for phase in wanted:
        phase_frames = [
            frame for frame in additions if _header_value(frame.header, "phase_label") == phase
        ]
        if max_per_phase is not None and len(phase_frames) > max_per_phase:
            indices = np.sort(rng.choice(len(phase_frames), size=max_per_phase, replace=False))
            phase_frames = [phase_frames[index] for index in indices]
        accepted = 0
        for frame in phase_frames:
            frame_id = _header_value(frame.header, "frame_id")
            if frame_id and frame_id in base_ids:
                skipped_duplicate += 1
                continue
            selected.append(frame)
            if frame_id:
                base_ids.add(frame_id)
            accepted += 1
        selected_counts[phase] = accepted
    if any(selected_counts.get(phase, 0) == 0 for phase in wanted):
        missing = [phase for phase in wanted if selected_counts.get(phase, 0) == 0]
        raise ValueError(f"No non-duplicate frames selected for phase(s): {', '.join(missing)}")

    output = [*base, *selected]
    target = Path(output_xyz).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for frame in output:
        lines.extend([str(frame.natoms), frame.header, *frame.atoms])
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    labels = 0
    phase_counts: dict[str, int] = {}
    for frame in output:
        phase = _header_value(frame.header, "phase_label") or "unlabeled"
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        _match, properties = _properties(frame.header)
        labels += int(any(name.lower() == "bec" for name, _kind, _width in properties))
    summary = {
        "schema_version": 1,
        "base": str(Path(base_xyz).resolve()),
        "addition": str(Path(addition_xyz).resolve()),
        "output": str(target),
        "phases": list(wanted),
        "max_per_phase": max_per_phase,
        "seed": seed,
        "base_frames": len(base),
        "selected_counts": selected_counts,
        "skipped_duplicate_frame_ids": skipped_duplicate,
        "frames": len(output),
        "labeled_frames": labels,
        "phase_counts": phase_counts,
        "raw_labels_modified": False,
    }
    audit = Path(audit_output).resolve() if audit_output else target.with_suffix(target.suffix + ".audit.json")
    audit.write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")
    summary["audit_output"] = str(audit)
    return summary


def _parity_statistics(reference: np.ndarray, predicted: np.ndarray) -> dict[str, float | int | None]:
    reference = np.asarray(reference, dtype=float).reshape(-1)
    predicted = np.asarray(predicted, dtype=float).reshape(-1)
    if reference.size != predicted.size or reference.size == 0:
        raise ValueError("Parity arrays must have the same non-zero number of values")
    residual = predicted - reference
    centered = reference - float(np.mean(reference))
    denominator = float(np.dot(centered, centered))
    r2 = None if denominator == 0.0 else float(1.0 - np.dot(residual, residual) / denominator)
    return {
        "values": int(reference.size),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "max_abs": float(np.max(np.abs(residual))),
        "r2": r2,
    }


def score_qnep_predictions(
    test_xyz: str | Path,
    prediction_directory: str | Path,
    *,
    output: str | Path | None = None,
) -> dict:
    """Compute E/F/BEC parity statistics from qNEP ``*_test.out`` files.

    qNEP writes rows for all test atoms in ``bec_test.out`` and uses zero
    placeholders where no BEC target exists.  The BEC metric here instead uses
    the explicit ``bec:R:9`` mask in ``test_xyz``; a missing BEC can therefore
    never improve a reported error by being mistaken for a physical zero.
    """

    frames = read_extxyz(test_xyz)
    directory = Path(prediction_directory)
    energy = np.loadtxt(directory / "energy_test.out", ndmin=2)
    force = np.loadtxt(directory / "force_test.out", ndmin=2)
    if energy.shape != (len(frames), 2):
        raise ValueError(
            f"energy_test.out shape {energy.shape} does not match {len(frames)} test frames"
        )
    atom_count = sum(frame.natoms for frame in frames)
    if force.shape != (atom_count, 6):
        raise ValueError(
            f"force_test.out shape {force.shape} does not match {atom_count} test atoms"
        )
    summary: dict = {
        "schema": "zstar-qnep-parity-v1",
        "test_xyz": str(Path(test_xyz).resolve()),
        "prediction_directory": str(directory.resolve()),
        "evaluation_scope": "as supplied by the caller",
        "energy": _parity_statistics(energy[:, 0], energy[:, 1]),
        "force": _parity_statistics(force[:, :3], force[:, 3:]),
    }
    summary["energy"]["unit"] = "eV_per_atom"
    summary["force"]["unit"] = "eV_per_angstrom"

    bec_path = directory / "bec_test.out"
    bec_mask: list[bool] = []
    for frame in frames:
        _match, properties = _properties(frame.header)
        has_bec = any(name.lower() == "bec" for name, _kind, _width in properties)
        bec_mask.extend([has_bec] * frame.natoms)
    if bec_path.is_file() and any(bec_mask):
        bec = np.loadtxt(bec_path, ndmin=2)
        if bec.shape != (atom_count, 18):
            raise ValueError(
                f"bec_test.out shape {bec.shape} does not match {atom_count} test atoms"
            )
        mask = np.asarray(bec_mask, dtype=bool)
        summary["bec"] = _parity_statistics(bec[mask, :9], bec[mask, 9:])
        summary["bec"]["unit"] = "elementary_charge_e"
        summary["bec"]["labeled_atom_rows"] = int(np.count_nonzero(mask))
    else:
        summary["bec"] = {"labeled_atom_rows": 0, "unit": "elementary_charge_e"}

    target = Path(output).resolve() if output else directory / "metrics.json"
    target.write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")
    summary["output"] = str(target)
    return summary


def _properties(header: str) -> tuple[re.Match[str], list[tuple[str, str, int]]]:
    match = _PROPERTIES_RE.search(header)
    if match is None:
        raise ValueError("Missing mandatory Properties field in extxyz header")
    value = match.group(2)
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    fields = value.split(":")
    if len(fields) % 3:
        raise ValueError(f"Malformed extxyz Properties field: {value}")
    properties: list[tuple[str, str, int]] = []
    for index in range(0, len(fields), 3):
        try:
            width = int(fields[index + 2])
        except ValueError as exc:
            raise ValueError(f"Invalid Properties width: {fields[index + 2]}") from exc
        properties.append((fields[index], fields[index + 1], width))
    return match, properties


def _property_offset(properties: Iterable[tuple[str, str, int]], name: str) -> tuple[int, int]:
    offset = 0
    for current, _kind, width in properties:
        if current.lower() == name.lower():
            return offset, width
        offset += width
    raise ValueError(f"Missing {name} property")


def _frame_labels(frame: ExtxyzFrame, properties: list[tuple[str, str, int]]) -> list[str]:
    offset, width = _property_offset(properties, "species")
    if width != 1:
        raise ValueError("species property must have width 1")
    expected = sum(item[2] for item in properties)
    labels: list[str] = []
    for atom_index, line in enumerate(frame.atoms, start=1):
        fields = line.split()
        if len(fields) != expected:
            raise ValueError(
                f"Frame atom {atom_index} has {len(fields)} columns; Properties declares {expected}"
            )
        labels.append(fields[offset])
    return labels


def _require_header_key(header: str, key: str) -> None:
    if not re.search(_KEY_RE_TEMPLATE.format(key=re.escape(key)), header):
        raise ValueError(f"Missing mandatory {key} field in extxyz header")


def read_bec_data(path: str | Path) -> BecData:
    """Read a canonical ZStar BEC source.

    Canonical tensors have displacement/force as rows and polarization/electric
    field as columns. qNEP conversion is deliberately done at export time.
    """

    from .artifacts import resolve_artifact
    source = resolve_artifact(path)
    if source.suffix.lower() == ".json":
        data = json.loads(source.read_text(encoding="utf-8"))
        atoms = data.get("atoms")
        if not isinstance(atoms, list) or not atoms:
            raise ValueError(f"No atoms with BEC tensors in {source}")
        tensors = np.asarray([atom["tensor"] for atom in atoms], dtype=float)
        labels = tuple(str(atom.get("label", "")) for atom in atoms)
        convention = str(data.get("tensor_convention", "zstar"))
    elif source.name.upper().startswith("BORN"):
        _epsilon, tensors = read_born(source)
        labels = ()
        convention = "zstar"
    else:
        tensors = read_zborn(source)
        labels_list: list[str] = []
        for raw in source.read_text(encoding="utf-8", errors="ignore").splitlines():
            fields = raw.split()
            numeric = 0
            for field in fields:
                try:
                    float(field.replace("D", "E").replace("d", "e"))
                    numeric += 1
                except ValueError:
                    continue
            label_match = re.match(r"^\s*\*?\s*\d+\s+(\S+)", raw)
            if numeric >= 10 and label_match:
                labels_list.append(label_match.group(1))
        labels = tuple(labels_list) if len(labels_list) == len(tensors) else ()
        convention = "zstar"
    if tensors.ndim != 3 or tensors.shape[1:] != (3, 3):
        raise ValueError(f"BEC tensor array must have shape (natoms, 3, 3), got {tensors.shape}")
    return BecData(tensors=tensors, labels=labels, convention=convention)


def load_bec_map(path: str | Path) -> dict[int, Path]:
    source = Path(path).resolve()
    mapping: dict[int, Path] = {}
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = {"frame", "bec"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"BEC map missing columns: {', '.join(sorted(missing))}")
        for row_number, row in enumerate(reader, start=2):
            frame = int(row["frame"])
            if frame < 0:
                raise ValueError(f"Negative frame index at {source}:{row_number}")
            if frame in mapping:
                raise ValueError(f"Duplicate frame {frame} in {source}")
            bec = Path(row["bec"].strip())
            if not bec.is_absolute():
                bec = (source.parent / bec).resolve()
            mapping[frame] = bec
    return mapping


def _qnep_tensors(data: BecData) -> np.ndarray:
    convention = data.convention.lower()
    if "rows=atomic displacement" in convention or convention == "zstar":
        return np.transpose(data.tensors, (0, 2, 1))
    if "rows=electric" in convention or convention == "qnep":
        return data.tensors.copy()
    raise ValueError(f"Unknown BEC tensor convention: {data.convention}")


def augment_qnep_dataset(
    input_xyz: str | Path,
    output_xyz: str | Path,
    *,
    bec: str | Path | None = None,
    frame: int = 0,
    bec_map: str | Path | None = None,
    audit_output: str | Path | None = None,
) -> dict:
    """Append optional qNEP ``bec:R:9`` labels to selected extxyz frames."""

    if (bec is None) == (bec_map is None):
        raise ValueError("Provide exactly one of bec or bec_map")
    frames = read_extxyz(input_xyz)
    mapping = load_bec_map(bec_map) if bec_map is not None else {int(frame): Path(bec).resolve()}
    unknown = sorted(set(mapping) - set(range(len(frames))))
    if unknown:
        raise ValueError(f"BEC map refers to absent frame indices: {unknown}")

    output_lines: list[str] = []
    frame_audit: list[dict] = []
    for frame_index, current in enumerate(frames):
        _require_header_key(current.header, "lattice")
        _require_header_key(current.header, "energy")
        match, properties = _properties(current.header)
        _property_offset(properties, "pos")
        force_name = next((name for name, _kind, _width in properties if name.lower() in {"force", "forces"}), None)
        if force_name is None:
            raise ValueError(f"Frame {frame_index} has no force/forces property")
        labels = _frame_labels(current, properties)
        if any(name.lower() == "bec" for name, _kind, _width in properties):
            raise ValueError(f"Frame {frame_index} already contains a bec property")

        output_header = current.header
        output_atoms = list(current.atoms)
        entry = {
            "frame": frame_index,
            "natoms": current.natoms,
            "bec_labeled": False,
            "bec_source": None,
        }
        if frame_index in mapping:
            data = read_bec_data(mapping[frame_index])
            if len(data.tensors) != current.natoms:
                raise ValueError(
                    f"Frame {frame_index} has {current.natoms} atoms but {mapping[frame_index]} "
                    f"has {len(data.tensors)} BEC tensors"
                )
            if data.labels and tuple(labels) != data.labels:
                raise ValueError(
                    f"Atom order mismatch for frame {frame_index}: extxyz={labels}, "
                    f"BEC={list(data.labels)}"
                )
            qnep = _qnep_tensors(data)
            property_text = match.group(2)
            quoted = property_text.startswith('"')
            raw_properties = property_text[1:-1] if quoted else property_text
            new_properties = raw_properties + ":bec:R:9"
            if quoted:
                new_properties = f'"{new_properties}"'
            output_header = output_header[:match.start(2)] + new_properties + output_header[match.end(2):]
            output_atoms = [
                f"{line} "
                + " ".join(
                    f"{value:.{QNEP_BEC_OUTPUT_PRECISION}f}"
                    for value in tensor.reshape(9)
                )
                for line, tensor in zip(current.atoms, qnep)
            ]
            acoustic = np.sum(data.tensors, axis=0)
            entry.update(
                bec_labeled=True,
                bec_source=str(mapping[frame_index]),
                input_convention=data.convention,
                qnep_transform="transpose_zstar_to_field_rows",
                acoustic_sum_max_abs_e=float(np.max(np.abs(acoustic))),
            )
        output_lines.extend([str(current.natoms), output_header, *output_atoms])
        frame_audit.append(entry)

    target = Path(output_xyz).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(output_lines) + "\n", encoding="utf-8", newline="\n")
    summary = {
        "schema_version": 1,
        "format": "gpumd-qnep-extxyz",
        "input": str(Path(input_xyz).resolve()),
        "output": str(target),
        "frames": len(frames),
        "labeled_frames": sum(item["bec_labeled"] for item in frame_audit),
        "unlabeled_frames": sum(not item["bec_labeled"] for item in frame_audit),
        "bec_unit": "elementary_charge_e",
        "qnep_tensor_convention": "row-major rows=electric field/polarization; columns=force/displacement",
        "frames_detail": frame_audit,
    }
    audit = Path(audit_output).resolve() if audit_output else target.with_suffix(target.suffix + ".audit.json")
    audit.write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")
    summary["audit_output"] = str(audit)
    return summary


def check_qnep_dataset(path: str | Path, *, audit_output: str | Path | None = None) -> dict:
    frames = read_extxyz(path)
    details: list[dict] = []
    elements: set[str] = set()
    for index, frame in enumerate(frames):
        _require_header_key(frame.header, "lattice")
        _require_header_key(frame.header, "energy")
        _match, properties = _properties(frame.header)
        labels = _frame_labels(frame, properties)
        elements.update(labels)
        _property_offset(properties, "pos")
        if not any(name.lower() in {"force", "forces"} for name, _kind, _width in properties):
            raise ValueError(f"Frame {index} has no force/forces property")
        bec = next((item for item in properties if item[0].lower() == "bec"), None)
        if bec is not None and (bec[1].upper(), bec[2]) != ("R", 9):
            raise ValueError(f"Frame {index} BEC property must be bec:R:9")
        details.append({"frame": index, "natoms": frame.natoms, "has_bec": bec is not None})
    summary = {
        "schema_version": 1,
        "format": "gpumd-qnep-extxyz",
        "path": str(Path(path).resolve()),
        "frames": len(frames),
        "labeled_frames": sum(item["has_bec"] for item in details),
        "elements": sorted(elements),
        "valid": True,
        "frames_detail": details,
    }
    if audit_output:
        target = Path(audit_output).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")
        summary["audit_output"] = str(target)
    return summary


def write_qnep_input(
    dataset: str | Path,
    output: str | Path = "nep.in",
    *,
    charge_mode: int = 2,
    lambda_z: float = 0.5,
) -> Path:
    if charge_mode not in {1, 2}:
        raise ValueError("qNEP charge_mode must be 1 or 2")
    if lambda_z < 0:
        raise ValueError("lambda_z must be nonnegative")
    summary = check_qnep_dataset(dataset)
    if summary["labeled_frames"] == 0:
        raise ValueError("Dataset has no bec:R:9 labels")
    elements = summary["elements"]
    target = Path(output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "# Minimal qNEP input generated by ZStar; converge model capacity and training controls.\n"
        f"type {len(elements)} {' '.join(elements)}\n"
        f"charge_mode {charge_mode}\n"
        f"lambda_z {lambda_z:.10g}\n",
        encoding="utf-8",
        newline="\n",
    )
    return target
