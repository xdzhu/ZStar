"""Make the Panel (d) overlay on exactly the archived DFT q-path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from phonopy import load

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from zstar.phonon_spectrum import compare_phonon_spectra


def _bands(root: Path, qpoints: list[np.ndarray], distances, nac: bool) -> dict:
    kwargs = {
        "phonopy_yaml": str(root / "phonopy.yaml"),
        "force_sets_filename": str(root / "FORCE_SETS"),
        "calculator": "vasp",
        "produce_fc": True,
    }
    if nac:
        kwargs.update(is_nac=True, born_filename=str(root / "BORN"))
    phonon = load(**kwargs)
    phonon.run_band_structure(qpoints, path_connections=[True] * len(qpoints))
    bands = phonon.get_band_structure_dict()
    return {
        "distances": distances,
        "frequencies": [np.asarray(item).tolist() for item in bands["frequencies"]],
        "qpoints": [np.asarray(item).tolist() for item in qpoints],
        "frequency_points": [],
        "total_dos": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True)
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--output-result", required=True)
    parser.add_argument("--output-figure", required=True)
    args = parser.parse_args()
    reference = Path(args.reference).resolve()
    candidate_root = Path(args.candidate_root).resolve()
    reference_data = json.loads(reference.read_text(encoding="utf-8"))
    qpoints = [np.asarray(item, dtype=float) for item in reference_data["with_nac"]["qpoints"]]
    result = {
        "schema": "zstar-phonon-spectrum-result",
        "calculator": "gpumd-qnep",
        "frequency_unit": reference_data["frequency_unit"],
        "nac_available": True,
        "nac_source": "BORN (qNEP model BEC and epsilon_infinity)",
        "npoints": reference_data["npoints"],
        "mesh": [0, 0, 0],
        "band_only": True,
        "omit_disconnected_tail": reference_data.get("omit_disconnected_tail", False),
        "space_group_number": reference_data.get("space_group_number"),
        "space_group_symbol": reference_data.get("space_group_symbol"),
        "path_generator": "reference-DFT-qpath",
        "labels": reference_data["labels"],
        "wo_nac": _bands(candidate_root, qpoints, reference_data["with_nac"]["distances"], False),
        "with_nac": _bands(candidate_root, qpoints, reference_data["with_nac"]["distances"], True),
        "outputs": [],
    }
    output_result = Path(args.output_result).resolve()
    output_result.parent.mkdir(parents=True, exist_ok=True)
    output_result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    compare_phonon_spectra(
        reference,
        output_result,
        args.output_figure,
        reference_label="DFT/PBEsol + NAC",
        candidate_label="qNEP + NAC (model BEC, ε∞)",
    )


if __name__ == "__main__":
    main()
