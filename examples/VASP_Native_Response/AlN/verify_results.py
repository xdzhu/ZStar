"""Check native outputs against raw VASP data and wurtzite constraints."""

import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from zstar.spectroscopy_backends import load_vasp_gamma_modes
from zstar.vasp_bec import parse_vasp_outcar


def xml_dielectric(run, path: Path) -> np.ndarray:
    epsilon = np.asarray(run.epsilon_static)
    if epsilon.shape == (3, 3):
        return epsilon
    # Native strain runs may write epsilon outside the final calculation block.
    arrays = ET.parse(path).findall(".//varray[@name='epsilon']")
    if not arrays:
        raise ValueError(f"No electronic dielectric tensor in {path}")
    epsilon = np.asarray([[float(value) for value in row.text.split()]
                          for row in arrays[-1].findall("v")])
    if epsilon.shape != (3, 3) or not np.all(np.isfinite(epsilon)):
        raise ValueError(f"Invalid electronic dielectric tensor in {path}")
    return epsilon


def validate(root: Path) -> dict:
    from pymatgen.io.vasp.outputs import Vasprun

    checks = {}
    reports = {}
    for route in ("dfpt", "elastic"):
        work = root / ".work" / route
        native = json.loads((work / "vasp_native_response.json").read_text())
        bec = json.loads((work / "vasp_bec.json").read_text())
        epsilon, born = parse_vasp_outcar(work / "response" / "OUTCAR")
        run = Vasprun(work / "response" / "vasprun.xml", parse_dos=False,
                      parse_projected_eigen=False, parse_potcar_file=False)
        xml_epsilon_error = float(np.max(np.abs(epsilon - xml_dielectric(run, work / "response" / "vasprun.xml"))))
        bec_error = float(np.max(np.abs(born - np.asarray([a["tensor"] for a in bec["atoms"]]))))
        modes = load_vasp_gamma_modes(work / "response" / "vasprun.xml")
        frequencies = np.sort(modes.frequencies_cm1)
        tensor = native["tensors"]
        e = np.asarray(tensor["piezoelectric_total_C_m2"])
        expected_e = np.zeros((3, 6))
        expected_e[0, 4] = expected_e[1, 3] = 0.5 * (e[0, 4] + e[1, 3])
        expected_e[2, 0] = expected_e[2, 1] = 0.5 * (e[2, 0] + e[2, 1])
        expected_e[2, 2] = e[2, 2]
        symmetry_error = float(np.max(np.abs(e - expected_e)))
        closure = float(native["diagnostics"]["static_dielectric_max_abs"])
        reference_run = Vasprun(work / "reference" / "vasprun.xml", parse_dos=False,
                               parse_projected_eigen=False, parse_potcar_file=False)
        gap = float(reference_run.eigenvalue_band_properties[0])
        checks[f"{route}: insulating electronic state"] = gap > 0.01
        checks[f"{route}: epsilon matches XML"] = xml_epsilon_error < 2e-6
        checks[f"{route}: BEC matches raw OUTCAR"] = bec_error < 1e-10
        checks[f"{route}: charge sum rule"] = float(np.max(np.abs(born.sum(axis=0)))) < 5e-3
        checks[f"{route}: 12 modes, 9 positive optical modes"] = (
            len(frequencies) == 12 and np.all(np.isfinite(frequencies)) and frequencies[3] > 5)
        checks[f"{route}: harmonic static closure"] = closure < 5e-3
        checks[f"{route}: 6mm piezo tensor"] = symmetry_error < 0.03
        reports[route] = {
            "band_gap_eV": gap,
            "epsilon_infinity": epsilon.tolist(),
            "epsilon_static": tensor["epsilon_static"],
            "optical_frequencies_cm1": frequencies[3:].tolist(),
            "Al_BEC_diagonal_e": np.diag(born[0]).tolist(),
            "e31_e33_e15_C_m2": [float(e[2, 0]), float(e[2, 2]), float(e[0, 4])],
            "piezo_symmetry_max_C_m2": symmetry_error,
            "independent_XML_epsilon_max": xml_epsilon_error,
            "diagnostics": native["diagnostics"],
        }
        if route == "elastic":
            checks["elastic: reliable derived d emitted"] = "piezoelectric_d_pm_V" in tensor
            if "piezoelectric_d_pm_V" in tensor:
                c = np.asarray(tensor["elastic_relaxed_GPa"])
                d = np.asarray(tensor["piezoelectric_d_pm_V"])
                checks["elastic: e = d C"] = float(np.max(np.abs(d @ c / 1000 - e))) < 1e-10
                reports[route]["d31_d33_d15_pm_V"] = [float(d[2, 0]), float(d[2, 2]), float(d[0, 4])]
                reports[route]["elastic_GPa"] = c.tolist()
    reports["optical_frequency_route_max_cm1"] = float(np.max(np.abs(
        np.asarray(reports["dfpt"]["optical_frequencies_cm1"])
        - np.asarray(reports["elastic"]["optical_frequencies_cm1"]))))
    checks["DFPT/FD optical frequencies agree"] = reports["optical_frequency_route_max_cm1"] < 2.0
    checks = {name: bool(passed) for name, passed in checks.items()}
    return {
        "passed": all(checks.values()), "checks": checks, "results": reports,
        "literature": {
            "doi": "10.1038/sdata.2015.53", "software": "VASP", "XC": "PBE",
            "potential": "PAW", "e33_C_m2": 1.46, "e31_C_m2": -0.58,
            "comparison_note": "Check polarity and proper tensor convention before signed comparison; different cutoff/mesh",
        },
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    report = validate(root)
    (root / "results" / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
