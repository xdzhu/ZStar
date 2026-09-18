"""Acceptance checks for the compact SiC native response and mixed spectra."""

import csv
import json
from pathlib import Path

import numpy as np

from zstar.spectra import load_gamma_modes, load_raman_tensors


def validate(root: Path) -> dict:
    results = root / "results"
    records = {route: json.loads((results / route / "vasp_native_response.json").read_text())
               for route in ("dfpt", "elastic")}
    checks = {}
    optical = {}
    for route, record in records.items():
        frequencies = np.sort(np.asarray(record["tensors"]["frequencies_thz"]))
        optical[route] = frequencies[3:]
        checks[f"{route}: three stable optical modes"] = (
            len(frequencies) == 6 and np.all(np.isfinite(frequencies)) and frequencies[3] > 1.)
        checks[f"{route}: harmonic dielectric closure"] = record["diagnostics"]["static_dielectric_max_abs"] < 1e-3
        born = json.loads((results / route / "vasp_bec.json").read_text())
        tensors = np.asarray([atom["tensor"] for atom in born["atoms"]])
        checks[f"{route}: charge sum rule"] = np.max(np.abs(tensors.sum(axis=0))) < 1e-3
    checks["native optical routes agree"] = np.max(np.abs(optical["dfpt"] - optical["elastic"])) < .01
    checks["quality-checked elastic d emitted"] = "piezoelectric_d_pm_V" in records["elastic"]["tensors"]
    modes = load_gamma_modes(results / "qpoints.yaml")
    numbers, tensors, _ = load_raman_tensors(results / "spectra_results.json")
    checks["Raman tensors match optical Gamma IDs"] = set(numbers) == {4, 5, 6} and tensors.shape == (3, 3, 3)
    spectral = json.loads((results / "spectra_results.json").read_text())
    checks["Raman frequency-ID alignment"] = np.allclose(
        modes.frequencies_cm1[numbers - 1], spectral["frequencies_cm-1"], atol=1e-6)
    with (results / "raman_spectrum" / "raman_modes.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    activity = np.asarray([float(row["activity_normalized"]) for row in rows])
    ratios = np.asarray([float(row["depolarization_ratio"]) for row in rows])
    checks["triplet Raman activity agreement"] = np.all(np.isfinite(activity)) and np.ptp(activity) < .002
    checks["T2 depolarization ratio"] = np.allclose(ratios, .75, atol=.001)
    checks = {name: bool(value) for name, value in checks.items()}
    return {"passed": all(checks.values()), "checks": checks,
            "DFPT_diagnostics": records["dfpt"]["diagnostics"],
            "elastic_diagnostics": records["elastic"]["diagnostics"],
            "note": "Native DFPT electromechanical warnings remain; Gamma TO data without directional NAC."}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    report = validate(root)
    (root / "results" / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
