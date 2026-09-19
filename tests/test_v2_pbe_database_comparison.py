import numpy as np
import pytest
import json
from pathlib import Path

from tools.compare_v2_pbe_database import tensor_comparison, compare_completed_result, space_group_number


def test_full_tensor_comparison_keeps_all_components_and_absolute_zero_errors():
    reference = np.zeros((3, 6))
    reference[2, 0] = -.58
    computed = reference.copy()
    computed[0, 0] = 1e-5
    computed[2, 0] = -.581
    result = tensor_comparison(computed, reference)
    assert len(result['components']) == 18
    assert result['components'][0]['absolute_relative_difference_percent'] is None
    assert result['components'][12]['absolute_relative_difference_percent'] == pytest.approx(100*.001/.58)
    assert result['zero_reference_max_absolute_C_m2'] == 1e-5


def test_tensor_comparison_rejects_incomplete_or_nonfinite_values():
    with pytest.raises(ValueError, match='3 x 6'):
        tensor_comparison(np.ones(3), np.zeros((3,6)))
    bad = np.zeros((3,6)); bad[0,0] = np.nan
    with pytest.raises(ValueError, match='finite'):
        tensor_comparison(bad, np.zeros((3,6)))


def completed_native(tmp_path, *, d=True, functional='PBE'):
    e = np.zeros((3,6)); e[2,2] = 1.4
    c = np.eye(6)*300
    tensors = {'piezoelectric_total_C_m2':e.tolist(), 'elastic_relaxed_GPa':c.tolist()}
    if d:
        tensors['piezoelectric_d_pm_V'] = (e/300*1000).tolist()
    result = tmp_path/'native.json'
    result.write_text(json.dumps({'backend':'vasp','dimensionality':3,'normalization':'bulk',
                                 'tensors':tensors,'diagnostics':{}}))
    provenance = tmp_path/'continuation.json'
    provenance.write_text(json.dumps({'functional':functional,'reference_gate':{
        'space_group':186,'force_max_eV_A':1e-5,'stress_max_kbar':.1,'gap_eV':2.}}))
    spec = {'material':'AlN','backend':'vasp','result':str(result), 'continuation':str(provenance),
            'coordinate_and_domain_verified':True, 'coordinate_audit_evidence':'explicit structural audit'}
    refs = {'AlN':{'space_group':186,'material_id':'mp-661','e_C_m2':e.tolist()}}
    return spec, refs


def completed_central_strain(tmp_path, *, force=1e-5, symmetry_residual=1e-7):
    e = np.zeros((3, 6)); e[2, 2] = 1.4
    c = np.eye(6) * 300
    d = e / 300 * 1000
    checks = {name: {
        'electronic_converged': True,
        'force_max_eV_per_A': force,
        'gap_eV': 2.0,
        'actual_NBANDS': 32,
        'space_group': 186,
    } for name in ['reference'] + [
        f'strain-{index:03d}-{sign}'
        for index in range(1, 7) for sign in ('minus', 'plus')
    ]}
    fit = {'complete': True, 'input_rank': 6, 'fit_rank': 18, 'allowed_rank': 18}
    elastic_fit = {'complete': True, 'input_rank': 6, 'fit_rank': 36, 'allowed_rank': 36}
    result = tmp_path / 'central.json'
    result.write_text(json.dumps({
        'schema': 'zstar-v2-VASP-independent-central-strain-result/1',
        'backend': 'VASP 6.3.2', 'functional': 'PBE',
        'dimensionality': 3, 'periodic_axes': ['x', 'y', 'z'],
        'space_group': 'P6_3mc',
        'finite_difference': {'method': 'central', 'amplitude': .005, 'order': 'O(h^2)'},
        'stage_count': 13, 'relaxation_stage_count': 13,
        'piezoelectric_proper_C_per_m2': e.tolist(),
        'elastic_GPa': c.tolist(), 'piezoelectric_d_pm_per_V': d.tolist(),
        'fit_diagnostics': {'piezoelectric_raw': fit, 'elastic': elastic_fit},
        'symmetry_diagnostics': {
            'piezoelectric_proper': {'projection_residual_relative': symmetry_residual},
            'elastic': {'projection_residual_relative': symmetry_residual},
        },
        'mechanical_stability': {'stable_within_tolerance': True},
        'branch_residuals': [0.0] * 13,
        'reference': {'stress_raw_kbar': np.zeros((3, 3)).tolist(), 'checks': checks['reference']},
        'stage_checks': checks, 'native_d_gate_changed': False, 'native_result_replaced': False,
    }))
    provenance = tmp_path / 'central-prepared.json'
    provenance.write_text(json.dumps({'settings': {'central_engineering_strain': .005}}))
    spec = {'material': 'AlN', 'backend': 'vasp-central-strain',
            'result': str(result), 'continuation': str(provenance),
            'coordinate_and_domain_verified': True,
            'coordinate_audit_evidence': 'exact P63mc projection with retained domain and site order'}
    refs = {'AlN': {'space_group': 186, 'material_id': 'mp-661', 'e_C_m2': e.tolist()}}
    return spec, refs


