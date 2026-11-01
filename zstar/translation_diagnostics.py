"""Compare already-computed forces under a rigid translation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np

from .abacus_assets import sha256_file
from .structure_io import StructureData, read_abacus_stru, read_poscar


@dataclass(frozen=True)
class TranslationStage:
    structure: StructureData
    forces_eV_A: np.ndarray
    energy_eV: float | None
    sources: dict
    input_hashes: dict
    calculator: str


def _vasp_last_force_positions(path: Path, natoms: int) -> np.ndarray:
    text = path.read_text(encoding='utf-8', errors='replace')
    headers = list(re.finditer(r'(?mi)^\s*POSITION\s+TOTAL-FORCE\s*\(eV/Angst\)', text))
    if not headers:
        raise ValueError(f'No VASP POSITION/TOTAL-FORCE block in {path}')
    rows = []
    for line in text[headers[-1].end():].splitlines():
        fields = line.split()
        if len(fields) < 6:
            if rows:
                break
            continue
        try:
            rows.append([float(value.replace('D', 'E')) for value in fields[:3]])
        except ValueError:
            if rows:
                break
        if len(rows) == natoms:
            break
    if len(rows) != natoms or not np.isfinite(rows).all():
        raise ValueError(f'Cannot parse final VASP force-block positions in {path}')
    return np.asarray(rows)


def read_translation_stage(path: str | Path, *, calculator: str) -> TranslationStage:
    """Read an already completed static stage; no native program is invoked."""
    root = Path(path).resolve()
    backend = calculator.lower()
    if backend == 'abacus':
        from .shared_abacus import read_forces
        from .workflow import _find_scf_log, scf_is_complete
        if not scf_is_complete(root):
            raise ValueError(f'ABACUS stage is not a completed SCF: {root}')
        stru, input_path, log = root/'STRU', root/'INPUT', _find_scf_log(root)
        if not input_path.is_file():
            raise FileNotFoundError(f'Actual ABACUS INPUT not found: {input_path}')
        text = input_path.read_text(encoding='utf-8')
        match = re.search(r'(?mi)^\s*calculation\s+(\S+)', text)
        if match is None or match.group(1).lower() != 'scf':
            raise ValueError('Translation diagnostics require an ABACUS static SCF')
        structure = read_abacus_stru(stru)
        forces = read_forces(root)
        energies = re.findall(r'(?mi)^\s*!FINAL_ETOT_IS\s+([-+\d.eEdD]+)',
                              log.read_text(encoding='utf-8', errors='replace'))
        energy = float(energies[-1].replace('D', 'E').replace('d', 'e')) if energies else None
        inputs = [input_path, root/'KPT']
        outputs = [stru, log]
    elif backend == 'vasp':
        from .v2.vasp import parse_vasp_outcar_observations
        from .vasp_bec import _incar_value, vasp_output_complete
        stru, input_path, log = root/'POSCAR', root/'INCAR', root/'OUTCAR'
        if not vasp_output_complete(log):
            raise ValueError(f'VASP OUTCAR is incomplete: {log}')
        text = input_path.read_text(encoding='utf-8')
        nsw = _incar_value(text, 'NSW')
        if nsw is None or int(float(nsw)) != 0:
            raise ValueError('Translation diagnostics require a VASP static NSW=0 calculation')
        structure = read_poscar(stru)
        parsed = parse_vasp_outcar_observations(log, natoms=len(structure.symbols),
                                                require_forces=True, require_stress=False)
        forces, energy = parsed.forces_final, parsed.energy
        if not np.allclose(parsed.lattice_angstrom, structure.lattice_angstrom, atol=1e-5, rtol=0):
            raise ValueError('VASP OUTCAR and POSCAR cells differ')
        actual_positions = _vasp_last_force_positions(log, len(structure.symbols))
        delta = (actual_positions - structure.cart_coords) @ np.linalg.inv(structure.lattice_angstrom)
        delta -= np.rint(delta)
        if np.max(np.linalg.norm(delta @ structure.lattice_angstrom, axis=1)) > 1e-4:
            raise ValueError('VASP OUTCAR force-block positions differ from POSCAR')
        inputs = [input_path, root/'KPOINTS', root/'POTCAR']
        outputs = [stru, log]
    else:
        raise ValueError('calculator must be abacus or vasp')
    return TranslationStage(structure, np.asarray(forces), energy,
                            {p.name: {'path': str(p), 'sha256': sha256_file(p)} for p in outputs},
                            {p.name: sha256_file(p) if p.is_file() else None for p in inputs}, backend)


def compare_translation_stages(reference: TranslationStage, translated: TranslationStage, *,
                               dimensionality: int, geometry_tolerance_A: float = 1e-5) -> dict:
    if dimensionality not in (0, 1, 2, 3):
        raise ValueError('dimensionality must be 0, 1, 2, or 3')
    if not np.isfinite(geometry_tolerance_A) or geometry_tolerance_A <= 0:
        raise ValueError('geometry_tolerance_A must be positive and finite')
    a, b = reference.structure, translated.structure
    if reference.calculator != translated.calculator:
        raise ValueError('A translation control must use the same calculator on both structures')
    if a.symbols != b.symbols or not a.symbols:
        raise ValueError('Translation stages have different atom ordering or species')
    cell = np.asarray(a.lattice_angstrom)
    if not np.allclose(cell, b.lattice_angstrom, atol=geometry_tolerance_A, rtol=0):
        raise ValueError('Translation stages have different cells')
    positions_a = np.asarray(a.positions_fractional, dtype=float)
    positions_b = np.asarray(b.positions_fractional, dtype=float)
    if (positions_a.shape != (len(a.symbols), 3) or positions_b.shape != positions_a.shape or
            not np.isfinite(positions_a).all() or not np.isfinite(positions_b).all()):
        raise ValueError('Translation stages have invalid positions')
    fractional = positions_b - positions_a
    axes = {0: (), 1: (2,), 2: (0, 1), 3: (0, 1, 2)}[dimensionality]
    if axes:
        fractional[:, axes] -= np.rint(fractional[:, axes] - fractional[0, axes])
        fractional[:, axes] -= np.rint(np.mean(fractional[:, axes], axis=0))
    displacement = fractional @ cell
    shift = np.mean(displacement, axis=0)
    residual = float(np.max(np.linalg.norm(displacement - shift, axis=1)))
    if residual > geometry_tolerance_A:
        raise ValueError(f'Structures are not related by a rigid translation: residual {residual:.6g} A')
    f0, f1 = np.asarray(reference.forces_eV_A, dtype=float), np.asarray(translated.forces_eV_A, dtype=float)
    if f0.shape != (len(a.symbols), 3) or f1.shape != f0.shape or not np.isfinite(f0).all() or not np.isfinite(f1).all():
        raise ValueError('Force arrays must be finite and match the atom count')
    difference = f1 - f0
    input_names = set(reference.input_hashes) | set(translated.input_hashes)
    input_checks = {name: (reference.input_hashes.get(name) == translated.input_hashes.get(name)
                           if reference.input_hashes.get(name) and translated.input_hashes.get(name) else None)
                    for name in sorted(input_names)}
    return {
        'schema': 'zstar-translation-control', 'version': 1, 'calculator': reference.calculator,
        'dimensionality': dimensionality, 'translation_A': shift.tolist(),
        'geometry_max_residual_A': residual, 'geometry_tolerance_A': geometry_tolerance_A,
        'energy_difference_eV': (translated.energy_eV - reference.energy_eV
                                 if reference.energy_eV is not None and translated.energy_eV is not None else None),
        'force_delta_eV_A': difference.tolist(),
        'max_atom_force_delta_eV_A': float(np.max(np.linalg.norm(difference, axis=1))),
        'rms_force_component_delta_eV_A': float(np.sqrt(np.mean(difference**2))),
        'reference_total_printed_force_eV_A': f0.sum(axis=0).tolist(),
        'translated_total_printed_force_eV_A': f1.sum(axis=0).tolist(),
        'input_file_hashes_equal': input_checks,
        'input_hashes': {'reference': reference.input_hashes, 'translated': translated.input_hashes},
        'sources': {'reference': reference.sources, 'translated': translated.sources},
        'interpretation': ('Forces are the printed calculator output; native net-force or drift correction '
                           'is not inferred. Input hashes are a limited consistency check, not proof of '
                           'matching pseudopotentials, settings, convergence, or stability.'),
    }
