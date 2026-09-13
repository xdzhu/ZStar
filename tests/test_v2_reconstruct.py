from __future__ import annotations

import numpy as np
import pytest

from zstar.dimensions import DimensionSpec
from zstar.v2 import (
    BoundaryConditions,
    ResponseDocument,
    TensorQuantity,
    fit_response_document,
    voigt_to_stress_tensor,
)


def _synthetic_document() -> tuple[ResponseDocument, dict[str, np.ndarray]]:
    rng = np.random.default_rng(20260913)
    strains = np.vstack([np.zeros(6), rng.normal(size=(24, 6)) * 0.01])
    reference_polarization = np.array([0.2, -0.1, 0.35])
    piezo = rng.normal(size=(3, 6))
    polarization = reference_polarization + strains @ piezo.T
    reference_stress = np.array([0.4, -0.2, 0.1, 0.03, -0.04, 0.02])
    elastic = rng.normal(size=(6, 6))
    elastic = 0.5 * (elastic + elastic.T)
    stress = np.asarray(
        [voigt_to_stress_tensor(reference_stress + strain @ elastic.T) for strain in strains]
    )
    reference_force = np.array([[0.4, -0.2, 0.1]])
    gamma = rng.normal(size=(3, 6))
    forces = (reference_force.reshape(1, 1, 3) - np.einsum("sm,am->sa", strains, gamma).reshape(-1, 1, 3))
    reference_displacement = np.array([[0.1, -0.2, 0.3]])
    internal = rng.normal(size=(1, 3, 6))
    displacement = reference_displacement + np.einsum("sm,iam->sia", strains, internal)
    stage_names = ["reference"] + [f"strain-{index:02d}" for index in range(1, strains.shape[0])]
    boundary = BoundaryConditions(electric="E", mechanical="strain", stress_sign="backend-raw")
    quantities = (
        TensorQuantity(
            name="strain_vector",
            values=strains,
            unit="engineering_strain",
            axes=("stage", "voigt_engineering"),
            voigt_convention=("xx", "yy", "zz", "2yz", "2xz", "2xy"),
            boundary_conditions=boundary,
            normalization="dimensionless",
            provenance={"stage_names": stage_names},
        ),
        TensorQuantity(
            name="polarization_cartesian",
            values=polarization,
            unit="C/m^2",
            axes=("stage", "cartesian"),
            boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
            normalization="cell_volume",
            provenance={"stage_names": stage_names, "branch_matched": True},
        ),
        TensorQuantity(
            name="stress_raw",
            values=stress,
            unit="kbar",
            axes=("stage", "stress_row_cartesian", "stress_column_cartesian"),
            boundary_conditions=boundary,
            normalization="cell_volume",
            provenance={"stage_names": stage_names, "sign_convention": "backend-raw"},
        ),
        TensorQuantity(
            name="forces_initial",
            values=forces,
            unit="eV/angstrom",
            axes=("stage", "atom", "cartesian"),
            boundary_conditions=boundary,
            ion_relaxation="clamped-ion",
            normalization="per_atom",
            provenance={"stage_names": stage_names},
        ),
        TensorQuantity(
            name="internal_displacement",
            values=displacement,
            unit="angstrom",
            axes=("stage", "atom", "cartesian"),
            boundary_conditions=boundary,
            ion_relaxation="relaxed-ion",
            normalization="per_atom",
            provenance={"stage_names": stage_names, "acoustic_gauge": "explicit-test-gauge"},
        ),
    )
    document = ResponseDocument(
        backend="synthetic",
        dimensionality=DimensionSpec(3),
        quantities=quantities,
        provenance={"source": "synthetic"},
        metadata={"ion_relaxation": "relaxed-ion"},
    )
    return document, {
        "piezo": piezo,
        "elastic": elastic,
        "gamma": gamma,
        "internal": internal,
    }


def test_fit_response_document_packages_all_available_strain_fits(tmp_path):
    document, expected = _synthetic_document()
    fitted = fit_response_document(document, stress_sign="tension-positive")

    np.testing.assert_allclose(fitted.quantity("piezoelectric_raw").values, expected["piezo"])
    np.testing.assert_allclose(fitted.quantity("elastic").values, expected["elastic"])
    np.testing.assert_allclose(
        fitted.quantity("strain_force_coupling").values,
        expected["gamma"].reshape(1, 3, 6),
    )
    np.testing.assert_allclose(
        fitted.quantity("internal_strain").values,
        expected["internal"],
    )
    for name in ("piezoelectric_raw", "elastic", "strain_force_coupling", "internal_strain"):
        diagnostics = fitted.quantity(name).diagnostics
        assert diagnostics["complete"] is True
        assert diagnostics["residual_max"] < 1.0e-12
    assert fitted.metadata["fitted_quantities"] == [
        "piezoelectric_raw",
        "elastic",
        "strain_force_coupling",
        "internal_strain",
    ]
    loaded = ResponseDocument.read(fitted.write(tmp_path / "response-fitted.json"))
    assert loaded.quantity("elastic").boundary_conditions.stress_sign == "tension-positive"


def test_fit_response_document_requires_explicit_stress_sign_and_rejects_duplicates():
    document, _ = _synthetic_document()
    with pytest.raises(ValueError, match="stress_sign explicitly"):
        fit_response_document(document)
    fitted = fit_response_document(
        document,
        stress_sign="tension-positive",
        include_piezoelectric=False,
        include_elastic=False,
        include_gamma=False,
    )
    with pytest.raises(ValueError, match="already contains fitted"):
        fit_response_document(
            fitted,
            stress_sign="tension-positive",
            include_piezoelectric=False,
            include_elastic=False,
            include_gamma=False,
        )
