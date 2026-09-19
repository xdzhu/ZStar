from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from zstar.dimensions import DimensionSpec
from zstar.v2 import (
    BoundaryConditions,
    ResponseDocument,
    TensorQuantity,
    derive_relaxed_elastic_response,
    derive_relaxed_piezoelectric_response,
    adapt_v1_response_file,
    relaxed_piezoelectric,
)
from zstar.v2.mechanical import ENGINEERING_VOIGT


def _document() -> ResponseDocument:
    clamped = TensorQuantity(
        name="piezoelectric_proper",
        values=np.array(
            [[0.20, 0.10, 0.00, 0.00, 0.00, 0.00],
             [0.00, 0.30, 0.00, 0.00, 0.00, 0.00],
             [0.00, 0.00, 0.40, 0.00, 0.00, 0.00]],
            dtype=float,
        ),
        unit="C/m^2",
        axes=("polarization_cartesian", "voigt_engineering"),
        coordinate_system="cartesian_right_handed",
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="clamped-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
        provenance={"piezoelectric_kind": "proper"},
    )
    # Deliberately use the v1-compatible displacement/polarization order to
    # prove that the document bridge handles explicit axis metadata.
    born = TensorQuantity(
        name="born_effective_charge",
        values=np.asarray([np.eye(3), 2.0 * np.eye(3)]),
        unit="e",
        axes=("atom", "displacement", "polarization"),
        coordinate_system="cartesian_right_handed",
        ion_relaxation="not-applicable",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="not-applicable"),
        normalization="per_atom",
    )
    internal = np.zeros((2, 3, 6), dtype=float)
    internal[0, 0, 0] = 0.10
    internal[1, 2, 2] = -0.04
    lambda_quantity = TensorQuantity(
        name="internal_strain",
        values=internal,
        unit="angstrom",
        axes=("atom", "cartesian", "voigt_engineering"),
        coordinate_system="cartesian_right_handed",
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="relaxed-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
        normalization="per_atom",
        provenance={"acoustic_gauge": "explicit-test-gauge"},
    )
    return ResponseDocument(
        backend="synthetic",
        dimensionality=DimensionSpec(3),
        quantities=(clamped, born, lambda_quantity),
        structure={
            "lattice_angstrom": np.diag([2.0, 3.0, 4.0]).tolist(),
            "fractional_positions": [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            "symbols": ["A", "B"],
        },
        provenance={"source": "synthetic"},
    )


def test_document_relaxed_piezo_assembly_reorders_bec_and_records_terms():
    document = _document()
    result = derive_relaxed_piezoelectric_response(document)
    expected_relaxed, expected_contribution = relaxed_piezoelectric(
        document.quantity("piezoelectric_proper").values,
        np.asarray([np.eye(3), 2.0 * np.eye(3)]),
        document.quantity("internal_strain").values,
        24.0e-30,
        internal_strain_unit="angstrom",
    )
    np.testing.assert_allclose(
        result.quantity("piezoelectric_internal").values,
        expected_contribution,
    )
    np.testing.assert_allclose(
        result.quantity("piezoelectric_relaxed").values,
        expected_relaxed,
    )
    assert result.quantity("piezoelectric_internal").ion_relaxation == "internal-contribution"
    assert result.quantity("piezoelectric_relaxed").ion_relaxation == "relaxed-ion"
    assert result.quantity("piezoelectric_relaxed").provenance["piezoelectric_kind"] == "proper"
    assert np.isclose(result.metadata["relaxed_piezoelectric_inputs"]["volume_m3"], 24.0e-30)


def test_document_relaxed_piezo_assembly_requires_proper_clamped_input():
    document = _document()
    clamped = document.quantity("piezoelectric_proper")
    bad = replace(clamped, provenance={})
    document = replace(
        document,
        quantities=tuple(
            bad if quantity.name == clamped.name else quantity
            for quantity in document.quantities
        ),
    )
    with pytest.raises(ValueError, match="piezoelectric_kind='proper'"):
        derive_relaxed_piezoelectric_response(document)


def test_document_relaxed_piezo_assembly_rejects_anonymous_bec_axes():
    document = _document()
    born = document.quantity("born_effective_charge")
    bad = replace(born, axes=())
    document = replace(
        document,
        quantities=tuple(
            bad if quantity.name == born.name else quantity
            for quantity in document.quantities
        ),
    )
    with pytest.raises(ValueError, match="explicit axes"):
        derive_relaxed_piezoelectric_response(document)


def _elastic_document() -> ResponseDocument:
    elastic = TensorQuantity(
        name="elastic",
        values=np.eye(6) * 100.0,
        unit="GPa",
        axes=("stress_voigt", "voigt_engineering"),
        coordinate_system="cartesian_right_handed",
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="clamped-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
    )
    phi = np.diag([2.0, 3.0, 4.0]).reshape(1, 1, 3, 3)
    force_constants = TensorQuantity(
        name="force_constants",
        values=phi,
        unit="eV/angstrom^2",
        axes=("atom_row", "atom_column", "force", "displacement"),
        coordinate_system="cartesian_right_handed",
        ion_relaxation="not-applicable",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="not-applicable"),
    )
    gamma = np.zeros((1, 3, 6), dtype=float)
    gamma[0, 0, 0] = 0.2
    gamma[0, 2, 2] = -0.3
    coupling = TensorQuantity(
        name="strain_force_coupling",
        values=gamma,
        unit="eV/angstrom",
        axes=("atom", "cartesian", "voigt_engineering"),
        coordinate_system="cartesian_right_handed",
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="clamped-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
    )
    return ResponseDocument(
        backend="synthetic",
        dimensionality=DimensionSpec(3),
        quantities=(elastic, force_constants, coupling),
        structure={"lattice_angstrom": np.diag([2.0, 3.0, 4.0]).tolist()},
        provenance={"source": "synthetic"},
    )


