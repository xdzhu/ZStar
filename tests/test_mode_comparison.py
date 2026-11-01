import numpy as np
import pytest

from zstar.mode_comparison import compare_gamma_modes
from zstar.spectra import GammaModes, THZ_TO_CM1


def _modes(vectors=None, positions=None, symbols=('Si', 'C')):
    return GammaModes(
        frequencies_thz=np.array([0, 0, 30, 70, 100, 200]) / THZ_TO_CM1,
        eigenvectors=(np.eye(6).reshape(6, 2, 3) if vectors is None else vectors),
        masses_amu=np.array([28.0, 12.0]), lattice_angstrom=np.diag([10., 10., 5.]),
        symbols=symbols,
        positions_fractional=(np.array([[0.4, 0.4, 0.95], [0.5, 0.5, 0.05]])
                              if positions is None else positions),
    )


def test_degenerate_rotations_are_compared_as_subspaces_without_modifying_input():
    reference = _modes()
    vectors = reference.eigenvectors.copy()
    vectors[:2] = np.einsum('ij,jab->iab', np.array([[0.6, 0.8], [-0.8, 0.6]]), vectors[:2])
    positions = np.array([[0.6, 0.4, 0.05], [0.7, 0.5, 0.15]])
    candidate = _modes(vectors=vectors, positions=positions)
    before = vectors.copy()
    result = compare_gamma_modes(reference, candidate, dimensionality=1)
    match = result['matches'][0]
    assert match['reference_modes'] == match['candidate_modes'] == [1, 2]
    assert match['subspace_overlap_score'] == pytest.approx(1)
    np.testing.assert_allclose(match['principal_overlaps'], [1, 1])
    np.testing.assert_array_equal(candidate.eigenvectors, before)
    assert not result['unmatched_reference_groups']


def test_different_geometry_and_atom_order_are_refused():
    reference = _modes()
    positions = reference.positions_fractional.copy()
    positions[1, 0] += 0.001
    with pytest.raises(ValueError, match='not the same geometry'):
        compare_gamma_modes(reference, _modes(positions=positions), dimensionality=1)
    with pytest.raises(ValueError, match='atom ordering'):
        compare_gamma_modes(reference, _modes(symbols=('C', 'Si')), dimensionality=1)


def test_nonorthogonal_eigenvectors_are_refused():
    reference = _modes()
    vectors = reference.eigenvectors.copy()
    vectors[1] = vectors[0]
    with pytest.raises(ValueError, match='orthonormal'):
        compare_gamma_modes(reference, _modes(vectors=vectors), dimensionality=1)
