"""Safe position-matrix APT collection for legacy Cartesian ensembles."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .molecular_bec import _ATOM_DIR_RE, _direction_directory, _write_zborn
from .molecular_position import extract_abacus_position_dipole
from .molecular_response_quality import check_raw_apt_consistency
from .response_schema import response_record_from_bec_result
from .shared_response import (actual_displacement, make_phonopy, project_response,
                              read_structure, reconstruct_responses, symmetry_operations)


def collect_legacy_position_apts(root='.', *, method='central', displacement_angstrom=0.01,
                                 symprec=1e-3, response_output='response.json') -> dict:
    """Reconstruct a legacy Cartesian 0D APT using actual written displacements.

    This experimental route is not an independent accuracy certification. It
    requires the same verified R=0 sources as the Unified position route.
    """
    root = Path(root).resolve()
    if method.lower() not in ('forward', 'central'):
        raise ValueError('method must be forward or central')
    if not np.isfinite(displacement_angstrom) or displacement_angstrom <= 0:
        raise ValueError('displacement_angstrom must be positive and finite')
    reference = root / '0.no-move'
    atoms = read_structure(reference / 'STRU')
    atom_dirs = []
    for path in root.iterdir():
        match = _ATOM_DIR_RE.match(path.name)
        if path.is_dir() and match:
            index = int(match.group(1)) - 1
            if index < 0 or index >= len(atoms) or atoms.symbols[index] != match.group(2):
                raise ValueError(f'Atom directory disagrees with the reference structure: {path}')
            atom_dirs.append((index, path))
    atom_dirs.sort(key=lambda pair: pair[0])
    if not atom_dirs or len({index for index, _ in atom_dirs}) != len(atom_dirs):
        raise ValueError('No unique molecular atom-displacement directories were found')
    state_dir = root / '.zstar'
    state_dir.mkdir(exist_ok=True)
    pending = state_dir / 'legacy_molecular_apt_validation.pending'
    pending.write_text('Molecular APT collection is incomplete.\n', encoding='utf-8')
    baseline = extract_abacus_position_dipole(reference)
    reference_dipole = np.asarray(baseline['dipole_e_angstrom'])
    source_records = {'0.no-move': baseline}
    observations = []
    for index, directory in atom_dirs:
        for axis, direction in enumerate('xyz'):
            for sign in (('+', '-') if method.lower() == 'central' else ('+',)):
                stage = _direction_directory(directory, direction, sign)
                atom, vector = actual_displacement(atoms, read_structure(stage / 'STRU'))
                if atom != index or np.argmax(np.abs(vector)) != axis or vector[axis] * (1 if sign == '+' else -1) <= 0:
                    raise ValueError(f'Actual displacement does not match {stage}')
                if np.linalg.norm(np.delete(vector, axis)) > 1e-8:
                    raise ValueError(f'Legacy Cartesian displacement is not along {direction}: {stage}')
                entry = extract_abacus_position_dipole(stage)
                for key in ('occupied_bands', 'ionic_valence_by_species',
                            'pseudopotential_sha256_by_species', 'orbital_sha256_by_species',
                            'electronic_settings'):
                    if entry[key] != baseline[key]:
                        raise ValueError(f'{key} differs from reference in {stage}')
                name = stage.relative_to(root).as_posix()
                source_records[name] = entry
                observations.append({'atom': index, 'displacement_A': vector.tolist(),
                                     'dipole_change_e_A': (np.asarray(entry['dipole_e_angstrom']) - reference_dipole).tolist(),
                                     'forces_eV_A': np.zeros((len(atoms), 3)).tolist()})
    phonon = make_phonopy(atoms, symprec=symprec)
    operations = symmetry_operations(phonon, dimension=0, diagnostics_path=state_dir / 'symmetry.json')
    raw = reconstruct_responses(len(atoms), observations, operations)
    quality = check_raw_apt_consistency(raw.born, absolute_sum_tolerance_e=.05,
                                        relative_projection_tolerance=.1)
    (state_dir / 'molecular_apt_diagnostic.json').write_text(json.dumps(
        {'status': quality['sum_consistency'], 'raw_apt_e': raw.born.tolist(),
         'quality': quality, 'independent_accuracy_validated': False}, indent=2) + '\n', encoding='utf-8')
    if quality['sum_consistency'] != 'pass':
        raise ValueError(f'Raw molecular APT sum-rule check failed before projection; see {state_dir}')
    projected = project_response(raw)
    all_atoms = [{'index': i+1, 'label': str(symbol), 'tensor': tensor.T.tolist()}
                 for i, (symbol, tensor) in enumerate(zip(atoms.symbols, projected.born))]
    raw_atoms = [{'index': i+1, 'label': str(symbol), 'tensor': tensor.T.tolist()}
                 for i, (symbol, tensor) in enumerate(zip(atoms.symbols, raw.born))]
    indices = [index for index, _ in atom_dirs]
    for name, entries in (('BEC.raw.dat', raw_atoms), ('BEC.dat', all_atoms),
                          ('BEC.rep.raw.dat', [raw_atoms[i] for i in indices]),
                          ('BEC.rep.dat', [all_atoms[i] for i in indices])):
        _write_zborn(root / name, entries)
    result = {'schema_version': 1, 'backend': 'abacus-position-experimental', 'dimensionality': 0,
              'quantity': 'atomic_polar_tensor', 'method': method.lower(),
              'nominal_displacement_angstrom': float(displacement_angstrom),
              'displacements': observations, 'natoms_total': len(atoms),
              'natoms_calculated': len(atom_dirs), 'atoms': all_atoms, 'raw_atoms': raw_atoms,
              'tensor_convention': 'rows=atomic displacement; columns=molecular dipole; units e',
              'quality': quality, 'raw_fit_diagnostics': raw.diagnostics,
              'independent_accuracy_validated': False,
              'source_sha256': {name: record['source_sha256'] for name, record in source_records.items()},
              'json_output': str(root / 'molecular_apt.json'),
              'response_output': str((root / response_output).resolve())}
    json_path = Path(result['json_output'])
    json_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    response_record_from_bec_result(result, dimensionality=0,
                                    provenance={'collector': 'legacy-position-experimental',
                                                'source': str(json_path),
                                                'sum_consistency': quality['sum_consistency'],
                                                'independent_accuracy_validated': False}).write(result['response_output'])
    from .abacus_assets import sha256_file
    sources = {}
    for name, record in source_records.items():
        sources[name] = {}
        for source_name, digest in record['source_sha256'].items():
            path = Path(source_name).resolve()
            key = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
            sources[name][key] = digest
    receipt = {'schema': 'zstar-legacy-molecular-apt-validation', 'version': 1,
               'method': 'abacus_r0_position_expectation_experimental',
               'sum_consistency': 'pass', 'independent_accuracy_validated': False,
               'source_sha256': sources,
               'output_sha256': {name: sha256_file(root / name) for name in
                                 ('BEC.raw.dat', 'BEC.dat', 'molecular_apt.json')}}
    (state_dir / 'legacy_molecular_apt_validation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    pending.unlink()
    return result
