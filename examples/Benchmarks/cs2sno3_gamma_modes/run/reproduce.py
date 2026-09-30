"""Reproduce the Cs2SnO3 Gamma-mode translation/instability audit."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
from phonopy import load

from zstar.spectra import GammaModes, assess_gamma_modes, load_gamma_modes, validate_gamma_stability


ROOT = Path(__file__).resolve().parent


def _asr_corrected_modes() -> GammaModes:
    source = ROOT / "asr_primitive"
    kwargs = {
        "phonopy_yaml": str(source / "phonopy.yaml"),
        "force_constants_filename": str(source / "FORCE_CONSTANTS"),
        "is_nac": False,
    }
    if "lang" in inspect.signature(load).parameters:
        kwargs["lang"] = "C"
    phonon = load(**kwargs)
    phonon.symmetrize_force_constants()
    phonon.run_qpoints([[0, 0, 0]], with_eigenvectors=True)
    result = phonon.qpoints
    primitive = phonon.primitive
    natoms = len(primitive.masses)
    eigenvectors = np.asarray(result.eigenvectors[0]).T.reshape(3 * natoms, natoms, 3)
    return GammaModes(
        frequencies_thz=np.asarray(result.frequencies[0], dtype=float),
        eigenvectors=eigenvectors,
        masses_amu=np.asarray(primitive.masses, dtype=float),
        lattice_angstrom=np.asarray(primitive.cell, dtype=float),
        symbols=tuple(primitive.symbols),
        positions_fractional=np.asarray(primitive.scaled_positions, dtype=float),
    )


def _audit(modes: GammaModes) -> dict:
    rows = assess_gamma_modes(modes)
    flagged = validate_gamma_stability(modes, allow_imaginary=True)
    return {
        "atom_count": len(modes.masses_amu),
        "flagged_mode_numbers": flagged.tolist(),
        "negative_modes": [row for row in rows if row["frequency_cm-1"] < -1e-3],
        "translation_modes": [row for row in rows if row["classification"] == "translation"],
        "mixed_modes": [row for row in rows if row["classification"] == "mixed"],
        "translation_subspace_weight": sum(row["translation_overlap"] for row in rows),
        "modes": rows,
    }


def main() -> None:
    results = {
        "raw_primitive_dfpt": _audit(load_gamma_modes(ROOT / "raw_primitive/qpoints.yaml")),
        "asr_corrected_primitive_dfpt": _audit(_asr_corrected_modes()),
        "conventional_cell": _audit(load_gamma_modes(ROOT / "conventional/qpoints.yaml")),
    }
    raw = results["raw_primitive_dfpt"]
    corrected = results["asr_corrected_primitive_dfpt"]
    conventional = results["conventional_cell"]
    assert raw["flagged_mode_numbers"] == [1]
    assert raw["modes"][0]["classification"] == "mixed"
    assert 0.65 < raw["modes"][0]["translation_overlap"] < 0.69
    assert corrected["flagged_mode_numbers"] == [1]
    assert corrected["modes"][0]["classification"] == "non-translation"
    assert abs(corrected["modes"][0]["translation_overlap"]) < 1e-4
    assert conventional["flagged_mode_numbers"] == []
    assert all(row["classification"] == "translation" for row in conventional["negative_modes"])
    destination = ROOT / "output" / "mode_audit.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    for name, result in results.items():
        print(f"{name}: flagged={result['flagged_mode_numbers']}")
        for row in result["negative_modes"]:
            print(
                f"  mode {row['mode']:2d}: {row['frequency_cm-1']:8.3f} cm-1; "
                f"translation overlap={row['translation_overlap']:.4f}; "
                f"{row['classification']}"
            )
    print(destination)


if __name__ == "__main__":
    main()
