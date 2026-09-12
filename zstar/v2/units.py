"""Small, explicit unit conversions used by the ZStar v2 response layer."""

from __future__ import annotations

from typing import Any

import numpy as np


ELEMENTARY_CHARGE = 1.602176634e-19  # C, exact SI definition
BOHR_RADIUS = 5.29177210903e-11  # m, CODATA 2018 value used by the draft API
EPSILON_0 = 8.8541878128e-12  # F m^-1, CODATA value used by the draft API
ELECTRONVOLT = 1.602176634e-19  # J, exact SI definition


class UnitConversionError(ValueError):
    """Raised when a conversion is ambiguous or not part of the draft table."""


def _canonical(unit: str) -> str:
    value = "".join(str(unit).strip().lower().split())
    aliases = {
        "å": "angstrom",
        "a": "angstrom",
        "angstrom": "angstrom",
        "angstroms": "angstrom",
        "meter": "m",
        "meters": "m",
        "metre": "m",
        "metres": "m",
        "m": "m",
        "ev/a": "ev_per_angstrom",
        "ev/å": "ev_per_angstrom",
        "ev/angstrom": "ev_per_angstrom",
        "ev/å^3": "ev_per_angstrom3",
        "ev/å3": "ev_per_angstrom3",
        "ev/a^3": "ev_per_angstrom3",
        "ev/a3": "ev_per_angstrom3",
        "ev/angstrom^3": "ev_per_angstrom3",
        "ev/angstrom3": "ev_per_angstrom3",
        "ev/m^3": "ev_per_m3",
        "ev/m3": "ev_per_m3",
        "j/å^3": "j_per_angstrom3",
        "j/å3": "j_per_angstrom3",
        "j/a^3": "j_per_angstrom3",
        "j/a3": "j_per_angstrom3",
        "j/angstrom^3": "j_per_angstrom3",
        "j/angstrom3": "j_per_angstrom3",
        "j/m^3": "j_per_m3",
        "j/m3": "j_per_m3",
        "electronvolt": "ev",
        "electronvolts": "ev",
        "joule": "j",
        "joules": "j",
        "ev": "ev",
        "j": "j",
        "n": "n",
        "gpa": "gpa",
        "kbar": "kbar",
        "pa": "pa",
        "eå": "e_angstrom",
        "ea": "e_angstrom",
        "e*angstrom": "e_angstrom",
        "c*m": "c_m",
        "c·m": "c_m",
        "coulomb*meter": "c_m",
        "1": "dimensionless",
        "relative": "relative",
        "epsilon_r": "relative",
        "εr": "relative",
        "f/m": "f_per_m",
        "f*m^-1": "f_per_m",
        "fm^-1": "f_per_m",
    }
    return aliases.get(value, value)


_FACTORS = {
    "angstrom": (1.0e-10, "length"),
    "m": (1.0, "length"),
    "e_angstrom": (ELEMENTARY_CHARGE * 1.0e-10, "dipole"),
    "c_m": (1.0, "dipole"),
    "ev_per_angstrom": (ELEMENTARY_CHARGE / 1.0e-10, "force"),
    "ev": (ELECTRONVOLT, "energy"),
    "j": (1.0, "energy"),
    # Energy density is dimensionally pressure; retaining it in this table
    # makes the eV/Angstrom^3 -> Pa/GPa conversion explicit and auditable.
    "ev_per_angstrom3": (ELECTRONVOLT / 1.0e-30, "pressure"),
    "ev_per_m3": (ELECTRONVOLT, "pressure"),
    "j_per_angstrom3": (1.0 / 1.0e-30, "pressure"),
    "j_per_m3": (1.0, "pressure"),
    "n": (1.0, "force"),
    "gpa": (1.0e9, "pressure"),
    "kbar": (1.0e8, "pressure"),
    "pa": (1.0, "pressure"),
    "dimensionless": (1.0, "dimensionless"),
}


def convert_values(values: Any, from_unit: str, to_unit: str) -> np.ndarray:
    """Convert compatible length/dipole/force/energy/pressure values.

    Energy density aliases such as ``eV/Angstrom^3`` are treated as pressure
    for conversion to Pa/GPa/kbar. Relative dielectric constants are
    intentionally excluded; use :func:`convert_dielectric` so that a
    dimensionless number is not silently
    interpreted as a dielectric tensor in another context.
    """

    source = _canonical(from_unit)
    target = _canonical(to_unit)
    if source == target:
        return np.asarray(values, dtype=float).copy()
    if source not in _FACTORS or target not in _FACTORS:
        raise UnitConversionError(f"unsupported conversion {from_unit!r} -> {to_unit!r}")
    source_factor, source_kind = _FACTORS[source]
    target_factor, target_kind = _FACTORS[target]
    if source_kind != target_kind:
        raise UnitConversionError(
            f"incompatible units {from_unit!r} ({source_kind}) and {to_unit!r} ({target_kind})"
        )
    return np.asarray(values, dtype=float) * source_factor / target_factor


def convert_dielectric(values: Any, from_unit: str, to_unit: str) -> np.ndarray:
    """Convert relative dielectric constants to/from absolute SI units."""

    source = _canonical(from_unit)
    target = _canonical(to_unit)
    array = np.asarray(values, dtype=float)
    if source == target:
        return array.copy()
    if source == "relative" and target == "f_per_m":
        return array * EPSILON_0
    if source == "f_per_m" and target == "relative":
        return array / EPSILON_0
    raise UnitConversionError(f"unsupported dielectric conversion {from_unit!r} -> {to_unit!r}")
