import numpy as np
import pytest

from zstar.molecular_response_quality import assess_raw_apt, check_raw_apt_consistency


def test_missing_electronic_response_is_visible_before_projection():
    raw = np.zeros((42, 3, 3))
    raw[:20, 0, 0] = 4
    raw[20:, 0, 0] = 1
    saved = raw.copy()
    result = assess_raw_apt(raw)
    assert result['sum_residual_frobenius_e'] == pytest.approx(102)
    assert result['uniform_projection_relative'] > .8
    assert not result['projection_applied']
    assert not result['accuracy_certified']
    np.testing.assert_array_equal(raw, saved)


def test_charged_translation_identity_and_nonfinite_input():
    tensors = np.array([np.eye(3), -0.5 * np.eye(3)])
    assert assess_raw_apt(tensors, net_charge_e=.5)['sum_residual_frobenius_e'] == 0
    assert assess_raw_apt(tensors)['sum_residual_frobenius_e'] > 0
    with pytest.raises(ValueError, match='finite'):
        assess_raw_apt(np.full((1, 3, 3), np.nan))
    with pytest.raises(ValueError, match='shape'):
        assess_raw_apt(np.zeros((3, 3)))


def test_zero_response_does_not_divide_by_zero_or_claim_accuracy():
    result = assess_raw_apt(np.zeros((2, 3, 3)))
    assert result['uniform_projection_relative'] is None
    assert not result['accuracy_certified']


def test_explicit_quality_thresholds_do_not_hide_missing_electrons():
    raw = np.zeros((42, 3, 3))
    raw[:20, 0, 0] = 4
    raw[20:, 0, 0] = 1
    report = check_raw_apt_consistency(raw, absolute_sum_tolerance_e=.05,
                                       relative_projection_tolerance=.1)
    assert report['sum_consistency'] == 'fail'
    assert not report['independent_accuracy_validated']
    near_zero = check_raw_apt_consistency(np.ones((2, 3, 3)) * 1e-6,
                                          absolute_sum_tolerance_e=.05,
                                          relative_projection_tolerance=.1)
    assert near_zero['sum_consistency'] == 'pass'
    assert not near_zero['accuracy_certified']
    charged_zero = check_raw_apt_consistency(np.zeros((2, 3, 3)), net_charge_e=1,
                                             absolute_sum_tolerance_e=.05,
                                             relative_projection_tolerance=.1)
    assert charged_zero['sum_consistency'] == 'fail'
    with pytest.raises(ValueError, match='nonnegative'):
        check_raw_apt_consistency(raw, absolute_sum_tolerance_e=-1,
                                  relative_projection_tolerance=.1)