def test_document_relaxed_elastic_assembly_solves_lambda_and_records_diagnostics():
    document = _elastic_document()
    result = derive_relaxed_elastic_response(document)
    phi = np.diag([2.0, 3.0, 4.0])
    gamma = np.zeros((3, 6), dtype=float)
    gamma[0, 0] = 0.2
    gamma[2, 2] = -0.3
    expected_lambda = -np.linalg.inv(phi) @ gamma
    expected_correction = gamma.T @ (-expected_lambda) / 24.0
    np.testing.assert_allclose(
        result.quantity("internal_strain_equilibrium").values.reshape(3, 6),
        expected_lambda,
    )
    np.testing.assert_allclose(
        result.quantity("elastic_internal_correction").values,
        expected_correction * (1.602176634e-19 / 1.0e-30) / 1.0e9,
    )
    np.testing.assert_allclose(
        result.quantity("elastic_relaxed").values,
        np.eye(6) * 100.0 - result.quantity("elastic_internal_correction").values,
    )
    assert result.quantity("internal_strain_equilibrium").unit == "angstrom"
    assert result.quantity("elastic_relaxed").ion_relaxation == "relaxed-ion"
    assert result.quantity("elastic_relaxed").diagnostics["internal_strain_rank"] == 3


def test_document_relaxed_elastic_assembly_rejects_unmatched_response_units():
    document = _elastic_document()
    coupling = document.quantity("strain_force_coupling")
    bad = replace(coupling, unit="eV/angstrom^2")
    document = replace(
        document,
        quantities=tuple(
            bad if quantity.name == coupling.name else quantity
            for quantity in document.quantities
        ),
    )
    with pytest.raises(ValueError, match="matched explicit"):
        derive_relaxed_elastic_response(document)


def test_document_relaxed_elastic_accepts_tracked_v1_sic_ifc_and_bec_axes():
    source = Path("examples/3D_Bulk/SiC/results/spectra/response.json")
    document = adapt_v1_response_file(source)
    elastic = TensorQuantity(
        name="elastic",
        values=np.eye(6) * 100.0,
        unit="GPa",
        axes=("stress_voigt", "voigt_engineering"),
        coordinate_system="cartesian_right_handed",
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="clamped-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
    )
    gamma = TensorQuantity(
        name="strain_force_coupling",
        values=np.zeros((2, 3, 6)),
        unit="eV/angstrom",
        axes=("atom", "cartesian", "voigt_engineering"),
        coordinate_system="cartesian_right_handed",
        voigt_convention=ENGINEERING_VOIGT,
        ion_relaxation="clamped-ion",
        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
    )
    document = replace(
        document,
        quantities=document.quantities + (elastic, gamma),
    )
    result = derive_relaxed_elastic_response(document, volume_m3=1.0e-28)
    np.testing.assert_allclose(result.quantity("elastic_relaxed").values, elastic.values)
    np.testing.assert_allclose(result.quantity("internal_strain_equilibrium").values, 0.0)
    assert result.quantity("force_constants").axes == (
        "atom_row", "atom_column", "force", "displacement"
    )
