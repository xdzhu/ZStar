"""Calculator-neutral sparse-BEC datasets and qNEP extended-XYZ export.

The format is intentionally small and JSONL based: one JSON object per frame,
with explicit ``born_effective_charges_available`` instead of a sentinel zero
tensor.  It is a preparation/validation bridge; it does not train an MLIP.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from .qnep_dataset import _properties, _property_offset, read_bec_data, read_extxyz

SCHEMA_VERSION = 1
REQUIRED = ("frame_id", "structure_id", "chemical_symbols", "cell", "positions")


def _array(value: Any, shape: tuple[int, ...], name: str) -> list:
    arr = np.asarray(value, dtype=float)
    if arr.shape != shape:
        raise ValueError(f"{name} must have shape {shape}, got {arr.shape}")
    return arr.tolist()


@dataclass
class ChargeAwareFrame:
    frame_id: str
    structure_id: str
    chemical_symbols: list[str]
    cell: list[list[float]]
    positions: list[list[float]]
    pbc: list[bool]
    total_charge: float = 0.0
    energy: float | None = None
    forces: list[list[float]] | None = None
    stress: list[float] | None = None
    polarization: list[float] | None = None
    dipole: list[float] | None = None
    born_effective_charges: list[list[list[float]]] | None = None
    born_effective_charges_available: bool = False
    calculator: str | None = None
    exchange_correlation: str | None = None
    pseudopotential: str | None = None
    orbital: str | None = None
    kpoints: str | None = None
    ecut: float | None = None
    temperature: float | None = None
    phase_label: str | None = None
    source_directory: str | None = None
    source_manifest: str | None = None
    source_commit: str | None = None
    units: dict[str, str] | None = None
    coordinate_convention: str = "cartesian_A"
    atom_order: list[str] | None = None
    validation_status: str = "unvalidated"
    split: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        n = len(self.chemical_symbols)
        if not self.frame_id or not self.structure_id:
            raise ValueError("frame_id and structure_id are required")
        if len(self.positions) != n:
            raise ValueError("positions and chemical_symbols lengths differ")
        _array(self.cell, (3, 3), "cell")
        for pos in self.positions:
            if len(pos) != 3:
                raise ValueError("positions must have shape (N, 3)")
        if self.forces is not None:
            if len(self.forces) != n or any(len(row) != 3 for row in self.forces):
                raise ValueError("forces must have shape (N, 3)")
        if self.stress is not None and len(self.stress) not in {6, 9}:
            raise ValueError("stress must contain 6 or 9 components")
        if self.pbc is None or len(self.pbc) != 3:
            raise ValueError("pbc must have three booleans")
        if self.atom_order is None:
            self.atom_order = list(self.chemical_symbols)
        if self.atom_order != self.chemical_symbols:
            raise ValueError("atom_order must match chemical_symbols")
        if self.born_effective_charges_available:
            if self.born_effective_charges is None:
                raise ValueError("available BEC requires born_effective_charges")
            _array(self.born_effective_charges, (n, 3, 3), "born_effective_charges")
        elif self.born_effective_charges is not None:
            raise ValueError("missing BEC must be represented by null plus availability=false")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ChargeAwareFrame":
        missing = [key for key in REQUIRED if key not in data]
        if missing:
            raise ValueError(f"frame missing required fields: {', '.join(missing)}")
        payload = dict(data)
        payload.setdefault("pbc", [True, True, True])
        payload.setdefault("born_effective_charges_available", False)
        payload.setdefault("units", {"length": "angstrom", "energy": "eV", "force": "eV/angstrom", "bec": "e"})
        payload.setdefault("coordinate_convention", "cartesian_A")
        return cls(**{field: payload[field] for field in cls.__dataclass_fields__ if field in payload})

    def to_mapping(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items()}


def _deepmd_array(path: Path, name: str) -> np.ndarray | None:
    """Read one DeepMD-npy field from a root or concatenated ``set.*`` folders."""
    direct = path / f"{name}.npy"
    if direct.is_file():
        return np.asarray(np.load(direct, allow_pickle=False))
    chunks: list[np.ndarray] = []
    for folder in sorted(path.glob("set.*")):
        candidate = folder / f"{name}.npy"
        if candidate.is_file():
            chunks.append(np.asarray(np.load(candidate, allow_pickle=False)))
    if not chunks:
        return None
    return np.concatenate(chunks, axis=0)


def _deepmd_types(path: Path, natoms: int) -> list[str]:
    raw = path / "type.raw"
    if not raw.is_file():
        raw = next(iter(sorted(path.glob("set.*/type.raw"))), raw)
    if not raw.is_file():
        raise ValueError(f"DeepMD dataset is missing type.raw: {path}")
    values = [int(item) for item in raw.read_text(encoding="utf-8").split()]
    if len(values) != natoms:
        raise ValueError(f"DeepMD type.raw has {len(values)} atoms, expected {natoms}")
    type_map = path / "type_map.raw"
    names = type_map.read_text(encoding="utf-8").split() if type_map.is_file() else []
    return [names[item] if 0 <= item < len(names) else str(item) for item in values]


def read_deepmd_dataset(path: str | Path, *, metadata: str | Path | None = None) -> list[ChargeAwareFrame]:
    """Read a compact DeepMD ``deepmd/npy`` dataset without requiring dpdata.

    This is intentionally a reader/selection bridge.  It accepts the standard
    ``coord.npy``, ``box.npy``, ``energy.npy``, ``force.npy`` and optional
    ``virial.npy`` fields either at the dataset root or under ``set.*`` folders.
    Temperatures and phase labels are supplied by an optional CSV with columns
    ``frame_id,temperature,phase_label``; they are never guessed from paths.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError(f"DeepMD dataset must be a directory: {root}")
    coord = _deepmd_array(root, "coord")
    box = _deepmd_array(root, "box")
    if coord is None or box is None:
        raise ValueError(f"DeepMD dataset requires coord.npy and box.npy: {root}")
    if coord.ndim == 2:
        type_path = root / "type.raw"
        if not type_path.is_file():
            type_path = next(iter(sorted(root.glob("set.*/type.raw"))), type_path)
        natoms = len(type_path.read_text(encoding="utf-8").split()) if type_path.is_file() else 0
        if natoms <= 0 or coord.shape[1] != natoms * 3:
            raise ValueError("DeepMD coord.npy must have shape (frames, natoms*3)")
        coord = coord.reshape((-1, natoms, 3))
    if coord.ndim != 3 or coord.shape[2] != 3:
        raise ValueError(f"DeepMD coord.npy must have shape (frames,natoms,3), got {coord.shape}")
    nframes, natoms, _ = coord.shape
    if box.ndim == 2 and box.shape[1] == 9:
        box = box.reshape((-1, 3, 3))
    if box.shape != (nframes, 3, 3):
        raise ValueError(f"DeepMD box.npy must have shape ({nframes},3,3), got {box.shape}")
    symbols = _deepmd_types(root, natoms)
    force = _deepmd_array(root, "force")
    if force is not None:
        force = force.reshape((nframes, natoms, 3))
    energy = _deepmd_array(root, "energy")
    if energy is not None:
        energy = energy.reshape((-1,))
    virial = _deepmd_array(root, "virial")
    if virial is not None:
        virial = virial.reshape((nframes, -1))
    metadata_rows: dict[str, dict[str, str]] = {}
    metadata_path = Path(metadata).resolve() if metadata else (root / "metadata.csv")
    if metadata_path.is_file():
        with metadata_path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                if row.get("frame_id"):
                    metadata_rows[str(row["frame_id"])] = row
    frames: list[ChargeAwareFrame] = []
    for index in range(nframes):
        frame_id = str(index)
        row = metadata_rows.get(frame_id, {})
        stress = virial[index].tolist() if virial is not None else None
        frames.append(ChargeAwareFrame(
            frame_id=frame_id,
            structure_id=row.get("structure_id", f"deepmd-{index}"),
            chemical_symbols=list(symbols),
            cell=box[index].tolist(),
            positions=coord[index].tolist(),
            pbc=[True, True, True],
            total_charge=float(row["total_charge"]) if row.get("total_charge") else 0.0,
            energy=float(energy[index]) if energy is not None and index < len(energy) else None,
            forces=force[index].tolist() if force is not None else None,
            stress=stress,
            temperature=float(row["temperature"]) if row.get("temperature") else None,
            phase_label=row.get("phase_label") or None,
            split=row.get("split") or None,
            source_directory=str(root),
            source_manifest=str(metadata_path) if metadata_path.is_file() else None,
            calculator="deepmd-npy",
            units={"length": "angstrom", "energy": "eV", "force": "eV/angstrom", "stress": "eV/angstrom^3", "bec": "e"},
            coordinate_convention="cartesian_A",
            metadata={"source_format": "deepmd/npy", "type_map": symbols},
        ))
    return frames


