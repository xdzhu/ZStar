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

from .algebra import relaxed_elastic, relaxed_piezoelectric, solve_internal_strain_response
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


def _ordered_force_constants(quantity: TensorQuantity) -> np.ndarray:
    """Return IFCs in ``(atom, force_cartesian, atom, displacement_cartesian)`` order."""

    values = np.asarray(quantity.values, dtype=float)
    if values.ndim != 4:
        raise ValueError(
            "force constants must have four explicit axes (atom_row, atom_column, force, displacement); "
            f"got {values.shape}"
        )
    axes = tuple(str(axis).strip().lower() for axis in quantity.axes)
    if len(axes) != 4:
        raise ValueError("force constants require explicit atom/force/displacement axes")
    atom_row = _axis_index(axes, {"atom_row", "force_atom", "site_row"}, "force constants row atom axis")
    atom_column = _axis_index(
        axes, {"atom_column", "displacement_atom", "site_column"}, "force constants column atom axis"
    )
    force = _axis_index(axes, {"force", "force_cartesian"}, "force constants force axis")
    displacement = _axis_index(
        axes, {"displacement", "displacement_cartesian"}, "force constants displacement axis"
    )
    if len({atom_row, atom_column, force, displacement}) != 4:
        raise ValueError("force constants axes must identify distinct row/column/force/displacement axes")
    ordered = np.transpose(values, (atom_row, force, atom_column, displacement))
    if ordered.shape[1] != 3 or ordered.shape[3] != 3 or ordered.shape[0] != ordered.shape[2]:
        raise ValueError(
            "force constants must contain a square atom block with 3 force and 3 displacement components; "
            f"got {ordered.shape}"
        )
    if not np.all(np.isfinite(ordered)):
        raise ValueError("force constants contain non-finite values")
    natoms = ordered.shape[0]
    return ordered.reshape(3 * natoms, 3 * natoms)


def _ordered_gamma(quantity: TensorQuantity, natoms: int) -> np.ndarray:
    """Return strain-force coupling in ``(atom, cartesian, voigt)`` order."""

    values = np.asarray(quantity.values, dtype=float)
    if values.ndim != 3:
        raise ValueError(f"strain-force coupling must have three explicit axes; got {values.shape}")
    axes = tuple(str(axis).strip().lower() for axis in quantity.axes)
    if len(axes) != 3:
        raise ValueError("strain-force coupling requires explicit atom/cartesian/Voigt axes")
    atom = _axis_index(axes, {"atom", "site"}, "strain-force coupling atom axis")
    cartesian = _axis_index(
        axes, {"cartesian", "force_cartesian", "displacement_cartesian"},
        "strain-force coupling Cartesian axis",
    )
    voigt = _axis_index(axes, {"voigt_engineering", "engineering_voigt"}, "strain-force coupling Voigt axis")
    if len({atom, cartesian, voigt}) != 3:
        raise ValueError("strain-force coupling axes must identify distinct atom/Cartesian/Voigt axes")
    ordered = np.transpose(values, (atom, cartesian, voigt))
    if ordered.shape != (natoms, 3, 6):
        raise ValueError(
            "strain-force coupling must have shape (natom, 3, 6); "
            f"got {ordered.shape}, expected ({natoms}, 3, 6)"
        )
    if not np.all(np.isfinite(ordered)):
        raise ValueError("strain-force coupling contains non-finite values")
    return ordered


def _force_response_units(force_constants: TensorQuantity, gamma: TensorQuantity) -> tuple[str, str, str]:
    """Infer a fully explicit energy/length basis for the unit-aware C fit."""

    def parse(unit: str, power: int) -> tuple[str, str] | None:
        canonical = _canonical_unit(unit).replace("å", "angstrom").replace("²", "^2")
        canonical = canonical.replace("**", "^")
        if power == 2:
            patterns = {
                "ev/angstrom^2": ("eV", "angstrom"),
                "ev/angstrom2": ("eV", "angstrom"),
                "j/m^2": ("J", "m"),
                "j/m2": ("J", "m"),
            }
        else:
            patterns = {
                "ev/angstrom": ("eV", "angstrom"),
                "j/m": ("J", "m"),
            }
        return patterns.get(canonical)

    phi_basis = parse(force_constants.unit, 2)
    gamma_basis = parse(gamma.unit, 1)
    if phi_basis is None or gamma_basis is None or phi_basis != gamma_basis:
        raise ValueError(
            "force_constants and strain_force_coupling units must be a matched explicit "
            "energy/length^2 and energy/length pair (supported: eV/angstrom^2 + "
            "eV/angstrom, or J/m^2 + J/m); got "
            f"{force_constants.unit!r} and {gamma.unit!r}"
        )
    energy, length = phi_basis
    return energy, length, "angstrom3" if length == "angstrom" else "m3"


