"""Explicit finite-difference policy on top of the existing response fitter."""

from dataclasses import replace
import warnings

import numpy as np

from .model import ResponseDocument
from .reconstruct import fit_response_document


FORWARD_DIFFERENCE_WARNING = (
    "Forward finite differences have O(h) truncation error for smooth responses; "
    "central differences have O(h^2). Numerical noise and incomplete relaxation "
    "can add further errors. Central differences are recommended."
)


def difference_policy(method: str, *, warn: bool = True) -> dict:
    if method not in {"central", "forward"}:
        raise ValueError("finite-difference method must be 'central' or 'forward'")
    if method == "forward" and warn:
        warnings.warn(FORWARD_DIFFERENCE_WARNING, UserWarning, stacklevel=2)
    return {
        "method": method,
        "truncation_error_order": "O(h^2)" if method == "central" else "O(h)",
        "error_order_assumptions": "smooth response, valid stencil, controlled numerical noise",
        "recommendation": "central",
        "warning": FORWARD_DIFFERENCE_WARNING if method == "forward" else None,
    }


def _positive_direction(vector) -> bool:
    values = np.asarray(vector, dtype=float)
    significant = np.flatnonzero(np.abs(values) > np.max(np.abs(values)) * 1e-8)
    if not len(significant):
        raise ValueError("finite differences require a nonzero direction")
    return bool(values[significant[0]] > 0)


def fit_finite_difference_document(
    document: ResponseDocument, *, method: str = "central", **fit_options
) -> ResponseDocument:
    """Fit a paired central stencil or explicitly requested positive-side stencil.

    Forward means the direction whose first nonzero actual engineering-strain
    component is positive, including mixed-vector symmetry-adapted plans. No
    nominal amplitude or directory-name sign is used. The general-purpose
    ``fit_response_document`` remains available for arbitrary research samples.
    """
    policy = difference_policy(method)
    fit_options = dict(fit_options)
    strain = document.quantity("strain_vector")
    x = np.asarray(strain.values)
    tolerance = float(fit_options.get("reference_strain_tolerance", 1e-10))
    if not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError("reference_strain_tolerance must be finite and non-negative")
    zeros = np.flatnonzero(np.linalg.norm(x, axis=1) <= tolerance)
    if len(zeros) != 1:
        raise ValueError("finite differences require exactly one zero-strain reference")
    ref = int(zeros[0])
    if fit_options.get("reference_index", ref) not in {None, ref}:
        raise ValueError("reference_index must identify the zero-strain reference")
    nonzero = [i for i in range(len(x)) if i != ref]
    if fit_options.get("sample_weights") is not None:
        weights = np.asarray(tuple(fit_options["sample_weights"]), dtype=float)
        if weights.shape != (len(x),):
            raise ValueError("sample_weights must match the original strain stage count")
        fit_options["sample_weights"] = weights
    if not nonzero:
        raise ValueError("finite differences require nonzero strain observations")
    if method == "central":
        # Pair actual serialized vectors, not labels or nominal step sizes.
        remaining = set(nonzero)
        while remaining:
            i = min(remaining)
            matches = [j for j in remaining if j != i
                       and np.allclose(x[i], -x[j], rtol=1e-8, atol=1e-12)]
            if len(matches) != 1:
                raise ValueError(
                    "central differences require unique +/- actual strain pairs; "
                    "complete the missing pair or explicitly choose method='forward'"
                )
            if fit_options.get("sample_weights") is not None:
                if weights[i] != weights[matches[0]]:
                    raise ValueError("central differences require equal weights within each +/- pair")
            remaining.difference_update((i, matches[0]))
        selected = list(range(len(x)))
    else:
        selected = [ref] + [i for i in nonzero
                           if _positive_direction(x[i])]
        if len(selected) == 1:
            raise ValueError("forward differences require positive-side strain observations")
    names = strain.provenance.get("stage_names", [str(i) for i in range(len(x))])
    if len(names) != len(x):
        raise ValueError("strain_vector stage_names must match the stage count")
    selected_names = [names[i] for i in selected]
    quantities = []
    for quantity in document.quantities:
        if quantity.axes and quantity.axes[0] == "stage":
            if quantity.shape[0] != len(x):
                raise ValueError(f"{quantity.name} stage count must match strain_vector")
            provenance = {**quantity.provenance, "stage_names": selected_names}
            if "reference_index" in provenance:
                provenance["reference_index"] = selected.index(ref)
            quantities.append(replace(quantity, values=quantity.values[selected], provenance=provenance))
        else:
            quantities.append(quantity)
    options = dict(fit_options)
    options["reference_index"] = selected.index(ref)
    if options.get("sample_weights") is not None:
        options["sample_weights"] = weights[selected]
    fitted = fit_response_document(replace(document, quantities=tuple(quantities)), **options)
    fitted_names = fitted.provenance["response_fit"]["quantities"]
    for name in fitted_names:
        if not fitted.quantity(name).diagnostics["complete"]:
            raise ValueError(f"{method} difference sampling is rank-deficient for {name}; add independent strains")
    return replace(
        fitted,
        quantities=tuple(
            replace(q, provenance={**q.provenance, "finite_difference": policy})
            if q.name in fitted_names else q for q in fitted.quantities
        ),
        metadata={**fitted.metadata, "finite_difference": policy,
                  "fitted_stage_count": len(selected)},
        provenance={**fitted.provenance, "finite_difference": {
            **policy, "selected_source_indices": selected, "stage_names": selected_names,
        }},
    )