def read_abacus_dataset(path: str | Path, *, metadata: str | Path | None = None) -> list[ChargeAwareFrame]:
    """Read labelled ABACUS SCF/relaxation directories through optional dpdata.

    ABACUS output parsing is deliberately optional: ordinary ZStar installs do
    not need ``dpdata``.  The adapter only normalizes the labelled structural
    and mechanical arrays; BECs remain separate annotations produced by the
    existing ZStar/PYATB workflow.  A directory must contain ``STRU`` and an
    ``OUT.*`` result directory.  The accepted dpdata keys are the standard
    ``coords/cells/energies/forces/virials`` arrays.
    """
    root = Path(path).resolve()
    if not root.is_dir() or not (root / "STRU").is_file() or not list(root.glob("OUT.*")):
        raise ValueError(f"ABACUS dataset requires STRU and OUT.* under {root}")
    try:
        import dpdata  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Reading ABACUS labelled directories requires optional dependency "
            "'dpdata'; install it in the external-data environment only"
        ) from exc
    system = None
    errors: list[str] = []
    for fmt in ("abacus/scf", "abacus/relax", "abacus"):
        try:
            system = dpdata.LabeledSystem(str(root), fmt=fmt)
            if len(system) > 0:
                break
        except Exception as exc:  # different dpdata releases expose different fmt names
            errors.append(f"{fmt}: {exc}")
            system = None
    if system is None or len(system) == 0:
        detail = "; ".join(errors[-3:])
        raise ValueError(f"dpdata could not read labelled ABACUS output {root}: {detail}")
    data = system.data
    coords = np.asarray(data.get("coords"), dtype=float)
    cells = np.asarray(data.get("cells"), dtype=float)
    if coords.ndim != 3 or coords.shape[2] != 3 or cells.shape != (len(coords), 3, 3):
        raise ValueError(f"dpdata ABACUS arrays have incompatible shapes: coords={coords.shape}, cells={cells.shape}")
    names = list(data.get("atom_names") or data.get("symbols") or [])
    if not names:
        raise ValueError("dpdata ABACUS output did not provide atom_names")
    type_indices = np.asarray(data.get("atom_types", data.get("atom_type")), dtype=int)
    symbols = [names[int(index)] for index in type_indices]
    energies = data.get("energies")
    forces = data.get("forces")
    virials = data.get("virials")
    metadata_rows: dict[str, dict[str, str]] = {}
    metadata_path = Path(metadata).resolve() if metadata else (root / "metadata.csv")
    if metadata_path.is_file():
        with metadata_path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                if row.get("frame_id"):
                    metadata_rows[str(row["frame_id"])] = row
    frames: list[ChargeAwareFrame] = []
    for index, position in enumerate(coords):
        frame_id = str(index)
        row = metadata_rows.get(frame_id, {})
        frame_forces = None if forces is None else np.asarray(forces[index], dtype=float).tolist()
        stress = None if virials is None else np.asarray(virials[index], dtype=float).reshape(-1).tolist()
        frames.append(ChargeAwareFrame(
            frame_id=frame_id,
            structure_id=row.get("structure_id", f"abacus-{index}"),
            chemical_symbols=list(symbols),
            cell=cells[index].tolist(),
            positions=np.asarray(position, dtype=float).tolist(),
            pbc=[True, True, True],
            energy=None if energies is None else float(np.asarray(energies).reshape(-1)[index]),
            forces=frame_forces,
            stress=stress,
            temperature=float(row["temperature"]) if row.get("temperature") else None,
            phase_label=row.get("phase_label") or None,
            source_directory=str(root),
            source_manifest=str(metadata_path) if metadata_path.is_file() else None,
            calculator="abacus-dpdata",
            exchange_correlation=row.get("exchange_correlation") or None,
            pseudopotential=row.get("pseudopotential") or None,
            orbital=row.get("orbital") or None,
            kpoints=row.get("kpoints") or None,
            ecut=float(row["ecut"]) if row.get("ecut") else None,
            units={"length": "angstrom", "energy": "eV", "force": "eV/angstrom", "stress": "eV/angstrom^3", "bec": "e"},
            coordinate_convention="cartesian_A",
            metadata={"source_format": "abacus", "dpdata_format": getattr(system, "fmt", None)},
        ))
    return frames


