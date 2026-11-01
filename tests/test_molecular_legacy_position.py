import json

import numpy as np
import pytest

from tests.test_shared_response import make_stru
from zstar.molecular_legacy import collect_legacy_position_apts
from zstar.shared_response import read_structure, write_structure


@pytest.mark.parametrize('charge', [0.0, 4.0])
def test_legacy_position_path_checks_raw_apt_before_projection(tmp_path, monkeypatch, charge):
    source = tmp_path / 'input.stru'
    make_stru(source)
    root = tmp_path / 'legacy'
    reference = root / '0.no-move'
    reference.mkdir(parents=True)
    (reference / 'STRU').write_text(source.read_text())
    atoms = read_structure(reference / 'STRU')
    for axis, name in enumerate('xyz'):
        for sign, factor in (('+', 1), ('-', -1)):
            directory = root / '1.Si' / (name + sign)
            directory.mkdir(parents=True)
            moved = atoms.copy()
            moved.positions = atoms.positions + np.eye(3)[axis] * factor * 0.010583544218
            write_structure(reference / 'STRU', directory / 'STRU', moved)

    def fake_position(stage):
        from zstar.abacus_assets import sha256_file
        moved = read_structure(stage / 'STRU')
        delta = moved.positions[0] - atoms.positions[0]
        return {'dipole_e_angstrom': (charge * delta).tolist(), 'occupied_bands': 1,
                'ionic_valence_by_species': {'Si': 2}, 'pseudopotential_sha256_by_species': {},
                'orbital_sha256_by_species': {}, 'electronic_settings': {},
                'source_sha256': {str(stage / 'STRU'): sha256_file(stage / 'STRU')}}
    monkeypatch.setattr('zstar.molecular_legacy.extract_abacus_position_dipole', fake_position)
    if charge:
        with pytest.raises(ValueError, match='before projection'):
            collect_legacy_position_apts(root)
        assert not (root / 'BEC.dat').exists()
        assert (root / '.zstar/legacy_molecular_apt_validation.pending').exists()
    else:
        result = collect_legacy_position_apts(root)
        assert result['natoms_calculated'] == 1
        assert not result['independent_accuracy_validated']
        assert len(result['displacements']) == 6
        assert np.linalg.norm(result['displacements'][0]['displacement_A']) == pytest.approx(0.010583544218)
        assert (root / 'BEC.dat').is_file()
        receipt = json.loads((root / '.zstar/legacy_molecular_apt_validation.json').read_text())
        assert receipt['sum_consistency'] == 'pass'
        assert not (root / '.zstar/legacy_molecular_apt_validation.pending').exists()
        from zstar.molecular_apt_validation import verify_legacy_molecular_apt_receipt
        assert verify_legacy_molecular_apt_receipt(root)['sum_consistency'] == 'pass'
        from zstar.response_schema import response_record_from_abacus_files
        record = response_record_from_abacus_files(root / 'BEC.dat', dimensionality=0)
        assert record.provenance['independent_accuracy_validated'] is False
        (root / 'BEC.dat').write_text('changed')
        with pytest.raises(ValueError, match='output changed'):
            verify_legacy_molecular_apt_receipt(root)
