"""Explicit adapters from the stable v1 response schema to the v2 draft schema.

The adapter deliberately does not infer electromechanical boundary conditions for
unknown v1 quantities.  Existing v1 records remain untouched; a v2 document is a
new object carrying the original quantity metadata in its provenance.
"""

from __future__ import annotations

from typing import Any, Mapping

from ..response_schema import ResponseRecord
from .model import BoundaryConditions, ResponseDocument, TensorQuantity


_KNOWN_DEFAULTS: dict[str, dict[str, Any]] = {
    "born_effective_charge": {
        "boundary_conditions": BoundaryConditions(electric="E", mechanical="not-applicable"),
        "ion_relaxation": "not-applicable",
    },
    "atomic_polar_tensor": {
        "boundary_conditions": BoundaryConditions(electric="E", mechanical="not-applicable"),
        "ion_relaxation": "not-applicable",
    },
    "electronic_dielectric": {
        "boundary_conditions": BoundaryConditions(electric="E", mechanical="not-applicable"),
        "ion_relaxation": "not-applicable",
    },
    "supercell_electronic_dielectric": {
        "boundary_conditions": BoundaryConditions(electric="E", mechanical="not-applicable"),
        "ion_relaxation": "not-applicable",
    },
    "polarization_cartesian": {
        "boundary_conditions": BoundaryConditions(electric="E", mechanical="not-applicable"),
        "ion_relaxation": "not-applicable",
    },
}

_OVERRIDE_KEYS = {
    "unit",
    "axes",
    "coordinate_system",
    "voigt_convention",
    "ion_relaxation",
    "boundary_conditions",
    "periodic_axes",
    "normalization",
    "source",
    "provenance",
    "diagnostics",
}


def adapt_v1_response_record(
    record: ResponseRecord,
    *,
    quantity_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ResponseDocument:
    """Adapt one v1 :class:`ResponseRecord` without changing the v1 object.

    Known BEC, dielectric and Cartesian-polarization names receive only their
    unambiguous boundary defaults.  Unknown quantities require an explicit
    ``quantity_overrides[name]`` entry; this prevents a legacy tensor with an
    ambiguous stress sign or ion-relaxation state from silently becoming a v2
    result.  Override values are copied into the new tensor and the original
    v1 quantity metadata is retained under ``provenance``.
    """

    if not isinstance(record, ResponseRecord):
        raise TypeError("record must be a v1 ResponseRecord")
    overrides = {} if quantity_overrides is None else dict(quantity_overrides)
    unknown_override_names = sorted(set(overrides) - {quantity.name for quantity in record.quantities})
    if unknown_override_names:
        raise ValueError(
            "quantity_overrides names are not present in the v1 record: "
            + ", ".join(unknown_override_names)
        )

    quantities: list[TensorQuantity] = []
    for quantity in record.quantities:
        provided = dict(overrides.get(quantity.name, {}))
        unknown_keys = sorted(set(provided) - _OVERRIDE_KEYS)
        if unknown_keys:
            raise ValueError(
                f"unsupported override field(s) for {quantity.name!r}: {', '.join(unknown_keys)}"
            )
        defaults = dict(_KNOWN_DEFAULTS.get(quantity.name, {}))
        if not defaults and not provided:
            raise ValueError(
                f"v1 quantity {quantity.name!r} has no unambiguous v2 mapping and requires explicit v2 override fields; "
                "supply quantity_overrides with boundary_conditions and ion_relaxation"
            )
        if not defaults:
            required = {"boundary_conditions", "ion_relaxation"}
            missing = sorted(required - set(provided))
            if missing:
                raise ValueError(
                    f"v1 quantity {quantity.name!r} requires explicit v2 override field(s): "
                    + ", ".join(missing)
                )
        merged = {**defaults, **provided}
        original_metadata = dict(quantity.metadata)
        v2_provenance = {
            "adapter": "zstar.v2.legacy.adapt_v1_response_record",
            "legacy_schema": "zstar-response",
            "legacy_schema_version": record.schema_version,
            "legacy_quantity": quantity.name,
            "legacy_convention": quantity.convention,
            "legacy_source": quantity.source,
            "legacy_metadata": original_metadata,
        }
        v2_provenance.update(dict(merged.pop("provenance", {})))
        v2_diagnostics = dict(merged.pop("diagnostics", {}))
        boundary_value = merged.pop("boundary_conditions", None)
        if isinstance(boundary_value, Mapping):
            boundary = BoundaryConditions.from_dict(boundary_value)
        elif boundary_value is None:
            boundary = BoundaryConditions(electric="E", mechanical="not-applicable")
        else:
            boundary = boundary_value
        if not isinstance(boundary, BoundaryConditions):
            raise TypeError(
                f"boundary_conditions override for {quantity.name!r} must be a mapping "
                "or BoundaryConditions"
            )
        quantities.append(
            TensorQuantity(
                name=quantity.name,
                values=quantity.values,
                unit=str(merged.pop("unit", quantity.unit)),
                axes=tuple(merged.pop("axes", quantity.axes)),
                coordinate_system=str(
                    merged.pop(
                        "coordinate_system",
                        original_metadata.get("coordinate_system", "legacy_unspecified"),
                    )
                ),
                voigt_convention=tuple(
                    merged.pop(
                        "voigt_convention",
                        original_metadata.get("voigt_convention", ()),
                    )
                ),
                ion_relaxation=str(merged.pop("ion_relaxation", "not-applicable")),
                boundary_conditions=boundary,
                periodic_axes=tuple(
                    merged.pop("periodic_axes", record.dimensionality.periodic_axes)
                ),
                normalization=str(merged.pop("normalization", quantity.normalization)),
                source=str(merged.pop("source", quantity.source or "v1")),
                backend=record.backend,
                provenance=v2_provenance,
                diagnostics=v2_diagnostics,
            )
        )
        if merged:
            raise ValueError(
                f"unconsumed v2 override fields for {quantity.name!r}: {sorted(merged)}"
            )

    record_metadata = dict(record.metadata)
    document_metadata = {**record_metadata, **dict(metadata or {})}
    document_metadata.update(
        {
            "adapted_from_schema": "zstar-response",
            "adapted_from_version": record.schema_version,
            "v1_record_provenance": dict(record.provenance),
        }
    )
    return ResponseDocument(
        backend=record.backend,
        dimensionality=record.dimensionality,
        quantities=tuple(quantities),
        provenance={
            "adapter": "zstar.v2.legacy.adapt_v1_response_record",
            "source_schema": "zstar-response",
            "source_schema_version": record.schema_version,
            "source_provenance": dict(record.provenance),
        },
        structure=record.structure,
        functional=str(record_metadata.get("functional", "")),
        pseudopotential=str(record_metadata.get("pseudopotential", "")),
        orbital=str(record_metadata.get("orbital", "")),
        convergence=dict(record_metadata.get("convergence", {})),
        metadata=document_metadata,
    )
