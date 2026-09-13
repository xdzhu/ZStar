from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from zstar.dimensions import dimension_spec
from zstar.response_schema import ResponseQuantity, ResponseRecord
from zstar.v2 import ENGINEERING_VOIGT, adapt_v1_response_record


def _record(*quantities: ResponseQuantity) -> ResponseRecord:
    return ResponseRecord(
        backend="abacus",
        dimensionality=dimension_spec(3),
        quantities=tuple(quantities),
        provenance={"source": "v1-fixture"},
        metadata={"functional": "PBEsol", "convergence": {"scf_thr": 1.0e-8}},
    )


def test_v1_bec_record_adapts_without_mutating_v1_metadata():
    quantity = ResponseQuantity(
        name="born_effective_charge",
        values=np.eye(3)[None],
        unit="e",
        normalization="per_atom",
        axes=("atom", "displacement", "polarization"),
        convention="rows=displacement; columns=polarization",
        source="v1-bec",
        metadata={"labels": ["X"]},
    )
    record = _record(quantity)
    adapted = adapt_v1_response_record(record)
    copied = adapted.quantity("born_effective_charge")
    assert copied.boundary_conditions.mechanical == "not-applicable"
    assert copied.coordinate_system == "legacy_unspecified"
    assert copied.provenance["legacy_quantity"] == "born_effective_charge"
    assert adapted.metadata["adapted_from_version"] == "1.0"
    assert record.quantity("born_effective_charge").metadata == {"labels": ["X"]}


def test_unknown_v1_quantity_requires_explicit_boundary_and_relaxation_override():
    stress = ResponseQuantity(
        name="stress_raw",
        values=np.zeros((1, 3, 3)),
        unit="kbar",
        normalization="cell_volume",
        axes=("stage", "row", "column"),
    )
    record = _record(stress)
    with pytest.raises(ValueError, match="requires explicit v2 override"):
        adapt_v1_response_record(record)
    with pytest.raises(ValueError, match="ion_relaxation"):
        adapt_v1_response_record(
            record,
            quantity_overrides={
                "stress_raw": {
                    "boundary_conditions": {
                        "electric": "E",
                        "mechanical": "strain",
                        "stress_sign": "compression-positive",
                    }
                }
            },
        )
    adapted = adapt_v1_response_record(
        record,
        quantity_overrides={
            "stress_raw": {
                "ion_relaxation": "clamped-ion",
                "boundary_conditions": {
                    "electric": "E",
                    "mechanical": "strain",
                    "stress_sign": "compression-positive",
                },
                "voigt_convention": ENGINEERING_VOIGT,
            }
        },
    )
    copied = adapted.quantity("stress_raw")
    assert copied.ion_relaxation == "clamped-ion"
    assert copied.boundary_conditions.stress_sign == "compression-positive"
    assert copied.voigt_convention == ENGINEERING_VOIGT


def test_adapter_rejects_override_for_missing_quantity():
    record = _record(
        ResponseQuantity(
            name="born_effective_charge",
            values=np.eye(3)[None],
            unit="e",
            normalization="per_atom",
        )
    )
    with pytest.raises(ValueError, match="not present"):
        adapt_v1_response_record(record, quantity_overrides={"stress_raw": {}})


def test_tracked_v1_nanowire_record_adapts_known_quantities():
    source = Path("examples/1D_Nanowire/BN_9_0/results/response.json")
    record = ResponseRecord.read(source)
    adapted = adapt_v1_response_record(record)
    assert adapted.dimensionality.value == 1
    assert adapted.dimensionality.periodic_axes == ("z",)
    assert adapted.quantity("born_effective_charge").periodic_axes == ("z",)
    assert adapted.quantity("supercell_electronic_dielectric").periodic_axes == ("z",)
