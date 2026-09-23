"""Insulating-state diagnostics shared by response workflows."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import numpy as np


def parse_abacus_occupation_gap(
    path: str | Path,
    *,
    occupation_tolerance: float = 1.0e-10,
    insulating_threshold_eV: float = 1.0e-2,
) -> dict[str, Any] | None:
    """Extract a full-SCF-mesh occupation gap from ABACUS ``istate.info``.

    ABACUS writes occupations multiplied by k-point weights.  The parser
    therefore determines the fully occupied value independently at every
    printed k point and classifies occupations relative to that value.  Small
    numerical tails are treated as empty; intermediate occupations are
    reported as fractional.  An insulating record requires a positive global
    gap, a constant number of occupied bands, and no fractionally occupied
    state.
    """

    if not np.isfinite(occupation_tolerance) or occupation_tolerance < 0.0:
        raise ValueError("occupation_tolerance must be finite and non-negative")
    if not np.isfinite(insulating_threshold_eV) or insulating_threshold_eV < 0.0:
        raise ValueError("insulating_threshold_eV must be finite and non-negative")

    source = Path(path)
    if not source.is_file():
        return None

    header = re.compile(r"Kpoint\s*=\s*(\d+)", re.IGNORECASE)
    row = re.compile(
        r"^\s*(\d+)\s+"
        r"([-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?)\s+"
        r"([-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?)\s*$"
    )
    states: dict[int, list[tuple[int, float, float]]] = {}
    kpoint = 1
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        match = header.search(line)
        if match is not None:
            kpoint = int(match.group(1))
            states.setdefault(kpoint, [])
            continue
        match = row.match(line)
        if match is None:
            continue
        band = int(match.group(1))
        energy = float(match.group(2))
        occupation = float(match.group(3))
        if not np.isfinite(energy) or not np.isfinite(occupation):
            raise ValueError(f"ABACUS istate.info has non-finite values: {source}")
        states.setdefault(kpoint, []).append((band, energy, occupation))

    if not states or any(not rows for rows in states.values()):
        return None

    occupied_energies: list[float] = []
    empty_energies: list[float] = []
    occupied_counts: dict[int, int] = {}
    fractional_states: list[dict[str, float | int]] = []
    for point, rows in sorted(states.items()):
        positive = [occupation for _band, _energy, occupation in rows
                    if occupation > occupation_tolerance]
        if not positive:
            return None
        full_occupation = max(positive)
        classification_tolerance = max(
            occupation_tolerance,
            abs(full_occupation) * 1.0e-6,
        )
        occupied_count = 0
        for band, energy, occupation in rows:
            if occupation >= full_occupation - classification_tolerance:
                occupied_count += 1
                occupied_energies.append(energy)
            elif abs(occupation) <= classification_tolerance:
                empty_energies.append(energy)
            else:
                fractional_states.append(
                    {
                        "kpoint": point,
                        "band": band,
                        "occupation": occupation,
                        "full_occupation": full_occupation,
                    }
                )
        occupied_counts[point] = occupied_count

    if not occupied_energies or not empty_energies:
        return None

    unique_counts = sorted(set(occupied_counts.values()))
    count_consistent = len(unique_counts) == 1
    vbm = float(max(occupied_energies))
    cbm = float(min(empty_energies))
    raw_gap = cbm - vbm
    gap = max(raw_gap, 0.0)
    insulating = (
        gap >= insulating_threshold_eV
        and count_consistent
        and not fractional_states
    )
    return {
        "gap_eV": gap,
        "vbm_eV": vbm,
        "cbm_eV": cbm,
        "raw_gap_eV": raw_gap,
        "insulating": bool(insulating),
        "threshold_eV": float(insulating_threshold_eV),
        "occupation_tolerance": float(occupation_tolerance),
        "kpoint_count": len(states),
        "occupied_band_count": unique_counts[0] if count_consistent else None,
        "occupied_band_counts": occupied_counts,
        "occupied_band_count_consistent": count_consistent,
        "fractional_occupation_count": len(fractional_states),
        "fractional_occupations": fractional_states,
        "source": str(source.resolve()),
    }
