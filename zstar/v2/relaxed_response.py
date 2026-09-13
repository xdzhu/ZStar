"""Document-level relaxed-ion electromechanical response assembly.

The low-level :func:`zstar.v2.relaxed_piezoelectric` routine intentionally
accepts arrays only.  This module supplies the calculator-neutral bridge from
annotated v2 quantities to that algebra without guessing atom/Cartesian axis
order, BEC units, or the reference-cell volume.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from .algebra import relaxed_piezoelectric
from .mechanical import ENGINEERING_VOIGT
from .model import BoundaryConditions, ResponseDocument, TensorQuantity
from .units import ELEMENTARY_CHARGE


def _quantity(document: ResponseDocument, name: str) -> TensorQuantity:
    try:
        return document.quantity(name)
    except KeyError as exc:
        raise ValueError(f"response document is missing required quantity {name!r}") from exc


def _canonical_unit(unit: str) -> str:
    return "".join(str(unit).strip().lower().split()).replace("²", "^2")


def _require_voigt(quantity: TensorQuantity, name: str) -> None:
    if quantity.voigt_convention != ENGINEERING_VOIGT:
        raise ValueError(
            f"{name} must use engineering Voigt convention {ENGINEERING_VOIGT}; "
            f"got {quantity.voigt_convention}"
        )


def _axis_index(axes: tuple[str, ...], candidates: set[str], label: str) -> int:
    matches = [index for index, axis in enumerate(axes) if axis.strip().lower() in candidates]
    if len(matches) != 1:
        raise ValueError(
            f"{label} requires exactly one explicitly labelled axis from "
            f"{sorted(candidates)}; got {axes}"
        )
    return matches[0]


def _ordered_bec(quantity: TensorQuantity) -> np.ndarray:
    """Return BEC in ``(atom, polarization, displacement)`` order.

    The v1 adapter commonly preserves ``(atom, displacement, polarization)``;
    accepting both explicit orders keeps migration calculator-neutral while
    rejecting anonymous ``(natom, 3, 3)`` arrays.
    """

    values = np.asarray(quantity.values, dtype=float)
    if values.ndim != 3 or values.shape[1:] != (3, 3):
        raise ValueError(
            "born effective charge must have shape (atom, 3, 3); "
            f"got {values.shape}"
        )
    axes = tuple(str(axis).strip().lower() for axis in quantity.axes)
    if len(axes) != 3:
        raise ValueError(
            "born effective charge requires explicit axes "
            "(atom, polarization, displacement); anonymous axes are not accepted"
        )
    atom = _axis_index(axes, {"atom", "site"}, "born effective charge atom axis")
    polarization = _axis_index(
        axes,
        {"polarization", "polarization_cartesian", "electric", "electric_axis"},
        "born effective charge polarization axis",
    )
    displacement = _axis_index(
        axes,
        {"displacement", "displacement_cartesian", "atomic_displacement"},
        "born effective charge displacement axis",
    )
    if len({atom, polarization, displacement}) != 3:
        raise ValueError("born effective charge axes must identify distinct atom/polarization/displacement axes")
    ordered = np.transpose(values, (atom, polarization, displacement))
    if not np.all(np.isfinite(ordered)):
        raise ValueError("born effective charge contains non-finite values")
    return ordered


def _internal_strain_values(quantity: TensorQuantity, natoms: int) -> np.ndarray:
    """Return Lambda in ``(atom, displacement, engineering-Voigt)`` order."""

    values = np.asarray(quantity.values, dtype=float)
    if values.ndim != 3:
        raise ValueError(
            "internal strain must have three axes (atom, displacement, voigt); "
            f"got {values.shape}"
        )
    axes = tuple(str(axis).strip().lower() for axis in quantity.axes)
    if len(axes) != 3:
        raise ValueError("internal strain requires explicit atom/cartesian/Voigt axes")
    atom = _axis_index(axes, {"atom", "site"}, "internal strain atom axis")
    displacement = _axis_index(
        axes,
        {"cartesian", "displacement", "displacement_cartesian", "atomic_displacement"},
        "internal strain displacement axis",
    )
    voigt = _axis_index(axes, {"voigt_engineering", "engineering_voigt"}, "internal strain Voigt axis")
    if len({atom, displacement, voigt}) != 3:
        raise ValueError("internal strain axes must identify distinct atom/displacement/Voigt axes")
    ordered = np.transpose(values, (atom, displacement, voigt))
    if ordered.shape != (natoms, 3, 6):
        raise ValueError(
            "internal strain must contain one 3-vector per BEC atom and six engineering-strain columns; "
            f"got {ordered.shape}, expected ({natoms}, 3, 6)"
        )
    if not np.all(np.isfinite(ordered)):
        raise ValueError("internal strain contains non-finite values")
    return ordered


def _reference_volume_m3(document: ResponseDocument, volume_m3: float | None) -> float:
    if volume_m3 is not None:
        value = float(volume_m3)
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError("volume_m3 must be finite and positive")
        return value
    if document.structure is None or "lattice_angstrom" not in document.structure:
        raise ValueError(
            "relaxed piezo assembly requires volume_m3 or structure['lattice_angstrom']; "
            "the cell volume must not be inferred from a calculator-specific path"
        )
    lattice = np.asarray(document.structure["lattice_angstrom"], dtype=float)
    if lattice.shape != (3, 3) or not np.all(np.isfinite(lattice)):
        raise ValueError("structure['lattice_angstrom'] must be a finite (3, 3) matrix")
    value = abs(float(np.linalg.det(lattice))) * 1.0e-30
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError("structure['lattice_angstrom'] has a non-positive cell volume")
    return value


def derive_relaxed_piezoelectric_response(
    document: ResponseDocument,
    *,
    clamped_piezo_name: str = "piezoelectric_proper",
    born_name: str = "born_effective_charge",
    internal_strain_name: str = "internal_strain",
    volume_m3: float | None = None,
) -> ResponseDocument:
    """Append proper internal and relaxed-ion piezoelectric quantities.

    The input ``clamped_piezo_name`` must be a proper, clamped-ion
    ``C/m^2`` tensor.  BEC values may be dimensionless elementary-charge units
    (``e``) or explicitly SI ``C``; the internal-strain quantity is converted
    from its declared length unit (normally Angstrom) by the shared algebra.
    The cell volume is either supplied explicitly in m³ or calculated from
    the document's reference ``lattice_angstrom``.  Every ambiguity fails
    instead of silently mixing v1 conventions.
    """

    if not isinstance(document, ResponseDocument):
        raise TypeError("document must be a v2 ResponseDocument")
    if document.dimensionality.value != 3:
        raise ValueError("relaxed-ion bulk piezoelectric assembly requires dimensionality=3")
    if tuple(document.dimensionality.periodic_axes) != ("x", "y", "z"):
        raise ValueError("relaxed-ion bulk piezoelectric assembly requires periodic axes ('x', 'y', 'z')")

    clamped = _quantity(document, clamped_piezo_name)
    if np.asarray(clamped.values).shape != (3, 6):
        raise ValueError(f"{clamped_piezo_name!r} must have shape (3, 6)")
    _require_voigt(clamped, clamped_piezo_name)
    if _canonical_unit(clamped.unit) not in {"c/m^2", "c/m2"}:
        raise ValueError(f"{clamped_piezo_name!r} must be explicitly in C/m^2; got {clamped.unit!r}")
    if clamped.ion_relaxation != "clamped-ion":
        raise ValueError(
            f"{clamped_piezo_name!r} must be marked ion_relaxation='clamped-ion'; "
            f"got {clamped.ion_relaxation!r}"
        )
    if clamped.provenance.get("piezoelectric_kind") != "proper":
        raise ValueError(
            f"{clamped_piezo_name!r} must carry provenance piezoelectric_kind='proper'; "
            "apply the explicit proper-piezo correction before relaxed assembly"
        )

    born = _quantity(document, born_name)
    born_values = _ordered_bec(born)
    bec_unit = _canonical_unit(born.unit)
    if bec_unit in {"e", "e_charge", "elementary_charge", "electron_charge"}:
        charge = ELEMENTARY_CHARGE
    elif bec_unit in {"c", "coulomb"}:
        charge = 1.0
    else:
        raise ValueError(
            f"{born_name!r} must use explicit BEC unit 'e' or 'C'; got {born.unit!r}"
        )

    internal = _quantity(document, internal_strain_name)
    lambda_values = _internal_strain_values(internal, born_values.shape[0])
    if internal.ion_relaxation != "relaxed-ion":
        raise ValueError(
            f"{internal_strain_name!r} must be marked ion_relaxation='relaxed-ion'; "
            f"got {internal.ion_relaxation!r}"
        )
    _require_voigt(internal, internal_strain_name)
    volume = _reference_volume_m3(document, volume_m3)

    relaxed, contribution = relaxed_piezoelectric(
        np.asarray(clamped.values, dtype=float),
        born_values,
        lambda_values,
        volume,
        charge=charge,
        internal_strain_unit=internal.unit,
    )
    periodic_axes = document.dimensionality.periodic_axes
    shared_provenance: dict[str, Any] = {
        "definition": "e_relaxed = e_clamped_proper + (charge/volume) sum_i Z*_i Lambda_i",
        "clamped_piezoelectric": clamped_piezo_name,
        "born_effective_charge": born_name,
        "internal_strain": internal_strain_name,
        "bec_input_unit": born.unit,
        "internal_strain_input_unit": internal.unit,
        "volume_m3": volume,
        "voigt_convention": list(ENGINEERING_VOIGT),
        "coordinate_system": clamped.coordinate_system,
    }
    correction_quantity = TensorQuantity(
        name="piezoelectric_internal",
        values=contribution,
        unit="C/m^2",
        axes=("polarization_cartesian", "voigt_engineering"),
        coordinate_system=clamped.coordinate_system,
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="internal-contribution",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
        periodic_axes=periodic_axes,
        normalization=clamped.normalization,
        source="bec_internal_strain_contraction",
        backend=document.backend,
        provenance={**shared_provenance, "piezoelectric_kind": "proper", "term": "internal-strain"},
        diagnostics={
            "contribution_max_C_per_m2": float(np.max(np.abs(contribution))),
        },
    )
    relaxed_quantity = TensorQuantity(
        name="piezoelectric_relaxed",
        values=relaxed,
        unit="C/m^2",
        axes=("polarization_cartesian", "voigt_engineering"),
        coordinate_system=clamped.coordinate_system,
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="relaxed-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
        periodic_axes=periodic_axes,
        normalization=clamped.normalization,
        source="proper_piezoelectric_internal_strain",
        backend=document.backend,
        provenance={**shared_provenance, "piezoelectric_kind": "proper", "term": "clamped-plus-internal"},
        diagnostics={
            "internal_contribution_max_C_per_m2": float(np.max(np.abs(contribution))),
        },
    )
    existing = {quantity.name for quantity in document.quantities}
    duplicates = sorted(existing.intersection({correction_quantity.name, relaxed_quantity.name}))
    if duplicates:
        raise ValueError("response document already contains derived quantity/quantities: " + ", ".join(duplicates))
    metadata = dict(document.metadata)
    metadata["relaxed_piezoelectric_inputs"] = dict(shared_provenance)
    metadata["fitted_quantities"] = list(metadata.get("fitted_quantities", ())) + [
        correction_quantity.name,
        relaxed_quantity.name,
    ]
    provenance = dict(document.provenance)
    provenance["relaxed_piezoelectric_assembly"] = dict(shared_provenance)
    return replace(
        document,
        quantities=document.quantities + (correction_quantity, relaxed_quantity),
        provenance=provenance,
        metadata=metadata,
    )

