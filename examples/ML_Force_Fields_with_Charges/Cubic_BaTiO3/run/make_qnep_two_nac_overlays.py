"""Create separate no-NAC and +NAC DFT/qNEP phonon comparisons."""

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
    return distances.reshape(-1), frequencies.reshape(-1, frequencies.shape[-1])


def _metrics(reference: np.ndarray, candidate: np.ndarray) -> dict:
    delta = candidate - reference
    return {
        "mae_thz": float(np.abs(delta).mean()),
        "rmse_thz": float(np.sqrt(np.mean(delta**2))),
        "max_abs_thz": float(np.abs(delta).max()),
        "n_values": int(delta.size),
    }


def _plot(
    dft_result: dict,
    dft_key: str,
    qnep_result: dict,
    qnep_key: str,
    output_png: Path,
    output_pdf: Path,
    title: str,
    y_limits: tuple[float, float],
) -> dict:
    dft_x, dft_y = _flatten(dft_result, dft_key)
    qnep_x, qnep_y = _flatten(qnep_result, qnep_key)
    if not np.allclose(dft_x, qnep_x) or dft_y.shape != qnep_y.shape:
        raise ValueError(f"DFT and qNEP {dft_key} arrays do not share a q-path")

    labels = dft_result.get("labels", [r"$\\Gamma$", "X", "M", r"$\\Gamma$", "R", "X"])
    tick_positions = [0.0] + [float(np.asarray(segment)[-1]) for segment in dft_result[dft_key]["distances"]]
    fig, ax = plt.subplots(figsize=(6.6, 4.5), constrained_layout=True)
    for branch in range(dft_y.shape[-1]):
        ax.plot(dft_x, dft_y[:, branch], color="#4d555d", lw=0.9, alpha=0.85)
        ax.plot(qnep_x, qnep_y[:, branch], color="#c54c4c", lw=0.9, alpha=0.82)
    handles = [
        mpl.lines.Line2D([], [], color="#4d555d", lw=1.4, label="DFT/PBEsol"),
        mpl.lines.Line2D([], [], color="#c54c4c", lw=1.4, label="qNEP"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=False, ncol=2, handlelength=2.4)
    ax.set_xlabel("Wave vector")
    ax.set_ylabel("Frequency (THz)")
    ax.set_title(title, pad=8)
    ax.set_xticks(tick_positions, labels)
    ax.set_xlim(float(dft_x.min()), float(dft_x.max()))
    ax.set_ylim(*y_limits)
    ax.grid(axis="y", color="#d9dde2", lw=0.5, alpha=0.8)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=600, bbox_inches="tight")
    fig.savefig(output_pdf, bbox_inches="tight")
    plt.close(fig)
    return _metrics(dft_y, qnep_y)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dft", required=True)
    parser.add_argument("--qnep", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="cubic_BaTiO3_DFT_vs_qNEP")
    parser.add_argument("--combined", action="store_true", help="also write a side-by-side combined figure")
    args = parser.parse_args()

    dft = json.loads(Path(args.dft).read_text(encoding="utf-8"))
    qnep = json.loads(Path(args.qnep).read_text(encoding="utf-8"))
    all_values = np.concatenate(
        [
            np.asarray(dft["wo_nac"]["frequencies"], dtype=float).ravel(),
            np.asarray(dft["with_nac"]["frequencies"], dtype=float).ravel(),
            np.asarray(qnep["wo_nac"]["frequencies"], dtype=float).ravel(),
            np.asarray(qnep["with_nac"]["frequencies"], dtype=float).ravel(),
        ]
    )
    margin = max(0.5, 0.03 * (all_values.max() - all_values.min()))
    y_limits = (float(all_values.min() - margin), float(all_values.max() + margin))
    out = Path(args.output_dir).resolve()
    no_nac_png = out / f"{args.stem}_without_NAC.png"
    no_nac_pdf = out / f"{args.stem}_without_NAC.pdf"
    with_nac_png = out / f"{args.stem}_with_NAC.png"
    with_nac_pdf = out / f"{args.stem}_with_NAC.pdf"
    metrics = {
        "schema": "zstar-qnep-two-nac-overlays",
        "frequency_unit": dft.get("frequency_unit", "THz"),
        "qpath_labels": dft.get("labels"),
        "common_y_limits_thz": list(y_limits),
        "source": {"dft": str(Path(args.dft).resolve()), "qnep": str(Path(args.qnep).resolve())},
        "without_nac": _plot(
            dft,
            "wo_nac",
            qnep,
            "wo_nac",
            no_nac_png,
            no_nac_pdf,
            "Cubic BaTiO$_3$: DFT vs qNEP without NAC",
            y_limits,
        ),
        "with_nac": _plot(
            dft,
            "with_nac",
            qnep,
            "with_nac",
            with_nac_png,
            with_nac_pdf,
            "Cubic BaTiO$_3$: DFT vs qNEP with NAC",
            y_limits,
        ),
        "outputs": [str(no_nac_png), str(no_nac_pdf), str(with_nac_png), str(with_nac_pdf)],
    }
    if args.combined:
        # The standalone plots are the authoritative files; the combined
        # figure is a convenience for a two-panel manuscript layout.
        fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.5), sharey=True, constrained_layout=True)
        for ax, key, title in zip(
            axes,
            ("wo_nac", "with_nac"),
            ("without NAC", "with NAC"),
        ):
            d_x, d_y = _flatten(dft, key)
            q_x, q_y = _flatten(qnep, key)
            for branch in range(d_y.shape[-1]):
                ax.plot(d_x, d_y[:, branch], color="#4d555d", lw=0.8, alpha=0.85)
                ax.plot(q_x, q_y[:, branch], color="#c54c4c", lw=0.8, alpha=0.82)
            ax.set_title(title)
            ax.set_xticks(
                [0.0] + [float(np.asarray(segment)[-1]) for segment in dft[key]["distances"]],
                dft.get("labels"),
            )
            ax.set_xlim(float(d_x.min()), float(d_x.max()))
            ax.set_ylim(*y_limits)
            ax.grid(axis="y", color="#d9dde2", lw=0.5, alpha=0.8)
            ax.set_xlabel("Wave vector")
        axes[0].set_ylabel("Frequency (THz)")
        combined_handles = [
            mpl.lines.Line2D([], [], color="#4d555d", lw=1.4, label="DFT/PBEsol"),
            mpl.lines.Line2D([], [], color="#c54c4c", lw=1.4, label="qNEP"),
        ]
        axes[0].legend(handles=combined_handles, frameon=False, loc="upper left")
        combined_png = out / f"{args.stem}_NAC_split.png"
        combined_pdf = out / f"{args.stem}_NAC_split.pdf"
        fig.savefig(combined_png, dpi=600, bbox_inches="tight")
        fig.savefig(combined_pdf, bbox_inches="tight")
        plt.close(fig)
        metrics["outputs"].extend([str(combined_png), str(combined_pdf)])
    json_path = out / f"{args.stem}_NAC_split.json"
    json_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
