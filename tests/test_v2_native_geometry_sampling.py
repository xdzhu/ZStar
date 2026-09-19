"""Three-dimensional geometry counting: reduced sampling is not full reconstruction."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from pymatgen.core import Structure
from pymatgen.io.vasp import Poscar

spec = importlib.util.spec_from_file_location('research_geometry', Path(__file__).resolve().parents[1] /
                                             '.codex-output/audit_native_perturbation_geometry.py')
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def fixture_files(tmp_path, full=False, terminal=True, negative=True, duplicate_atomic=False):
    parent = Structure(np.diag([4., 5., 6.]), ['Ga', 'N'], [[0, 0, 0], [.5, .5, .4]])
    poscar = tmp_path/'POSCAR'
    poscar.write_text(Poscar(parent).get_str(), encoding='utf-8')
    incar = tmp_path/'INCAR'
    incar.write_text('IBRION=6\nISYM=1\nNFREE=2\nISIF=3\n', encoding='utf-8')
    frames = [(parent.lattice.matrix, parent.cart_coords)]
    for component in range(6 if full else 1):
        for sign in (-1, 1) if negative else (1,):
            eps = np.zeros((3, 3))
            if component < 3:
                eps[component, component] = sign*.01
            else:
                i, j = [(1, 2), (0, 2), (0, 1)][component-3]
                eps[i, j] = eps[j, i] = sign*.005
            cell = parent.lattice.matrix@(np.eye(3)+eps)
            frames.append((cell, parent.frac_coords@cell))
    for component in range(6 if full else 1):
        for sign in (-1, 1) if negative else (1,):
            positions = parent.cart_coords.copy()
            positions.flat[0 if duplicate_atomic else component] += sign*.01
            frames.append((parent.lattice.matrix, positions))
    lines = []
    for cell, positions in frames:
        lines.append('direct lattice vectors reciprocal lattice vectors')
        lines.extend(' '.join(map(str, row))+' 0 0 0' for row in cell)
        lines.extend(['POSITION TOTAL-FORCE', '---------------------'])
        lines.extend(' '.join(map(str, row))+' 0 0 0' for row in positions)
    if terminal:
        lines.append('General timing and accounting informations')
    outcar = tmp_path/'OUTCAR'
    outcar.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return outcar, poscar, incar


def test_full_explicit_3d_central_sampling_retained(tmp_path):
    outcar, poscar, _ = fixture_files(tmp_path, full=True)
    result = geometry.audit(outcar, poscar)
    assert result['counts'] == dict(reference=1, atomic=12, strain=12, mixed=0)
    assert result['raw_sampling_ranks']['strain']['unexpanded_sample_rank'] == 6
    assert result['explicit_sign_pairing']['atomic']['complete_explicit_pairs']


def test_reduced_counts_not_hardcoded_full_or_promoted(tmp_path):
    outcar, poscar, incar = fixture_files(tmp_path)
    with pytest.raises(ValueError, match='Incomplete explicit full'):
        geometry.audit(outcar, poscar)
    result = geometry.audit(outcar, poscar, sampling='symmetry-reduced', incar=incar)
    assert result['counts'] == dict(reference=1, atomic=2, strain=2, mixed=0)
    assert not result['symmetry_reconstruction_completeness_verified']
    assert result['reference_symmetry']['symprec_angstrom'] == .001
    assert result['reduced_input_evidence']['settings']['ISYM'] == 1


def test_reduced_missing_negative_reported_not_assumed_reconstructed(tmp_path):
    outcar, poscar, incar = fixture_files(tmp_path, negative=False)
    result = geometry.audit(outcar, poscar, sampling='symmetry-reduced', incar=incar)
    assert not result['explicit_sign_pairing']['atomic']['complete_explicit_pairs']
    assert result['explicit_sign_pairing']['atomic']['unmatched_explicit_negative_record_indices']
    assert not result['symmetry_reconstruction_completeness_verified']


def test_no_freeze_live_outcar(tmp_path):
    outcar, poscar, incar = fixture_files(tmp_path, terminal=False)
    with pytest.raises(ValueError, match='not terminal'):
        geometry.audit(outcar, poscar, sampling='symmetry-reduced', incar=incar)


def test_reduced_requires_actual_compatible_input(tmp_path):
    outcar, poscar, incar = fixture_files(tmp_path)
    with pytest.raises(ValueError, match='INCAR required'):
        geometry.audit(outcar, poscar, sampling='symmetry-reduced')
    incar.write_text('IBRION=6\nISYM=0\nNFREE=2\nISIF=3\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Reduced audit requires'):
        geometry.audit(outcar, poscar, sampling='symmetry-reduced', incar=incar)


def test_correct_counts_but_repeated_atomic_directions_rejected(tmp_path):
    outcar, poscar, _ = fixture_files(tmp_path, full=True, duplicate_atomic=True)
    with pytest.raises(ValueError, match='raw atomic rank'):
        geometry.audit(outcar, poscar)
