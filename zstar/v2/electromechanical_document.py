"""Document-level electromechanical form derivation.

The matrix converter in :mod:`zstar.v2.electromechanical` is deliberately
calculator-neutral.  This module adds the small amount of schema plumbing
needed to consume annotated :class:`ResponseDocument` quantities without
guessing units, thermodynamic boundaries, or whether a Berry derivative has
already received the proper correction.
"""

from __future__ import annotations

from dataclasses import replace

from .electromechanical import convert_piezoelectric_forms
from .mechanical import ENGINEERING_VOIGT
from .model import ResponseDocument, TensorQuantity


def _required_quantity(document: ResponseDocument, name: str) -> TensorQuantity:
    try:
        return document.quantity(name)
    except KeyError as exc:
        raise ValueError(
            f"response document is missing required electromechanical quantity {name!r}"
        ) from exc


def _check_boundary(
    quantity: TensorQuantity,
    *,
    electric: str,
    mechanical: str,
    label: str,
) -> None:
    boundary = quantity.boundary_conditions
    if boundary.electric != electric or boundary.mechanical != mechanical:
        raise ValueError(
            f"{label} {quantity.name!r} must declare boundary "
            f"electric={electric!r}, mechanical={mechanical!r}; got "
            f"electric={boundary.electric!r}, mechanical={boundary.mechanical!r}. "
            "Adapt the source quantity with an explicit boundary override before conversion."
        )


def _check_shape_and_axes(
    quantity: TensorQuantity,
    *,
    shape: tuple[int, ...],
    axes: tuple[str, ...],
    label: str,
) -> None:
    if quantity.shape != shape:
        raise ValueError(f"{label} {quantity.name!r} must have shape {shape}; got {quantity.shape}")
    if quantity.axes != axes:
        raise ValueError(f"{label} {quantity.name!r} must use axes {axes}; got {quantity.axes}")
    if quantity.voigt_convention != ENGINEERING_VOIGT and "voigt" in " ".join(quantity.axes):
        raise ValueError(
            f"{label} {quantity.name!r} must declare engineering Voigt convention "
            f"{ENGINEERING_VOIGT}; got {quantity.voigt_convention}"
        )


def derive_electromechanical_forms(
    document: ResponseDocument,
    *,
    piezoelectric_name: str = "piezoelectric_proper",
    elastic_name: str = "elastic",
    dielectric_name: str = "dielectric_input",
    require_thermodynamic_boundaries: bool = True,
    source: str = "thermodynamic_conversion",
) -> ResponseDocument:
    """Derive and append annotated ``e/d/g/h`` and reciprocal forms.

    The three input quantities must be calculator-neutral and explicitly
    annotated as proper ``e`` (C/m², fixed ``E``/strain), ``C^E`` (pressure
    unit, fixed ``E``/strain), and ``epsilon^S`` (relative or F/m, fixed
    ``E``/strain).  No stress sign, dielectric convention, or proper
    correction is inferred.  Set ``require_thermodynamic_boundaries=False``
    only for a separately audited legacy record; the resulting provenance
    records that the boundary declaration was not checked.
    """

    if not isinstance(document, ResponseDocument):
        raise TypeError("document must be a v2 ResponseDocument")
    if document.dimensionality.value != 3:
        raise ValueError("electromechanical form conversion currently requires dimensionality=3")
    if not isinstance(require_thermodynamic_boundaries, bool):
        raise TypeError("require_thermodynamic_boundaries must be a bool")
    if not str(source).strip():
        raise ValueError("source must not be empty")

    piezoelectric = _required_quantity(document, piezoelectric_name)
    elastic = _required_quantity(document, elastic_name)
    dielectric = _required_quantity(document, dielectric_name)
    generated_names = {
        "piezoelectric_e",
        "piezoelectric_d",
        "piezoelectric_g",
        "piezoelectric_h",
        "elastic_CE",
        "elastic_CD",
        "compliance_sE",
        "compliance_sD",
        "dielectric_epsilonS",
        "dielectric_epsilonT",
        "impermittivity_betaS",
        "impermittivity_betaT",
    }
    input_name_collisions = sorted(
        {piezoelectric.name, elastic.name, dielectric.name}.intersection(generated_names)
    )
    if input_name_collisions:
        raise ValueError(
            "input electromechanical quantity name(s) collide with derived output(s): "
            + ", ".join(input_name_collisions)
            + "; use source names such as piezoelectric_proper, elastic, and dielectric_input"
        )
    _check_shape_and_axes(
        piezoelectric,
        shape=(3, 6),
        axes=("polarization_cartesian", "voigt_engineering"),
        label="proper piezoelectric quantity",
    )
    _check_shape_and_axes(
        elastic,
        shape=(6, 6),
        axes=("stress_voigt", "voigt_engineering"),
        label="elastic quantity",
    )
    _check_shape_and_axes(
        dielectric,
        shape=(3, 3),
        axes=("electric_row", "electric_column"),
        label="dielectric quantity",
    )
    if piezoelectric.provenance.get("piezoelectric_kind") != "proper":
        raise ValueError(
            f"piezoelectric quantity {piezoelectric.name!r} is not explicitly marked proper; "
            "apply proper_piezoelectric_response before thermodynamic conversion"
        )
    if require_thermodynamic_boundaries:
        _check_boundary(
            piezoelectric, electric="E", mechanical="strain", label="proper piezoelectric quantity"
        )
        _check_boundary(elastic, electric="E", mechanical="strain", label="elastic quantity")
        _check_boundary(dielectric, electric="E", mechanical="strain", label="dielectric quantity")

    forms = convert_piezoelectric_forms(
        piezoelectric.values,
        elastic.values,
        dielectric.values,
        piezoelectric_unit=piezoelectric.unit,
        elastic_unit=elastic.unit,
        dielectric_unit=dielectric.unit,
        piezoelectric_kind="proper",
        voigt_convention=piezoelectric.voigt_convention,
    )
    quantities = forms.to_tensor_quantities(
        backend=document.backend,
        source=source,
        periodic_axes=document.dimensionality.periodic_axes,
        ion_relaxation=piezoelectric.ion_relaxation,
        normalization=piezoelectric.normalization,
        provenance={
            "input_quantities": {
                "piezoelectric": piezoelectric.name,
                "elastic": elastic.name,
                "dielectric": dielectric.name,
            },
            "thermodynamic_boundaries_checked": require_thermodynamic_boundaries,
        },
    )
    existing = {quantity.name for quantity in document.quantities}
    duplicates = sorted(existing.intersection(quantity.name for quantity in quantities))
    if duplicates:
        raise ValueError(
            "response document already contains electromechanical quantity/quantities: "
            + ", ".join(duplicates)
        )
    metadata = dict(document.metadata)
    metadata["electromechanical_forms"] = [quantity.name for quantity in quantities]
    metadata["electromechanical_inputs"] = [piezoelectric.name, elastic.name, dielectric.name]
    provenance = dict(document.provenance)
    provenance["electromechanical_conversion"] = {
        "inputs": {
            "piezoelectric": piezoelectric.name,
            "elastic": elastic.name,
            "dielectric": dielectric.name,
        },
        "thermodynamic_boundaries_checked": require_thermodynamic_boundaries,
        "diagnostics": dict(forms.diagnostics),
    }
    return replace(
        document,
        quantities=tuple(document.quantities) + tuple(quantities),
        metadata=metadata,
        provenance=provenance,
    )


__all__ = ["derive_electromechanical_forms"]
