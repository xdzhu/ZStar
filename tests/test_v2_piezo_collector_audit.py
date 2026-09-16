from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from zstar.dimensions import DimensionSpec
from zstar.v2 import (
    ResponseDocument,
    StructureSpec,
    TensorQuantity,
    analyze_space_group,
    space_group_report_to_dict,
)


def _collector_module():
    source = Path(__file__).resolve().parents[1] / "tools" / "collect_v2_piezo_case.py"
    spec = importlib.util.spec_from_file_location("v2_piezo_collector", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _centrosymmetric_document(maximum: float) -> ResponseDocument:
    report = analyze_space_group(
        StructureSpec(
            lattice=np.diag([5.43, 5.43, 5.43]),
            fractional_positions=np.array([[0.0, 0.0, 0.0]]),
            symbols=("Si",),
        )
    )
    values = np.zeros((3, 6))
    values[0, 0] = maximum
    return ResponseDocument(
        backend="synthetic",
        dimensionality=DimensionSpec(3),
        quantities=(
            TensorQuantity(
                name="piezoelectric_proper",
                values=values,
                unit="C/m^2",
                axes=("polarization", "engineering_strain"),
            ),
        ),
        provenance={"source": "unit-test"},
        symmetry=space_group_report_to_dict(report),
    )


def test_forbidden_piezo_uses_absolute_zero_gate_for_numerical_noise():
    audit = _collector_module()._symmetry_response_audit(
        _centrosymmetric_document(5.4e-5)
    )
    result = audit["quantities"]["piezoelectric_proper"]
    assert result["allowed_rank"] == 0
    assert result["acceptance_metric"] == "absolute_max"
    assert result["zero_absolute_tolerance"] == 1.0e-3
    assert result["status"] == "consistent_absolute_zero"


def test_forbidden_piezo_rejects_signal_above_absolute_zero_gate():
    audit = _collector_module()._symmetry_response_audit(
        _centrosymmetric_document(2.0e-3)
    )
    result = audit["quantities"]["piezoelectric_proper"]
    assert result["status"] == "forbidden_response_detected"
