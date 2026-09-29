"""Four source-traceable figures for the Sb2S3 local-field technical note."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class Route:
    short: str
    full: str
    grid: np.ndarray
    zz: np.ndarray
    yz: np.ndarray
    color: str
    source: Path

    @property
    def ratio(self) -> float:
        return float(np.max(self.yz))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_modes(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    numbers = np.asarray([int(row["mode"]) for row in rows], dtype=int)
    frequencies = np.asarray([float(row["frequency_cm-1"]) for row in rows])
    tensors = np.asarray([
        [[float(row[f"R{first}{second}"]) for second in "xyz"]
         for first in "xyz"] for row in rows
    ])
    if len(numbers) != 26 or len(set(numbers)) != 26:
        raise ValueError(f"Expected 26 distinct Raman modes: {path}")
    if not np.all(np.isfinite(tensors)) or np.any(frequencies <= 0):
        raise ValueError(f"Invalid mode archive: {path}")
    return numbers, frequencies, tensors


def _stokes(
    numbers: np.ndarray, frequencies: np.ndarray, tensors: np.ndarray,
    component: str,
) -> tuple[np.ndarray, np.ndarray]:
    from zstar.spectra import (
        BOLTZMANN, PLANCK, SPEED_OF_LIGHT, calculate_native_line_spectrum,
    )

    first, second = ("xyz".index(axis) for axis in component)
    laser_cm1 = 1e7 / 532.0
    x = PLANCK * SPEED_OF_LIGHT * frequencies * 100.0 / (BOLTZMANN * 298.0)
    weights = (
        np.maximum(laser_cm1 - frequencies, 0) ** 4 / frequencies
        * (1.0 + 1.0 / np.expm1(x)) * tensors[:, first, second] ** 2
    )
    spectrum = calculate_native_line_spectrum(
        frequencies, weights, mode_numbers=numbers,
        activity_kind="polarized_Raman_intensity", activity_unit="relative",
        broadening_cm1=8.0, max_frequency_cm1=480.0, points=3001,
    )
    return spectrum.frequency_grid_cm1, spectrum.spectrum


def _calculated(
    source: Path, short: str, full: str, color: str,
    *, screened_csv: Path | None = None,
) -> Route:
    numbers, frequencies, tensors = _read_modes(source)
    if screened_csv is not None:
        from zstar.raman_local_field import load_bare_raman_csv
        new_numbers, tensors = load_bare_raman_csv(screened_csv, numbers.tolist())
        if not np.array_equal(numbers, new_numbers):
            raise ValueError("ABACUS screened tensor IDs differ from the mode source")
    grid, zz = _stokes(numbers, frequencies, tensors, "zz")
    other_grid, yz = _stokes(numbers, frequencies, tensors, "yz")
    np.testing.assert_allclose(grid, other_grid)
    scale = float(np.max(zz))
    if scale <= 0:
        raise ValueError(f"No axial Raman intensity: {source}")
    return Route(short, full, grid, zz / scale, yz / scale, color,
                 screened_csv if screened_csv is not None else source)


def _vasp_pair(path: Path) -> tuple[Route, Route]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = sorted(data["records"], key=lambda item: item["mode"])
    numbers = np.asarray([item["mode"] for item in records], dtype=int)
    frequencies = np.asarray([item["frequency_cm-1"] for item in records])
    routes = []
    for key, short, full, color in (
        ("independent_particle", "VASP, IPA", "ZStar (VASP) PBE+D3(BJ)\nno local-field response", "#936186"),
        ("self_consistent_dft", "VASP, DFT response", "ZStar (VASP) PBE+D3(BJ)\nself-consistent response", "#3575a2"),
    ):
        tensors = np.asarray([item[key] for item in records], dtype=float)
        grid, zz = _stokes(numbers, frequencies, tensors, "zz")
        other_grid, yz = _stokes(numbers, frequencies, tensors, "yz")
        np.testing.assert_allclose(grid, other_grid)
        scale = float(np.max(zz))
        if scale <= 0:
            raise ValueError(f"No VASP {key} axial intensity")
        routes.append(Route(short, full, grid, zz / scale, yz / scale, color, path))
    return routes[0], routes[1]


def _crystal(path: Path) -> Route:
    original = np.loadtxt(path)
    if original.shape[1] != 10 or len(original) < 400:
        raise ValueError("Expected original CRYSTAL RAMSPEC.DAT")
    # ZStar (x,y,z) = CRYSTAL (y,z,x): new zz=old xx; new yz=old xz.
    zz = original[:, 4]
    yz = original[:, 6]
    scale = float(np.max(zz))
    if scale <= 0:
        raise ValueError("No CRYSTAL axial intensity")
    return Route("CRYSTAL", "CRYSTAL B3LYP-D3(BJ)", original[:, 0],
                 zz / scale, yz / scale, "#707980", path)


def _save(fig: plt.Figure, path: Path) -> None:
    for extension in ("pdf", "svg", "png"):
        fig.savefig(path.with_suffix(f".{extension}"), dpi=320,
                    bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def _stack(
    routes: list[Route], path: Path, *, yz_gains: list[float] | None = None
) -> None:
    if not routes:
        raise ValueError("No Raman routes")
    rows = len(routes)
    gains = yz_gains if yz_gains is not None else [1.0] * rows
    if len(gains) != rows or any(gain <= 0 for gain in gains):
        raise ValueError("Provide one positive yz display gain per route")
    fig, axes = plt.subplots(
        1, 2, figsize=(8.4, 0.78 * rows + 0.9), sharey=True,
        gridspec_kw={"width_ratios": [1, 1]},
    )
    fig.subplots_adjust(left=0.292, right=0.986, bottom=0.085,
                        top=0.925, wspace=0.08)
    offsets = np.arange(rows - 1, -1, -1, dtype=float) * 1.15
    for column, ax in enumerate(axes):
        for route, offset, gain in zip(routes, offsets, gains):
            ax.hlines(offset, 0, 390, color="#d7dade", lw=0.55)
            signal = route.zz if column == 0 else route.yz * gain
            if 0.9 * float(np.max(signal)) > 1.04:
                raise ValueError(f"Stack would clip {route.short} in {path}")
            window = route.grid <= 390
            ax.plot(route.grid[window], offset + 0.9 * signal[window],
                    color=route.color, lw=1.2, clip_on=True)
            if column == 1 and yz_gains is not None:
                ax.text(8, offset + 0.81, rf"$\times${gain:g}",
                        color=route.color, fontsize=7.4, va="top")
        ax.set_xlim(0, 390)
        ax.set_ylim(-0.06, offsets[0] + 1.05)
        ax.set_xticks([0, 100, 200, 300])
        ax.set_xlabel(r"Raman shift (cm$^{-1}$)", labelpad=4)
        ax.set_yticks(offsets)
        ax.tick_params(axis="x", direction="in", top=True, labelsize=8)
        ax.tick_params(axis="y", length=0)
        for spine in ax.spines.values():
            spine.set_visible(True)
    axes[0].set_yticklabels([route.full for route in routes], fontsize=7.6,
                            linespacing=1.02)
    axes[1].tick_params(labelleft=False)
    axes[0].set_title("Axial $zz$", fontsize=10.2)
    yz_title = "Crossed $yz$" + (" (row gains shown)" if yz_gains is not None else "")
    axes[1].set_title(yz_title, fontsize=10.2)
    _save(fig, path)


def _overlay(routes: list[Route], path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(6.9, 4.6), sharex=True,
                             gridspec_kw={"height_ratios": [1, 0.76]})
    fig.subplots_adjust(left=0.105, right=0.982, bottom=0.105,
                        top=0.965, hspace=0.15)
    for route in routes:
        axes[0].plot(route.grid, route.zz, color=route.color, lw=1.35,
                     label=route.short)
        axes[1].plot(route.grid, route.yz, color=route.color, lw=1.35)
    for ax in axes:
        ax.set_xlim(0, 390)
        ax.set_ylim(bottom=0)
        ax.tick_params(direction="in", top=True, right=True, labelsize=8)
    axes[0].set_ylim(0, 1.08)
    axes[1].set_ylim(0, 0.032)
    axes[0].set_ylabel("Axial $zz$ / axial maximum", fontsize=8.3)
    axes[1].set_ylabel("Crossed $yz$ / axial maximum", fontsize=8.3)
    axes[1].set_xlabel(r"Raman shift (cm$^{-1}$)", fontsize=9)
    axes[0].legend(frameon=False, loc="upper right", fontsize=8, ncol=3)
    axes[0].text(0.015, 0.955, "(a)", transform=axes[0].transAxes,
                 va="top", fontsize=9)
    axes[1].text(0.015, 0.955, "(b)", transform=axes[1].transAxes,
                 va="top", fontsize=9)
    _save(fig, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "figures")
    args = parser.parse_args()
    repo = args.repo.resolve()
    sys.path.insert(0, str(repo))
    root = repo / "examples/IR_Raman_Spectra"
    original = root / "Nanowire_Sb2S3/results/Raman/raman_modes.csv"
    tzdp = root / "Nanowire_Sb2S3_TZDP_10au/results/relaxed/raman/raman_modes.csv"
    hse = root / "Nanowire_Sb2S3_HSE_TZDP_10au/results/response/raman/raman_modes.csv"
    screened = root / "Nanowire_Sb2S3/results/local_field_screened/raman_tensors.csv"
    vasp_pair = Path(__file__).parent / "source_data/sb2s3_vasp/ipa_dft_mode_tensors.json"
    ref = (root / "Nanowire_Sb2S3/results/reference/B3LYP-D3/gamma-point"
           / "sb2s3_fc_b3lyp-d3_freq.ramspec.dat")

    dzp = _calculated(original, "ZStar (ABACUS), DZP", "ZStar (ABACUS) PBE+D3(BJ)\nDZP, zero field", "#bd4d42")
    tzdp_route = _calculated(tzdp, "ZStar (ABACUS), TZDP", "ZStar (ABACUS) PBE+D3(BJ)\nTZDP, zero field", "#c18643")
    hse_route = _calculated(hse, "ZStar (ABACUS), HSE", "ZStar (ABACUS) HSE06+D3(BJ)\nTZDP, zero field", "#448979")
    ipa, dft = _vasp_pair(vasp_pair)
    crystal = _crystal(ref)
    corrected = _calculated(original, "ZStar (ABACUS), screened $x/y$", "ZStar (ABACUS) PBE+D3(BJ)\nscreened $x/y$", "#b73b33", screened_csv=screened)

    if not 0.39 < dzp.ratio < 0.41 or not 0.38 < tzdp_route.ratio < 0.41:
        raise ValueError("Original ABACUS peak ratios changed")
    if not 0.40 < ipa.ratio < 0.46 or not 0.006 < dft.ratio < 0.009:
        raise ValueError("VASP response selection no longer reproduces the audit")
    if not 0.005 < corrected.ratio < 0.008 or not 0.016 < crystal.ratio < 0.021:
        raise ValueError("Screened ABACUS or reference spectrum changed")

    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8.5,
        "pdf.fonttype": 42, "svg.fonttype": "none",
        "axes.linewidth": 0.8, "xtick.direction": "in",
        "ytick.direction": "in", "xtick.top": True, "ytick.right": True,
    })
    args.out.mkdir(parents=True, exist_ok=True)
    _stack([dzp, tzdp_route, hse_route, ipa, dft, crystal],
           args.out / "14_sb2s3_six_route_discrepancy")
    _stack([dzp, ipa, dft, crystal],
           args.out / "15_sb2s3_vasp_response_control")
    _stack([corrected, dzp, dft, crystal],
           args.out / "16_sb2s3_abacus_field_correction",
           yz_gains=[30.0, 1.0, 30.0, 30.0])
    _overlay([corrected, dft, crystal],
             args.out / "17_sb2s3_screened_directional_overlay")
    routes = [dzp, tzdp_route, hse_route, ipa, dft, corrected, crystal]
    audit = {
        "conditions": {"temperature_K": 298, "laser_nm": 532,
                       "broadening": "Lorentzian FWHM 8 cm^-1",
                       "response": "static nonresonant Placzek"},
        "normalization": "each route's own axial zz maximum, shared with yz; no peak shifts or per-channel fits",
        "figure_3_yz_display_gains": {
            corrected.short: 30, dzp.short: 1, dft.short: 30, crystal.short: 30,
        },
        "routes": [{"label": item.short, "yz_over_zz": item.ratio,
                    "source": str(item.source), "sha256": _sha(item.source)}
                   for item in routes],
        "crystal_total_available": "RAMSPEC.DAT column 2 is powder total; figures use mapped single-crystal directional columns 5 and 7",
        "axial_caveat": "ABACUS corrected route retains zero-field PYATB zz",
    }
    (args.out / "sb2s3_note_figure_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    for item in routes:
        print(f"{item.short:40s} {item.ratio:.6f}")


if __name__ == "__main__":
    main()