def derive_relaxed_elastic_response(
    document: ResponseDocument,
    *,
    clamped_elastic_name: str = "elastic",
    force_constants_name: str = "force_constants",
    strain_force_coupling_name: str = "strain_force_coupling",
    volume_m3: float | None = None,
    check_acoustic: bool = False,
    acoustic_tolerance: float = 1.0e-10,
    svd_rcond: float = 1.0e-10,
) -> ResponseDocument:
    """Append relaxed-ion elastic and equilibrium internal-strain quantities.

    ``clamped_elastic_name`` is a clamped-ion, engineering-Voigt stiffness.
    The IFC and Gamma quantities are consumed in their explicitly labelled
    v1/v2 axis orders and matched eV/Angstrom (or J/m) units.  The result is
    rejected when acoustic compatibility is requested but not satisfied; no
    translational projection is applied implicitly.
    """

    if not isinstance(document, ResponseDocument):
        raise TypeError("document must be a v2 ResponseDocument")
    if document.dimensionality.value != 3 or tuple(document.dimensionality.periodic_axes) != ("x", "y", "z"):
        raise ValueError("relaxed-ion bulk elastic assembly requires a three-dimensional periodic document")
    clamped = _quantity(document, clamped_elastic_name)
    c_values = np.asarray(clamped.values, dtype=float)
    if c_values.shape != (6, 6):
        raise ValueError(f"{clamped_elastic_name!r} must have shape (6, 6)")
    _require_voigt(clamped, clamped_elastic_name)
    if clamped.ion_relaxation != "clamped-ion":
        raise ValueError(
            f"{clamped_elastic_name!r} must be marked ion_relaxation='clamped-ion'; "
            f"got {clamped.ion_relaxation!r}"
        )
    phi_quantity = _quantity(document, force_constants_name)
    phi = _ordered_force_constants(phi_quantity)
    gamma_quantity = _quantity(document, strain_force_coupling_name)
    gamma = _ordered_gamma(gamma_quantity, phi.shape[0] // 3)
    energy_unit, length_unit, volume_unit = _force_response_units(phi_quantity, gamma_quantity)
    volume_si = _reference_volume_m3(document, volume_m3)
    volume = volume_si / 1.0e-30 if volume_unit == "angstrom3" else volume_si
    # Run the same audited solver used by the low-level algebra so rank and
    # equilibrium diagnostics are retained alongside the material tensor.
    solution = solve_internal_strain_response(
        phi,
        gamma.reshape(phi.shape[0], 6),
        svd_rcond=svd_rcond,
        check_acoustic=check_acoustic,
        acoustic_tolerance=acoustic_tolerance,
    )
    relaxed, _lambda, correction = relaxed_elastic(
        c_values,
        phi,
        gamma.reshape(phi.shape[0], 6),
        volume,
        svd_rcond=svd_rcond,
        check_acoustic=False,
        energy_unit=energy_unit,
        length_unit=length_unit,
        volume_unit=volume_unit,
        elastic_unit=clamped.unit,
    )
    periodic_axes = document.dimensionality.periodic_axes
    shared = {
        "definition": "C_relaxed = C_clamped - Gamma.T Phi^+ Gamma / volume",
        "clamped_elastic": clamped_elastic_name,
        "force_constants": force_constants_name,
        "strain_force_coupling": strain_force_coupling_name,
        "force_constants_unit": phi_quantity.unit,
        "strain_force_coupling_unit": gamma_quantity.unit,
        "volume_m3": volume_si,
        "voigt_convention": list(ENGINEERING_VOIGT),
        "svd_rcond": float(svd_rcond),
    }
    diagnostics = {
        "internal_strain_rank": int(solution.rank),
        "internal_strain_residual_max": float(solution.residual_max),
        "internal_strain_residual_rms": float(solution.residual_rms),
        "internal_strain_residual_relative": float(solution.residual_relative),
        "internal_strain_translation_gauge_max": float(solution.translation_gauge_max),
        "elastic_internal_correction_max": float(np.max(np.abs(correction))),
        "acoustic_checked": bool(check_acoustic),
    }
    elastic_quantity = TensorQuantity(
        name="elastic_relaxed",
        values=relaxed,
        unit=clamped.unit,
        axes=("stress_voigt", "voigt_engineering"),
        coordinate_system=clamped.coordinate_system,
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="relaxed-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
        periodic_axes=periodic_axes,
        normalization=clamped.normalization,
        source="ifc_internal_strain_relaxation",
        backend=document.backend,
        provenance={**shared, "term": "relaxed-stiffness"},
        diagnostics=diagnostics,
    )
    correction_quantity = TensorQuantity(
        name="elastic_internal_correction",
        values=correction,
        unit=clamped.unit,
        axes=("stress_voigt", "voigt_engineering"),
        coordinate_system=clamped.coordinate_system,
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="internal-contribution",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
        periodic_axes=periodic_axes,
        normalization=clamped.normalization,
        source="ifc_internal_strain_relaxation",
        backend=document.backend,
        provenance={**shared, "term": "clamped-minus-relaxed correction"},
        diagnostics=diagnostics,
    )
    lambda_quantity = TensorQuantity(
        name="internal_strain_equilibrium",
        values=solution.lambda_response.reshape(phi.shape[0] // 3, 3, 6),
        unit=length_unit,
        axes=("atom", "cartesian", "voigt_engineering"),
        coordinate_system=gamma_quantity.coordinate_system,
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="relaxed-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
        periodic_axes=periodic_axes,
        normalization="per_atom",
        source="ifc_internal_strain_solver",
        backend=document.backend,
        provenance={**shared, "term": "Phi-pseudoinverse equilibrium Lambda"},
        diagnostics=diagnostics,
    )
    additions = (elastic_quantity, correction_quantity, lambda_quantity)
    existing = {quantity.name for quantity in document.quantities}
    duplicates = sorted(existing.intersection(quantity.name for quantity in additions))
    if duplicates:
        raise ValueError("response document already contains derived quantity/quantities: " + ", ".join(duplicates))
    metadata = dict(document.metadata)
    metadata["relaxed_elastic_inputs"] = dict(shared)
    metadata["fitted_quantities"] = list(metadata.get("fitted_quantities", ())) + [quantity.name for quantity in additions]
    provenance = dict(document.provenance)
    provenance["relaxed_elastic_assembly"] = {**shared, **diagnostics}
    return replace(document, quantities=document.quantities + additions, provenance=provenance, metadata=metadata)
