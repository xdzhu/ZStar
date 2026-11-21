"""Compare the held-out hBN responses using the same branch convention."""
from pathlib import Path
import argparse
import json
import math
import re

E_CHARGE = 1.602176634e-19
NUMBER = r"[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[Ee][+-]?\d+)?"
LINE = re.compile(rf"direction is in c,\s*P\s*=?\s*({NUMBER})\s*\(mod\s*({NUMBER})\)")
PLUS, MINUS = "disp-005", "disp-006"
LIMIT, NULL_LIMIT = 0.05, 0.005


def out(path):
    status = int((path / "exit_status.txt").read_text().strip())
    if status:
        raise ValueError(f"Failed PYATB run ({status}) at {path}")
    filename = path / "Out" / "Polarization" / "polarization.dat"
    match = LINE.findall(filename.read_text())
    if len(match) != 1:
        raise ValueError(f"Invalid z polarization at {filename}")
    p, q = map(float, match[0])
    if not math.isfinite(p) or not math.isfinite(q) or q <= 0:
        raise ValueError(f"Invalid polarization or quantum at {filename}")
    return p,q


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control", type=Path)
    parser.add_argument("hamgnn", type=Path)
    parser.add_argument("deeph", type=Path)
    parser.add_argument("summary", type=Path)
    args = parser.parse_args()
    controls = json.loads((args.control / "spectra.json").read_text())
    results = {}
    assert controls[PLUS]["volume_A3"] == controls[MINUS]["volume_A3"]
    volume = controls[PLUS]["volume_A3"] * 1e-30
    span = (controls[PLUS]["z_N_A"] - controls[MINUS]["z_N_A"]) * 1e-10
    assert span > 0
    for model in ("reference", "fixed", "hamgnn", "deeph"):
        root = args.control if model in ("reference","fixed") else getattr(args, model)
        spectra = json.loads((root / "spectra.json").read_text())
        p_plus, quantum_plus = out(root / PLUS / model)
        p_minus, quantum_minus = out(root / MINUS / model)
        assert quantum_plus == quantum_minus
        difference = p_plus - p_minus
        difference -= round(difference / quantum_plus) * quantum_plus
        if abs(difference) > 0.01 * quantum_plus:
            raise ValueError(f"Unexpected branch for {model}")
        z = volume * difference / (E_CHARGE * span)
        results[model] = {
            "P_plus_C_per_m2": p_plus, "P_minus_C_per_m2": p_minus,
            "delta_Pz_C_per_m2": difference, "Zstar_zz_e": z,
            "minimum_sampled_indirect_gap_eV": min(spectra[n]["methods"][model]["indirect_gap_eV"] for n in (PLUS,MINUS)),
        }
    z_ref = results["reference"]["Zstar_zz_e"]
    base = abs(results["fixed"]["Zstar_zz_e"] - z_ref)
    for model in ("fixed","hamgnn","deeph"):
        error = abs(results[model]["Zstar_zz_e"] - z_ref)
        results[model]["abs_Zstar_error_e"] = error
        if model in ("hamgnn","deeph"):
            gain = base - error
            results[model]["abs_Zstar_error_improvement_e"] = gain
            results[model]["assessment"] = (
                "supports_accuracy" if error <= LIMIT and gain > NULL_LIMIT
                else "indistinguishable_from_fixed_H" if abs(gain) <= NULL_LIMIT
                else "end_to_end_only"
            )
    summary = {"sample_material": "hBN", "displacement_span_A": span * 1e10,
               "Berry_mesh": [36,36,8], "z_quantum_C_per_m2": quantum_plus, "methods": results}
    result = json.dumps(summary, indent=2)
    args.summary.write_text(result + "\n")
    print(result)


if __name__ == "__main__":
    main()
