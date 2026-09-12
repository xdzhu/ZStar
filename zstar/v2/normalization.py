"""Explicit low-dimensional normalization helpers for v2 response records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from ..dimensions import DimensionSpec
from .units import convert_values


@dataclass(frozen=True)
class NormalizedPolarization:
    """A polarization converted from bulk cell density to an intrinsic object."""

    values: np.ndarray
    unit: str
    normalization: str
    periodic_axes: tuple[str, ...]
    geometric_factor_si: float
    geometric_factor_unit: str
    projection: str
    boundary_condition: str

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=float)
        if values.ndim < 1 or values.shape[-1] != 3 or not np.all(np.isfinite(values)):
            raise ValueError("normalized polarization must be finite with a final Cartesian axis of length 3")
        axes = tuple(str(axis).lower() for axis in self.periodic_axes)
        if len(set(axes)) != len(axes) or any(axis not in {"x", "y", "z"} for axis in axes):
            raise ValueError(f"invalid periodic_axes {axes}")
        if not np.isfinite(float(self.geometric_factor_si)) or float(self.geometric_factor_si) <= 0.0:
            raise ValueError("geometric_factor_si must be finite and positive")
        if not str(self.geometric_factor_unit).strip():
            raise ValueError("geometric_factor_unit must not be empty")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "periodic_axes", axes)

    def to_dict(self) -> dict[str, object]:
        return {
            "values": self.values.tolist(),
            "unit": self.unit,
            "normalization": self.normalization,
            "periodic_axes": list(self.periodic_axes),
            "geometric_factor_si": float(self.geometric_factor_si),
            "geometric_factor_unit": self.geometric_factor_unit,
            "projection": self.projection,
            "boundary_condition": self.boundary_condition,
        }


def _lattice(value: np.ndarray | Iterable[Iterable[float]]) -> np.ndarray:
    lattice = np.asarray(value, dtype=float)
    if lattice.shape != (3, 3) or not np.all(np.isfinite(lattice)):
        raise ValueError("lattice must be a finite (3, 3) array")
    volume = abs(float(np.linalg.det(lattice)))
    if volume <= 1.0e-30:
        raise ValueError("lattice must have a non-zero cell volume")
    return lattice


def _polarization(values: np.ndarray | Iterable[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim < 1 or array.shape[-1] != 3 or not np.all(np.isfinite(array)):
        raise ValueError("polarization must be finite with a final Cartesian axis of length 3")
    return array


def normalize_polarization(
    polarization: np.ndarray | Iterable[float],
    lattice: np.ndarray | Iterable[Iterable[float]],
    *,
    dimensionality: int,
    periodic_axes: Iterable[str] | None = None,
    source_unit: str = "C/m^2",
    lattice_unit: str = "angstrom",
    boundary_condition: str = "explicit_slab_or_wire",
) -> NormalizedPolarization:
    """Convert a bulk polarization density to an explicit low-dimensional form.

    For a 2D slab, the in-plane projection is multiplied by the perpendicular
    cell height ``Omega/A`` and returned in C/m.  For a 1D wire, the component
    along the periodic axis is multiplied by the transverse cell area and
    returned in C.  The open-direction component is projected out rather than
    silently presented as an intrinsic response.  Bulk values are returned
    unchanged.  Molecular (0D) bulk polarization is rejected because its
    observable is a dipole, not a cell-volume polarization.

    This helper performs geometry and units only; it does not establish an
    electrostatic boundary condition or make a piezoelectric/elastic claim.
    """

    values = _polarization(polarization)
    if "".join(str(source_unit).lower().split()) not in {"c/m^2", "c/m2", "c*m^-2"}:
        raise ValueError("source_unit must be C/m^2 for low-dimensional polarization normalization")
    dimensions = DimensionSpec(int(dimensionality), None if periodic_axes is None else tuple(periodic_axes))
    raw_cell = _lattice(lattice)
    try:
        cell_scale = float(convert_values([1.0], lattice_unit, "m")[0])
    except (TypeError, ValueError) as exc:
        raise ValueError("lattice_unit must be a supported length unit") from exc
    cell = raw_cell * cell_scale
    if dimensions.value == 0:
        raise ValueError(
            "dimensionality=0 has no intrinsic bulk C/m^2 polarization; provide a molecular dipole in C*m"
        )
    if dimensions.value == 3:
        return NormalizedPolarization(
            values=values.copy(),
            unit="C/m^2",
            normalization="cell_volume",
            periodic_axes=dimensions.periodic_axes,
            geometric_factor_si=1.0,
            geometric_factor_unit="1",
            projection="identity",
            boundary_condition=boundary_condition,
        )

    indices = tuple("xyz".index(axis) for axis in dimensions.periodic_axes)
    volume = abs(float(np.linalg.det(cell)))
    if dimensions.value == 2:
        first, second = (cell[index] for index in indices)
        area_vector = np.cross(first, second)
        area = float(np.linalg.norm(area_vector))
        if area <= 1.0e-30:
            raise ValueError("periodic slab vectors must span a non-zero area")
        normal = area_vector / area
        open_index = next(index for index in range(3) if index not in indices)
        height = abs(float(np.dot(cell[open_index], normal)))
        if height <= 1.0e-12:
            raise ValueError("open slab vector has zero perpendicular height")
        projector = np.eye(3) - np.outer(normal, normal)
        projected = np.einsum("ab,...b->...a", projector, values) * height
        return NormalizedPolarization(
            values=projected,
            unit="C/m",
            normalization="sheet_area",
            periodic_axes=dimensions.periodic_axes,
            geometric_factor_si=height,
            geometric_factor_unit="m",
            projection="periodic_plane",
            boundary_condition=boundary_condition,
        )

    # dimensionality == 1
    axis = indices[0]
    direction = cell[axis]
    length = float(np.linalg.norm(direction))
    if length <= 1.0e-30:
        raise ValueError("periodic wire vector must have non-zero length")
    axis_vector = direction / length
    cross_section = volume / length
    projected = np.einsum(
        "ab,...b->...a", np.outer(axis_vector, axis_vector), values
    ) * cross_section
    return NormalizedPolarization(
        values=projected,
        unit="C",
        normalization="line_length",
        periodic_axes=dimensions.periodic_axes,
        geometric_factor_si=cross_section,
        geometric_factor_unit="m^2",
        projection="periodic_axis",
        boundary_condition=boundary_condition,
    )