def read_charge_dataset(path: str | Path, *, metadata: str | Path | None = None) -> list[ChargeAwareFrame]:
    source = Path(path)
    if source.is_dir():
        # DeepMD directories are detected by their canonical coord/box fields.
        # Other directory-based force-field datasets (e.g. ASE/MACE extxyz)
        # are treated as a generic extended-XYZ source rather than being forced
        # into the DeepMD schema.
        if _deepmd_array(source, "coord") is not None or _deepmd_array(source, "box") is not None:
            return read_deepmd_dataset(source, metadata=metadata)
        if (source / "STRU").is_file() and list(source.glob("OUT.*")):
            return read_abacus_dataset(source, metadata=metadata)
        candidates = [source / name for name in ("dataset.extxyz", "data.extxyz", "dataset.xyz", "data.xyz")]
        candidates.extend(sorted(source.glob("*.extxyz")))
        candidates.extend(sorted(source.glob("*.xyz")))
        for candidate in candidates:
            if candidate.is_file():
                return _read_extxyz_dataset(candidate, metadata=metadata)
        raise ValueError(f"Could not detect DeepMD npy or extxyz dataset in {source}")
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() in {".xyz", ".extxyz"}:
        return _read_extxyz_dataset(source, metadata=metadata)
    if source.suffix.lower() == ".json":
        raw = json.loads(text)
        rows = raw.get("frames", raw) if isinstance(raw, dict) else raw
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"No frames found in {source}")
    return [ChargeAwareFrame.from_mapping(row) for row in rows]


