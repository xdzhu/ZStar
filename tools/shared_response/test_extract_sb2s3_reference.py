import numpy as np
import pytest

from tools.shared_response.extract_sb2s3_reference import rotation_audit


def fixture_text(tmp_path):
    structure = tmp_path / 'structure.f34'
    structure.write_text('1 1 1\n4 0 0\n0 30 0\n0 0 30\n0\n2\n'
                         '16 0 1 0\n16 0 -1 0\n')
    rows = ['NORMAL MODES NORMALIZED TO CLASSICAL AMPLITUDES (IN BOHR)',
            'FREQ(CM**-1) 0 0 0 4 5 6']
    for i, vector in enumerate(np.eye(6)):
        label = f'AT. {i // 3 + 1} S ' if i % 3 == 0 else ''
        rows.append(label + 'XYZ'[i % 3] + ' ' + ' '.join(map(str, vector)))
    return '\n'.join(rows), structure


def test_rotation_overlap_and_numbering(tmp_path):
    text, structure = fixture_text(tmp_path)
    audit = rotation_audit(text, structure)
    assert [row['mode'] for row in audit['modes']] == list(range(1, 7))
    assert [row['axial_rotation_overlap'] for row in audit['modes']] == pytest.approx(
        [0, 0, .5, 0, 0, .5])
    assert not audit['filtering_applied']


def test_reject_component_reordering(tmp_path):
    text, structure = fixture_text(tmp_path)
    with pytest.raises(ValueError, match='component ordering'):
        rotation_audit(text.replace('AT. 1 S X', 'AT. 1 S Z'), structure)
