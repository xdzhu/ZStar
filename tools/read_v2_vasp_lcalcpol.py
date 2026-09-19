"""Research-only 3D LCALCPOL dipole intake; not a convergence/acceptance gate.

Old ``electrons Angst`` uses negative electron charge (VASP LCALCPOL wiki).
The explicitly positive ``|e| Angst`` label uses positive elementary charge.
Never infer a sign from agreement with a reference piezoelectric tensor.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

from zstar.v2.units import ELEMENTARY_CHARGE, convert_values

_DIPOLE = re.compile(
    r"^\s*(?:Ionic dipole moment:\s*p\[ion\]|"
    r"Total electronic dipole moment:\s*p\[elc\])\s*=\s*"
    r"\(\s*([^()]*)\)\s*(electrons Angst|\|e\| Angst)\s*$"
)


def read_lcalcpol(text: str, *, lattice_rows_A, periodic_axes=(True, True, True),
                 source: str = "") -> dict:
    """Read the last complete ionic/electronic pair, retaining its raw units.

Lattice rows are Cartesian Angstrom vectors of the SAME static calculation.
Reject incomplete/malformed final records rather than reusing an older pair.
Full 3D quantum vectors are columns, matching existing v2 branch APIs. No
branch choice, proper-piezo correction, or spontaneous polarization is made.
The caller separately validates convergence, insulator status and geometry.
"""
    if len(text) > 100_000_000:
        raise ValueError("OUTCAR exceeds bounded research intake")
    if tuple(periodic_axes) != (True, True, True):
        raise ValueError("This reader supports 3D bulk only; slab/molecular normalization is undefined here")
    cell = np.asarray(lattice_rows_A, dtype=float)
    if cell.shape != (3, 3) or not np.isfinite(cell).all():
        raise ValueError("lattice_rows_A must be finite Cartesian 3x3 Angstrom rows")
    volume_A3 = float(np.linalg.det(cell))
    if volume_A3 <= 0 or np.linalg.cond(cell) > 1e12:
        raise ValueError("Require a nondegenerate right-handed 3D lattice")
    pending, last, count = None, None, 0
    for number, line in enumerate(text.splitlines(), 1):
        if not any(key in line for key in ("p[ion]", "p[elc]")):
            continue
        match = _DIPOLE.fullmatch(line)
        if match is None:
            raise ValueError(f"Malformed dipole record or unsupported unit at line {number}")
        tokens = match[1].split()
        try:
            value = np.asarray([float(token.replace('D', 'E').replace('d', 'e'))
                                for token in tokens])
        except ValueError as error:
            raise ValueError(f"Invalid dipole numbers at line {number}") from error
        if value.shape != (3,) or not np.isfinite(value).all():
            raise ValueError(f"Dipole must have three finite Cartesian components at line {number}")
        raw = {'value': value.tolist(), 'unit': match[2], 'tokens': tokens,
               'line_one_based': number, 'coordinate_system': 'Cartesian'}
        if "p[ion]" in line:
            if pending is not None:
                raise ValueError("Unpaired ionic dipole; refusing to mix records")
            pending = raw
        else:
            if pending is None or pending['unit'] != raw['unit']:
                raise ValueError("Electronic dipole lacks matching ionic record/unit")
            last = (pending, raw)
            pending = None
            count += 1
    if pending is not None or last is None:
        raise ValueError("Missing or truncated final ionic/electronic dipole pair")
    ionic, electronic = last
    charge_sign = -1 if ionic['unit'] == 'electrons Angst' else 1
    total_raw = np.asarray(ionic['value']) + np.asarray(electronic['value'])
    dipole_C_m = charge_sign * convert_values(total_raw, 'e_angstrom', 'C*m')
    volume_m3 = volume_A3 * float(convert_values(1., 'angstrom', 'm')) ** 3
    quantum = ELEMENTARY_CHARGE * convert_values(cell.T, 'angstrom', 'm') / volume_m3
    return {
        'schema': 'zstar-v2-research-LCALCPOL-dipole/1', 'source': source,
        'source_text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        'raw_ionic_dipole': ionic, 'raw_electronic_dipole': electronic,
        'complete_pair_count': count, 'charge_sign_relative_to_positive_e': charge_sign,
        'dipole': {'value': dipole_C_m.tolist(), 'unit': 'C*m', 'coordinate_system': 'Cartesian'},
        'polarization': {'value': (dipole_C_m / volume_m3).tolist(), 'unit': 'C/m^2',
                         'coordinate_system': 'Cartesian', 'branch_matched': False},
        'polarization_quantum': {'value': quantum.tolist(), 'unit': 'C/m^2',
                                'vectors_stored_as': 'columns', 'coordinate_system': 'Cartesian'},
        'lattice': {'value': cell.tolist(), 'unit': 'angstrom', 'vectors_stored_as': 'rows'},
        'volume': {'value': volume_m3, 'unit': 'm^3'},
        'periodic_axes': [True, True, True], 'backend': 'VASP',
        'convergence_checked_by_reader': False, 'accepted_full_tensor': False,
        'standard_uncertainty': None,
        'limitation': 'Raw printed dipoles only; no convergence, branch, SCF error or response accuracy inferred.',
    }
