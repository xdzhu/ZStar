#!/usr/bin/env python3
"""Collect and fit a completed ABACUS+PYATB v2 strain case.

The script is deliberately post-processing only: it never launches a
calculator.  Stress is converted explicitly from ABACUS compression-positive
raw output to the tension-positive thermodynamic convention before fitting.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zstar.v2.abacus import collect_pyatb_strain_response
from zstar.v2.reconstruct import fit_response_document
from zstar.v2.units import convert_values


def _quantity(document, name):
    try:
        return document.quantity(name)
    except KeyError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, default=None)
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
