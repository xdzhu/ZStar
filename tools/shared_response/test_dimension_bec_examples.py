from pathlib import Path

import pytest

from tools.shared_response.verify_one_dimensional_example import verify


@pytest.mark.parametrize('name', ['BN_9_0', 'Sb2S3'])
def test_response_only_bundle_does_not_claim_spectral_validation(name):
    root = Path(__file__).resolve().parents[2]
    case = root / 'examples/1D_Nanowire' / name
    result = verify(case, archive=True, response_only=True)
    assert result['verified']
    assert not result['spectra_verified']
    assert result['evidence_files_verified'] > 0
    assert 'IR_spectrum' not in result['maximum_errors']
    assert 'Gamma_frequency_THz' in result['maximum_errors']
    with pytest.raises(FileNotFoundError, match='ir_spectrum.dat'):
        verify(case)