def test_complete_native_result_compares_all_18_components_and_keeps_d33_separate(tmp_path):
    spec, refs = completed_native(tmp_path)
    result = compare_completed_result(spec,refs)
    assert result['quality_issues'] == []
    assert len(result['comparison']['components']) == 18
    assert result['d33_pm_V'] == pytest.approx(1.4/300*1000)
    assert result['d33_database_value'] is None
    assert result['d33_database_difference_percent'] is None


def test_missing_d_is_not_full_e_c_d_acceptance(tmp_path):
    spec, refs = completed_native(tmp_path,d=False)
    result = compare_completed_result(spec,refs)
    assert result['status'] == 'scientific_gate_pending'
    assert result['d33_pm_V'] is None
    assert len(result['comparison']['components']) == 18


def test_complete_independent_central_strain_result_is_compared_without_replacing_native(tmp_path):
    spec, refs = completed_central_strain(tmp_path)
    result = compare_completed_result(spec, refs)
    assert result['quality_issues'] == []
    assert result['status'] == 'internally_consistent_external_difference_reported'
    assert result['backend'] == 'vasp-central-strain'
    assert result['d33_pm_V'] == pytest.approx(1.4 / 300 * 1000)
    assert len(result['comparison']['components']) == 18
    assert result['quality_diagnostics']['route'].endswith('not native displaced-atoms d')


def test_independent_central_strain_quality_gates_remain_visible(tmp_path):
    spec, refs = completed_central_strain(tmp_path, force=2e-4, symmetry_residual=2e-3)
    result = compare_completed_result(spec, refs)
    assert result['status'] == 'scientific_gate_pending'
    assert any('force gate failed' in issue for issue in result['quality_issues'])
    assert any('symmetry projection' in issue for issue in result['quality_issues'])


def test_independent_central_strain_cannot_claim_to_replace_native_gate(tmp_path):
    spec, refs = completed_central_strain(tmp_path)
    result_path = Path(spec['result'])
    payload = json.loads(result_path.read_text())
    payload['native_result_replaced'] = True
    result_path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='must not replace'):
        compare_completed_result(spec, refs)


def test_explicit_frame_rotation_uses_d_stress_not_e_strain_convention(tmp_path):
    spec, refs = completed_native(tmp_path)
    angle = .23
    spec['frame_rotation_old_to_new'] = [[np.cos(angle),0,np.sin(angle)],
                                        [0,1,0],[-np.sin(angle),0,np.cos(angle)]]
    result = compare_completed_result(spec,refs)
    assert result['quality_issues'] == []
    assert result['d_e_C_closure_max_C_m2'] < 1e-12
    assert not np.allclose(result['e_C_m2'],result['e_C_m2_original_frame'])


def test_additional_result_refuses_pbesol_or_missing_axis_domain_audit(tmp_path):
    spec, refs = completed_native(tmp_path,functional='PBEsol')
    with pytest.raises(ValueError,match='Not a PBE'):
        compare_completed_result(spec,refs)
    spec, refs = completed_native(tmp_path)
    spec['coordinate_and_domain_verified'] = False
    with pytest.raises(ValueError,match='coordinate/domain'):
        compare_completed_result(spec,refs)


def test_collector_space_group_symbol_is_not_a_numeric_phase_mismatch():
    assert space_group_number('P6_3mc') == 186
    assert space_group_number('P4mm') == 99
    assert space_group_number(1) == 1
    with pytest.raises(ValueError, match='Unknown/ambiguous'):
        space_group_number('unknown')


def test_abacus_collector_symbol_and_full_rank_can_be_compared(tmp_path):
    spec, refs = completed_native(tmp_path)
    e = np.zeros((3,6)); e[2,2] = 1.4
    audit = {'status':'available', 'quantities': {
        'piezoelectric_proper': {'status':'consistent_mixed_tolerance'},
        'elastic': {'status':'consistent'}}}
    payload = {'functional':'pbe','dimensionality':{'value':3},
               'observed_reference_space_group':'P6_3mc',
               'piezoelectric_proper_C_per_m2':e.tolist(),
               'elastic_GPa':(np.eye(6)*300).tolist(),
               'piezoelectric_d_pm_per_V':(e/300*1000).tolist(),
               'mechanical_stable_positive_definite':True,
               'reference_force_max_eV_per_angstrom':1e-5,
               'piezoelectric_proper_diagnostics':{'complete':True,'input_rank':6,'fit_rank':18,'allowed_rank':18},
               'elastic_diagnostics':{'complete':True,'input_rank':6,'fit_rank':21,'allowed_rank':21},
               'stage_band_gaps_eV':{'reference':{'insulating':True}},
               'symmetry_response_audit':audit}
    Path(spec['result']).write_text(json.dumps(payload))
    Path(spec['continuation']).write_text(json.dumps({'functional':'PBE','space_group':186}))
    spec['backend']='abacus'
    assert compare_completed_result(spec,refs)['quality_issues'] == []
    payload['piezoelectric_proper_diagnostics']['complete']=False
    Path(spec['result']).write_text(json.dumps(payload))
    assert compare_completed_result(spec,refs)['status'] == 'scientific_gate_pending'
    Path(spec['continuation']).write_text(json.dumps({'functional':'PBE','space_group':99}))
    with pytest.raises(ValueError, match='differs from continuation'):
        compare_completed_result(spec,refs)
