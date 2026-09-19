"""Full three-dimensional paired-response audit controls, not calculator tests."""
import numpy as np
import pytest

from tools.audit_v2_completed_backend_pairs import accepted_native_record, compare_pair, difference, tensors
from zstar.v2.mechanical import rotate_elastic_tensor, rotate_piezoelectric_tensor, stress_representation


def sample():
    c = np.array([[200, 50, 40, 0, 0, 0], [50, 180, 30, 0, 0, 0],
                  [40, 30, 150, 0, 0, 0], [0, 0, 0, 60, 0, 0],
                  [0, 0, 0, 0, 55, 0], [0, 0, 0, 0, 0, 50]], float)
    e = np.array([[.1, .2, .3, .4, .5, .6], [.2, -.1, .4, -.3, .7, -.2],
                  [-.5, -.6, 1.5, .3, .2, -.1]])
    return e, c


def test_full_3d_algebraic_d_never_promotes_missing_native_d():
    e, c = sample()
    _, _, d = tensors(e, c)
    ab = dict(e_C_m2=e, C_GPa=c, d_pm_V=d)
    native = dict(e_C_m2=e, C_GPa=c, d_pm_V=None, status='scientific_gate_pending', quality_issues=['raw warning'])
    result = compare_pair(ab, native)
    assert not result['native_d_emitted_in_source'] and not result['native_d_acceptance_changed']
    assert result['native_source_status'] == 'scientific_gate_pending'
    assert result['native_source_quality_issues'] == ['raw warning']
    assert result['d']['max_absolute_difference'] == pytest.approx(0)
    assert native['d_pm_V'] is None
    np.testing.assert_allclose(d@c/1000, e, atol=1e-14)


def test_full_matrix_difference_and_zero_comparator_no_infinite_percent():
    e, _ = sample()
    result = difference(e, np.zeros((3, 6)), 'C/m^2', (3, 6), .02, .02)
    assert result['frobenius_relative_difference_percent'] is None
    assert result['largest_difference_index_zero_based'] == [2, 2]
    np.testing.assert_array_equal(result['signed_difference'], e)


@pytest.mark.parametrize('bad', [np.zeros((6, 6)), np.diag([1, 1, 1, 1, 1, -1]),
                              np.eye(6)+np.eye(6, k=1)])
def test_reject_singular_unstable_and_nonmajor_C(bad):
    e, _ = sample()
    with pytest.raises(ValueError):
        tensors(e, bad)


def test_wrong_shear_or_unit_scale_d_fails_complete_roundtrip():
    e, c = sample()
    _, _, d = tensors(e, c)
    wrong = d.copy()
    wrong[:, 3:] *= 2
    with pytest.raises(ValueError):
        tensors(e, c, wrong)
    with pytest.raises(ValueError):
        tensors(e, c, d/1000)


def test_generic_3d_rotation_preserves_stress_dual_d_closure():
    e, c = sample()
    _, _, d = tensors(e, c)
    axis = np.array([1., 2., 3.]) / np.sqrt(14.)
    cross = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]],
                      [-axis[1], axis[0], 0]])
    angle = .47
    q = np.eye(3)*np.cos(angle) + (1-np.cos(angle))*np.outer(axis, axis) + np.sin(angle)*cross
    er = rotate_piezoelectric_tensor(e, q)
    cr = rotate_elastic_tensor(c, q)
    dr = q @ d @ np.linalg.inv(stress_representation(q))
    tensors(er, cr, dr)
    np.testing.assert_allclose(dr@cr/1000, er, atol=1e-14)
    # Treating d as an engineering-strain map gives the wrong shear scaling.
    with pytest.raises(ValueError):
        tensors(er, cr, rotate_piezoelectric_tensor(d, q))


def test_accepted_native_override_requires_complete_closing_tensors(tmp_path):
    import json

    e, c = sample()
    _, _, d = tensors(e, c)
    path = tmp_path / 'vasp_native_response.json'
    path.write_text(json.dumps({'tensors': {
        'piezoelectric_total_C_m2': e.tolist(),
        'elastic_relaxed_GPa': c.tolist(),
        'piezoelectric_d_pm_V': d.tolist(),
        'electromechanical_warning': 'retained diagnostic warning',
    }}), encoding='utf-8')
    record = accepted_native_record(path)
    assert record['status'] == 'accepted_native_response_override'
    assert record['quality_issues'] == ['retained diagnostic warning']
    np.testing.assert_allclose(record['d_pm_V'], d)

    path.write_text(json.dumps({'tensors': {
        'piezoelectric_total_C_m2': e.tolist(),
        'elastic_relaxed_GPa': c.tolist(),
    }}), encoding='utf-8')
    with pytest.raises(ValueError, match='lacks complete e/C/d'):
        accepted_native_record(path)
