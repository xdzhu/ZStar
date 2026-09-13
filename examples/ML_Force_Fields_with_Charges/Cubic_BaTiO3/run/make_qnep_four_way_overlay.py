"""Plot DFT/qNEP phonons with and without NAC on one common q-path.

The four-way comparison separates short-range force-field error from the
additional change introduced by BEC/NAC: DFT(no NAC), qNEP(no NAC),
DFT(+NAC), and qNEP(+NAC).  The input result JSON files are produced by the
existing ZStar/Phonopy workflows and therefore share the same q-path.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 8,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "xtick.direction": "out",
        "ytick.direction": "out",
    }
)


def _flatten(result: dict, key: str) -> tuple[np.ndarray, np.ndarray]:
    distances = np.asarray(result[key]["distances"], dtype=float)
    frequencies = np.asarray(result[key]["frequencies"], dtype=float)
    if distances.shape[:2] != frequencies.shape[:2]:
        raise ValueError(f"distance/frequency shape mismatch for {key}: {distances.shape} vs {frequencies.shape}")
    return distances.reshape(-1), frequencies.reshape(-1, frequencies.shape[-1])


def _metric(reference: np.ndarray, candidate: np.ndarray) -> dict:
    delta = candidate - reference
    return {
        "mae_thz": float(np.mean(np.abs(delta))),
        "rmse_thz": float(np.sqrt(np.mean(delta**2))),
        "max_abs_thz": float(np.max(np.abs(delta))),
        "n_values": int(delta.size),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dft", required=True, help="DFT result JSON with wo_nac and with_nac")
    parser.add_argument("--qnep", required=True, help="qNEP result JSON with wo_nac and with_nac")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-png", required=True)
    parser.add_argument("--output-pdf", required=True)
    args = parser.parse_args()

    dft = json.loads(Path(args.dft).read_text(encoding="utf-8"))
    qnep = json.loads(Path(args.qnep).read_text(encoding="utf-8"))
    dft_wo_d, dft_wo = _flatten(dft, "wo_nac")
    dft_nac_d, dft_nac = _flatten(dft, "with_nac")
    qnep_wo_d, qnep_wo = _flatten(qnep, "wo_nac")
    qnep_nac_d, qnep_nac = _flatten(qnep, "with_nac")
    if not (np.allclose(dft_wo_d, dft_nac_d) and np.allclose(dft_wo_d, qnep_wo_d) and np.allclose(dft_wo_d, qnep_nac_d)):
        raise ValueError("DFT and qNEP results do not use the same q-path distances")
    if dft_wo.shape != qnep_wo.shape or dft_nac.shape != qnep_nac.shape:
        raise ValueError("DFT and qNEP band arrays have different shapes")

    nbranches = dft_wo.shape[-1]
    x = dft_wo_d
    labels = dft.get("labels", [r"$\\Gamma$", "X", "M", r"$\\Gamma$", "R", "X"])
    boundaries = np.linspace(x.min(), x.max(), len(labels))
    # The archived result stores path segments, so use segment ends rather
    # than assume equal physical lengths for the tick locations.
    segment_ends = [float(np.asarray(seg)[-1]) for seg in dft["wo_nac"]["distances"]]
    tick_positions = [0.0] + segment_ends

    fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    for branch in range(nbranches):
        ax.plot(x, dft_wo[:, branch], color="#7f8790", lw=0.75, alpha=0.65)
        ax.plot(x, dft_nac[:, branch], color="#20252b", lw=1.05, alpha=0.85)
        ax.plot(x, qnep_wo[:, branch], color="#2f6da8", lw=0.75, ls="--", alpha=0.75)
        ax.plot(x, qnep_nac[:, branch], color="#c84b4b", lw=0.9, alpha=0.8)

    handles = [
        mpl.lines.Line2D([], [], color="#7f8790", lw=1.2, label="DFT / no NAC"),
        mpl.lines.Line2D([], [], color="#20252b", lw=1.4, label="DFT / +NAC"),
        mpl.lines.Line2D([], [], color="#2f6da8", lw=1.2, ls="--", label="qNEP / no NAC"),
        mpl.lines.Line2D([], [], color="#c84b4b", lw=1.3, label="qNEP / +NAC"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=False, ncol=2, handlelength=2.4, columnspacing=1.2)
    ax.set_xlabel("Wave vector")
    ax.set_ylabel("Frequency (THz)")
    ax.set_xticks(tick_positions, labels)
    ax.grid(axis="y", color="#d9dde2", lw=0.5, alpha=0.8)
    ax.set_xlim(float(x.min()), float(x.max()))
    all_freq = np.concatenate([dft_wo.ravel(), dft_nac.ravel(), qnep_wo.ravel(), qnep_nac.ravel()])
    margin = max(0.5, 0.03 * (all_freq.max() - all_freq.min()))
    ax.set_ylim(float(all_freq.min() - margin), float(all_freq.max() + margin))
    ax.set_title("Cubic BaTiO$_3$: separating force-field and NAC effects", pad=8)

    output_png = Path(args.output_png).resolve()
    output_pdf = Path(args.output_pdf).resolve()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=600, bbox_inches="tight")
    fig.savefig(output_pdf, bbox_inches="tight")
    plt.close(fig)

    dft_delta = dft_nac - dft_wo
    qnep_delta = qnep_nac - qnep_wo
    result = {
        "schema": "zstar-qnep-four-way-phonon-comparison",
        "frequency_unit": dft.get("frequency_unit", "THz"),
        "qpath_labels": labels,
        "source": {"dft": str(Path(args.dft).resolve()), "qnep": str(Path(args.qnep).resolve())},
        "metrics": {
            "short_range_force_field_error_no_nac": _metric(dft_wo, qnep_wo),
            "total_error_with_nac": _metric(dft_nac, qnep_nac),
            "nac_increment_difference": _metric(dft_delta, qnep_delta),
        },
        "outputs": [str(output_png), str(output_pdf)],
    }
    Path(args.output_json).resolve().write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
