from __future__ import annotations

import pytest

from zstar.v2 import BackendCapabilities, CapabilityError


def test_capability_roundtrip_and_feature_validation():
    capabilities = BackendCapabilities(
        backend="abacus+pyatb",
        version="3.10",
        features={"polarization", "force", "stress", "homogeneous_strain"},
        units={"stress": "kbar"},
        restrictions=("three-dimensional Berry normalization only",),
    )
    restored = BackendCapabilities.from_dict(capabilities.to_dict())
    assert restored == capabilities
    restored.require(("polarization", "stress"), dimensionality=3, insulating=True)
    with pytest.raises(CapabilityError, match="does not provide.*bec"):
        restored.require(("bec",))


def test_capability_rejects_metallic_berry_and_unsupported_dimension():
    capabilities = BackendCapabilities(
        backend="audit",
        features={"polarization"},
        max_dimensionality=2,
    )
    with pytest.raises(CapabilityError, match="cannot collect Berry polarization for a metal"):
        capabilities.require(("polarization",), insulating=False)
    with pytest.raises(CapabilityError, match="dimensionality <= 2"):
        capabilities.require(("polarization",), dimensionality=3, insulating=True)


def test_capability_rejects_unknown_features_and_dimensions():
    with pytest.raises(ValueError, match="unknown backend capability"):
        BackendCapabilities(backend="x", features={"unknown"})
    capabilities = BackendCapabilities(backend="x")
    with pytest.raises(CapabilityError, match="dimensionality must be"):
        capabilities.require((), dimensionality=4)

