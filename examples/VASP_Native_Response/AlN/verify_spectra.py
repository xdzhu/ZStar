"""Check native-mode indexing and 6mm IR/Raman selection rules."""

import csv
import json
from pathlib import Path

import numpy as np

from zstar.group_modesDB import get_irrep_activities
from zstar.read_irrep import read_irreps_yaml
from zstar.spectra import load_gamma_modes, load_raman_tensors


def validate(root: Path) -> dict:
    results = root / "results"
    modes = load_gamma_modes(results / "qpoints.yaml")
    numbers, tensors, _ = load_raman_tensors(results / "spectra_results.json")
    spectral = json.loads((results / "spectra_results.json").read_text())
    group, branches = read_irreps_yaml(results / "elastic" / "irreps.yaml")
    labels = {number: label for label, indices, _ in branches for number in indices}
    checks = {
        "equilibrium point group is 6mm": group == "6mm",
        "nine optical Raman tensors": tensors.shape == (9, 3, 3) and set(numbers) == set(range(4, 13)),
        "finite Raman tensors": np.all(np.isfinite(tensors)),
        "JSON IDs match exported mode frequencies": np.allclose(
            modes.frequencies_cm1[numbers - 1], spectral["frequencies_cm-1"], atol=1e-6),
    }
    reports = {}
    for kind, filename, field, tolerance in (
        ("ir", "ir_modes.csv", "intensity_total", 1e-4),
        ("raman", "raman_modes.csv", "activity_normalized", 0.01),
    ):
        with (results / f"{kind}_spectrum" / filename).open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        active, _ = get_irrep_activities(group, kind)
        values = np.asarray([float(row[field]) for row in rows])
        scale = float(np.max(values))
        normalizer = scale if np.isfinite(scale) and scale > 0 else 1.
        checks[f"{kind}: finite nonnegative activities"] = (
            np.all(np.isfinite(values)) and np.all(values >= 0) and scale > 0)
        checks[f"{kind}: all optical modes exported"] = {int(row["mode"]) for row in rows} == set(range(4, 13))
        inactive = [float(row[field]) / normalizer for row in rows if labels[int(row["mode"])] not in active]
        maximum = max(inactive, default=0.)
        checks[f"{kind}: inactive modes below numerical tolerance"] = maximum < tolerance
        reports[kind] = {"inactive_activity_max_normalized": maximum,
                         "inactive_activity_tolerance": tolerance,
                         "modes": [{"mode": int(row["mode"]), "irrep": labels[int(row["mode"])],
                                    "frequency_cm-1": float(row["frequency_cm-1"]),
                                    "activity_normalized": float(row[field]) / normalizer} for row in rows]}
    checks = {name: bool(value) for name, value in checks.items()}
    return {"passed": all(checks.values()), "checks": checks, "results": reports,
            "note": "Gamma TO modes without directional NAC; activity checks are not an absolute intensity benchmark."}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    report = validate(root)
    (root / "results" / "spectral_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
