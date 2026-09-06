import json
import numpy as np
import pytest
from phonopy.structure.atoms import PhonopyAtoms

from tools.shared_response import one_dimensional_cases as cases
from tools.shared_response.one_dimensional_cases import center_transverse


def test_centering_unwraps_vacuum_cut_without_distorting_structure():
    atoms = PhonopyAtoms(symbols=['B', 'N', 'B'], cell=np.diag([20., 22., 4.]),
                         scaled_positions=[[.98, .96, .1], [.03, .04, .3], [.01, .02, .8]])
    before = atoms.scaled_positions.copy()
    centered = center_transverse(atoms).scaled_positions
    np.testing.assert_allclose((centered[:, :2].min(0) + centered[:, :2].max(0)) / 2, .5)
    np.testing.assert_array_equal(centered[:, 2], before[:, 2])
    for i in range(3):
        delta = (centered[i] - centered[0]) - (before[i] - before[0])
        np.testing.assert_allclose(delta - np.rint(delta), 0, atol=1e-14)
    np.testing.assert_allclose(center_transverse(atoms).scaled_positions, centered)


def test_centering_rejects_skew_cell():
    atoms = PhonopyAtoms(symbols=['B'], cell=[[20., 1, 0], [0, 20, 0], [0, 0, 4]],
                         scaled_positions=[[0, 0, 0]])
    with pytest.raises(ValueError, match='orthogonal'):
        center_transverse(atoms)


def test_audit_refuses_live_relaxation(tmp_path):
    folder = tmp_path / 'case/relaxation'
    folder.mkdir(parents=True)
    (folder / 'worker.json').write_text(json.dumps({'status': 'running'}))
    with pytest.raises(ValueError, match='not finished'):
        cases.audit_relaxation(tmp_path, 'case')


@pytest.mark.parametrize('force,stress,accepted', [(0.002, .02, True),
                                                 (.02, .02, False),
                                                 (.002, .2, False)])
def test_audit_checks_axial_stress_and_force(tmp_path, monkeypatch, force, stress, accepted):
    folder = tmp_path / 'case/relaxation/OUT.TEST'
    folder.mkdir(parents=True)
    (folder.parent / 'worker.json').write_text(json.dumps({
        'status': 'finished-awaiting-stress-and-geometry-audit', 'allocated_core_hours': 1}))
    (folder / 'running_cell-relax.log').write_text(
        'TOTAL-STRESS (KBAR)\n---\n3 0 0\n0 4 0\n0 0 ' + str(stress)
        + '\n---\n Relaxation is converged!\n')
    (folder / 'STRU_ION_D').touch()
    atoms = PhonopyAtoms(symbols=['B'], cell=np.diag([20., 20., 4.]),
                         scaled_positions=[[.5, .5, 0]])
    monkeypatch.setattr(cases, 'read_structure', lambda path: atoms)
    monkeypatch.setattr(cases, 'read_abacus_output', lambda path: [[force, 0, 0]])
    if accepted:
        _, _, result = cases.audit_relaxation(tmp_path, 'case')
        assert result['status'] == 'accepted'
        assert result['final_stress_kbar'][0][0] == 3
    else:
        with pytest.raises(ValueError, match='Unconverged force/stress'):
            cases.audit_relaxation(tmp_path, 'case')


def test_scf_convergence_does_not_imply_geometry_convergence(tmp_path, monkeypatch):
    folder = tmp_path / 'case/relaxation/OUT.TEST'
    folder.mkdir(parents=True)
    (folder.parent / 'worker.json').write_text(json.dumps({
        'status': 'finished-awaiting-stress-and-geometry-audit', 'allocated_core_hours': 1}))
    (folder / 'STRU_ION_D').touch()
    (folder / 'running_cell-relax.log').write_text(
        'SCF converged\n Relaxation is not converged yet!\n')
    monkeypatch.setattr(cases, 'read_abacus_output', lambda path: [[0, 0, 0]])
    with pytest.raises(ValueError, match='explicit geometry'):
        cases.audit_relaxation(tmp_path, 'case')