def _header_value(header: str, key: str, default: str | None = None) -> str | None:
    import re
    match = re.search(rf"(?:^|\s){re.escape(key)}=(\"[^\"]*\"|\S+)", header)
    if match is None:
        return default
    value = match.group(1)
    return value[1:-1] if value.startswith('"') and value.endswith('"') else value


def _read_extxyz_dataset(source: Path, *, metadata: str | Path | None = None) -> list[ChargeAwareFrame]:
    metadata_rows: dict[str, dict[str, str]] = {}
    metadata_path = Path(metadata).resolve() if metadata else (source.parent / "metadata.csv")
    if metadata_path.is_file():
        with metadata_path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                if row.get("frame_id"):
                    metadata_rows[str(row["frame_id"])] = row
    rows: list[ChargeAwareFrame] = []
    for index, raw in enumerate(read_extxyz(source)):
        _match, properties = _properties(raw.header)
        species_offset, _ = _property_offset(properties, "species")
        pos_offset, pos_width = _property_offset(properties, "pos")
        force_name = next((name for name, _kind, _width in properties if name.lower() in {"force", "forces", "ref_force", "ref_forces", "dft_force", "dft_forces"}), None)
        force_offset, force_width = _property_offset(properties, force_name) if force_name else (0, 0)
        bec_item = next((item for item in properties if item[0].lower() == "bec"), None)
        bec_offset = _property_offset(properties, "bec")[0] if bec_item else 0
        symbols: list[str] = []
        positions: list[list[float]] = []
        forces: list[list[float]] = []
        becs: list[list[list[float]]] = []
        for line in raw.atoms:
            fields = line.split()
            symbols.append(fields[species_offset])
            positions.append([float(x) for x in fields[pos_offset:pos_offset + pos_width]])
            if force_name:
                forces.append([float(x) for x in fields[force_offset:force_offset + force_width]])
            if bec_item:
                flat = [float(x) for x in fields[bec_offset:bec_offset + 9]]
                becs.append(np.asarray(flat, dtype=float).reshape(3, 3).T.tolist())
        lattice = _header_value(raw.header, "Lattice")
        if lattice is None:
            raise ValueError(f"Frame {index} in {source} has no Lattice")
        cell = np.asarray([float(x) for x in lattice.split()], dtype=float).reshape(3, 3).tolist()
        frame_id = _header_value(raw.header, "frame_id", str(index))
        frame_id = _header_value(raw.header, "frame_id", str(index))
        meta = metadata_rows.get(str(frame_id), {})
        energy = next((_header_value(raw.header, key) for key in ("energy", "REF_energy", "ref_energy", "dft_energy") if _header_value(raw.header, key) is not None), None)
        stress = next((_header_value(raw.header, key) for key in ("stress", "REF_stress", "ref_stress", "virial", "REF_virial") if _header_value(raw.header, key) is not None), None)
        rows.append(ChargeAwareFrame(
            frame_id=str(frame_id), structure_id=str(meta.get("structure_id") or _header_value(raw.header, "structure_id", "extxyz")),
            chemical_symbols=symbols, cell=cell, positions=positions, pbc=[True, True, True],
            total_charge=float(meta.get("total_charge") or _header_value(raw.header, "total_charge", "0")),
            energy=float(energy) if energy is not None else None, forces=forces or None,
            stress=[float(x) for x in stress.split()] if stress else None,
            temperature=float(meta.get("temperature") or _header_value(raw.header, "temperature")) if (meta.get("temperature") or _header_value(raw.header, "temperature")) else None,
            phase_label=meta.get("phase_label") or _header_value(raw.header, "phase_label"),
            split=meta.get("split") or _header_value(raw.header, "split"),
            born_effective_charges=becs or None, born_effective_charges_available=bool(becs),
            calculator=meta.get("calculator") or _header_value(raw.header, "calculator", "extxyz"),
            exchange_correlation=meta.get("exchange_correlation") or _header_value(raw.header, "exchange_correlation"),
            pseudopotential=meta.get("pseudopotential") or _header_value(raw.header, "pseudopotential"),
            orbital=meta.get("orbital") or _header_value(raw.header, "orbital"),
            kpoints=meta.get("kpoints") or _header_value(raw.header, "kpoints"),
            ecut=float(meta["ecut"]) if meta.get("ecut") else (float(_header_value(raw.header, "ecut")) if _header_value(raw.header, "ecut") else None),
            source_directory=str(source.parent.resolve()), source_manifest=str(metadata_path) if metadata_path.is_file() else None,
            validation_status="imported", metadata={"source_format": "extxyz"},
        ))
    return rows


