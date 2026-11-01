import numpy as np
import pytest

from zstar.molecular_position import (extract_abacus_position_dipole,
                                      diagnose_position_apt, experimental_position_responses,
                                      molecular_position_dipole, read_r0_sparse_matrix,
                                      read_r0_position_matrices)


def _inputs():
    overlap = np.diag([2.0, 0.5])
    hamiltonian = overlap @ np.diag([-2.0, 1.0])
    position = np.array([overlap @ np.diag([1.0, 3.0]),
                         overlap @ np.diag([2.0, 4.0]),
                         overlap @ np.diag([3.0, 5.0])])
    return hamiltonian, overlap, position, np.array([[1.5, 2.5, 3.5]]), [2.0]


def test_nonorthogonal_occupied_state_dipole_and_origin_invariance():
    h, s, r, positions, charges = _inputs()
    result = molecular_position_dipole(h, s, r, positions, charges, occupied_bands=1)
    np.testing.assert_allclose(result['dipole_e_angstrom'], [1, 1, 1], atol=1e-12)
    assert result['electron_count'] == pytest.approx(2)
    assert not result['independent_accuracy_validated']
    shift = np.array([.13, -.21, .07])
    shifted = molecular_position_dipole(h, s, r + shift[:, None, None] * s,
                                        positions + shift, charges, occupied_bands=1)
    np.testing.assert_allclose(shifted['dipole_e_angstrom'], result['dipole_e_angstrom'], atol=1e-12)


def test_invalid_overlap_occupation_and_charge_are_rejected():
    h, s, r, positions, charges = _inputs()
    with pytest.raises(ValueError, match='ill-conditioned'):
        molecular_position_dipole(h, np.diag([1, 0]), r, positions, charges, occupied_bands=1)
    with pytest.raises(ValueError, match='neutral closed-shell'):
        molecular_position_dipole(h, s, r, positions, [1], occupied_bands=1)
    with pytest.raises(ValueError, match='occupied and an empty'):
        molecular_position_dipole(h, s, r, positions, charges, occupied_bands=2)
    with pytest.raises(ValueError, match='integer'):
        molecular_position_dipole(h, s, r, positions, charges, occupied_bands=1.0)
    h[0, 1] = 2
    with pytest.raises(ValueError, match='Non-Hermitian'):
        molecular_position_dipole(h, s, r, positions, charges, occupied_bands=1)


def test_r0_sparse_parsers_reject_periodic_and_malformed_data(tmp_path):
    path = tmp_path / 'matrix.csr'
    header = 'STEP: 0\nMatrix Dimension of H(R): 2\nMatrix number of H(R): 1\n'
    block = '2 0.5\n0 1\n0 1 2\n'
    path.write_text(header + '0 0 0 2\n' + block)
    np.testing.assert_array_equal(read_r0_sparse_matrix(path), np.diag([2, .5]))
    path.write_text(header + '1 0 0 2\n' + block)
    with pytest.raises(ValueError, match='R=0'):
        read_r0_sparse_matrix(path)
    path.write_text(header + '0 0 0 2\n2 0.5\n0 1\n0 2 1\n')
    with pytest.raises(ValueError, match='Malformed'):
        read_r0_sparse_matrix(path)
    path.write_text(header + '0 0 0\n' + ('2\n' + block) * 3)
    np.testing.assert_array_equal(read_r0_position_matrices(path), np.tile(np.diag([2, .5]), (3, 1, 1)))
    path.write_text(header + '0 0 0\n0\n0\n0\nextra')
    with pytest.raises(ValueError, match='extra'):
        read_r0_position_matrices(path)


