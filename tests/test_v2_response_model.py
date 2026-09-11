from __future__ import annotations

import numpy as np
import pytest

from zstar.dimensions import DimensionSpec
from zstar.response_schema import RESPONSE_SCHEMA_VERSION
from zstar.v2 import (
    BoundaryConditions,
    ResponseDocument,
    TensorQuantity,
    V2_SCHEMA_NAME,
    V2_SCHEMA_VERSION,
    UnitConversionError,
    convert_dielectric,
    convert_values,
    mechanical_stability,
    strain_tensor_to_voigt,
    stress_tensor_to_voigt,
    voigt_to_strain_tensor,
    voigt_to_stress_tensor,
)


def test_v2_document_roundtrip_keeps_explicit_metadata(tmp_path):
    quantity = TensorQuantity(
        name="piezoelectric",
        values=np.arange(18, dtype=float).reshape(3, 6),
        unit="C m^-2",
        axes=("polarization_cartesian", "voigt_engineering"),
        voigt_convention=("xx", "yy", "zz", "2yz", "2xz", "2xy"),
        ion_relaxation="relaxed-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
        periodic_axes=("x", "y", "z"),
        normalization="cell_volume",
        source="finite_difference",
        backend="abacus",
        provenance={"actual_vectors": [[-0.01], [0.01]]},
        diagnostics={"rank": 6, "residual": 1.0e-9},
    )
    document = ResponseDocument(
        backend="abacus",
        dimensionality=DimensionSpec(3),
        quantities=(quantity,),
        provenance={"reference_hash": "abc123"},
        symmetry={"space_group": "P4mm", "hall_number": 402},
        functional="PBE",
        pseudopotential="test.uspp",
        orbital="test.orb",
        convergence={"scf": 1.0e-8},
        restart_state={"completed_stages": ["reference"]},
    )
    target = document.write(tmp_path / "response.json")
    loaded = ResponseDocument.read(target)
    assert loaded.schema == V2_SCHEMA_NAME
    assert loaded.schema_version == V2_SCHEMA_VERSION
    assert loaded.quantity("piezoelectric").unit == "C m^-2"
    assert loaded.quantity("piezoelectric").shape == (3, 6)
    assert loaded.quantity("piezoelectric").boundary_conditions.mechanical == "strain"
    assert loaded.symmetry["space_group"] == "P4mm"


def test_v2_schema_is_isolated_from_v1():
    assert RESPONSE_SCHEMA_VERSION == "1.0"
    assert V2_SCHEMA_NAME != "zstar-response"


def test_metadata_and_quantity_validation():
    with pytest.raises(ValueError, match="duplicate axes"):
        TensorQuantity(name="bad", values=[1.0, 2.0], unit="1", axes=("x", "x"))
    with pytest.raises(ValueError, match="periodic_axes"):
        TensorQuantity(name="bad", values=[1.0], unit="1", periodic_axes=("x", "x"))
    with pytest.raises(ValueError, match="unique"):
        ResponseDocument(
            backend="test",
            dimensionality=DimensionSpec(0),
            quantities=(
                TensorQuantity(name="a", values=[1.0], unit="1", periodic_axes=()),
                TensorQuantity(name="a", values=[2.0], unit="1", periodic_axes=()),
            ),
            provenance={"source": "synthetic"},
        )


def test_unit_conversions_are_explicit():
    assert np.isclose(convert_values([1.0], "angstrom", "m")[0], 1.0e-10)
    assert np.isclose(convert_values([1.0], "eV/angstrom", "N")[0], 1.602176634e-9)
    assert np.isclose(convert_values([1.0], "GPa", "Pa")[0], 1.0e9)
    assert np.isclose(convert_values([1.0], "kbar", "GPa")[0], 0.1)
    assert np.isclose(convert_dielectric([2.0], "relative", "F/m")[0], 2.0 * 8.8541878128e-12)
    with pytest.raises(UnitConversionError):
        convert_values([1.0], "1", "F/m")


def test_engineering_voigt_roundtrip_and_work_conjugacy():
    strain = np.array([[0.01, 0.002, 0.003], [0.002, -0.02, 0.004], [0.003, 0.004, 0.03]])
    stress = np.array([[10.0, 2.0, 3.0], [2.0, -20.0, 4.0], [3.0, 4.0, 30.0]])
    eta = strain_tensor_to_voigt(strain)
    sigma = stress_tensor_to_voigt(stress)
    np.testing.assert_allclose(voigt_to_strain_tensor(eta), strain)
    np.testing.assert_allclose(voigt_to_stress_tensor(sigma), stress)
    assert np.isclose(np.sum(stress * strain), sigma @ eta)


def test_mechanical_stability_reports_subspace():
    stable = mechanical_stability(np.diag([2.0, 3.0, 4.0]), indices=(0, 1))
    assert stable["stable_within_tolerance"] is True
    unstable = mechanical_stability(np.diag([2.0, -0.1, 4.0]))
    assert unstable["stable_within_tolerance"] is False
