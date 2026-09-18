from dataclasses import replace
from pathlib import Path
import warnings

import numpy as np
import pytest

from zstar.dimensions import DimensionSpec
from zstar.v2 import (
    ResponseDocument, TensorQuantity, fit_finite_difference_document,
    proper_piezoelectric_response, prepare_abacus_strain_ensemble,
)


def _document(h=0.005):
    x = np.vstack((np.zeros(6), -h*np.eye(6), h*np.eye(6)))
    # Serialized oblique cells can carry roundoff in a preceding component.
    x[8, 0] = -1e-16
    p0 = np.array([0.1, -0.2, 0.3])
    jacobian = np.arange(18).reshape(3, 6)/10
    curvature = np.ones((3, 6))*4
    p = p0 + x@jacobian.T + x**2@curvature.T
    names = ['reference'] + [f'strain-{i}-' for i in range(6)] + [f'strain-{i}+' for i in range(6)]
    quantities = (
        TensorQuantity(name='strain_vector', values=x, unit='engineering_strain',
                       axes=('stage','voigt_engineering'),
                       provenance={'stage_names': names}),
        TensorQuantity(name='polarization_cartesian', values=p, unit='C/m^2',
                       axes=('stage','cartesian'),
                       provenance={'stage_names': names, 'branch_matched': True}),
    )
    return ResponseDocument(backend='synthetic', dimensionality=DimensionSpec(3),
                            quantities=quantities, provenance={'source':'synthetic'}), jacobian, curvature, p0


def test_default_central_cancels_quadratic_response_without_warning():
    doc, j, _, p0 = _document()
    with warnings.catch_warnings(record=True) as caught:
        result = fit_finite_difference_document(doc, include_proper_piezoelectric=True)
    assert not caught
    np.testing.assert_allclose(result.quantity('piezoelectric_proper').values,
                               proper_piezoelectric_response(j,p0).proper, atol=1e-12)
    assert result.metadata['finite_difference']['method'] == 'central'
    assert result.metadata['finite_difference']['truncation_error_order'] == 'O(h^2)'


def test_forward_is_explicit_warns_and_selects_actual_positive_vectors():
    doc, j, curvature, p0 = _document()
    with pytest.warns(UserWarning, match=r'O\(h\).*O\(h\^2\).*recommended'):
        result = fit_finite_difference_document(doc, method='forward', include_proper_piezoelectric=True)
    np.testing.assert_allclose(result.quantity('piezoelectric_proper').values,
                               proper_piezoelectric_response(j+0.005*curvature,p0).proper, atol=1e-12)
    assert result.quantity('strain_vector').shape == (7,6)
    assert doc.quantity('strain_vector').shape == (13,6)
    assert result.metadata['finite_difference']['truncation_error_order'] == 'O(h)'
    assert result.quantity('piezoelectric_proper').provenance['finite_difference']['recommendation'] == 'central'
    restored = ResponseDocument.from_dict(result.to_dict())
    assert restored.metadata['finite_difference']['warning']


@pytest.mark.parametrize('method', ['backward','auto',None])
def test_unsupported_method_is_rejected(method):
    doc, *_ = _document()
    with pytest.raises(ValueError, match='method'):
        fit_finite_difference_document(doc, method=method)


def test_central_never_silently_falls_back_to_forward():
    doc, *_ = _document()
    one_sided = replace(doc, quantities=tuple(
        replace(q, values=q.values[[0,7,8,9,10,11,12]],
                provenance={**q.provenance,'stage_names':['reference']+[f'plus{i}' for i in range(6)]})
        for q in doc.quantities))
    with pytest.raises(ValueError, match='unique'):
        fit_finite_difference_document(one_sided)
    with pytest.warns(UserWarning):
        result = fit_finite_difference_document(one_sided,method='forward')
    assert result.quantity('piezoelectric_raw').diagnostics['complete']


def test_forward_rejects_incomplete_rank():
    doc, *_ = _document()
    incomplete = replace(doc, quantities=tuple(
        replace(q,values=q.values[:8],provenance={**q.provenance,'stage_names':q.provenance['stage_names'][:8]})
        for q in doc.quantities))
    with pytest.warns(UserWarning), pytest.raises(ValueError,match='rank-deficient'):
        fit_finite_difference_document(incomplete,method='forward')


@pytest.mark.parametrize('method,count', [('central',12),('forward',6)])
def test_preparation_method_is_persisted_without_running_calculator(tmp_path,method,count):
    case=Path('examples/3D_Bulk/tetragonal_BaTiO3/inputs').resolve()
    with warnings.catch_warnings(record=True) as caught:
        result=prepare_abacus_strain_ensemble(tmp_path/method,structure=case/'STRU',
                                             input_template=case/'INPUT',kpt_template=case/'KPT',method=method)
    ensemble=result['ensemble']
    assert len(ensemble.stages)==count
    assert ensemble.metadata['finite_difference']['method']==method
    policy_warnings = [item for item in caught if 'Forward finite differences' in str(item.message)]
    assert bool(policy_warnings)==(method=='forward')
    if method=='forward':
        assert all(stage.sign=='+' for stage in ensemble.stages)


def test_unequal_pair_weights_do_not_claim_central_error_order():
    doc, *_ = _document()
    weights=np.ones(13); weights[1]=2
    with pytest.raises(ValueError,match='equal weights'):
        fit_finite_difference_document(doc,sample_weights=weights)


def test_actual_amplitudes_not_nominal_step_control_forward_slope():
    doc, j, curvature, p0 = _document()
    h = np.arange(1,7)*0.001
    x = np.vstack((np.zeros(6), -np.diag(h), np.diag(h)))
    changed = replace(doc, quantities=(
        replace(doc.quantity('strain_vector'), values=x),
        replace(doc.quantity('polarization_cartesian'), values=p0+x@j.T+x**2@curvature.T),
    ))
    with pytest.warns(UserWarning):
        result = fit_finite_difference_document(changed,method='forward')
    np.testing.assert_allclose(result.quantity('piezoelectric_raw').values,j+curvature*h,atol=1e-12)


def test_asymmetric_actual_pair_is_rejected_even_if_labels_look_paired():
    doc, *_ = _document()
    x = doc.quantity('strain_vector').values.copy(); x[7,0] *= 1.01
    changed = replace(doc,quantities=(replace(doc.quantity('strain_vector'),values=x),doc.quantity('polarization_cartesian')))
    with pytest.raises(ValueError,match='unique'):
        fit_finite_difference_document(changed)