def _write_stage(root):
    (root / 'STRU').write_text(
        'ATOMIC_SPECIES\nHe 4.0 He.upf\n\nNUMERICAL_ORBITAL\nHe.orb\n\nLATTICE_CONSTANT\n1\n\n'
        'LATTICE_VECTORS\n10 0 0\n0 10 0\n0 0 10\n\n'
        'ATOMIC_POSITIONS\nDirect\nHe\n0\n1\n0.5 0.5 0.5 1 1 1\n')
    (root / 'He.upf').write_text('<PP_HEADER z_valence="    2.00"/>')
    (root / 'He.orb').write_text('test orbital')
    (root / 'INPUT').write_text('INPUT_PARAMETERS\nbasis_type lcao\nnspin 1\n')
    pyatb = root / 'pyatb'
    pyatb.mkdir()
    (pyatb / 'Input').write_text('HR_unit Ry\nrR_unit Bohr\nocc_band 1\n')
    out = root / 'OUT.TEST'
    out.mkdir()
    (out / 'running_scf.log').write_text('DIRECT COORDINATES\natom x y z mag\n'
                                          'He 0.5 0.5 0.5 0\n\n'
                                          'charge density convergence is achieved\ntotal time\n')
    (out / 'KPT.info').write_text('nkstot now = 1\nKPOINTS DIRECT_X DIRECT_Y DIRECT_Z WEIGHT\n'
                                   '1 0.0 0.0 0.0 1.0\n')
    (out / 'istate.info').write_text('BAND Energy(ev) Occupation Kpoint = 1 (0 0 0)\n'
                                    '1 -27.211386245988 2\n2 13.605693122994 0\n')
    header = 'STEP: 0\nMatrix Dimension of H(R): 2\nMatrix number of H(R): 1\n'
    block = '1 1\n0 1\n0 1 2\n'
    (out / 'data-HR-sparse_SPIN0.csr').write_text(header + '0 0 0 2\n-2 1\n0 1\n0 1 2\n')
    (out / 'data-SR-sparse_SPIN0.csr').write_text(header + '0 0 0 2\n' + block)
    (out / 'data-rR-sparse.csr').write_text(header + '0 0 0\n' + ('2\n' + block) * 3)
    return out


def test_abacus_stage_adapter_checks_provenance_and_scf_occupancy(tmp_path):
    out = _write_stage(tmp_path)
    result = extract_abacus_position_dipole(tmp_path)
    assert result['electron_count'] == pytest.approx(2)
    assert result['ionic_valence_by_species'] == {'He': 2}
    assert len(result['source_sha256']) == 11
    assert not result['independent_accuracy_validated']
    (out / 'istate.info').write_text('BAND Energy(ev) Occupation Kpoint = 1\n1 -2 1\n2 1 0\n')
    with pytest.raises(ValueError, match='doubly occupied'):
        extract_abacus_position_dipole(tmp_path)


def test_position_stage_tracks_nonstandard_electronic_settings(tmp_path):
    _write_stage(tmp_path)
    path = tmp_path / 'INPUT'
    path.write_text(path.read_text() + 'dft_plus_u 1\ninit_chg file\nout_chg 1\n')
    settings = extract_abacus_position_dipole(tmp_path)['electronic_settings']
    assert settings['dft_plus_u'] == '1'
    assert 'init_chg' not in settings
    assert 'out_chg' not in settings


def test_abacus_stage_adapter_rejects_stale_scf_geometry(tmp_path):
    out = _write_stage(tmp_path)
    log = out / 'running_scf.log'
    log.write_text(log.read_text().replace('He 0.5 0.5 0.5', 'He 0.51 0.5 0.5'))
    with pytest.raises(ValueError, match='SCF coordinates differ from STRU'):
        extract_abacus_position_dipole(tmp_path)


def test_abacus_stage_adapter_rejects_matrix_scf_gap_mismatch(tmp_path):
    out = _write_stage(tmp_path)
    (out / 'istate.info').write_text('BAND Energy(ev) Occupation Kpoint = 1\n'
                                    '1 -2 2\n2 1 0\n')
    with pytest.raises(ValueError, match='Matrix and SCF occupation gaps disagree'):
        extract_abacus_position_dipole(tmp_path)


def test_abacus_stage_adapter_rejects_non_gamma_and_unit_mismatch(tmp_path):
    out = _write_stage(tmp_path)
    (out / 'KPT.info').write_text('nkstot now = 1\nKPOINTS DIRECT_X DIRECT_Y DIRECT_Z WEIGHT\n'
                                  '1 0.5 0.0 0.0 1.0\n')
    with pytest.raises(ValueError, match='Gamma-point'):
        extract_abacus_position_dipole(tmp_path)
    (out / 'KPT.info').write_text('nkstot now = 1\nKPOINTS DIRECT_X DIRECT_Y DIRECT_Z WEIGHT\n'
                                  '1 0.0 0.0 0.0 1.0\n')
    (tmp_path / 'pyatb' / 'Input').write_text('HR_unit eV\nrR_unit Bohr\nocc_band 1\n')
    with pytest.raises(ValueError, match='HR_unit=Ry'):
        extract_abacus_position_dipole(tmp_path)


def test_archived_single_gamma_can_be_verified_from_occupation_header(tmp_path):
    out = _write_stage(tmp_path)
    (out / 'KPT.info').unlink()
    result = extract_abacus_position_dipole(tmp_path)
    assert result['kpoint_source'].endswith('istate.info')
    path = out / 'istate.info'
    path.write_text(path.read_text().replace('(0 0 0)', '(0.5 0 0)'))
    with pytest.raises(ValueError, match='Gamma-point'):
        extract_abacus_position_dipole(tmp_path)


