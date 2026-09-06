import numpy as np
import pytest

from zstar.spectra import GammaModes
from tools.shared_response.one_dimensional_spectra import rigid_mode_audit


def make_modes(phase=1):
    masses = np.array([10., 14., 32.])
    positions = np.array([[1., 0, 0], [-1., .5, 0], [0, -1., 1.]])
    centered = positions - np.average(positions, axis=0, weights=masses)
    weight = np.sqrt(masses)[:, None]
    basis = [np.broadcast_to(x, positions.shape) * weight for x in np.eye(3)]
    basis.append(np.cross([0., 0., 1.], centered) * weight)
    q, _ = np.linalg.qr(np.array([x.ravel() for x in basis]).T, mode='complete')
    return GammaModes(frequencies_thz=np.r_[np.zeros(4), np.arange(1., 6.)],
                      eigenvectors=(phase * q.T).reshape(9, 3, 3), masses_amu=masses,
                      lattice_angstrom=np.diag([20., 20., 4.]),
                      symbols=('B', 'N', 'S'), positions_fractional=positions / [20., 20., 4.])


@pytest.mark.parametrize('phase', [1., -1., 1j])
def test_rigid_mode_identification_is_mass_weighted_and_phase_invariant(phase):
    audit = rigid_mode_audit(make_modes(phase))
    assert [r['mode'] for r in audit if r['classified_rigid']] == [1, 2, 3, 4]
    np.testing.assert_allclose([r['rigid_overlap'] for r in audit], [1] * 4 + [0] * 5, atol=1e-14)
