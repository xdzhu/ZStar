import numpy as np

from tools.diagnose_molecular_cube_origin import shifted_apt


def test_fixed_origin_shift_uses_electron_count_derivative_and_preserves_ionic_sign():
    displacements = np.vstack((np.eye(3), -np.eye(3))) * .01
    derivative = np.array([.01, -.02, .03])
    counts = 8 + displacements @ derivative
    raw = np.eye(3)
    origin = np.array([4., 2., -1.])
    shifted, obtained = shifted_apt(raw, origin, displacements, counts)
    np.testing.assert_allclose(obtained, derivative, atol=1e-12)
    np.testing.assert_allclose(shifted, raw + np.outer(origin, derivative), atol=1e-12)