def test_molecular_insulation_gate_uses_recorded_gamma_not_band_path(tmp_path, monkeypatch):
    import json
    from zstar.workflow import _run_insulation_gate

    out = _write_stage(tmp_path)
    monkeypatch.setattr('zstar.workflow._run_shell',
                        lambda *args, **kwargs: pytest.fail('PYATB must not run for a molecular gap'))
    kwargs = dict(pyatb_input='pyatb_input', pyatb_command='pyatb', gap_mode='path',
                  dimensionality=0, mp_density=0.08, min_gap_eV=0.01,
                  env={}, log_path=tmp_path / 'gate.log', dry_run=False)
    result = _run_insulation_gate(tmp_path, **kwargs)
    assert result.sampling == 'scf-gamma'
    assert result.path_gap_eV is None and result.bz_gap_eV is None
    report = json.loads((tmp_path / 'zstar_insulation.json').read_text())
    assert report['insulating'] and report['sampling'] == 'scf-gamma'
    (out / 'KPT.info').write_text('nkstot now = 1\nKPOINTS DIRECT_X DIRECT_Y DIRECT_Z WEIGHT\n'
                                  '1 0.5 0 0 1\n')
    with pytest.raises(ValueError, match='Gamma-point'):
        _run_insulation_gate(tmp_path, **kwargs)
    assert json.loads((tmp_path / 'zstar_insulation.json').read_text())['status'] == 'failed'


def test_experimental_ensemble_keeps_sources_and_detects_mismatch(tmp_path, monkeypatch):
    from zstar import molecular_position
    monkeypatch.setattr('zstar.shared_response.read_structure', lambda path: str(path))
    monkeypatch.setattr('zstar.shared_response.actual_displacement',
                        lambda ref, displaced: (0, np.array([.01, 0, 0])))
    manifest = {'dimension': 0, 'stages': [{'name': 'disp-001', 'atom': 0,
                                             'displacement_A': [.01, 0, 0]}]}
    def extract(stage):
        return {'method': 'test', 'dipole_e_angstrom': [1.01 if stage.name == 'disp-001' else 1., 0, 0],
                'occupied_bands': 1, 'ionic_valence_by_species': {'He': 2},
                'pseudopotential_sha256_by_species': {'He': 'abcd'},
                'orbital_sha256_by_species': {'He': 'ef01'},
                'electronic_settings': {'ecutwfc': '100'}}
    monkeypatch.setattr(molecular_position, 'extract_abacus_position_dipole', extract)
    changes, report = experimental_position_responses(tmp_path, manifest)
    np.testing.assert_allclose(changes, [[.01, 0, 0]])
    assert not report['accuracy_certified']
    def mismatch(stage):
        result = extract(stage)
        if stage.name == 'disp-001':
            result['pseudopotential_sha256_by_species'] = {'He': 'different'}
        return result
    monkeypatch.setattr(molecular_position, 'extract_abacus_position_dipole', mismatch)
    with pytest.raises(ValueError, match='pseudopotential_sha256_by_species'):
        experimental_position_responses(tmp_path, manifest)


def test_position_apt_diagnostic_never_projects_or_writes_production_outputs(tmp_path, monkeypatch):
    from zstar import molecular_position
    from phonopy.structure.atoms import PhonopyAtoms
    atoms = PhonopyAtoms(symbols=['He'], cell=np.eye(3) * 10,
                         scaled_positions=[[.5, .5, .5]])
    monkeypatch.setattr('zstar.shared_response.read_structure', lambda path: atoms)
    monkeypatch.setattr('zstar.shared_response.make_phonopy', lambda *a, **k: None)
    monkeypatch.setattr('zstar.shared_response.symmetry_operations',
                        lambda *a, **k: [(np.eye(3), np.array([0]))])
    stages = [{'name': f'disp-{i+1:03d}', 'atom': 0, 'displacement_A': row.tolist()}
              for i, row in enumerate(np.eye(3) * .01)]
    monkeypatch.setattr(molecular_position, 'experimental_position_responses',
                        lambda root, manifest: ([np.array(s['displacement_A']) * 4 for s in stages],
                                                {'method': 'synthetic', 'accuracy_certified': False}))
    report = diagnose_position_apt(tmp_path, {'dimension': 0, 'symprec_A': 1e-5, 'stages': stages},
                                   absolute_sum_tolerance_e=.05, relative_projection_tolerance=.1)
    assert report['status'] == 'diagnostic_only'
    assert report['sum_rule_diagnostics']['sum_consistency'] == 'fail'
    np.testing.assert_allclose(report['raw_apt_e'][0], np.eye(3)*4)
    assert not report['independent_accuracy_validated']
    assert not (tmp_path/'BEC.dat').exists()
