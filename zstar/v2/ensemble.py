"""Restartable, calculator-neutral perturbation ensembles for v2."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..dimensions import DimensionSpec


def _vector(value: Iterable[float], name: str) -> tuple[float, ...]:
    array = np.asarray(tuple(value), dtype=float)
    if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite, non-empty vector")
    return tuple(float(item) for item in array)


@dataclass(frozen=True)
class PerturbationStage:
    """One planned or completed reference/displacement/strain calculation."""

    stage_id: str
    kind: str
    requested_vector: tuple[float, ...]
    unit: str = "1"
    expected_outputs: tuple[str, ...] = ()
    sign: str = "none"
    actual_vector: tuple[float, ...] | None = None
    status: str = "planned"
    input_hash: str = ""
    result_path: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.stage_id.strip():
            raise ValueError("stage_id must not be empty")
        if self.kind not in {"reference", "displacement", "strain", "field"}:
            raise ValueError(f"unsupported perturbation kind {self.kind!r}")
        if self.sign not in {"none", "+", "-"}:
            raise ValueError("stage sign must be 'none', '+' or '-'")
        if self.status not in {"planned", "running", "complete", "failed", "skipped"}:
            raise ValueError(f"unsupported stage status {self.status!r}")
        if not self.unit.strip():
            raise ValueError("stage unit must not be empty")
        object.__setattr__(self, "requested_vector", _vector(self.requested_vector, "requested_vector"))
        if self.actual_vector is not None:
            object.__setattr__(self, "actual_vector", _vector(self.actual_vector, "actual_vector"))
            if len(self.actual_vector) != len(self.requested_vector):
                raise ValueError("actual_vector and requested_vector dimensions differ")
        object.__setattr__(self, "expected_outputs", tuple(str(item) for item in self.expected_outputs))

    @property
    def fit_ready(self) -> bool:
        return self.status == "complete" and self.actual_vector is not None and bool(self.result_path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "kind": self.kind,
            "requested_vector": list(self.requested_vector),
            "actual_vector": None if self.actual_vector is None else list(self.actual_vector),
            "unit": self.unit,
            "expected_outputs": list(self.expected_outputs),
            "sign": self.sign,
            "status": self.status,
            "input_hash": self.input_hash,
            "result_path": self.result_path,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerturbationStage":
        return cls(
            stage_id=str(data["stage_id"]),
            kind=str(data["kind"]),
            requested_vector=tuple(data["requested_vector"]),
            actual_vector=None if data.get("actual_vector") is None else tuple(data["actual_vector"]),
            unit=str(data.get("unit", "1")),
            expected_outputs=tuple(data.get("expected_outputs", ())),
            sign=str(data.get("sign", "none")),
            status=str(data.get("status", "planned")),
            input_hash=str(data.get("input_hash", "")),
            result_path=str(data.get("result_path", "")),
            error=str(data.get("error", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class ResponseEnsemble:
    """Manifest for a reference-first response task graph."""

    reference_hash: str
    stages: tuple[PerturbationStage, ...]
    dimensionality: int = 3
    schema_version: str = "0.1"
    metadata: dict[str, Any] = field(default_factory=dict)
    periodic_axes: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not self.reference_hash.strip():
            raise ValueError("response ensemble requires a reference_hash")
        dimensions = DimensionSpec(int(self.dimensionality), self.periodic_axes)
        object.__setattr__(self, "dimensionality", dimensions.value)
        object.__setattr__(self, "periodic_axes", dimensions.periodic_axes)
        ids = [stage.stage_id for stage in self.stages]
        if len(set(ids)) != len(ids):
            raise ValueError(f"stage ids must be unique; got {ids}")
        if not self.stages:
            raise ValueError("response ensemble requires at least one stage")

    @property
    def pending(self) -> tuple[PerturbationStage, ...]:
        return tuple(stage for stage in self.stages if stage.status in {"planned", "running"})

    @property
    def completed(self) -> tuple[PerturbationStage, ...]:
        return tuple(stage for stage in self.stages if stage.fit_ready)

    def stage(self, stage_id: str) -> PerturbationStage:
        for stage in self.stages:
            if stage.stage_id == stage_id:
                return stage
        raise KeyError(stage_id)

    def with_stage(self, replacement: PerturbationStage) -> "ResponseEnsemble":
        if replacement.stage_id not in {stage.stage_id for stage in self.stages}:
            raise KeyError(replacement.stage_id)
        return replace(
            self,
            stages=tuple(
                replacement if stage.stage_id == replacement.stage_id else stage
                for stage in self.stages
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "zstar-v2-ensemble",
            "schema_version": self.schema_version,
            "reference_hash": self.reference_hash,
            "dimensionality": self.dimensionality,
            "periodic_axes": list(self.periodic_axes),
            "stages": [stage.to_dict() for stage in self.stages],
            "metadata": self.metadata,
        }

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8", newline="\n")
        temporary.replace(target)
        return target.resolve()

    @classmethod
    def read(cls, path: str | Path) -> "ResponseEnsemble":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema") != "zstar-v2-ensemble":
            raise ValueError("not a zstar-v2-ensemble manifest")
        return cls(
            reference_hash=str(data["reference_hash"]),
            stages=tuple(PerturbationStage.from_dict(item) for item in data["stages"]),
            dimensionality=int(data.get("dimensionality", 3)),
            periodic_axes=None if data.get("periodic_axes") is None else tuple(data["periodic_axes"]),
            schema_version=str(data.get("schema_version", "")),
            metadata=dict(data.get("metadata", {})),
        )


def plan_central_stages(
    vectors: Iterable[Iterable[float]],
    *,
    kind: str,
    unit: str = "1",
    expected_outputs: Iterable[str] = (),
    prefix: str | None = None,
) -> tuple[PerturbationStage, ...]:
    """Create deterministic ± stages; actual vectors are filled after serialization."""

    clean_vectors = [tuple(_vector(vector, "vector")) for vector in vectors]
    if not clean_vectors:
        raise ValueError("at least one perturbation vector is required")
    label = prefix or kind
    outputs = tuple(str(item) for item in expected_outputs)
    stages = []
    for index, vector in enumerate(clean_vectors, start=1):
        for sign, factor in (("-", -1.0), ("+", 1.0)):
            requested = tuple(factor * value for value in vector)
            stages.append(
                PerturbationStage(
                    stage_id=f"{label}-{index:03d}{sign}",
                    kind=kind,
                    requested_vector=requested,
                    unit=unit,
                    expected_outputs=outputs,
                    sign=sign,
                )
            )
    return tuple(stages)


class V2StateStore:
    """Atomic stage state under ``.zstar/v2`` without touching v1 state."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve() / ".zstar" / "v2"
        self.stage_root = self.root / "stages"
        self.stage_root.mkdir(parents=True, exist_ok=True)

    def path_for(self, stage_id: str) -> Path:
        if not stage_id or any(token in stage_id for token in ("/", "\\", "..")):
            raise ValueError("stage_id must be a safe relative identifier")
        return self.stage_root / f"{stage_id}.json"

    def write_stage(self, stage: PerturbationStage) -> Path:
        target = self.path_for(stage.stage_id)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(json.dumps(stage.to_dict(), indent=2), encoding="utf-8", newline="\n")
        temporary.replace(target)
        return target

    def read_stage(self, stage_id: str) -> PerturbationStage:
        return PerturbationStage.from_dict(json.loads(self.path_for(stage_id).read_text(encoding="utf-8")))
