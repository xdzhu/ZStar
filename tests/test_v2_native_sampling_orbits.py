import numpy as np
import pytest
from tools.audit_v2_native_sampling_orbits import orbit_span
from zstar.v2.structure import StructureSpec, analyze_space_group, displacement_representation


def representations():
    parent = StructureSpec(np.array([[3., 0., 0.], [-1.5, 1.5*np.sqrt(3), 0.], [0., 0., 5.]]),
                           np.array([[1/3, 2/3, 0.], [1/3, 2/3, .38]]), ('Ga', 'N'))
    report = analyze_space_group(parent)
    assert report.status == 'stable'
    return [displacement_representation(report, i) for i in range(report.operation_count)]


def test_full_3d_atomic_span_recovered_by_existing_symmetry():
    vectors = .01*np.eye(6)[[0, 2, 3, 5]]
    result = orbit_span(vectors, representations(), 6, 3e-5)
    assert result['raw_rank'] == 4
    assert result['orbit_expanded_rank'] == 6
    assert result['input_span_complete']


def test_inequivalent_missing_atom_cannot_be_invented():
    result = orbit_span(.01*np.eye(6)[[0, 2]], representations(), 6, 3e-5)
    assert result['orbit_expanded_rank'] == 3
    assert not result['input_span_complete']


def test_serialization_noise_not_false_full_rank():
    vectors = np.array([[.01, 1e-7, 0.], [.01, -1e-7, 0.]])
    result = orbit_span(vectors, [np.eye(3)], 3, 3e-5)
    assert result['orbit_expanded_rank'] == 1
    with pytest.raises(ValueError):
        orbit_span(np.full((2, 3), np.nan), [np.eye(3)], 3, 3e-5)
