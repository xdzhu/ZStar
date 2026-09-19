"""Calculator-neutral response records for the ZStar v2 research API.

The v2 schema is intentionally marked as a draft.  It is isolated from the
v1 ``zstar-response`` schema so that adding electromechanical metadata cannot
change the meaning of existing response files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from ..dimensions import DimensionSpec


V2_SCHEMA_NAME = "zstar-v2-response"
V2_SCHEMA_VERSION = "0.1"
_AXES = {"x", "y", "z"}
_ION_RELAXATION = {"clamped-ion", "relaxed-ion", "internal-contribution", "not-applicable"}
_ELECTRIC_BOUNDARIES = {"E", "D", "open-circuit", "short-circuit", "not-applicable"}
_MECHANICAL_BOUNDARIES = {"strain", "stress", "not-applicable"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _numeric_array(values: Any, name: str) -> np.ndarray:
    try:
        array = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name!r} must be numeric") from exc
    if not array.size:
        raise ValueError(f"{name!r} must not be empty")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name!r} contains non-finite values")
    return array


@dataclass(frozen=True)
class BoundaryConditions:
    """Electrical/mechanical boundary metadata attached to every tensor."""

    electric: str = "E"
    mechanical: str = "strain"
    stress_sign: str = "tension-positive"

    def __post_init__(self) -> None:
        if self.electric not in _ELECTRIC_BOUNDARIES:
            raise ValueError(
                f"unsupported electric boundary {self.electric!r}; "
                f"choose one of {sorted(_ELECTRIC_BOUNDARIES)}"
            )
        if self.mechanical not in _MECHANICAL_BOUNDARIES:
            raise ValueError(
                f"unsupported mechanical boundary {self.mechanical!r}; "
                f"choose one of {sorted(_MECHANICAL_BOUNDARIES)}"
            )
        if not self.stress_sign.strip():
            raise ValueError("stress_sign must not be empty")

    def to_dict(self) -> dict[str, str]:
        return {
            "electric": self.electric,
            "mechanical": self.mechanical,
            "stress_sign": self.stress_sign,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "BoundaryConditions":
        return cls() if data is None else cls(
            electric=str(data.get("electric", "E")),
            mechanical=str(data.get("mechanical", "strain")),
            stress_sign=str(data.get("stress_sign", "tension-positive")),
        )


@dataclass(frozen=True)
class TensorQuantity:
    """A named tensor/scalar with explicit axes, units and provenance."""

    name: str
    values: Any
    unit: str
    axes: tuple[str, ...] = ()
    coordinate_system: str = "cartesian_right_handed"
    voigt_convention: tuple[str, ...] = ()
    ion_relaxation: str = "not-applicable"
    boundary_conditions: BoundaryConditions = field(default_factory=BoundaryConditions)
    periodic_axes: tuple[str, ...] = ("x", "y", "z")
    normalization: str = "cell_volume"
    source: str = ""
    backend: str = ""
    provenance: Mapping[str, Any] = field(default_factory=dict)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("tensor name must not be empty")
        if not self.unit.strip():
            raise ValueError(f"tensor {self.name!r} requires an explicit unit")
        if not self.coordinate_system.strip():
            raise ValueError(f"tensor {self.name!r} requires a coordinate system")
        if self.ion_relaxation not in _ION_RELAXATION:
            raise ValueError(
                f"unsupported ion_relaxation {self.ion_relaxation!r}; "
                f"choose one of {sorted(_ION_RELAXATION)}"
            )
        if not self.normalization.strip():
            raise ValueError(f"tensor {self.name!r} requires normalization")
        axes = tuple(str(axis) for axis in self.axes)
        if len(set(axes)) != len(axes):
            raise ValueError(f"tensor {self.name!r} has duplicate axes: {axes}")
        periodic = tuple(str(axis).lower() for axis in self.periodic_axes)
        if len(set(periodic)) != len(periodic) or any(axis not in _AXES for axis in periodic):
            raise ValueError(f"invalid periodic_axes for {self.name!r}: {periodic}")
        array = _numeric_array(self.values, self.name)
        if axes and len(axes) != array.ndim:
            raise ValueError(
                f"tensor {self.name!r} has shape {array.shape} but {len(axes)} axes"
            )
        object.__setattr__(self, "axes", axes)
        object.__setattr__(self, "periodic_axes", periodic)
        object.__setattr__(self, "values", array)

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(int(size) for size in np.asarray(self.values).shape)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "values": _jsonable(self.values),
            "shape": list(self.shape),
            "unit": self.unit,
            "axes": list(self.axes),
            "coordinate_system": self.coordinate_system,
            "voigt_convention": list(self.voigt_convention),
            "ion_relaxation": self.ion_relaxation,
            "boundary_conditions": self.boundary_conditions.to_dict(),
            "periodic_axes": list(self.periodic_axes),
            "normalization": self.normalization,
            "source": self.source,
            "backend": self.backend,
            "provenance": _jsonable(self.provenance),
            "diagnostics": _jsonable(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TensorQuantity":
        quantity = cls(
            name=str(data["name"]),
            values=data["values"],
            unit=str(data["unit"]),
            axes=tuple(str(axis) for axis in data.get("axes", ())),
            coordinate_system=str(data.get("coordinate_system", "cartesian_right_handed")),
            voigt_convention=tuple(str(item) for item in data.get("voigt_convention", ())),
            ion_relaxation=str(data.get("ion_relaxation", "not-applicable")),
            boundary_conditions=BoundaryConditions.from_dict(data.get("boundary_conditions")),
            periodic_axes=tuple(str(axis) for axis in data.get("periodic_axes", ("x", "y", "z"))),
            normalization=str(data.get("normalization", "cell_volume")),
            source=str(data.get("source", "")),
            backend=str(data.get("backend", "")),
            provenance=dict(data.get("provenance", {})),
            diagnostics=dict(data.get("diagnostics", {})),
        )
        declared_shape = tuple(int(size) for size in data.get("shape", quantity.shape))
        if quantity.shape != declared_shape:
            raise ValueError(
                f"tensor {quantity.name!r} shape {quantity.shape} does not match "
                f"declared shape {declared_shape}"
            )
        return quantity


@dataclass(frozen=True)
class ResponseDocument:
    """Top-level v2 response document, separate from the v1 schema."""

    backend: str
    dimensionality: DimensionSpec
    quantities: tuple[TensorQuantity, ...]
    provenance: Mapping[str, Any]
    structure: Mapping[str, Any] | None = None
    symmetry: Mapping[str, Any] = field(default_factory=dict)
    functional: str = ""
    pseudopotential: str = ""
    orbital: str = ""
    convergence: Mapping[str, Any] = field(default_factory=dict)
    restart_state: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)
    schema: str = V2_SCHEMA_NAME
    schema_version: str = V2_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema != V2_SCHEMA_NAME:
            raise ValueError(f"unsupported v2 response schema {self.schema!r}")
        if self.schema_version != V2_SCHEMA_VERSION:
            raise ValueError(f"unsupported v2 response version {self.schema_version!r}")
        if not self.backend.strip():
            raise ValueError("response backend must not be empty")
        if not self.quantities:
            raise ValueError("response document must contain at least one quantity")
        names = [quantity.name for quantity in self.quantities]
        if len(set(names)) != len(names):
            raise ValueError(f"response quantity names must be unique; got {names}")
        expected_periodic = tuple(self.dimensionality.periodic_axes)
        mismatched_periodic = {
            quantity.name: tuple(quantity.periodic_axes)
            for quantity in self.quantities
            if tuple(quantity.periodic_axes) != expected_periodic
        }
        if mismatched_periodic:
            raise ValueError(
                "response quantity periodic_axes must match document dimensionality "
                f"{expected_periodic}; got {mismatched_periodic}"
            )
        if not self.provenance:
            raise ValueError("response document requires provenance metadata")

    def quantity(self, name: str) -> TensorQuantity:
        for quantity in self.quantities:
            if quantity.name == name:
                return quantity
        raise KeyError(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "backend": self.backend,
            "dimensionality": self.dimensionality.to_dict(),
            "structure": _jsonable(self.structure),
            "symmetry": _jsonable(self.symmetry),
            "functional": self.functional,
            "pseudopotential": self.pseudopotential,
            "orbital": self.orbital,
            "convergence": _jsonable(self.convergence),
            "quantities": [quantity.to_dict() for quantity in self.quantities],
            "provenance": _jsonable(self.provenance),
            "restart_state": _jsonable(self.restart_state),
            "metadata": _jsonable(self.metadata),
        }

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8", newline="\n")
        return target.resolve()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResponseDocument":
        return cls(
            backend=str(data["backend"]),
            dimensionality=DimensionSpec.from_dict(dict(data["dimensionality"])),
            quantities=tuple(TensorQuantity.from_dict(item) for item in data.get("quantities", ())),
            provenance=dict(data.get("provenance", {})),
            structure=None if data.get("structure") is None else dict(data["structure"]),
            symmetry=dict(data.get("symmetry", {})),
            functional=str(data.get("functional", "")),
            pseudopotential=str(data.get("pseudopotential", "")),
            orbital=str(data.get("orbital", "")),
            convergence=dict(data.get("convergence", {})),
            restart_state=dict(data.get("restart_state", {})),
            metadata=dict(data.get("metadata", {})),
            created_at=str(data.get("created_at", _utc_now())),
            schema=str(data.get("schema", "")),
            schema_version=str(data.get("schema_version", "")),
        )

    @classmethod
    def read(cls, path: str | Path) -> "ResponseDocument":
        source = Path(path)
        return cls.from_dict(json.loads(source.read_text(encoding="utf-8")))
