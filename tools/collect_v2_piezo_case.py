#!/usr/bin/env python3
"""Collect and fit a completed ABACUS+PYATB v2 strain case.

The script is deliberately post-processing only: it never launches a
calculator.  Stress is converted explicitly from ABACUS compression-positive
raw output to the tension-positive thermodynamic convention before fitting.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zstar.v2.abacus import collect_pyatb_strain_response
from zstar.v2.algebra import remove_acoustic_translation
from zstar.v2.fit import fit_internal_strain_response
from zstar.v2.reconstruct import fit_response_document
from zstar.v2.structure import (
    allowed_response_basis,
    space_group_report_from_dict,
)
from zstar.v2.symmetry import intertwining_residual
from zstar.v2.mechanical import stress_representation
from zstar.v2.structure import (
    displacement_representation,
    polarization_representation,
    strain_representation,
)
from zstar.v2.units import convert_values


def _quantity(document, name):
    try:
        return document.quantity(name)
    except KeyError:
        return None


def _symmetry_response_audit(
    document,
    *,
    relative_tolerance: float = 1.0e-5,
    acoustic_gauge: str = "raw",
) -> dict[str, object]:
    """Compare measured tensors with the persisted space-group subspaces.

    The ordinary fitted quantities remain untouched: for example,
    ``piezoelectric_proper`` is the branch-matched finite-difference result.
    This audit separately projects that result onto the intended symmetry
    basis and reports the forbidden/violating component.  Proper piezoelectric
    symmetry is audited after the geometric correction; applying an
    intertwiner directly to the improper derivative would be physically wrong.
    """

    if not np.isfinite(relative_tolerance) or relative_tolerance <= 0.0:
        raise ValueError("symmetry relative_tolerance must be finite and positive")
    if acoustic_gauge not in {"raw", "equal-weight"}:
        raise ValueError("acoustic_gauge must be 'raw' or 'equal-weight'")
    try:
        report = space_group_report_from_dict(dict(document.symmetry))
    except (TypeError, ValueError) as exc:
        return {
            "status": "unavailable",
            "reason": str(exc),
            "quantities": {},
        }
    quantity_specs = {
        "piezoelectric_proper": ("polarization", False),
        "elastic": ("stress", True),
        "strain_force_coupling": ("force", False),
        "internal_strain": ("displacement", False),
    }
    audit: dict[str, object] = {
        "status": "available",
        "space_group": report.space_group,
        "operation_count": report.operation_count,
        "relative_tolerance": float(relative_tolerance),
        "acoustic_gauge": acoustic_gauge,
        "comparison": dict(document.symmetry.get("comparison", {})),
        "quantities": {},
    }
    input_representations = [
        strain_representation(report, index) for index in range(report.operation_count)
    ]
    for quantity_name, (output_kind, major_symmetric) in quantity_specs.items():
        quantity = _quantity(document, quantity_name)
        if quantity is None:
            continue
        values = np.asarray(quantity.values, dtype=float)
        matrix = values
        if values.ndim == 3 and values.shape[-1] == 6:
            matrix = values.reshape(values.shape[0] * values.shape[1], 6)
        basis = allowed_response_basis(
            report,
            input_kind="strain",
            output_kind=output_kind,
        )
        if major_symmetric:
            # The elastic response is already major-symmetrized by the main
            # collector.  The audit basis must use the same thermodynamic
            # intersection; asking fit_elastic_response is unnecessary here
            # because only the stored matrix is being diagnosed.
            from zstar.v2.fit import _major_symmetric_basis

            basis = _major_symmetric_basis(basis)
        if matrix.shape != (basis.output_dimension, basis.input_dimension):
            raise ValueError(
                f"{quantity_name} shape {matrix.shape} is incompatible with "
                f"the {report.space_group} {output_kind} basis "
                f"{basis.output_dimension, basis.input_dimension}"
            )
        flat = matrix.reshape(-1, order="F")
        if basis.allowed_rank:
            coefficients, *_ = np.linalg.lstsq(basis.basis, flat, rcond=None)
            projected = basis.matrix_from_coefficients(coefficients)
        else:
            projected = np.zeros_like(matrix)
        difference = projected - matrix
        matrix_norm = float(np.linalg.norm(matrix))
        output = {
            "allowed_rank": int(basis.allowed_rank),
            "projection_residual_max": float(np.max(np.abs(difference))),
            "projection_residual_rms": float(np.sqrt(np.mean(difference**2))),
            "projection_residual_relative": (
                float(np.linalg.norm(difference) / matrix_norm)
                if matrix_norm > 0.0
                else float(np.linalg.norm(difference))
            ),
            "forbidden_component_max": float(np.max(np.abs(difference))),
            "intertwining_residual": float(
                intertwining_residual(
                    matrix,
                    input_representations,
                    {
                        "polarization": [
                            polarization_representation(report, index)
                            for index in range(report.operation_count)
                        ],
                        "stress": [
                            # Stress is tensorial and the basis itself carries
                            # the correct non-engineering shear representation.
                            stress_representation(report.operations[index].rotation_cartesian)
                            for index in range(report.operation_count)
                        ],
                        "force": [
                            displacement_representation(report, index)
                            for index in range(report.operation_count)
                        ],
                        "displacement": [
                            displacement_representation(report, index)
                            for index in range(report.operation_count)
                        ],
                    }[output_kind],
                )
            ),
            "status": (
                "consistent"
                if (
                    matrix_norm == 0.0
                    or float(np.linalg.norm(difference) / matrix_norm) <= float(relative_tolerance)
                )
                else "allowed_subspace_violation"
            ),
        }
        audit["quantities"][quantity_name] = output

    # Relaxed-ion coordinates carry an arbitrary acoustic translation.  Keep
    # the collected/fitted ``internal_strain`` quantity untouched and expose a
    # separate, opt-in equal-weight gauge audit.  This is intentionally not a
    # mass-weighted gauge: masses and the corresponding dynamical convention
    # are not guaranteed to be present in a calculator-neutral document.
    if acoustic_gauge == "equal-weight":
        displacement = _quantity(document, "internal_displacement")
        strain_quantity = _quantity(document, "strain_vector")
        if displacement is not None and strain_quantity is not None:
            displacements = np.asarray(displacement.values, dtype=float)
            strains = np.asarray(strain_quantity.values, dtype=float)
            translations = np.mean(displacements, axis=1)
            gauged = remove_acoustic_translation(displacements)
            reference_index = displacement.provenance.get("reference_index")
            if reference_index is None:
                reference_index = int(np.argmin(np.linalg.norm(strains, axis=1)))
            reference_index = int(reference_index)
            fit = fit_internal_strain_response(
                strains,
                gauged,
                reference_displacement=gauged[reference_index],
            )
            matrix = fit.matrix
            basis = allowed_response_basis(
                report,
                input_kind="strain",
                output_kind="displacement",
            )
            flat = matrix.reshape(-1, order="F")
            coefficients, *_ = np.linalg.lstsq(basis.basis, flat, rcond=None)
            projected = basis.matrix_from_coefficients(coefficients)
            difference = projected - matrix
            matrix_norm = float(np.linalg.norm(matrix))
            projection_relative = (
                float(np.linalg.norm(difference) / matrix_norm)
                if matrix_norm > 0.0
                else float(np.linalg.norm(difference))
            )
            audit["internal_strain_acoustic_gauge"] = {
                "status": (
                    "consistent"
                    if projection_relative <= float(relative_tolerance)
                    else "allowed_subspace_violation"
                ),
                "gauge": "equal-weight-mean-translation-removal",
                "reference_index": reference_index,
                "translation_max_angstrom": float(np.max(np.linalg.norm(translations, axis=1))),
                "translation_rms_angstrom": float(
                    np.sqrt(np.mean(np.linalg.norm(translations, axis=1) ** 2))
                ),
                "fit_residual_max": float(fit.residual_max),
                "fit_residual_rms": float(fit.residual_rms),
                "fit_residual_relative": float(fit.residual_relative),
                "allowed_rank": int(basis.allowed_rank),
                "projection_residual_max": float(np.max(np.abs(difference))),
                "projection_residual_rms": float(np.sqrt(np.mean(difference**2))),
                "projection_residual_relative": projection_relative,
                "raw_quantity_unchanged": True,
            }
        else:
            audit["internal_strain_acoustic_gauge"] = {
                "status": "unavailable",
                "reason": "internal_displacement or strain_vector is missing",
                "raw_quantity_unchanged": True,
            }
    comparison = audit.get("comparison", {})
    if isinstance(comparison, dict) and comparison.get("status") != "consistent":
        audit["status"] = "conditional_intended_symmetry"
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--symmetry-relative-tolerance",
        type=float,
        default=1.0e-5,
        help="relative Frobenius tolerance for the post-fit symmetry audit",
    )
    parser.add_argument(
        "--acoustic-gauge",
        choices=("raw", "equal-weight"),
        default="raw",
        help="internal-strain audit gauge; raw leaves relaxed translations untouched",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output or (root / "results")).resolve()
    output.mkdir(parents=True, exist_ok=True)

    collected = collect_pyatb_strain_response(root, require_precision=True)
    fitted = fit_response_document(
        collected,
        stress_sign="compression-positive",
        enforce_major_symmetry=True,
        include_piezoelectric=True,
        include_proper_piezoelectric=True,
        include_elastic=True,
        include_gamma=True,
        include_internal_strain=True,
    )
    symmetry_response_audit = _symmetry_response_audit(
        fitted,
        relative_tolerance=args.symmetry_relative_tolerance,
        acoustic_gauge=args.acoustic_gauge,
    )
    fitted = replace(
        fitted,
        provenance={
            **fitted.provenance,
            "symmetry_response_audit": symmetry_response_audit,
        },
        metadata={
            **fitted.metadata,
            "symmetry_response_audit": symmetry_response_audit,
        },
    )
    fitted.write(output / "response_document.json")

    piezo = _quantity(fitted, "piezoelectric_proper")
    raw = _quantity(fitted, "piezoelectric_raw")
    elastic = _quantity(fitted, "elastic")
    internal = _quantity(fitted, "internal_strain")
    gamma = _quantity(fitted, "strain_force_coupling")
    summary = {
        "schema": "zstar-v2-piezo-result-summary",
        "status": "completed_research_gate_pending_literature_audit",
        "root": str(root),
        "backend": fitted.backend,
        "functional": fitted.functional,
        "space_group": fitted.symmetry.get("space_group"),
        "intended_preparation_space_group": fitted.symmetry.get("space_group"),
        "observed_reference_space_group": fitted.symmetry.get("reference_observed", {}).get("space_group"),
        "symmetry_audit": dict(fitted.symmetry.get("comparison", {})),
        "symmetry_response_audit": symmetry_response_audit,
        "dimensionality": fitted.dimensionality.to_dict(),
        "stage_count": int(fitted.metadata.get("stage_count", 0)),
        "pyatb_run_count": int(fitted.metadata.get("pyatb_run_count", 0)),
        "branch_shift_max": int(fitted.metadata.get("branch_shift_max", 0)),
        "branch_residual_max_C_per_m2": float(fitted.metadata.get("branch_residual_max", 0.0)),
        "reference_force_max_eV_per_angstrom": fitted.metadata.get("reference_force_max_eV_per_angstrom"),
    }
    if raw is not None:
        summary["piezoelectric_raw_C_per_m2"] = np.asarray(raw.values).tolist()
        summary["piezoelectric_raw_diagnostics"] = dict(raw.diagnostics)
    if piezo is not None:
        summary["piezoelectric_proper_C_per_m2"] = np.asarray(piezo.values).tolist()
        summary["piezoelectric_proper_diagnostics"] = dict(piezo.diagnostics)
        summary["piezoelectric_proper_max_abs_C_per_m2"] = float(np.max(np.abs(piezo.values)))
    if elastic is not None:
        elastic_gpa = convert_values(elastic.values, elastic.unit, "GPa")
        symmetric = 0.5 * (elastic_gpa + elastic_gpa.T)
        summary["elastic_raw_unit"] = elastic.unit
        summary["elastic_GPa"] = elastic_gpa.tolist()
        summary["elastic_eigenvalues_GPa"] = np.linalg.eigvalsh(symmetric).tolist()
        summary["mechanical_stable_positive_definite"] = bool(np.min(np.linalg.eigvalsh(symmetric)) > 0.0)
        summary["elastic_diagnostics"] = dict(elastic.diagnostics)
        # The stress-charge form follows directly from the thermodynamic
        # matrix relation d = e (C^E)^-1.  With e in C/m^2 and C in GPa,
        # multiplying by 1e3 gives the conventional pm/V (= pC/N) unit.
        # This conversion needs no dielectric tensor; g/h remain unavailable
        # until an explicitly labelled dielectric response is supplied.
        if piezo is not None:
            elastic_pa = convert_values(elastic.values, elastic.unit, "Pa")
            elastic_pa = 0.5 * (elastic_pa + elastic_pa.T)
            try:
                compliance_pa = np.linalg.inv(elastic_pa)
            except np.linalg.LinAlgError as exc:
                raise ValueError("elastic tensor is singular; cannot derive piezoelectric d") from exc
            d_c_per_n = np.asarray(piezo.values, dtype=float) @ compliance_pa
            d_pm_per_v = d_c_per_n * 1.0e12
            summary["piezoelectric_d_C_per_N"] = d_c_per_n.tolist()
            summary["piezoelectric_d_pm_per_V"] = d_pm_per_v.tolist()
            summary["piezoelectric_d_diagnostics"] = {
                "relation": "d = e @ inverse(C^E)",
                "piezoelectric_input": "proper",
                "elastic_input_unit": elastic.unit,
                "voigt_convention": ["xx", "yy", "zz", "2yz", "2xz", "2xy"],
                "condition_number_C": float(np.linalg.cond(elastic_pa)),
                "roundtrip_max_C_per_m2": float(
                    np.max(np.abs(np.asarray(piezo.values) - d_c_per_n @ elastic_pa))
                ),
            }
    if internal is not None:
        summary["internal_strain_angstrom_per_strain"] = np.asarray(internal.values).tolist()
        summary["internal_strain_diagnostics"] = dict(internal.diagnostics)
    if gamma is not None:
        summary["strain_force_coupling_eV_per_angstrom"] = np.asarray(gamma.values).tolist()
        summary["strain_force_coupling_diagnostics"] = dict(gamma.diagnostics)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "space_group": summary["space_group"], "stage_count": summary["stage_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
