import json

import pytest

from zstar.abacus_assets import sha256_file
from zstar.molecular_apt_validation import PENDING, RECEIPT, verify_molecular_apt_receipt


def test_receipt_rejects_missing_stale_and_pending_sources(tmp_path):
    with pytest.raises(ValueError, match='unverified'):
        verify_molecular_apt_receipt(tmp_path)
    source = tmp_path/'source'
    source.write_text('valid source')
    names = ['shared_response.json', 'response_fit.json', 'BEC.dat', 'qpoints.yaml']
    for name in names:
        (tmp_path/name).write_text(name)
    receipt = {'schema': 'zstar-molecular-apt-validation', 'version': 1,
               'sum_consistency': 'pass', 'method': 'abacus_r0_position_expectation_experimental',
               'independent_accuracy_validated': False,
               'source_sha256': {str(source.resolve()): sha256_file(source)},
               'output_sha256': {name: sha256_file(tmp_path/name) for name in names}}
    (tmp_path/RECEIPT).parent.mkdir()
    (tmp_path/RECEIPT).write_text(json.dumps(receipt))
    assert verify_molecular_apt_receipt(tmp_path)['sum_consistency'] == 'pass'
    (tmp_path/PENDING).write_text('pending')
    with pytest.raises(ValueError, match='incomplete'):
        verify_molecular_apt_receipt(tmp_path)
    (tmp_path/PENDING).unlink()
    source.write_text('changed')
    with pytest.raises(ValueError, match='source changed'):
        verify_molecular_apt_receipt(tmp_path)


def test_receipt_rejects_changed_bec_even_with_valid_source(tmp_path):
    source = tmp_path/'source'
    source.write_text('source')
    outputs = {}
    for name in ('shared_response.json', 'response_fit.json', 'BEC.dat', 'qpoints.yaml'):
        path = tmp_path/name
        path.write_text(name)
        outputs[name] = sha256_file(path)
    (tmp_path/RECEIPT).parent.mkdir()
    (tmp_path/RECEIPT).write_text(json.dumps({
        'schema': 'zstar-molecular-apt-validation', 'version': 1,
        'sum_consistency': 'pass', 'method': 'abacus_r0_position_expectation_experimental',
        'independent_accuracy_validated': False,
        'source_sha256': {str(source.resolve()): sha256_file(source)}, 'output_sha256': outputs}))
    (tmp_path/'BEC.dat').write_text('other tensor')
    with pytest.raises(ValueError, match='output changed'):
        verify_molecular_apt_receipt(tmp_path)