def write_charge_dataset(frames: Iterable[ChargeAwareFrame], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = list(frames)
    target.write_text("".join(json.dumps(frame.to_mapping(), sort_keys=True) + "\n" for frame in rows), encoding="utf-8", newline="\n")
    return target


def dataset_manifest(frames: Iterable[ChargeAwareFrame], source: str | Path | None = None) -> dict[str, Any]:
    rows = list(frames)
    temperatures = [f.temperature for f in rows if f.temperature is not None]
    phases: dict[str, int] = {}
    splits: dict[str, int] = {}
    for frame in rows:
        if frame.phase_label:
            phases[frame.phase_label] = phases.get(frame.phase_label, 0) + 1
        if frame.split:
            splits[frame.split] = splits.get(frame.split, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "format": "zstar-charge-aware-jsonl",
        "source": str(Path(source).resolve()) if source else None,
        "frames": len(rows),
        "bec_labeled_frames": sum(f.born_effective_charges_available for f in rows),
        "bec_coverage": (sum(f.born_effective_charges_available for f in rows) / len(rows)) if rows else 0.0,
        "temperature_min": min(temperatures) if temperatures else None,
        "temperature_max": max(temperatures) if temperatures else None,
        "phase_counts": phases,
        "split_counts": splits,
        "frame_ids": [f.frame_id for f in rows],
    }


def validate_charge_dataset(
    path: str | Path,
    *,
    report_output: str | Path | None = None,
    metadata: str | Path | None = None,
) -> dict[str, Any]:
    frames = read_charge_dataset(path, metadata=metadata)
    issues: list[str] = []
    seen: set[str] = set()
    signatures: dict[str, str] = {}
    parent_splits: dict[str, set[str]] = defaultdict(set)
    for frame in frames:
        if frame.frame_id in seen:
            issues.append(f"duplicate frame_id: {frame.frame_id}")
        seen.add(frame.frame_id)
        if frame.born_effective_charges_available and np.allclose(frame.born_effective_charges, 0.0):
            issues.append(f"BEC is an all-zero matrix for labeled frame {frame.frame_id}; verify source")
        signature = hashlib.sha256(json.dumps({"symbols": frame.chemical_symbols, "cell": frame.cell, "positions": frame.positions}, sort_keys=True).encode()).hexdigest()
        if signature in signatures:
            issues.append(f"duplicate structure geometry: {frame.frame_id} and {signatures[signature]}")
        signatures[signature] = frame.frame_id
        parent_id = (frame.metadata or {}).get("parent_frame_id")
        if parent_id is not None and frame.split:
            parent_splits[str(parent_id)].add(str(frame.split))
    for parent_id, splits in sorted(parent_splits.items()):
        if len(splits) > 1:
            issues.append(
                f"finite-displacement parent {parent_id} is split across "
                f"{', '.join(sorted(splits))}; split by parent_frame_id to avoid leakage"
            )
    def _kpoint_policy(frame: ChargeAwareFrame) -> str | None:
        metadata = frame.metadata or {}
        # A fixed Gamma 9x9x9 mesh was the primitive-cell representation of
        # the same ABACUS kspacing=0.1 policy used for the 2x2x2 frames.  The
        # explicit provenance tag is written by the BTO DFT collector; keep
        # raw unrelated meshes distinct for generic datasets.
        policy = metadata.get("kpoint_policy")
        if policy:
            normalized = str(policy).lower().replace(" ", "")
            if "kspacing=0.1" in normalized:
                return "abacus-kspacing-0.1"
            return str(policy)
        raw = str(frame.kpoints or "")
        if "kspacing=0.1" in raw.lower().replace(" ", ""):
            return "abacus-kspacing-0.1"
        return frame.kpoints

    settings = {
        (f.calculator, f.exchange_correlation, f.pseudopotential, f.orbital, _kpoint_policy(f), f.ecut)
        for f in frames
    }
    if len(settings) > 1:
        issues.append("mixed calculator/functional/pseudopotential/orbital/k-point/cutoff settings")
    report = dataset_manifest(frames, path) | {"valid": not issues, "issues": issues}
    if report_output:
        target = Path(report_output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        report["report_output"] = str(target.resolve())
    return report


def select_charge_frames(
    path: str | Path,
    output: str | Path,
    *,
    count: int | None = None,
    ratio: float | None = None,
    seed: int = 0,
    phases: Iterable[str] | None = None,
    temperature_bins: Iterable[float] | None = None,
    metadata: str | Path | None = None,
) -> dict[str, Any]:
    frames = read_charge_dataset(path, metadata=metadata)
    if count is None and ratio is None:
        raise ValueError("provide count or ratio")
    if count is not None and count < 1:
        raise ValueError("count must be positive")
    if ratio is not None and not 0 < ratio <= 1:
        raise ValueError("ratio must be in (0, 1]")
    requested = count if count is not None else max(1, round(len(frames) * float(ratio)))
    requested = min(requested, len(frames))
    allowed = set(phases or [])
    candidates = [f for f in frames if not allowed or f.phase_label in allowed]
    if requested > len(candidates):
        raise ValueError("selection requests more frames than the filtered dataset")
    rng = np.random.default_rng(seed)
    bins = sorted(float(x) for x in (temperature_bins or []))
    strata: dict[str, list[ChargeAwareFrame]] = {}
    for frame in candidates:
        if bins and frame.temperature is not None:
            b = sum(frame.temperature >= edge for edge in bins)
            stratum = f"{frame.phase_label or 'unknown'}@Tbin{b}"
        else:
            stratum = frame.phase_label or "unknown"
        strata.setdefault(stratum, []).append(frame)
    keys = sorted(strata)
    chosen: list[ChargeAwareFrame] = []
    # Round-robin stratification guarantees phase/temperature coverage where possible.
    while len(chosen) < requested:
        progressed = False
        for key in keys:
            pool = strata[key]
            if pool and len(chosen) < requested:
                index = int(rng.integers(0, len(pool)))
                chosen.append(pool.pop(index))
                progressed = True
        if not progressed:
            break
    chosen.sort(key=lambda f: f.frame_id)
    write_charge_dataset(chosen, output)
    manifest = dataset_manifest(chosen, output) | {"selection_seed": seed, "selected_from": str(Path(path).resolve()), "selected_frame_ids": [f.frame_id for f in chosen]}
    return manifest


def annotate_bec_dataset(path: str | Path, output: str | Path, mapping_csv: str | Path) -> dict[str, Any]:
    frames = read_charge_dataset(path)
    by_id = {f.frame_id: f for f in frames}
    with Path(mapping_csv).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not {"frame_id", "bec"}.issubset(reader.fieldnames or []):
            raise ValueError("BEC map requires frame_id,bec columns")
        for row in reader:
            frame_id = row["frame_id"]
            if frame_id not in by_id:
                raise ValueError(f"BEC map refers to absent frame_id {frame_id}")
            bec_path = Path(row["bec"])
            if not bec_path.is_absolute():
                bec_path = (Path(mapping_csv).parent / bec_path).resolve()
            bec = read_bec_data(bec_path)
            frame = by_id[frame_id]
            if len(bec.tensors) != len(frame.chemical_symbols):
                raise ValueError(f"BEC atom count mismatch for {frame_id}")
            tensors = np.asarray(bec.tensors, dtype=float)
            if bec.labels and tuple(frame.chemical_symbols) != bec.labels:
                if Counter(frame.chemical_symbols) != Counter(bec.labels):
                    raise ValueError(f"BEC atom order mismatch for {frame_id}")
                positions: dict[str, list[int]] = defaultdict(list)
                for index, label in enumerate(bec.labels):
                    positions[label].append(index)
                used: dict[str, int] = defaultdict(int)
                permutation: list[int] = []
                for symbol in frame.chemical_symbols:
                    index = positions[symbol][used[symbol]]
                    used[symbol] += 1
                    permutation.append(index)
                tensors = tensors[np.asarray(permutation, dtype=int)]
                frame.metadata = dict(
                    frame.metadata or {},
                    bec_source_atom_order=list(bec.labels),
                    bec_reordered_to_frame_atom_order=True,
                )
            frame.born_effective_charges = tensors.tolist()
            frame.born_effective_charges_available = True
            frame.validation_status = "bec-annotated"
            frame.metadata = dict(frame.metadata or {}, bec_source=str(bec_path), bec_convention=bec.convention)
    write_charge_dataset(frames, output)
    return dataset_manifest(frames, output)


def export_qnep_xyz(path: str | Path, output: str | Path) -> dict[str, Any]:
    frames = read_charge_dataset(path)
    lines: list[str] = []
    detail: list[dict[str, Any]] = []
    for frame in frames:
        n = len(frame.chemical_symbols)
        props = "species:S:1:pos:R:3:force:R:3"
        if frame.born_effective_charges_available:
            props += ":bec:R:9"
        header = f'Lattice="' + " ".join(f"{x:.12g}" for row in frame.cell for x in row) + f'" Properties={props} energy={frame.energy if frame.energy is not None else 0.0:.12g} frame_id={frame.frame_id} structure_id={frame.structure_id} total_charge={frame.total_charge:.12g}'
        if frame.stress is not None:
            header += ' stress="' + " ".join(f"{float(x):.12g}" for x in frame.stress) + '"'
        if frame.temperature is not None:
            header += f" temperature={frame.temperature:.12g}"
        if frame.phase_label:
            header += f" phase_label={frame.phase_label}"
        if frame.split:
            header += f" split={frame.split}"
        lines.extend([str(n), header])
        for i, symbol in enumerate(frame.chemical_symbols):
            pos = frame.positions[i]
            force = frame.forces[i] if frame.forces is not None else [0.0, 0.0, 0.0]
            values = [symbol, *pos, *force]
            if frame.born_effective_charges_available:
                # GPUMD expects electric-field/polarization rows; ZStar stores displacement rows.
                values.extend(np.asarray(frame.born_effective_charges[i]).T.reshape(9).tolist())
            lines.append(" ".join(str(v) if isinstance(v, str) else f"{float(v):.10f}" for v in values))
        detail.append({"frame_id": frame.frame_id, "has_bec": frame.born_effective_charges_available, "natoms": n})
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return {"format": "gpumd-qnep-extxyz", "output": str(target.resolve()), "frames": len(frames), "labeled_frames": sum(x["has_bec"] for x in detail), "unlabeled_frames": sum(not x["has_bec"] for x in detail), "frames_detail": detail}
