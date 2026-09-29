"""Preview direction-resolved Figure 10 layouts from archived spectra."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


IR = "#c43d32"
RAMAN = "#2f6b9a"
REF = "#aeb4ba"
INK = "#24292d"


def read_csv_modes(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    numbers = np.array([int(row["mode"]) for row in rows])
    freqs = np.array([float(row["frequency_cm-1"]) for row in rows])
    tensors = np.array([
        [[float(row[f"R{a}{b}"]) for b in "xyz"] for a in "xyz"]
        for row in rows
    ])
    if len(numbers) != len(set(numbers)) or not np.all(np.isfinite(tensors)):
        raise ValueError(f"Invalid Raman tensors: {path}")
    return numbers, freqs, tensors


def raman_channels(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from zstar.spectra import (
        BOLTZMANN, PLANCK, SPEED_OF_LIGHT, calculate_native_line_spectrum,
    )

    numbers, freqs, tensors = read_csv_modes(path)
    laser = 1e7 / 532.0
    exponent = PLANCK * SPEED_OF_LIGHT * freqs * 100.0 / (BOLTZMANN * 298.0)
    factors = np.maximum(laser - freqs, 0) ** 4 * (
        1.0 + 1.0 / np.expm1(exponent)
    ) / freqs
    in_plane = np.sum(tensors[:, :2, :2] ** 2, axis=(1, 2))
    tilted = np.sum(tensors[:, :2, 2] ** 2, axis=1) + np.sum(
        tensors[:, 2, :2] ** 2, axis=1
    )
    outputs = []
    for weights in (in_plane, tilted):
        result = calculate_native_line_spectrum(
            freqs, factors * weights, mode_numbers=numbers,
            activity_kind="polarized_Raman_intensity", activity_unit="relative",
            broadening_cm1=8.0, max_frequency_cm1=500.0, points=3001,
        )
        outputs.append(result.spectrum)
        grid = result.frequency_grid_cm1
    scale = float(np.max(outputs[0]))
    if scale <= 0:
        raise ValueError("MoS2 in-plane Raman is zero")
    return grid, outputs[0] / scale, outputs[1] / scale


def norm(values: np.ndarray) -> np.ndarray:
    maximum = float(np.max(values))
    if maximum <= 0:
        raise ValueError("Cannot normalize a zero spectrum")
    return values / maximum


def style(ax: plt.Axes, xlim: tuple[float, float], ylim: tuple[float, float],
          *, xlabel: bool = True) -> None:
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.tick_params(direction="in", top=True, right=True, labelsize=7.4,
                   labelbottom=xlabel)
    ax.grid(axis="y", color="#e2e5e8", linewidth=0.45)
    if xlabel:
        ax.set_xlabel(r"Wavenumber (cm$^{-1}$)", fontsize=8)
    for spine in ax.spines.values():
        spine.set_linewidth(0.75)


def panel(ax: plt.Axes, label: str) -> None:
    ax.text(-0.19, 1.09, f"({label})", transform=ax.transAxes,
            fontsize=10, va="bottom", color=INK)


def curves(ax: plt.Axes, first: np.ndarray, second: np.ndarray | None,
           xlim: tuple[float, float], *, color: str, first_label: str,
           second_label: str | None, ylim: tuple[float, float] = (0, 1.12),
           show_legend: bool = True, xlabel: bool = True) -> None:
    ax.plot(first[:, 0], first[:, 1], color=color, lw=1.35,
            label=first_label, zorder=3)
    if second is not None:
        ax.plot(second[:, 0], second[:, 1], color=REF, lw=1.25,
                label=second_label, zorder=2)
    style(ax, xlim, ylim, xlabel=xlabel)
    if show_legend and second is not None:
        outside_legend(ax)


def outside_legend(ax: plt.Axes, *, handles=None, columns: int = 2,
                   fontsize: float = 7.1) -> None:
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.055),
              borderaxespad=0, frameon=False, fontsize=fontsize, ncol=columns,
              columnspacing=0.8, handlelength=1.5, handletextpad=0.35)


def spectrum_handles(color: str, calculation: str, reference: str,
                     *, reference_is_frequency: bool = False) -> list[Line2D]:
    return [
        Line2D([0], [0], color=color, lw=1.35, label=calculation),
        Line2D([0], [0], color=REF, lw=1.25,
               linestyle=(0, (3, 2)) if reference_is_frequency else "-",
               label=reference),
    ]


def marker(ax: plt.Axes, x: float) -> None:
    ax.axvline(x, ymin=0, ymax=1, color=REF, lw=1,
               linestyle=(0, (3, 2)), zorder=2)


def channel_label(ax: plt.Axes, label: str, *, small: bool = False) -> None:
    ax.text(0.025, 0.83 if not small else 0.78, label, transform=ax.transAxes,
            fontsize=7.5, va="center", color=INK,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85,
                  "pad": 1.2})


def annotate_mode(ax: plt.Axes, data: np.ndarray, frequency: float,
                  label: str, text_x: float, text_y: float) -> None:
    ax.annotate(
        label,
        xy=(frequency, float(np.interp(frequency, data[:, 0], data[:, 1]))),
        xycoords="data", xytext=(text_x, text_y),
        textcoords=("data", "axes fraction"),
        ha="center", va="center", fontsize=7.5, color=INK,
        arrowprops={"arrowstyle": "-", "lw": 0.5, "color": "#7d858c"},
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86,
              "pad": 0.5},
    )


def split_axes(fig: plt.Figure, cell) -> tuple[plt.Axes, plt.Axes]:
    sub = cell.subgridspec(2, 1, hspace=0.13)
    return fig.add_subplot(sub[0]), fig.add_subplot(sub[1])


def load(path: Path, column: int = -1) -> np.ndarray:
    data = np.loadtxt(path)
    return np.column_stack((data[:, 0], data[:, column]))


def normalized_pair(first: Path, second: Path, column: int = -1,
                    ref_column: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    a = load(first, column)
    b = load(second, ref_column if ref_column is not None else column)
    a[:, 1] = norm(a[:, 1])
    b[:, 1] = norm(b[:, 1])
    return a, b


def figure(repo: Path, out: Path, *, zoom_e_double_prime: bool) -> dict:
    paper = repo / "docs/paper_figures"
    data = paper / "source_data"
    sb_case = repo / "examples/IR_Raman_Spectra/Nanowire_Sb2S3/results"
    sb = sb_case / "reference/B3LYP-D3/gamma-point"
    sys.path.insert(0, str(paper))
    import plot_spectroscopy_across_dimensions as old
    import plot_sb2s3_screening_comparison as note

    old.configure_matplotlib()
    numbers = json.loads((paper / "reference_numbers.json").read_text(encoding="utf-8"))
    numbers = numbers.get("references", numbers)
    ref_sb = numbers.get("Ulian2026Sb2S3Data", 66)
    ref_mo = numbers.get("Ulian2023MoS2", 83)
    ref_ch = numbers.get("Shimanouchi1972", 84)
    if any(not isinstance(value, int) for value in (ref_sb, ref_mo, ref_ch)):
        raise ValueError("Reference numbers must be integers")

    fig = plt.figure(figsize=(9.15, 10.0))
    grid = fig.add_gridspec(4, 3, width_ratios=(1.02, 1.37, 1.37),
                           left=0.105, right=0.985, top=0.955, bottom=0.065,
                           hspace=0.38, wspace=0.32)
    structures = [
        ("HfO$_2$\n3D, bulk", data / "structure_images/HfO2_tetragonal.png",
         (0.20, 0.17, 0.79, 0.78), False, -15),
        ("MoS$_2$\n2D, slab", data / "structure_images/MoS2_monolayer.png",
         (0.17, 0.28, 0.82, 0.55), True, 0),
        ("Sb$_2$S$_3$\n1D, nanowire", data / "structure_images/Sb2S3.png",
         (0.2204, -0.0031, 0.7992, 0.8856), None, 0),
        ("CH$_4$\n0D, molecule", data / "structure_images/CH4_molecule.png",
         (0.18, 0.19, 0.82, 0.73), False, -15),
    ]
    files: list[Path] = []
    for row, (name, image, bounds, out_of_plane_a, angle) in enumerate(structures):
        ax = fig.add_subplot(grid[row, 0])
        old.draw_structure_image(ax, name, image, bounds)
        if out_of_plane_a is None:
            old.draw_sb2s3_axis_triad(ax)
        else:
            old.draw_axis_triad(ax, out_of_plane_a, angle,
                                a_length_scale=0.8 if row in (0, 3) else 1)
        panel(ax, "adgj"[row])
        files.append(image)

    # Bulk: retain the matched ABACUS and VASP comparison.
    h_ir_a = data / "hfo2/ir/ir_spectrum.dat"
    h_ir_v = data / "hfo2/vasp/ir_spectrum.dat"
    h_r_a = data / "hfo2/raman/raman_spectrum.dat"
    h_r_v = data / "hfo2/vasp/raman_spectrum.dat"
    for column, pair, color, xlim, letter in (
        (1, (h_ir_a, h_ir_v), IR, (0, 620), "b"),
        (2, (h_r_a, h_r_v), RAMAN, (0, 800), "c"),
    ):
        ax = fig.add_subplot(grid[0, column])
        a, b = normalized_pair(*pair)
        curves(ax, a, b, xlim, color=color, first_label="ZStar (ABACUS)",
               second_label="ZStar (VASP, DFPT)")
        ax.set_ylabel("IR intensity" if column == 1 else "Raman intensity",
                      fontsize=8, labelpad=1)
        labels = (
            ((96, r"$E_u$", 140, .77),
             (319, r"$A_{2u}$", 290, .78),
             (448, r"$E_u$", 405, .76))
            if column == 1 else
            ((120, r"$E_g$", 153, .43),
             (286, r"$A_{1g}$", 253, .76),
             (450, r"$E_g$", 420, .41),
             (616, r"$B_{1g}$", 588, .35),
             (700, r"$E_g$", 670, .58))
        )
        for frequency, label, text_x, text_y in labels:
            annotate_mode(ax, a, frequency, label, text_x, text_y)
        panel(ax, letter)
        files.extend(pair)

    # 2D IR: use one in-plane normalization for both optical channels.
    m_ir = data / "mos2/vasp/ir_spectrum.dat"
    m = np.loadtxt(m_ir)
    in_plane = m[:, 1] + m[:, 2]
    out_plane = m[:, 3]
    ir_ratio = float(np.max(out_plane) / np.max(in_plane))
    ir_upper, ir_lower = split_axes(fig, grid[1, 1])
    for ax, intensity, position, label, letter in (
        (ir_upper, in_plane, 381.8, "in-plane  $E'$", "e"),
        (ir_lower, out_plane, 467.7, r"out-of-plane  $A_2''$", None),
    ):
        ax.plot(m[:, 0], intensity / np.max(in_plane), color=IR,
                lw=1.35, zorder=3)
        marker(ax, position)
        style(ax, (320, 520), (0, 1.12) if ax is ir_upper else (0, 0.04),
              xlabel=ax is ir_lower)
        channel_label(ax, label)
        if letter:
            panel(ax, letter)
    outside_legend(ir_upper, handles=spectrum_handles(
        IR, "ZStar (VASP, DFPT)", f"Ref. [{ref_mo}]",
        reference_is_frequency=True))
    ir_upper.set_ylabel("IR intensity", fontsize=8, labelpad=1)
    ir_lower.set_ylabel("IR intensity", fontsize=8, labelpad=1)
    ir_lower.text(0.025, 0.62, rf"$I_z^{{\max}}/I_{{xy}}^{{\max}}={ir_ratio:.4f}$",
                  transform=ir_lower.transAxes, fontsize=7.1)
    files.append(m_ir)

    # 2D Raman: normal in-plane optical geometry versus tilted xz/yz geometry.
    m_r = data / "mos2/vasp/raman_modes.csv"
    freq, normal, tilted = raman_channels(m_r)
    raman_ratio = float(np.max(tilted))
    r_upper, r_lower = split_axes(fig, grid[1, 2])
    main_xlim = (320, 470) if zoom_e_double_prime else (260, 470)
    weak_xlim = (265, 302) if zoom_e_double_prime else (260, 470)
    r_upper.plot(freq, normal, color=RAMAN, lw=1.35, zorder=3)
    for location in (381.8, 402.3):
        marker(r_upper, location)
    style(r_upper, main_xlim, (0, 1.12), xlabel=zoom_e_double_prime)
    channel_label(r_upper, r"in-plane optics  $E',A_1'$", small=True)
    panel(r_upper, "f")
    outside_legend(r_upper, handles=spectrum_handles(
        RAMAN, "ZStar (VASP, DFPT)", f"Ref. [{ref_mo}]",
        reference_is_frequency=True))
    r_upper.set_ylabel("Raman intensity", fontsize=8, labelpad=1)
    r_lower.plot(freq, tilted, color=RAMAN, lw=1.35, zorder=3)
    marker(r_lower, 281.9)
    style(r_lower, weak_xlim, (0, 0.003), xlabel=True)
    r_lower.set_ylabel("Raman intensity", fontsize=8, labelpad=1)
    channel_label(r_lower, r"tilted optics  $E''$", small=True)
    r_lower.text(0.98, 0.8, rf"peak ratio $={raman_ratio:.2g}$",
                 ha="right", transform=r_lower.transAxes, fontsize=7.1)
    files.append(m_r)

    # 1D IR uses the same ABACUS case as the finite-field Raman tensors.
    s_ir = sb_case / "IR/ir_spectrum.dat"
    s_ir_ref = sb / "sb2s3_fc_b3lyp-d3_freq.irspec.dat"
    s_ira, s_irb = normalized_pair(s_ir, s_ir_ref, -1, 2)
    ax = fig.add_subplot(grid[2, 1])
    curves(ax, s_ira, s_irb, (0, 390), color=IR,
           first_label="ZStar (ABACUS)", second_label=f"Ref. [{ref_sb}]")
    ax.set_ylabel("IR intensity", fontsize=8, labelpad=1)
    for frequency, label, text_x, text_y in (
        (127, r"$A_u$", 105, .77),
        (238, r"$A_u$", 220, .61),
        (296, r"$B_u$", 313, .36),
    ):
        annotate_mode(ax, s_ira, frequency, label, text_x, text_y)
    panel(ax, "h")
    files.extend((s_ir, s_ir_ref))

    # 1D Raman: transverse finite-field response with the archived axial response.
    bare = sb_case / "Raman/raman_modes.csv"
    corrected = sb_case / "local_field_screened/raman_tensors.csv"
    abacus = note._calculated(
        bare, "ABACUS", "ZStar (ABACUS)", RAMAN, screened_csv=corrected,
    )
    s_ref = sb / "sb2s3_fc_b3lyp-d3_freq.ramspec.dat"
    crystal = note._crystal(s_ref)
    ax_z, ax_yz = split_axes(fig, grid[2, 2])
    curves(ax_z, np.column_stack((abacus.grid, abacus.zz)),
           np.column_stack((crystal.grid, crystal.zz)), (0, 390),
           color=RAMAN, first_label="ZStar (ABACUS)",
           second_label=f"Ref. [{ref_sb}]", xlabel=False)
    channel_label(ax_z, "axial  $zz$")
    ax_z.set_ylabel("Raman intensity", fontsize=8, labelpad=1)
    for frequency, label, text_x, text_y in (
        (45, r"$A_g$", 81, .61),
        (194, r"$B_g$", 219, .52),
        (327, r"$A_g$", 318, .65),
    ):
        annotate_mode(ax_z, np.column_stack((abacus.grid, abacus.zz)),
                      frequency, label, text_x, text_y)
    panel(ax_z, "i")
    curves(ax_yz, np.column_stack((abacus.grid, abacus.yz)),
           np.column_stack((crystal.grid, crystal.yz)), (0, 390),
           color=RAMAN, first_label="ZStar (ABACUS)",
           second_label=f"Ref. [{ref_sb}]", ylim=(0, 0.12),
           show_legend=False)
    channel_label(ax_yz, "crossed  $yz$", small=True)
    ax_yz.set_ylabel("Raman intensity", fontsize=8, labelpad=1)
    files.extend((bare, corrected, s_ref))

    # Molecular spectra: literature records contain frequencies, not intensities.
    c_ir = data / "molecular/ch4/ir_spectrum.dat"
    c_r = data / "molecular/ch4/raman_spectrum.dat"
    for column, source, color, xlim, refs, letter in (
        (1, c_ir, IR, (1050, 3250), (1306, 3019), "k"),
        (2, c_r, RAMAN, (1320, 3500), (1534, 2917, 3019), "l"),
    ):
        ax = fig.add_subplot(grid[3, column])
        d = load(source)
        ax.plot(d[:, 0], norm(d[:, 1]), color=color, lw=1.35,
                label="ZStar (ABACUS)")
        for location in refs:
            marker(ax, location)
        style(ax, xlim, (0, 1.12))
        ax.set_ylabel("IR intensity" if column == 1 else "Raman intensity",
                      fontsize=8, labelpad=1)
        outside_legend(ax, handles=spectrum_handles(
            color, "ZStar (ABACUS)", f"Ref. [{ref_ch}]",
            reference_is_frequency=True))
        labels = (
            ((r"$\nu_4(F_2)$", 1510, .76),
             (r"$\nu_3(F_2)$", 2810, .80))
            if column == 1 else
            ((r"$\nu_2(E)$", 1740, .43),
             (r"$\nu_1(A_1)$", 2780, .83),
             (r"$\nu_3(F_2)$", 3280, .66))
        )
        for label, text_x, text_y in labels:
            ax.text(text_x, text_y, label, transform=ax.get_xaxis_transform(),
                    ha="center", va="center", fontsize=7.7, color=INK,
                    bbox={"facecolor": "white", "edgecolor": "none",
                          "alpha": 0.88, "pad": 0.5})
        panel(ax, letter)
        files.append(source)

    for row in range(4):
        for col in (1, 2):
            for ax in fig.axes:
                if ax.get_subplotspec().get_topmost_subplotspec() == grid[row, col]:
                    ax.tick_params(axis="both", labelsize=7.4)
    title = "directional_focus" if zoom_e_double_prime else "Spectroscopy_four_dimensions"
    out.mkdir(parents=True, exist_ok=True)
    products = {}
    for suffix in ("pdf", "svg", "png"):
        path = out / f"Figure_10_{title}.{suffix}"
        fig.savefig(path, dpi=320, bbox_inches="tight", pad_inches=0.08)
        products[suffix] = path.name
    plt.close(fig)
    return {
        "name": title,
        "products": products,
        "mos2_ir_z_to_xy_peak_ratio": ir_ratio,
        "mos2_raman_tilted_to_inplane_peak_ratio": raman_ratio,
        "sb2s3_screened_abacus_yz_to_zz_peak_ratio": abacus.ratio,
        "sb2s3_crystal_yz_to_zz_peak_ratio": crystal.ratio,
        "normalization": {
            "MoS2_IR": "Both channels share in-plane peak normalization",
            "MoS2_Raman": "Both channels share in-plane peak normalization",
            "Sb2S3_Raman": "Each route uses its own axial peak; axial and crossed share that scale",
            "other_panels": "Each spectrum independently normalized; no cross-material intensity claim",
        },
        "source_files": {
            path.resolve().relative_to(repo.resolve()).as_posix():
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(files))
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "figures")
    args = parser.parse_args()
    results = [
        figure(args.repo, args.out, zoom_e_double_prime=False),
        figure(args.repo, args.out, zoom_e_double_prime=True),
    ]
    audit = args.out / "Figure_10_directional_candidates_audit.json"
    audit.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    for result in results:
        print(result["products"]["pdf"])
        print("MoS2 ratios:", result["mos2_ir_z_to_xy_peak_ratio"],
              result["mos2_raman_tilted_to_inplane_peak_ratio"])


if __name__ == "__main__":
    main()
