"""Finite-molecule dipoles from a verified R=0 nonorthogonal basis.

This numerical kernel does not itself certify that supplied matrices are from
the same self-consistent geometry, or that a periodic calculation represents
an isolated molecule. Those checks belong to the source adapter.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
from scipy.linalg import eigh
from scipy.sparse import csr_matrix


_RY_EV = 13.605693122994
_BOHR_ANGSTROM = 0.529177210903


def _matrix_header(handle):
    line = handle.readline()
    if line.startswith('STEP:'):
        line = handle.readline()
    if 'Matrix Dimension' not in line:
        raise ValueError('Missing sparse matrix dimension header')
    dimension = int(line.split()[-1])
    line = handle.readline()
    if 'Matrix number' not in line or int(line.split()[-1]) != 1:
        raise ValueError('Only finite-molecule matrices with exactly one R=0 block are supported')
    if dimension <= 0:
        raise ValueError('Sparse matrix dimension must be positive')
    return dimension


def _csr_block(handle, dimension, nnz):
    if nnz < 0:
        raise ValueError('Negative sparse matrix entry count')
    if nnz == 0:
        return np.zeros((dimension, dimension))
    try:
        values = np.asarray([float(x) for x in handle.readline().split()])
        indices = np.asarray([int(x) for x in handle.readline().split()])
        pointers = np.asarray([int(x) for x in handle.readline().split()])
    except ValueError as exc:
        raise ValueError('Invalid real-valued CSR block') from exc
    if (len(values) != nnz or len(indices) != nnz or len(pointers) != dimension + 1
            or not np.all(np.isfinite(values)) or pointers[0] != 0 or pointers[-1] != nnz
            or np.any(np.diff(pointers) < 0) or np.any(indices < 0)
            or np.any(indices >= dimension)):
        raise ValueError('Malformed sparse matrix CSR block')
    result = csr_matrix((values, indices, pointers), shape=(dimension, dimension))
    if not result.has_canonical_format:
        raise ValueError('Sparse matrix has duplicate or unsorted CSR indices')
    return result.toarray()


def read_r0_sparse_matrix(path):
    """Read a real ABACUS H(R) or S(R) file with one R=0 block."""
    with open(path, encoding='utf-8') as handle:
        dimension = _matrix_header(handle)
        try:
            header = [int(x) for x in handle.readline().split()]
        except ValueError as exc:
            raise ValueError('Invalid lattice-vector header') from exc
        if len(header) != 4 or header[:3] != [0, 0, 0]:
            raise ValueError('Only R=0 sparse matrices are supported')
        matrix = _csr_block(handle, dimension, header[3])
        if handle.read().strip():
            raise ValueError('Unexpected extra sparse matrix data')
    return matrix


def read_r0_position_matrices(path):
    """Read three real ABACUS r(R) components with one R=0 block."""
    with open(path, encoding='utf-8') as handle:
        dimension = _matrix_header(handle)
        if handle.readline().split() != ['0', '0', '0']:
            raise ValueError('Only R=0 position matrices are supported')
        components = []
        for _ in range(3):
            try:
                nnz = int(handle.readline().strip())
            except ValueError as exc:
                raise ValueError('Missing position-matrix entry count') from exc
            components.append(_csr_block(handle, dimension, nnz))
        if handle.read().strip():
            raise ValueError('Unexpected extra position matrix data')
    return np.asarray(components)


def molecular_position_dipole(hamiltonian, overlap, position, ionic_positions,
                              ionic_valence, *, occupied_bands: int,
                              min_gap_eV: float = 0.01) -> dict:
    """Compute a closed-shell R=0 dipole; matrices use eV and Angstrom.

    The occupation is exactly two electrons per occupied spatial orbital.
    This routine is deliberately not a parser or a general spin/metal solver.
    """
    h = np.asarray(hamiltonian, dtype=complex)
    s = np.asarray(overlap, dtype=complex)
    r = np.asarray(position, dtype=complex)
    positions = np.asarray(ionic_positions, dtype=float)
    charges = np.asarray(ionic_valence, dtype=float)
    if h.ndim != 2 or h.shape[0] != h.shape[1] or s.shape != h.shape:
        raise ValueError('Hamiltonian and overlap must be matching square matrices')
    n = h.shape[0]
    if r.shape != (3, n, n):
        raise ValueError('Position matrices must have shape (3, nbasis, nbasis)')
    if positions.ndim != 2 or positions.shape[1:] != (3,) or charges.shape != (len(positions),):
        raise ValueError('Ionic positions and valence charges have inconsistent shapes')
    if not all(np.all(np.isfinite(a)) for a in (h, s, r, positions, charges)):
        raise ValueError('Matrices, positions, and charges must be finite')
    if np.any(charges <= 0) or not len(charges):
        raise ValueError('Ionic valence charges must be positive and nonempty')
    if isinstance(occupied_bands, bool) or not isinstance(occupied_bands, (int, np.integer)):
        raise ValueError('occupied_bands must be an integer')
    nocc = int(occupied_bands)
    if not 0 < nocc < n:
        raise ValueError('An occupied and an empty orbital are required')
    if not np.isfinite(min_gap_eV) or min_gap_eV <= 0:
        raise ValueError('min_gap_eV must be positive and finite')
    if not np.isclose(charges.sum(), 2 * nocc, atol=1e-8, rtol=0):
        raise ValueError('This kernel requires a neutral closed-shell molecule')

    errors = [float(np.max(np.abs(a - a.conj().T))) for a in (h, s, *r)]
    if max(errors) > 1e-6:
        raise ValueError(f'Non-Hermitian source matrices: maximum residual {max(errors):.3g}')
    h = (h + h.conj().T) / 2
    s = (s + s.conj().T) / 2
    r = (r + r.conj().transpose(0, 2, 1)) / 2
    overlap_eigenvalues = np.linalg.eigvalsh(s)
    if overlap_eigenvalues[0] <= 1e-10 * overlap_eigenvalues[-1]:
        raise ValueError('Overlap matrix is non-positive or ill-conditioned')
    energy, coeff = eigh(h, s, subset_by_index=[0, nocc], driver='gvx')
    gap = float(energy[nocc] - energy[nocc - 1])
    if gap < min_gap_eV:
        raise ValueError(f'Occupied-state gap {gap:.6g} eV is below {min_gap_eV:.6g} eV')
    orthogonality = float(np.max(np.abs(coeff.conj().T @ s @ coeff - np.eye(nocc + 1))))
    if orthogonality > 1e-8:
        raise ValueError('Generalized eigenvectors fail overlap normalization')
    residual = h @ coeff - (s @ coeff) * energy[None, :]
    relative_residual = float(np.linalg.norm(residual) / max(np.linalg.norm(h), 1e-30))
    if relative_residual > 1e-8:
        raise ValueError('Generalized eigenproblem residual is too large')
    occupied = coeff[:, :nocc]
    electronic_complex = -2 * np.einsum('ib,aij,jb->a', occupied.conj(), r, occupied)
    if np.max(np.abs(electronic_complex.imag)) > 1e-8:
        raise ValueError('Electronic dipole has an unexpected imaginary component')
    electronic = electronic_complex.real
    ionic = charges @ positions
    electron_count = float(2 * np.trace(occupied.conj().T @ s @ occupied).real)
    return {
        'dipole_e_angstrom': (ionic + electronic).tolist(),
        'ionic_dipole_e_angstrom': ionic.tolist(),
        'electronic_dipole_e_angstrom': electronic.tolist(),
        'electron_count': electron_count,
        'occupied_bands': nocc,
        'gap_eV': gap,
        'overlap_condition_number': float(overlap_eigenvalues[-1] / overlap_eigenvalues[0]),
        'max_hermiticity_residual': max(errors),
        'orthogonality_residual': orthogonality,
        'eigenproblem_relative_residual': relative_residual,
        'independent_accuracy_validated': False,
    }


def validate_abacus_gamma_point(output: Path) -> Path:
    """Require an explicitly recorded single Gamma point; return its source."""
    kpt = output / 'KPT.info'
    occupation_path = output / 'istate.info'
    if kpt.is_file():
        text = kpt.read_text(encoding='utf-8')
        count = re.search(r'nkstot\s+now\s*=\s*(\d+)', text, re.I)
        point = re.search(r'KPOINTS\s+DIRECT_X\s+DIRECT_Y\s+DIRECT_Z\s+WEIGHT\s*\n\s*1\s+([^\n]+)', text, re.I)
        if count is None or int(count.group(1)) != 1 or point is None:
            raise ValueError('A single Gamma-point SCF is required for R=0 molecular matrices')
        tokens = point.group(1).split()[:3]
        source = kpt
    else:
        text = occupation_path.read_text(encoding='utf-8')
        points = re.findall(r'(?mi)^.*Kpoint\s*=\s*(\d+)\s*\(([^)]+)\)', text)
        if len(points) != 1 or points[0][0] != '1':
            raise ValueError('A single explicit Gamma point is required in istate.info')
        tokens = points[0][1].split()
        source = occupation_path
    try:
        coords = np.asarray([float(x) for x in tokens])
    except ValueError as exc:
        raise ValueError('Cannot parse the actual SCF k point') from exc
    if coords.shape != (3,) or not np.allclose(coords, 0, atol=1e-10, rtol=0):
        raise ValueError('A single Gamma-point SCF is required for R=0 molecular matrices')
    return source


def validate_abacus_scf_geometry(log: Path, atoms) -> None:
    """Compare SCF-recorded fractional positions with the requested structure."""
    text = log.read_text(encoding='utf-8', errors='replace')
    headers = list(re.finditer(r'(?mi)^\s*DIRECT\s+COORDINATES\s*$', text))
    if not headers:
        raise ValueError(f'ABACUS SCF log does not record direct atomic coordinates: {log}')
    rows = []
    for line in text[headers[-1].end():].splitlines():
        fields = line.split()
        if len(fields) < 4:
            if rows:
                break
            continue
        try:
            vector = [float(value.replace('D', 'E').replace('d', 'e')) for value in fields[1:4]]
        except ValueError:
            if rows:
                break
            continue
        rows.append((fields[0], vector))
        if len(rows) == len(atoms):
            break
    if len(rows) != len(atoms) or [row[0] for row in rows] != list(atoms.symbols):
        raise ValueError(f'Cannot verify ABACUS SCF atom order and coordinates: {log}')
    positions = np.asarray([row[1] for row in rows])
    if not np.all(np.isfinite(positions)):
        raise ValueError(f'ABACUS SCF coordinates are not finite: {log}')
    delta = positions - np.asarray(atoms.scaled_positions)
    delta -= np.rint(delta)
    residual = float(np.max(np.linalg.norm(delta @ np.asarray(atoms.cell), axis=1)))
    if residual > 1e-6:
        raise ValueError(f'ABACUS SCF coordinates differ from STRU by up to {residual:.6g} A: {log}')


def extract_abacus_position_dipole(stage, *, min_gap_eV: float = 0.01) -> dict:
    """Read one experimental neutral, nonmagnetic Gamma-point ABACUS stage.

    The returned source hashes and consistency checks do not establish that a
    periodic supercell is an isolated molecule, or independently validate APTs.
    """
    from .abacus_assets import sha256_file
    from .density_adapters import _upf_z_valence
    from .insulation import parse_abacus_occupation_gap
    from .shared_response import read_structure
    from .stru_analyzer import stru_analyzer
    from .workflow import _find_scf_log, scf_is_complete

    root = Path(stage).resolve()
    if not scf_is_complete(root):
        raise ValueError(f'ABACUS SCF is not demonstrably converged: {root}')
    log = _find_scf_log(root)
    output = log.parent
    atoms = read_structure(root / 'STRU')
    validate_abacus_scf_geometry(log, atoms)
    input_path = root / 'INPUT'
    if not input_path.is_file():
        raise FileNotFoundError(f'Actual ABACUS INPUT not found: {input_path}')
    params = {}
    for line in input_path.read_text(encoding='utf-8').splitlines():
        fields = line.split('#', 1)[0].split()
        if len(fields) >= 2:
            key = fields[0].lower()
            if key in params:
                raise ValueError(f'Duplicate ABACUS input parameter: {key}')
            params[key] = fields[1]
    if params.get('basis_type', '').lower() != 'lcao' or params.get('nspin', '1') != '1':
        raise ValueError('Position dipoles require nonmagnetic nspin=1 LCAO stages')
    for key in ('noncolin', 'lspinorb', 'gate_flag', 'efield_flag'):
        if params.get(key, '0').lower() not in ('0', 'false', '.false.'):
            raise ValueError(f'Unsupported molecular response setting: {key}')
    if float(params.get('nelec_delta', '0')) != 0 or 'nelec' in params:
        raise ValueError('Charged or explicitly overridden electron counts are unsupported')

    occupation_path = output / 'istate.info'
    kpoint_source = validate_abacus_gamma_point(output)
    occupation = parse_abacus_occupation_gap(occupation_path, insulating_threshold_eV=min_gap_eV)
    if occupation is None or not occupation['insulating'] or occupation['kpoint_count'] != 1:
        raise ValueError('SCF occupation table does not establish an insulating closed-shell state')
    nocc = occupation['occupied_band_count']
    # The generic gap parser classifies weights relatively; an R=0 closed-shell
    # calculation also needs the absolute two-electron Gamma occupation.
    rows = []
    for line in occupation_path.read_text(encoding='utf-8').splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0].isdigit():
            rows.append((int(fields[0]), float(fields[1]), float(fields[2])))
    if (len(rows) <= nocc or [row[0] for row in rows] != list(range(1, len(rows) + 1))
            or any(abs(row[2] - 2.0) > 1e-6 for row in rows[:nocc])
            or any(abs(row[2]) > 2e-6 for row in rows[nocc:])):
        raise ValueError('R=0 position dipoles require contiguous doubly occupied Gamma states')

    pyatb = root / 'pyatb' / 'Input'
    text = pyatb.read_text(encoding='utf-8')
    for key, expected in (('HR_unit', 'Ry'), ('rR_unit', 'Bohr')):
        matches = re.findall(rf'(?mi)^\s*{key}\s+(\S+)', text)
        if not matches or any(value.lower() != expected.lower() for value in matches):
            raise ValueError(f'Missing or inconsistent {key}={expected} in {pyatb}')
    occ = re.findall(r'(?mi)^\s*occ_band\s+(\d+)', text)
    if not occ or any(int(value) != nocc for value in occ):
        raise ValueError('PYATB and SCF occupied-band counts disagree')

    values = stru_analyzer(str(root / 'STRU'))
    labels, pseudopotentials, orbitals = values[2], values[9], values[10]
    pseudo_dir = Path(params.get('pseudo_dir', '.')).expanduser()
    if not pseudo_dir.is_absolute():
        pseudo_dir = root / pseudo_dir
    pseudo_paths = {label: (pseudo_dir / name).resolve()
                    for label, name in zip(labels, pseudopotentials)}
    orbital_dir = Path(params.get('orbital_dir', '.')).expanduser()
    if not orbital_dir.is_absolute():
        orbital_dir = root / orbital_dir
    if not all(orbitals) or len(orbitals) != len(labels):
        raise ValueError('A numerical orbital must be specified for each species')
    orbital_paths = {label: (orbital_dir / name).resolve()
                     for label, name in zip(labels, orbitals)}
    valences = {label: _upf_z_valence(path) for label, path in pseudo_paths.items()}
    charges = [valences[label] for label in atoms.symbols]
    paths = [output / 'data-HR-sparse_SPIN0.csr', output / 'data-SR-sparse_SPIN0.csr',
             output / 'data-rR-sparse.csr']
    sources = [*paths, root / 'STRU', input_path, log, kpoint_source, occupation_path, pyatb,
               *pseudo_paths.values(), *orbital_paths.values()]
    hashes = {str(path): sha256_file(path) for path in sources}
    result = molecular_position_dipole(
        read_r0_sparse_matrix(paths[0]) * _RY_EV,
        read_r0_sparse_matrix(paths[1]),
        read_r0_position_matrices(paths[2]) * _BOHR_ANGSTROM,
        atoms.positions, charges, occupied_bands=nocc, min_gap_eV=min_gap_eV)
    gap_difference = abs(result['gap_eV'] - occupation['gap_eV'])
    gap_tolerance_eV = 1e-3
    if gap_difference > gap_tolerance_eV:
        raise ValueError(
            f'Matrix and SCF occupation gaps disagree by {gap_difference:.6g} eV '
            f'(limit {gap_tolerance_eV:g} eV); check that outputs belong to the same SCF.'
        )
    if any(sha256_file(path) != hashes[str(path)] for path in sources):
        raise ValueError('A source file changed while computing the molecular dipole')
    result.update(method='abacus_r0_position_expectation_experimental',
                  source_sha256=hashes, scf_occupation_gap_eV=occupation['gap_eV'],
                  matrix_scf_gap_difference_eV=gap_difference,
                  matrix_scf_gap_tolerance_eV=gap_tolerance_eV,
                  kpoint_source=str(kpoint_source),
                  ionic_valence_by_species=valences,
                  pseudopotential_sha256_by_species={label: hashes[str(path)]
                                                     for label, path in pseudo_paths.items()},
                  orbital_sha256_by_species={label: hashes[str(path)]
                                             for label, path in orbital_paths.items()},
                  # Retain all response-relevant settings, not only a short
                  # allowlist that could miss e.g. a Hubbard or field option.
                  electronic_settings={key: value for key, value in params.items()
                                       if not key.startswith('out_') and key not in {
                                           'suffix', 'pseudo_dir', 'orbital_dir',
                                           'init_chg', 'read_file_dir', 'cal_force',
                                           'cal_stress', 'out_level'}},
                  boundary_scope='R=0 Gamma supercell; isolation not certified')
    return result


def experimental_position_responses(root, manifest):
    """Extract same-method dipole changes for a Unified displacement ensemble.

    Returns diagnostics only; callers must independently gate the reconstructed
    full-atom APT before producing or promoting a physical result.
    """
    from .shared_response import actual_displacement, read_structure

    root = Path(root).resolve()
    if manifest.get('dimension') != 0:
        raise ValueError('Position expectation is currently restricted to 0D')
    reference = root / '0.no-move'
    atoms = read_structure(reference / 'STRU')
    stages = manifest.get('stages')
    if not isinstance(stages, list) or not stages:
        raise ValueError('A nonempty displacement ensemble is required')
    for entry in stages:
        name = entry['name']
        if not re.fullmatch(r'disp-\d+', name):
            raise ValueError(f'Invalid displacement stage name: {name}')
        atom, displacement = actual_displacement(atoms, read_structure(root / name / 'STRU'))
        if atom != entry['atom'] or not np.allclose(displacement, entry['displacement_A'],
                                                    atol=1e-10, rtol=0):
            raise ValueError(f'Displacement differs from manifest: {name}')
    baseline = extract_abacus_position_dipole(reference)
    reference_dipole = np.asarray(baseline['dipole_e_angstrom'])
    changes, records = [], {}
    for entry in stages:
        result = extract_abacus_position_dipole(root / entry['name'])
        for key in ('occupied_bands', 'ionic_valence_by_species',
                    'pseudopotential_sha256_by_species', 'orbital_sha256_by_species',
                    'electronic_settings'):
            if result[key] != baseline[key]:
                raise ValueError(f'{key} differs from reference in {entry["name"]}')
        changes.append((np.asarray(result['dipole_e_angstrom']) - reference_dipole).tolist())
        records[entry['name']] = result
    return changes, {'method': baseline['method'], 'reference': baseline,
                     'stages': records, 'accuracy_certified': False,
                     'scope': 'experimental R=0 position expectation; no APT projection'}


def diagnose_position_apt(root, manifest, *, absolute_sum_tolerance_e: float,
                          relative_projection_tolerance: float) -> dict:
    """Reconstruct an unprojected diagnostic APT from experimental dipoles.

    This returns data in memory only and must not create BEC.dat/BORN or a
    production validation marker. A sum-rule pass is not independent evidence.
    """
    from .molecular_response_quality import check_raw_apt_consistency
    from .shared_response import (make_phonopy, read_structure,
                                  reconstruct_responses, symmetry_operations)

    root = Path(root).resolve()
    if manifest.get('dimension') != 0:
        raise ValueError('Position APT diagnostics are restricted to 0D')
    atoms = read_structure(root / '0.no-move' / 'STRU')
    operations = symmetry_operations(make_phonopy(atoms, symprec=manifest['symprec_A']),
                                     dimension=0)
    changes, provenance = experimental_position_responses(root, manifest)
    if len(changes) != len(manifest['stages']):
        raise ValueError('Incomplete molecular dipole displacement series')
    observations = [dict(**stage, dipole_change_e_A=delta,
                         forces_eV_A=np.zeros((len(atoms), 3)))
                    for stage, delta in zip(manifest['stages'], changes)]
    raw = reconstruct_responses(len(atoms), observations, operations)
    quality = check_raw_apt_consistency(
        raw.born, absolute_sum_tolerance_e=absolute_sum_tolerance_e,
        relative_projection_tolerance=relative_projection_tolerance)
    return {'schema': 'zstar-molecular-position-apt-diagnostic', 'version': 1,
            'status': 'diagnostic_only', 'tensor_convention': 'atom,dipole,displacement',
            'raw_apt_e': raw.born.tolist(), 'raw_fit_diagnostics': raw.diagnostics,
            'sum_rule_diagnostics': quality, 'source_provenance': provenance,
            'independent_accuracy_validated': False}
