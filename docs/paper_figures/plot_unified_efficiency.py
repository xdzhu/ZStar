"""Plot measured Separate/Unified workflow costs from manuscript Tables 14 and 15."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter
import numpy as np


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source_data" / "unified_efficiency_benchmarks.csv"

COLORS = {
    "separate": "#AEB5B8",
    "separate_edge": "#697176",
    "unified": "#377D73",
    "connector": "#C9CECF",
    "grid": "#E7EAEB",
    "text": "#303538",
}

LABELS = {
    "c-BaTiO3": r"c-BaTiO$_3$",
    "3C-SiC": "SiC",
    "t-HfO2": r"t-HfO$_2$",
    "alpha-In2Se3": r"$\alpha$-In$_2$Se$_3$",
    "hBN": "hBN",
    "MoS2": r"MoS$_2$",
    "BN(9,0)": "BN(9,0)",
    "Sb2S3": r"Sb$_2$S$_3$",
    "H2O": r"H$_2$O",
    "CH4": r"CH$_4$",
}


def _read_rows() -> list[dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        separate = float(row["separate_core_hours"])
        unified = float(row["unified_core_hours"])
        reported = float(row["reported_speedup"])
        if separate <= unified:
            raise ValueError(f"Expected a positive speedup for {row['system']}")
        if abs(separate / unified - reported) > 0.03:
            raise ValueError(f"Reported speedup is inconsistent for {row['system']}")
    return rows


def _format_log_tick(value: float, _position: int) -> str:
    if value < 1:
        return f"{value:.1f}"
    return f"{value:g}"


def _style_axis(axis: plt.Axes, ticks: list[float], limits: tuple[float, float]) -> None:
    axis.set_xscale("log")
    axis.set_xlim(*limits)
    axis.xaxis.set_major_locator(FixedLocator(ticks))
    axis.xaxis.set_major_formatter(FuncFormatter(_format_log_tick))
    axis.xaxis.set_minor_locator(FixedLocator([]))
    axis.grid(axis="x", color=COLORS["grid"], linewidth=0.7, zorder=0)
    for spine in axis.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
    axis.tick_params(
        axis="both",
        which="both",
        direction="in",
        top=True,
        right=True,
        length=4.0,
        width=0.8,
        colors=COLORS["text"],
    )
    axis.set_xlabel("Measured solver cost (CPU core-hours, log scale)")


def _draw_panel(
    axis: plt.Axes,
    rows: list[dict[str, str]],
    *,
    title: str,
    ticks: list[float],
    limits: tuple[float, float],
) -> None:
    positions = np.arange(len(rows), dtype=float)
    separate = np.asarray([float(row["separate_core_hours"]) for row in rows])
    unified = np.asarray([float(row["unified_core_hours"]) for row in rows])
    speedups = np.asarray([float(row["reported_speedup"]) for row in rows])

    for y_value, old_cost, new_cost, speedup in zip(
        positions, separate, unified, speedups
    ):
        axis.annotate(
            "",
            xy=(new_cost, y_value),
            xytext=(old_cost, y_value),
            arrowprops={
                "arrowstyle": "-|>",
                "color": COLORS["connector"],
                "linewidth": 1.35,
                "mutation_scale": 9,
                "shrinkA": 7,
                "shrinkB": 7,
            },
            zorder=1,
        )
        midpoint = float(np.sqrt(old_cost * new_cost))
        axis.text(
            midpoint,
            y_value - 0.20,
            rf"${speedup:.2f}\times$",
            ha="center",
            va="bottom",
            color=COLORS["unified"],
            fontsize=8.3,
            fontweight="semibold",
            zorder=4,
        )

    axis.scatter(
        separate,
        positions,
        s=48,
        color=COLORS["separate"],
        edgecolor=COLORS["separate_edge"],
        linewidth=0.8,
        zorder=3,
    )
    axis.scatter(
        unified,
        positions,
        s=52,
        color=COLORS["unified"],
        edgecolor="white",
        linewidth=0.7,
        zorder=3,
    )
    axis.set_yticks(positions, [LABELS[row["system"]] for row in rows])
    axis.invert_yaxis()
    axis.set_ylim(len(rows) - 0.45, -0.65)
    axis.set_title(title, loc="left", fontsize=11.5, fontweight="normal", pad=8)
    _style_axis(axis, ticks, limits)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_svg(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def _update_manifest(exports: dict[str, Path], metadata_path: Path) -> None:
    manifest_path = ROOT / "figure_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = {
        "figure": "unified_efficiency_benchmarks",
        "files": {
            **{kind: path.name for kind, path in exports.items()},
            "metadata": metadata_path.name,
        },
        "source_data": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "layout": "two stacked paired-cost panels for BEC/phonons and IR/Raman",
        "placeholder": False,
    }
    manifest["figures"] = [
        item
        for item in manifest.get("figures", [])
        if item.get("figure") != record["figure"]
    ] + [record]

    source_rel = str(SOURCE.relative_to(ROOT / "source_data")).replace("\\", "/")
    sources = {item["path"]: item for item in manifest.get("source_data", [])}
    sources[source_rel] = {
        "path": source_rel,
        "size": SOURCE.stat().st_size,
        "sha256": _sha256(SOURCE),
    }
    manifest["source_data"] = [sources[key] for key in sorted(sources)]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def build_figure() -> None:
    rows = _read_rows()
    bec_rows = [row for row in rows if row["benchmark"] == "BEC/APT + Gamma phonons"]
    spectra_rows = [row for row in rows if row["benchmark"] == "IR + Raman"]

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 9.5,
            "axes.linewidth": 0.8,
            "axes.spines.right": True,
            "axes.spines.top": True,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.top": True,
            "ytick.right": True,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(8.0, 7.0),
        gridspec_kw={"height_ratios": [2.35, 1.0]},
    )
    _draw_panel(
        axes[0],
        bec_rows,
        title=r"(a) BEC/APT + $\Gamma$-point phonons",
        ticks=[0.5, 1, 2, 5, 10, 20, 50, 100, 200],
        limits=(0.45, 340),
    )
    _draw_panel(
        axes[1],
        spectra_rows,
        title="(b) IR + Raman",
        ticks=[2, 5, 10, 20, 50, 100],
        limits=(2.5, 110),
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor=COLORS["separate"],
            markeredgecolor=COLORS["separate_edge"],
            markersize=7,
            label="Separate",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor=COLORS["unified"],
            markeredgecolor="white",
            markersize=7,
            label="Unified",
        ),
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.80, 0.995),
        ncol=2,
        handletextpad=0.5,
        columnspacing=1.8,
        fontsize=9.5,
    )
    fig.subplots_adjust(left=0.18, right=0.985, top=0.945, bottom=0.085, hspace=0.42)

    stem = ROOT / "unified_efficiency_benchmarks"
    exports = {
        "pdf": stem.with_suffix(".pdf"),
        "svg": stem.with_suffix(".svg"),
        "png": stem.with_suffix(".png"),
        "tiff": stem.with_suffix(".tiff"),
    }
    fig.savefig(exports["pdf"], bbox_inches="tight")
    fig.savefig(exports["svg"], bbox_inches="tight")
    _normalize_svg(exports["svg"])
    fig.savefig(exports["png"], dpi=350, bbox_inches="tight")
    fig.savefig(
        exports["tiff"],
        dpi=600,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)

    metadata = {
        "schema": 1,
        "backend": "Python/matplotlib",
        "figure_contract": {
            "conclusion": "The Unified workflow lowers measured solver cost across dimensionalities for both BEC/phonon and combined IR/Raman calculations.",
            "archetype": "quantitative comparison",
            "cost_definition": "successful ABACUS and PYATB solver wall time multiplied by allocated CPU cores",
            "excluded_costs": [
                "geometry relaxation",
                "workflow preparation",
                "failed attempts",
                "additional validation runs",
            ],
        },
        "source": "manuscript Tables 14 and 15",
        "source_data": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": _sha256(SOURCE),
        "exports": {kind: path.name for kind, path in exports.items()},
    }
    metadata_path = ROOT / "unified_efficiency_benchmarks.metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    _update_manifest(exports, metadata_path)


if __name__ == "__main__":
    build_figure()
