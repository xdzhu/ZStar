"""Calculator capability declarations for the v2 research layer.

Capabilities are deliberately descriptive: declaring a backend feature does
not execute a calculation or imply that a particular material has passed its
physical validation gate.  Adapters should construct one record after
checking their executable/version and input restrictions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


class CapabilityError(ValueError):
    """Raised when a requested response is outside a backend contract."""


_FEATURES = {
    "polarization",
    "force",
    "stress",
    "bec",
    "force_constants",
    "homogeneous_strain",
    "relaxation",
    "finite_field",
    "dfpt",
}


@dataclass(frozen=True)
class BackendCapabilities:
    """Explicit, calculator-neutral statement of adapter support.

    ``supports`` only describes the adapter surface.  Runtime validation still
    needs to check structure dimensionality, insulating status, boundary
    conditions, units, and actual output files.
    """

    backend: str
    version: str = ""
    features: frozenset[str] = frozenset()
    max_dimensionality: int = 3
    metallic_polarization: bool = False
    units: Mapping[str, str] = field(default_factory=dict)
    restrictions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.backend.strip():
            raise ValueError("backend capability record requires a backend name")
        if int(self.max_dimensionality) not in {0, 1, 2, 3}:
            raise ValueError("max_dimensionality must be 0, 1, 2, or 3")
        features = frozenset(str(feature).strip().lower() for feature in self.features)
        unknown = sorted(features - _FEATURES)
        if unknown:
            raise ValueError(f"unknown backend capability feature(s): {unknown}")
        object.__setattr__(self, "features", features)
        object.__setattr__(self, "max_dimensionality", int(self.max_dimensionality))
        object.__setattr__(self, "units", {str(key): str(value) for key, value in self.units.items()})
        object.__setattr__(self, "restrictions", tuple(str(item) for item in self.restrictions))

    def supports(self, feature: str) -> bool:
        """Return whether a normalized feature is declared by this adapter."""

        return str(feature).strip().lower() in self.features

    def require(
        self,
        features: Iterable[str],
        *,
        dimensionality: int | None = None,
        insulating: bool | None = None,
    ) -> None:
        """Validate a response request and raise an actionable error.

        ``insulating=False`` is rejected for polarization unless the adapter
        explicitly declares a metallic-polarization method.  The default is
        intentionally conservative because ordinary Berry polarization is not
        defined for a metal.
        """

        requested = tuple(str(feature).strip().lower() for feature in features)
        missing = sorted({feature for feature in requested if feature not in self.features})
        if missing:
            raise CapabilityError(
                f"backend {self.backend!r} does not provide: {', '.join(missing)}. "
                "Choose a backend with that capability, restrict the request to "
                "supported response terms, or stop before submitting the task."
            )
        if dimensionality is not None:
            dimension = int(dimensionality)
            if dimension not in {0, 1, 2, 3}:
                raise CapabilityError("dimensionality must be 0, 1, 2, or 3")
            if dimension > self.max_dimensionality:
                raise CapabilityError(
                    f"backend {self.backend!r} supports dimensionality <= "
                    f"{self.max_dimensionality}, not {dimension}; supply an adapter "
                    "with an explicit low-dimensional normalization."
                )
        if insulating is False and "polarization" in requested and not self.metallic_polarization:
            raise CapabilityError(
                f"backend {self.backend!r} cannot collect Berry polarization for a metal. "
                "Verify an insulating gap or use a separately validated metallic-response method."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "version": self.version,
            "features": sorted(self.features),
            "max_dimensionality": self.max_dimensionality,
            "metallic_polarization": self.metallic_polarization,
            "units": dict(self.units),
            "restrictions": list(self.restrictions),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BackendCapabilities":
        return cls(
            backend=str(data["backend"]),
            version=str(data.get("version", "")),
            features=frozenset(str(item) for item in data.get("features", ())),
            max_dimensionality=int(data.get("max_dimensionality", 3)),
            metallic_polarization=bool(data.get("metallic_polarization", False)),
            units=dict(data.get("units", {})),
            restrictions=tuple(str(item) for item in data.get("restrictions", ())),
        )
