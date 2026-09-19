"""Calculator-neutral fitting and packaging for v2 response documents."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Mapping

import numpy as np

from .fit import (
    LinearFitResult,
    fit_elastic_response,
    fit_internal_strain_response,
    fit_piezoelectric_response,
    fit_strain_force_coupling,
    fit_proper_piezoelectric_response,
)
from .mechanical import ENGINEERING_VOIGT
from .model import BoundaryConditions, ResponseDocument, TensorQuantity
from .symmetry import IntertwinerBasis


def _fit_diagnostics(result: LinearFitResult) -> dict[str, object]:
    """Serialize the numerical diagnostics shared by all linear fits."""

    return {
        "input_rank": int(result.input_rank),
        "allowed_rank": int(result.allowed_rank),
        "fit_rank": int(result.fit_rank),
        "complete": bool(result.complete),
        "singular_values": np.asarray(result.singular_values, dtype=float).tolist(),
        "condition_number": float(result.condition_number),
        "residual_max": float(result.residual_max),
        "residual_rms": float(result.residual_rms),
        "residual_relative": float(result.residual_relative),
        "suggested_input_indices": list(result.suggested_input_indices),
    }


def _reference_index(
    strains: np.ndarray,
    reference_index: int | None,
    tolerance: float,
) -> int:
    if not np.isfinite(float(tolerance)) or float(tolerance) < 0.0:
        raise ValueError("reference_strain_tolerance must be finite and non-negative")
    if strains.ndim != 2 or strains.shape[1] != 6 or strains.shape[0] == 0:
        raise ValueError(f"strain_vector must have shape (samples, 6); got {strains.shape}")
    if reference_index is None:
        candidates = np.flatnonzero(np.linalg.norm(strains, axis=1) <= float(tolerance))
        if candidates.size != 1:
            raise ValueError(
                "response document must contain exactly one zero-strain reference; "
                "pass reference_index explicitly or regenerate the ensemble"
            )
        index = int(candidates[0])
    else:
        index = int(reference_index)
        if index < 0 or index >= strains.shape[0]:
            raise ValueError(f"reference_index {index} is outside {strains.shape[0]} strain stages")
        if np.linalg.norm(strains[index]) > float(tolerance):
            raise ValueError(
                "reference_index does not identify a zero-strain stage within "
                "reference_strain_tolerance"
            )
    return index


def _quantity_or_none(document: ResponseDocument, name: str) -> TensorQuantity | None:
    try:
        return document.quantity(name)
    except KeyError:
        return None


def _stage_names(strain_quantity: TensorQuantity) -> list[str]:
    names = strain_quantity.provenance.get("stage_names", ())
    if names is not None and len(names):
        return [str(value) for value in names]
    return [str(index) for index in range(strain_quantity.shape[0])]


def _allowed_basis(
    allowed_bases: Mapping[str, IntertwinerBasis] | None,
    key: str,
) -> IntertwinerBasis | None:
    if allowed_bases is None:
        return None
    return allowed_bases.get(key)


def fit_response_document(
    document: ResponseDocument,
    *,
    reference_index: int | None = None,
    reference_strain_tolerance: float = 1.0e-10,
    stress_sign: str | None = None,
    enforce_major_symmetry: bool = False,
    allowed_bases: Mapping[str, IntertwinerBasis] | None = None,
    sample_weights: Iterable[float] | None = None,
    svd_cutoff: float | None = None,
    include_piezoelectric: bool = True,
    include_proper_piezoelectric: bool = False,
    include_elastic: bool = True,
    include_gamma: bool = True,
    include_internal_strain: bool = True,
) -> ResponseDocument:
    """Fit available strain responses and append explicit tensor quantities.

    The input must be a collected v2 document containing ``strain_vector`` and
    the corresponding observation quantities.  The function never guesses a
    stress sign: when ``stress_raw`` is present, ``stress_sign`` is required
    and must describe the calculator output.  Polarization is fitted only from
    branch-matched Cartesian ``polarization_cartesian`` values and only for a
    three-dimensional document.  Missing observation blocks are left untouched
    rather than filled with zeros.

    This is a research API.  It packages raw finite-difference fits with units,
    axes and rank/residual diagnostics; it does not apply proper-piezoelectric
    geometric corrections, acoustic projections, or relaxed-ion BEC algebra.
    Those operations require separately validated inputs and remain explicit
    downstream steps.  Set ``include_proper_piezoelectric=True`` only when the
    Cartesian reference polarization is branch-matched; this appends the raw
    geometric correction and proper tensor without overwriting the raw fit.
    ``sample_weights`` and ``svd_cutoff`` are forwarded to
    every enabled linear fit so precision/conditioning choices remain visible.
    """

    if not isinstance(document, ResponseDocument):
        raise TypeError("document must be a v2 ResponseDocument")
    strains_quantity = _quantity_or_none(document, "strain_vector")
    if strains_quantity is None:
        raise ValueError("response document is missing required strain_vector quantity")
    strains = np.asarray(strains_quantity.values, dtype=float)
    index = _reference_index(strains, reference_index, reference_strain_tolerance)
    stage_names = _stage_names(strains_quantity)
    if len(stage_names) != strains.shape[0]:
        raise ValueError("strain_vector provenance stage_names must match the stage count")
    periodic_axes = document.dimensionality.periodic_axes
    additions: list[TensorQuantity] = []

    polarization = _quantity_or_none(document, "polarization_cartesian")
    if include_piezoelectric and polarization is not None:
        if document.dimensionality.value != 3:
            raise ValueError(
                "bulk piezoelectric fitting requires dimensionality=3; "
                "use an explicit validated low-dimensional response definition"
            )
        if polarization.shape != (strains.shape[0], 3):
            raise ValueError(
                "polarization_cartesian must have shape (samples, 3) matching strain_vector; "
                f"got {polarization.shape}"
            )
        # A Cartesian Berry value is not a usable finite-difference
        # observable merely because it has the right shape: wrapped values
        # from different stages can differ by a polarization quantum.  The
        # collector must therefore leave an explicit, auditable contract in
        # provenance.  Do not infer this from the source/backend name, since
        # hand-written or legacy documents may contain unwrapped-looking
        # numbers without having performed branch matching.
        if polarization.provenance.get("branch_matched") is not True:
            raise ValueError(
                "polarization_cartesian is missing explicit branch-matching "
                "provenance; match every stage to the reference Berry branch "
                "and set provenance['branch_matched']=true before fitting "
                "a piezoelectric response"
            )
        branch_residual = polarization.provenance.get("branch_residual_max")
        if branch_residual is not None:
            try:
                branch_residual_value = float(branch_residual)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "polarization_cartesian branch_residual_max must be numeric"
                ) from exc
            if not np.isfinite(branch_residual_value) or branch_residual_value < 0.0:
                raise ValueError(
                    "polarization_cartesian branch_residual_max must be finite and non-negative"
                )
        if include_proper_piezoelectric:
            proper_fit = fit_proper_piezoelectric_response(
                strains,
                polarization.values,
                reference_polarization=polarization.values[index],
                allowed_basis=_allowed_basis(allowed_bases, "piezoelectric"),
                sample_weights=sample_weights,
                svd_cutoff=svd_cutoff,
            )
            fit = proper_fit.raw_fit
        else:
            proper_fit = None
            fit = fit_piezoelectric_response(
                strains,
                polarization.values,
                reference_polarization=polarization.values[index],
                allowed_basis=_allowed_basis(allowed_bases, "piezoelectric"),
                sample_weights=sample_weights,
                svd_cutoff=svd_cutoff,
            )
        additions.append(
            TensorQuantity(
                name="piezoelectric_raw",
                values=fit.matrix,
                unit=polarization.unit,
                axes=("polarization_cartesian", "voigt_engineering"),
                coordinate_system=polarization.coordinate_system,
                voigt_convention=ENGINEERING_VOIGT,
                ion_relaxation=polarization.ion_relaxation,
                boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
                periodic_axes=periodic_axes,
                normalization=polarization.normalization,
                source="finite_difference_fit",
                backend=document.backend,
                provenance={
                    "stage_names": stage_names,
                    "reference_index": index,
                    "input_quantity": polarization.name,
                    "branch_matching_required": True,
                    "piezoelectric_kind": "raw",
                    "definition": "dP_cartesian/dengineering_strain at fixed declared ion state",
                },
                diagnostics=_fit_diagnostics(fit),
            )
        )
        if include_proper_piezoelectric:
            assert proper_fit is not None
            proper_provenance = {
                "stage_names": stage_names,
                "reference_index": index,
                "input_quantity": polarization.name,
                "reference_polarization_C_per_m2": polarization.values[index].tolist(),
                "piezoelectric_kind": "proper",
                "definition": "Vanderbilt proper piezoelectric derivative",
            }
            proper_diagnostics = {
                **_fit_diagnostics(fit),
                "proper_reference_index": int(index),
            }
            for name, values, definition in (
                (
                    "piezoelectric_geometric_correction",
                    proper_fit.proper.correction,
                    "proper minus raw geometric correction",
                ),
                (
                    "piezoelectric_proper",
                    proper_fit.proper.proper,
                    "proper piezoelectric derivative at fixed declared ion state",
                ),
            ):
                additions.append(
                    TensorQuantity(
                        name=name,
                        values=values,
                        unit=polarization.unit,
                        axes=("polarization_cartesian", "voigt_engineering"),
                        coordinate_system=polarization.coordinate_system,
                        voigt_convention=ENGINEERING_VOIGT,
                        ion_relaxation=polarization.ion_relaxation,
                        boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
                        periodic_axes=periodic_axes,
                        normalization=polarization.normalization,
                        source="proper_piezoelectric_correction",
                        backend=document.backend,
                        provenance={**proper_provenance, "definition": definition},
                        diagnostics=proper_diagnostics,
                    )
                )

    stress = _quantity_or_none(document, "stress_raw")
    if include_elastic and stress is not None:
        if stress_sign is None:
            raise ValueError(
                "stress_raw uses a backend-dependent sign; pass stress_sign explicitly "
                "as tension-positive or compression-positive before fitting elastic response"
            )
        if stress.shape[0] != strains.shape[0]:
            raise ValueError("stress_raw stage count must match strain_vector")
        fit = fit_elastic_response(
            strains,
            stress.values,
            reference_stress=stress.values[index],
            stress_sign=stress_sign,
            allowed_basis=_allowed_basis(allowed_bases, "elastic"),
            enforce_major_symmetry=enforce_major_symmetry,
            sample_weights=sample_weights,
            svd_cutoff=svd_cutoff,
        )
        additions.append(
            TensorQuantity(
                name="elastic",
                values=fit.matrix,
                unit=stress.unit,
                axes=("stress_voigt", "voigt_engineering"),
                coordinate_system=stress.coordinate_system,
                voigt_convention=ENGINEERING_VOIGT,
                ion_relaxation=stress.ion_relaxation,
                boundary_conditions=BoundaryConditions(
                    electric="E", mechanical="strain", stress_sign="tension-positive"
                ),
                periodic_axes=periodic_axes,
                normalization=stress.normalization,
                source="finite_difference_fit",
                backend=document.backend,
                provenance={
                    "stage_names": stage_names,
                    "reference_index": index,
                    "input_quantity": stress.name,
                    "input_stress_sign": str(stress_sign),
                    "output_stress_sign": "tension-positive",
                    "output_stress_voigt_convention": ["xx", "yy", "zz", "yz", "xz", "xy"],
                },
                diagnostics=_fit_diagnostics(fit),
            )
        )

    force = _quantity_or_none(document, "forces_initial")
    if include_gamma and force is None:
        force = _quantity_or_none(document, "forces")
        relaxed_declared = str(document.metadata.get("ion_relaxation", "")).strip().lower()
        relaxed_quantity = force is not None and force.ion_relaxation == "relaxed-ion"
        if force is not None and (relaxed_declared == "relaxed-ion" or relaxed_quantity):
            raise ValueError(
                "cannot fit Gamma from final relaxed-ion forces: the response document "
                "is missing forces_initial; recollect logs with an identifiable first "
                "TOTAL-FORCE block instead of using the converged zero-force block"
            )
    if include_gamma and force is not None:
        if force.shape[0] != strains.shape[0] or len(force.shape) != 3 or force.shape[-1] != 3:
            raise ValueError(
                "force quantity must have shape (samples, atoms, 3) matching strain_vector; "
                f"got {force.shape}"
            )
        fit = fit_strain_force_coupling(
            strains,
            force.values,
            reference_forces=force.values[index],
            allowed_basis=_allowed_basis(allowed_bases, "gamma"),
            sample_weights=sample_weights,
            svd_cutoff=svd_cutoff,
        )
        additions.append(
            TensorQuantity(
                name="strain_force_coupling",
                values=fit.matrix.reshape(force.shape[1], 3, 6),
                unit=force.unit,
                axes=("atom", "cartesian", "voigt_engineering"),
                coordinate_system=force.coordinate_system,
                voigt_convention=ENGINEERING_VOIGT,
                ion_relaxation="clamped-ion",
                boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
                periodic_axes=periodic_axes,
                normalization="cell_response",
                source="finite_difference_fit",
                backend=document.backend,
                provenance={
                    "stage_names": stage_names,
                    "reference_index": index,
                    "input_quantity": force.name,
                    "definition": "Gamma = -dF/dengineering_strain",
                },
                diagnostics=_fit_diagnostics(fit),
            )
        )

    displacement = _quantity_or_none(document, "internal_displacement")
    if include_internal_strain and displacement is not None:
        if (
            displacement.shape[0] != strains.shape[0]
            or len(displacement.shape) != 3
            or displacement.shape[-1] != 3
        ):
            raise ValueError(
                "internal_displacement must have shape (samples, atoms, 3) matching strain_vector; "
                f"got {displacement.shape}"
            )
        fit = fit_internal_strain_response(
            strains,
            displacement.values,
            reference_displacement=displacement.values[index],
            allowed_basis=_allowed_basis(allowed_bases, "internal_strain"),
            sample_weights=sample_weights,
            svd_cutoff=svd_cutoff,
        )
        additions.append(
            TensorQuantity(
                name="internal_strain",
                values=fit.matrix.reshape(displacement.shape[1], 3, 6),
                unit=displacement.unit,
                axes=("atom", "cartesian", "voigt_engineering"),
                coordinate_system=displacement.coordinate_system,
                voigt_convention=ENGINEERING_VOIGT,
                ion_relaxation="relaxed-ion",
                boundary_conditions=BoundaryConditions(electric="E", mechanical="strain"),
                periodic_axes=periodic_axes,
                normalization=displacement.normalization,
                source="finite_difference_fit",
                backend=document.backend,
                provenance={
                    "stage_names": stage_names,
                    "reference_index": index,
                    "input_quantity": displacement.name,
                    "acoustic_gauge": displacement.provenance.get("acoustic_gauge", "unspecified"),
                    "definition": "Lambda = dinternal_displacement/dengineering_strain",
                },
                diagnostics=_fit_diagnostics(fit),
            )
        )

    if not additions:
        raise ValueError(
            "response document contains no enabled strain response observations; "
            "expected polarization_cartesian, stress_raw, forces(_initial), or internal_displacement"
        )
    existing_names = {quantity.name for quantity in document.quantities}
    duplicate_names = sorted(existing_names.intersection(quantity.name for quantity in additions))
    if duplicate_names:
        raise ValueError(
            "response document already contains fitted quantity/quantities: "
            + ", ".join(duplicate_names)
        )
    metadata = dict(document.metadata)
    metadata["fitted_quantities"] = list(metadata.get("fitted_quantities", ())) + [
        quantity.name for quantity in additions
    ]
    provenance = dict(document.provenance)
    provenance["response_fit"] = {
        "reference_index": index,
        "reference_strain_tolerance": float(reference_strain_tolerance),
        "quantities": [quantity.name for quantity in additions],
        "stress_sign": None if stress_sign is None else str(stress_sign),
    }
    return replace(
        document,
        quantities=tuple(document.quantities) + tuple(additions),
        provenance=provenance,
        metadata=metadata,
    )
