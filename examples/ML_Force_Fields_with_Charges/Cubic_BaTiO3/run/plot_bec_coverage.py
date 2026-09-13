"""Plot the small BTO force-pool/BEC-subset coverage audit.

The public qNEP excerpt does not carry per-frame MD temperatures, so the plot
uses phase as the source-resolved axis and states the temperature limitation
explicitly rather than inventing temperature values.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


PHASE_COLORS = {
    "rhombohedral": "#4472c4",
    "orthorhombic": "#70ad47",
    "tetragonal": "#ed7d31",
    "cubic": "#a5a5a5",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.sort(key=lambda row: int(str(row["frame_id"])) if str(row["frame_id"]).isdigit() else str(row["frame_id"]))
    x = list(range(1, len(rows) + 1))
    phase = [row.get("phase_label") or "other" for row in rows]
    labelled = [bool(row.get("born_effective_charges_available")) for row in rows]
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(7.2, 3.9), sharex=True, gridspec_kw={"height_ratios": [1, 1.5]})
    for index, value in enumerate(phase):
        ax0.axvspan(index + 0.5, index + 1.5, color=PHASE_COLORS.get(value, "#cccccc"), alpha=0.85, linewidth=0)
    ax0.set_ylim(0, 1)
    ax0.set_yticks([])
    ax0.set_ylabel("phase")
    ax0.text(0.01, 0.78, "temperature metadata unavailable in public excerpt", transform=ax0.transAxes, fontsize=7)
    for value, color in PHASE_COLORS.items():
        if value in phase:
            ax0.plot([], [], color=color, linewidth=6, label=value)
    ax0.legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.32), frameon=False)
    ax1.scatter(x, [1 if item else 0 for item in labelled], s=23, c=["#c00000" if item else "white" for item in labelled], edgecolors="#333333", linewidths=0.6)
    ax1.set_yticks([0, 1], ["missing BEC", "BEC labelled"])
    ax1.set_xlabel("selected force-pool frame (source frame order)")
    ax1.set_xlim(0.5, len(rows) + 0.5)
    ax1.grid(axis="x", alpha=0.15)
    ax1.set_title(f"Sparse BEC coverage: {sum(labelled)}/{len(rows)} = {sum(labelled)/len(rows):.1%}", fontsize=9)
    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=220, bbox_inches="tight")
    fig.savefig(args.output.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
