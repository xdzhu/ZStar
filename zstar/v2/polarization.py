"""Draft Berry-polarization parsing and branch matching for v2.

The parser deliberately returns wrapped values and quanta separately.  A
polarization difference is only physical after a branch has been matched
along a continuous path; no function in this module silently chooses a
ferroelectric branch or zero-fills a missing component.  ABACUS's scalar
``gdir`` value and optional Cartesian tuple are retained separately because a
non-orthogonal cell needs an explicit coordinate transformation before a
Cartesian response tensor can be reconstructed.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence

import numpy as np

from .units import BOHR_RADIUS, ELEMENTARY_CHARGE


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
_POLARIZATION_PATTERN = re.compile(
    rf"\bP\s*=\s*({_NUMBER})\s*\(\s*mod\s*({_NUMBER})\s*\)\s*"
    rf"(?:\(\s*([-+0-9.,EeDd\s]+)\)\s*)?"
    rf"(C\s*/\s*m(?:\^?2|²)|e\s*/\s*bohr(?:\^?2|²)|"
    rf"\(\s*e\s*/\s*(?:Omega|Ω)\s*\)\s*\.\s*bohr|"
    rf"e\s*/\s*\(\s*(?:Omega|Ω)\s*\)\s*\.\s*bohr|"
    rf"e\s*/\s*(?:Omega|Ω)\s*\.\s*bohr)",
    flags=re.IGNORECASE,
)
_AXES = ("x", "y", "z")


def _finite_vector(value: Iterable[float], name: str) -> np.ndarray:
    array = np.asarray(tuple(value), dtype=float)
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite vector of shape (3,)")
    return array


def _normalized_polarization_unit(raw_unit: str) -> str:
    return "".join(raw_unit.lower().split()).replace("²", "^2")


def _polarization_factor(raw_unit: str, *, volume_bohr3: float | None = None) -> float:
    unit = _normalized_polarization_unit(raw_unit)
    if unit in {"c/m^2", "c/m2"}:
        return 1.0
    if unit in {"e/bohr^2", "e/bohr2"}:
        return ELEMENTARY_CHARGE / BOHR_RADIUS**2
    if unit in {
        "e/(omega).bohr",
        "e/omega.bohr",
        "e/(ω).bohr",
        "e/ω.bohr",
        "(e/ω).bohr",
        "(e/omega).bohr",
    }:
        if volume_bohr3 is None or not np.isfinite(float(volume_bohr3)) or float(volume_bohr3) <= 0.0:
            raise ValueError(
                "converting ABACUS (e/Omega).bohr requires positive volume_bohr3"
            )
        return ELEMENTARY_CHARGE / (float(volume_bohr3) * BOHR_RADIUS**2)
    raise ValueError(f"unsupported ABACUS polarization unit {raw_unit!r}")


@dataclass(frozen=True)
class PolarizationComponent:
    """One scalar Berry component, branch quantum, and optional Cartesian tuple."""

    value: float
    quantum: float
    unit: str = "C/m^2"
    raw_unit: str = "C/m^2"
    gdir: int | None = None
    cartesian_value: np.ndarray | None = None

    def __post_init__(self) -> None:
        if not np.isfinite(float(self.value)) or not np.isfinite(float(self.quantum)):
            raise ValueError("polarization value and quantum must be finite")
        if float(self.quantum) <= 0.0:
            raise ValueError("polarization quantum must be positive")
        if self.gdir is not None and int(self.gdir) not in {1, 2, 3}:
            raise ValueError("gdir must be 1, 2, 3, or None")
        if self.cartesian_value is not None:
            vector = _finite_vector(self.cartesian_value, "cartesian_value")
            object.__setattr__(self, "cartesian_value", vector)


def parse_abacus_berry_polarization(
    text: str,
    *,
    volume_bohr3: float | None = None,
) -> PolarizationComponent:
    """Parse a Berry record, preferring direct ``C/m^2`` output.

    ABACUS commonly prints three equivalent records.  The ``e/Omega`` record
    contains the cell volume symbolically and therefore is only converted when
    ``volume_bohr3`` is supplied; a direct ``C/m^2`` record is preferred and
    avoids any ambiguity.
    """

    matches = list(_POLARIZATION_PATTERN.finditer(str(text)))
    if not matches:
        raise ValueError("ABACUS output does not contain a Berry polarization record")
    def priority(match: re.Match[str]) -> tuple[int, int]:
        unit = _normalized_polarization_unit(match.group(4))
        if unit in {"c/m^2", "c/m2"}:
            rank = 0
        elif unit in {"e/bohr^2", "e/bohr2"}:
            rank = 1
        else:
            rank = 2
        return rank, -matches.index(match)

    match = min(matches, key=priority)
    value = float(match.group(1).replace("D", "E").replace("d", "e"))
    quantum = float(match.group(2).replace("D", "E").replace("d", "e"))
    raw_unit = match.group(4)
    factor = _polarization_factor(raw_unit, volume_bohr3=volume_bohr3)
    value *= factor
    quantum *= factor
    if not np.isfinite(value) or not np.isfinite(quantum) or quantum <= 0.0:
        raise ValueError("Berry polarization value and quantum must be finite with positive quantum")
    cartesian_value = None
    if match.group(3) is not None:
        fields = re.split(r"[,\s]+", match.group(3).strip())
        if len(fields) != 3:
            raise ValueError("ABACUS Berry polarization Cartesian tuple must contain three values")
        try:
            cartesian_value = np.asarray(
                [float(field.replace("D", "E").replace("d", "e")) for field in fields],
                dtype=float,
            ) * factor
        except ValueError as exc:
            raise ValueError("ABACUS Berry polarization Cartesian tuple is not numeric") from exc
        if not np.all(np.isfinite(cartesian_value)):
            raise ValueError("ABACUS Berry polarization Cartesian tuple must be finite")
    return PolarizationComponent(
        value=value,
        quantum=quantum,
        raw_unit=raw_unit,
        cartesian_value=cartesian_value,
    )


def _find_abacus_polarization_log(stage: Path, axis: str) -> Path:
    candidates = sorted(stage.glob(f"OUT.*/running_nscf_{axis}.log"))
    candidates.extend(sorted(stage.glob(f"running_nscf_{axis}.log")))
    if len(candidates) != 1:
        raise ValueError(
            f"Expected exactly one ABACUS running_nscf_{axis}.log in {stage}; "
            f"found {len(candidates)}"
        )
    return candidates[0]


def _find_single_abacus_polarization_log(stage: Path) -> Path:
    candidates = sorted(stage.glob("OUT.*/running_nscf.log"))
    candidates.extend(sorted(stage.glob("running_nscf.log")))
    if len(candidates) != 1:
        raise ValueError(
            f"Expected exactly one ABACUS running_nscf.log in {stage}; found {len(candidates)}"
        )
    return candidates[0]


def _read_gdir(stage: Path) -> int:
    input_path = stage / "INPUT"
    if not input_path.is_file():
        raise ValueError(f"ABACUS polarization stage has no INPUT to identify gdir: {input_path}")
    for line in input_path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("#", 1)[0].split()
        if len(fields) >= 2 and fields[0].lower() == "gdir":
            try:
                value = int(fields[1])
            except ValueError as exc:
                raise ValueError(f"invalid ABACUS gdir in {input_path}: {fields[1]!r}") from exc
            if value not in {1, 2, 3}:
                raise ValueError(f"ABACUS gdir must be 1, 2, or 3; got {value}")
            return value
    raise ValueError(f"ABACUS polarization stage INPUT has no gdir: {input_path}")


def _read_volume_bohr3(text: str) -> float | None:
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
    matches = re.findall(rf"Volume\s*\(\s*Bohr\^3\s*\)\s*=\s*({number})", text, flags=re.IGNORECASE)
    if not matches:
        return None
    value = float(matches[-1].replace("D", "E").replace("d", "e"))
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError("ABACUS volume in Berry output must be finite and positive")
    return value


def collect_abacus_polarization_component(
    stage: str | Path,
    *,
    gdir: int | None = None,
) -> PolarizationComponent:
    """Collect one ABACUS ``running_nscf.log`` component.

    ABACUS writes the same filename for each Berry direction; the direction is
    therefore taken from the stage INPUT unless supplied explicitly.  The
    result remains a wrapped scalar and is not branch-matched here.
    """

    directory = Path(stage).resolve()
    log = _find_single_abacus_polarization_log(directory)
    direction = _read_gdir(directory) if gdir is None else int(gdir)
    if direction not in {1, 2, 3}:
        raise ValueError("gdir must be 1, 2, or 3")
    text = log.read_text(encoding="utf-8", errors="replace")
    component = parse_abacus_berry_polarization(text, volume_bohr3=_read_volume_bohr3(text))
    return PolarizationComponent(
        value=component.value,
        quantum=component.quantum,
        unit=component.unit,
        raw_unit=component.raw_unit,
        gdir=direction,
        cartesian_value=component.cartesian_value,
    )


@dataclass(frozen=True)
class PolarizationSample:
    """Three lattice-axis scalar components, all normalized to C/m².

    This container does not imply that the three scalars form a Cartesian
    vector for a non-orthogonal cell; use ``PolarizationComponent``'s retained
    Cartesian tuples and an explicit lattice transformation for that case.
    """

    values: np.ndarray
    quanta: np.ndarray
    axes: tuple[str, str, str] = ("a", "b", "c")
    unit: str = "C/m^2"
    logs: tuple[str, str, str] = ("", "", "")
    raw_units: tuple[str, str, str] = ("", "", "")
    cartesian_values: np.ndarray | None = None

    def __post_init__(self) -> None:
        values = _finite_vector(self.values, "values")
        quanta = _finite_vector(self.quanta, "quanta")
        if np.any(quanta <= 0.0):
            raise ValueError("polarization quanta must be positive")
        if len(self.axes) != 3 or len(set(self.axes)) != 3:
            raise ValueError("polarization axes must contain three distinct labels")
        if self.cartesian_values is not None:
            cartesian = np.asarray(self.cartesian_values, dtype=float)
            if cartesian.shape != (3, 3) or not np.all(np.isfinite(cartesian)):
                raise ValueError("cartesian_values must be a finite array with shape (3, 3)")
            object.__setattr__(self, "cartesian_values", cartesian)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "quanta", quanta)


def collect_abacus_polarization_stage(stage: str | Path) -> PolarizationSample:
    """Collect ``running_nscf_{a,b,c}.log`` without branch unwrapping."""

    directory = Path(stage).resolve()
    components = []
    logs = []
    raw_units = []
    for axis in ("a", "b", "c"):
        log = _find_abacus_polarization_log(directory, axis)
        text = log.read_text(encoding="utf-8", errors="replace")
        component = parse_abacus_berry_polarization(
            text,
            volume_bohr3=_read_volume_bohr3(text),
        )
        components.append(component)
        logs.append(str(log))
        raw_units.append(component.raw_unit)
    cartesian_values = (
        np.asarray([component.cartesian_value for component in components], dtype=float)
        if all(component.cartesian_value is not None for component in components)
        else None
    )
    return PolarizationSample(
        values=np.asarray([component.value for component in components]),
        quanta=np.asarray([component.quantum for component in components]),
        logs=tuple(logs),
        raw_units=tuple(raw_units),
        cartesian_values=cartesian_values,
    )


def collect_abacus_polarization_triplet(
    stages: Mapping[int | str, str | Path] | Iterable[str | Path],
) -> PolarizationSample:
    """Collect one component from each ABACUS ``gdir`` direction.

    ``stages`` may be a mapping keyed by ``1, 2, 3`` (or ``a, b, c``), or an
    iterable of three stage directories whose ``INPUT`` files declare ``gdir``.
    The result is ordered by lattice direction ``a, b, c`` and keeps the
    optional Cartesian tuples separately from the scalar directional values.
    Missing, duplicate, or ambiguous directions are errors rather than an
    implicit ordering convention.
    """

    if isinstance(stages, Mapping):
        if len(stages) != 3:
            raise ValueError("polarization triplet mapping must contain exactly three stages")
        normalized: dict[int, Path] = {}
        for key, stage in stages.items():
            if isinstance(key, str):
                label = key.lower()
                if label not in {"a", "b", "c"}:
                    raise ValueError(f"unsupported polarization direction key {key!r}")
                direction = {"a": 1, "b": 2, "c": 3}[label]
            else:
                direction = int(key)
            directory = Path(stage).resolve()
            if direction not in {1, 2, 3} or direction in normalized:
                raise ValueError("polarization triplet mapping must identify gdir 1, 2, and 3 once each")
            if directory in normalized.values():
                raise ValueError("polarization triplet mapping must use three distinct stage directories")
            normalized[direction] = directory
        if set(normalized) != {1, 2, 3}:
            raise ValueError("polarization triplet mapping must identify gdir 1, 2, and 3")
    else:
        directories = tuple(Path(stage) for stage in stages)
        if len(directories) != 3:
            raise ValueError("polarization triplet iterable must contain exactly three stages")
        normalized = {}
        for directory in directories:
            direction = collect_abacus_polarization_component(directory).gdir
            if direction is None or direction in normalized:
                raise ValueError("polarization triplet stages must have unique gdir 1, 2, and 3")
            normalized[direction] = directory

    components = []
    logs = []
    for index in (1, 2, 3):
        directory = Path(normalized[index]).resolve()
        log = _find_single_abacus_polarization_log(directory)
        components.append(collect_abacus_polarization_component(directory, gdir=index))
        logs.append(str(log))
    cartesian_values = (
        np.asarray([component.cartesian_value for component in components], dtype=float)
        if all(component.cartesian_value is not None for component in components)
        else None
    )
    return PolarizationSample(
        values=np.asarray([component.value for component in components], dtype=float),
        quanta=np.asarray([component.quantum for component in components], dtype=float),
        logs=tuple(logs),
        raw_units=tuple(component.raw_unit for component in components),
        cartesian_values=cartesian_values,
    )


def _quantum_matrix(quantum_vectors: np.ndarray | Iterable[float]) -> np.ndarray:
    array = np.asarray(quantum_vectors, dtype=float)
    if array.shape == (3,):
        matrix = np.diag(array)
    elif array.shape == (3, 3):
        matrix = array
    else:
        raise ValueError(f"quantum_vectors must have shape (3,) or (3, 3); got {array.shape}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("quantum_vectors contains non-finite values")
    return matrix


def _active_axes(periodic_axes: Sequence[str | int] | None) -> tuple[int, ...]:
    if periodic_axes is None:
        return (0, 1, 2)
    indices = []
    for axis in periodic_axes:
        if isinstance(axis, str):
            value = axis.lower()
            if value not in _AXES:
                raise ValueError(f"unsupported periodic axis {axis!r}")
            index = _AXES.index(value)
        else:
            index = int(axis)
            if index < 0 or index >= 3:
                raise ValueError(f"unsupported periodic axis index {axis!r}")
        if index not in indices:
            indices.append(index)
    return tuple(indices)


@dataclass(frozen=True)
class BranchMatch:
    """Nearest branch representative relative to a reference polarization."""

    matched: np.ndarray
    branch_shift: np.ndarray
    delta: np.ndarray
    residual: float
    periodic_axes: tuple[int, ...]

    def __post_init__(self) -> None:
        matched = _finite_vector(self.matched, "matched")
        shift = np.asarray(self.branch_shift, dtype=int)
        delta = _finite_vector(self.delta, "delta")
        if shift.shape != (3,):
            raise ValueError("branch_shift must have shape (3,)")
        if not np.isfinite(float(self.residual)) or float(self.residual) < 0.0:
            raise ValueError("branch residual must be finite and non-negative")
        object.__setattr__(self, "matched", matched)
        object.__setattr__(self, "branch_shift", shift)
        object.__setattr__(self, "delta", delta)


def match_polarization_branch(
    reference: Iterable[float],
    wrapped: Iterable[float],
    quantum_vectors: np.ndarray | Iterable[float],
    *,
    periodic_axes: Sequence[str | int] | None = None,
    search_radius: int = 1,
) -> BranchMatch:
    """Match a wrapped value to ``reference + quantum_lattice``.

    Quantum vectors are columns of a 3x3 matrix; a length-three input denotes
    mutually orthogonal scalar quanta.  Non-periodic components are never
    shifted.  The returned residual is the mismatch that branch shifts cannot
    remove (for example, a real discontinuity or an inconsistent coordinate
    system).
    """

    ref = _finite_vector(reference, "reference")
    value = _finite_vector(wrapped, "wrapped")
    matrix = _quantum_matrix(quantum_vectors)
    axes = _active_axes(periodic_axes)
    radius = int(search_radius)
    if radius < 0:
        raise ValueError("search_radius must be non-negative")
    if not axes:
        return BranchMatch(value, np.zeros(3, dtype=int), value - ref, float(np.linalg.norm(ref - value)), axes)
    active_matrix = matrix[:, axes]
    if np.linalg.matrix_rank(active_matrix) < len(axes):
        raise ValueError("quantum vectors are rank-deficient on the selected periodic axes")
    center = np.rint(np.linalg.pinv(active_matrix) @ (ref - value)).astype(int)
    candidates = []
    for offsets in product(range(-radius, radius + 1), repeat=len(axes)):
        branch = center + np.asarray(offsets, dtype=int)
        candidate = value + active_matrix @ branch
        residual = float(np.linalg.norm(ref - candidate))
        candidates.append((residual, tuple(int(item) for item in branch), candidate))
    _, branch_tuple, matched = min(candidates, key=lambda item: (item[0], item[1]))
    shift = np.zeros(3, dtype=int)
    shift[list(axes)] = np.asarray(branch_tuple, dtype=int)
    residual = float(np.linalg.norm(ref - matched))
    return BranchMatch(matched, shift, matched - ref, residual, axes)


@dataclass(frozen=True)
class PolarizationPath:
    """Sequentially unwrapped polarization values and diagnostics."""

    values: np.ndarray
    branch_shifts: np.ndarray
    residuals: np.ndarray

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=float)
        shifts = np.asarray(self.branch_shifts, dtype=int)
        residuals = np.asarray(self.residuals, dtype=float)
        if values.ndim != 2 or values.shape[1] != 3 or not np.all(np.isfinite(values)):
            raise ValueError("path values must have shape (samples, 3) and be finite")
        if shifts.shape != values.shape or residuals.shape != (values.shape[0],):
            raise ValueError("path diagnostics do not match values")
        if not np.all(np.isfinite(residuals)) or np.any(residuals < 0.0):
            raise ValueError("path residuals must be finite and non-negative")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "branch_shifts", shifts)
        object.__setattr__(self, "residuals", residuals)


@dataclass(frozen=True)
class MatchedPolarizationEnsemble:
    """Reference-matched Cartesian polarization observations over strain stages."""

    actual_strains: np.ndarray
    wrapped_values: np.ndarray
    matched_values: np.ndarray
    branch_shifts: np.ndarray
    residuals: np.ndarray
    quantum_vectors: np.ndarray
    reference_index: int = 0
    periodic_axes: tuple[int, ...] = (0, 1, 2)

    def __post_init__(self) -> None:
        strains = np.asarray(self.actual_strains, dtype=float)
        wrapped = np.asarray(self.wrapped_values, dtype=float)
        matched = np.asarray(self.matched_values, dtype=float)
        shifts = np.asarray(self.branch_shifts, dtype=int)
        residuals = np.asarray(self.residuals, dtype=float)
        quantum = np.asarray(self.quantum_vectors, dtype=float)
        if strains.ndim != 2 or strains.shape[1] != 6 or not np.all(np.isfinite(strains)):
            raise ValueError("actual_strains must have shape (samples, 6) and be finite")
        samples = strains.shape[0]
        for name, value in (("wrapped_values", wrapped), ("matched_values", matched), ("branch_shifts", shifts)):
            if value.shape != (samples, 3):
                raise ValueError(f"{name} must have shape ({samples}, 3)")
        if not np.all(np.isfinite(wrapped)) or not np.all(np.isfinite(matched)):
            raise ValueError("polarization values must be finite")
        if residuals.shape != (samples,) or not np.all(np.isfinite(residuals)) or np.any(residuals < 0.0):
            raise ValueError("residuals must be finite, non-negative and match the sample count")
        if quantum.shape != (samples, 3, 3) or not np.all(np.isfinite(quantum)):
            raise ValueError("quantum_vectors must have shape (samples, 3, 3) and be finite")
        reference_index = int(self.reference_index)
        if reference_index < 0 or reference_index >= samples:
            raise ValueError("reference_index is outside the polarization ensemble")
        periodic_axes = tuple(int(axis) for axis in self.periodic_axes)
        if len(set(periodic_axes)) != len(periodic_axes) or any(axis not in {0, 1, 2} for axis in periodic_axes):
            raise ValueError("periodic_axes must contain distinct Cartesian indices 0, 1, and/or 2")
        object.__setattr__(self, "actual_strains", strains)
        object.__setattr__(self, "wrapped_values", wrapped)
        object.__setattr__(self, "matched_values", matched)
        object.__setattr__(self, "branch_shifts", shifts)
        object.__setattr__(self, "residuals", residuals)
        object.__setattr__(self, "quantum_vectors", quantum)
        object.__setattr__(self, "reference_index", reference_index)
        object.__setattr__(self, "periodic_axes", periodic_axes)


def _ensemble_quantum_matrices(
    quantum_vectors: np.ndarray | Iterable[float],
    samples: int,
) -> np.ndarray:
    array = np.asarray(quantum_vectors, dtype=float)
    if array.shape == (3,):
        matrix = np.diag(array)[None, :, :]
    elif array.shape == (3, 3):
        matrix = array[None, :, :]
    elif array.shape == (samples, 3):
        matrix = np.asarray([np.diag(row) for row in array], dtype=float)
    elif array.shape == (samples, 3, 3):
        matrix = array
    else:
        raise ValueError(
            "quantum_vectors must have shape (3,), (3, 3), (samples, 3), "
            f"or (samples, 3, 3); got {array.shape}"
        )
    if matrix.shape[0] == 1:
        matrix = np.repeat(matrix, samples, axis=0)
    if not np.all(np.isfinite(matrix)):
        raise ValueError("quantum_vectors contains non-finite values")
    return matrix


def match_polarization_ensemble(
    actual_strains: Iterable[Iterable[float]],
    wrapped_values: Iterable[Iterable[float]],
    quantum_vectors: np.ndarray | Iterable[float],
    *,
    reference_index: int = 0,
    periodic_axes: Sequence[str | int] | None = None,
    search_radius: int = 1,
    max_residual: float | None = None,
) -> MatchedPolarizationEnsemble:
    """Match independent strain-stage polarizations to one reference branch.

    Unlike :func:`unwrap_polarization_path`, each stage is matched directly to
    the selected reference, which is appropriate for a ``reference, +η, -η``
    finite-difference ensemble whose directory order is not a continuous path.
    The input polarization values must already be Cartesian and in one unit.
    """

    strains = np.asarray(tuple(tuple(row) for row in actual_strains), dtype=float)
    wrapped = np.asarray(tuple(tuple(row) for row in wrapped_values), dtype=float)
    if strains.ndim != 2 or strains.shape[1] != 6 or strains.shape[0] == 0 or not np.all(np.isfinite(strains)):
        raise ValueError("actual_strains must be a non-empty finite array with shape (samples, 6)")
    if wrapped.shape != (strains.shape[0], 3) or not np.all(np.isfinite(wrapped)):
        raise ValueError("wrapped_values must have shape (samples, 3) and be finite")
    index = int(reference_index)
    if index < 0 or index >= strains.shape[0]:
        raise ValueError("reference_index is outside the polarization ensemble")
    matrices = _ensemble_quantum_matrices(quantum_vectors, strains.shape[0])
    axes = _active_axes(periodic_axes)
    reference = wrapped[index]
    matched = np.empty_like(wrapped)
    shifts = np.zeros_like(wrapped, dtype=int)
    residuals = np.zeros(strains.shape[0], dtype=float)
    matched[index] = reference
    for sample in range(strains.shape[0]):
        if sample == index:
            continue
        result = match_polarization_branch(
            reference,
            wrapped[sample],
            matrices[sample],
            periodic_axes=axes,
            search_radius=search_radius,
        )
        matched[sample] = result.matched
        shifts[sample] = result.branch_shift
        residuals[sample] = result.residual
        if max_residual is not None and result.residual > float(max_residual):
            raise ValueError(
                f"polarization branch residual {result.residual:g} exceeds max_residual {max_residual:g}"
            )
    return MatchedPolarizationEnsemble(
        actual_strains=strains,
        wrapped_values=wrapped,
        matched_values=matched,
        branch_shifts=shifts,
        residuals=residuals,
        quantum_vectors=matrices,
        reference_index=index,
        periodic_axes=axes,
    )


def unwrap_polarization_path(
    wrapped_values: Iterable[Iterable[float]],
    quantum_vectors: np.ndarray | Iterable[float],
    *,
    periodic_axes: Sequence[str | int] | None = None,
    search_radius: int = 1,
    max_residual: float | None = None,
) -> PolarizationPath:
    """Unwrap a path by matching each point to the preceding unwrapped point."""

    values = np.asarray(tuple(tuple(row) for row in wrapped_values), dtype=float)
    if values.ndim != 2 or values.shape[1] != 3 or values.shape[0] == 0 or not np.all(np.isfinite(values)):
        raise ValueError("wrapped_values must be a non-empty finite array with shape (samples, 3)")
    matrix = np.asarray(quantum_vectors, dtype=float)
    varying = matrix.ndim == 3
    if varying and matrix.shape != (values.shape[0], 3, 3):
        raise ValueError("per-sample quantum_vectors must have shape (samples, 3, 3)")
    if not varying and matrix.shape not in {(3,), (3, 3)}:
        raise ValueError("quantum_vectors must have shape (3,), (3, 3), or (samples, 3, 3)")
    unwrapped = np.empty_like(values)
    shifts = np.zeros_like(values, dtype=int)
    residuals = np.zeros(values.shape[0], dtype=float)
    unwrapped[0] = values[0]
    for index in range(1, values.shape[0]):
        current_quantum = matrix[index] if varying else matrix
        match = match_polarization_branch(
            unwrapped[index - 1],
            values[index],
            current_quantum,
            periodic_axes=periodic_axes,
            search_radius=search_radius,
        )
        unwrapped[index] = match.matched
        shifts[index] = match.branch_shift
        residuals[index] = match.residual
        if max_residual is not None and match.residual > float(max_residual):
            raise ValueError(
                f"polarization branch residual {match.residual:g} exceeds max_residual {max_residual:g}"
            )
    return PolarizationPath(unwrapped, shifts, residuals)
