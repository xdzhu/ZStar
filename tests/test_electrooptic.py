import numpy as np
import pytest

from zstar.electrooptic import electrooptic, longitudinal_raman
from zstar.spectra import ATOMIC_MASS_UNIT, ELEMENTARY_CHARGE


def test_static_electrooptic_terms():
    frequency = np.array([8.0])
    charges = np.array([[0, 0, 1.5]])
    raman = np.diag([0.4, 0.4, 0.1])[None]
    eps = 4 * np.eye(3)
    chi2 = np.zeros((3, 3, 3))
    chi2[2, 2, 2] = 24.0
    photoelastic = np.zeros((3, 3, 6))
    photoelastic[2, 2, 0] = 0.2
    piezoelectric = np.zeros((6, 3))
    piezoelectric[0, 2] = 8.0
    result = electrooptic(
        frequency, charges, raman, eps, chi2_pm_v=chi2,
        photoelastic=photoelastic, piezoelectric_pm_v=piezoelectric,
    )
    expected = (-0.1 * 1.5 * ELEMENTARY_CHARGE
                / (16 * ATOMIC_MASS_UNIT * 1e-10 * (2*np.pi*8e12)**2) * 1e12)
    assert result["ionic_fixed_strain"][2, 2, 2] == pytest.approx(expected, rel=1e-12)
    assert result["electronic_clamped_ion"][2, 2, 2] == -3.0
    assert result["total_relaxed_stress"][2, 2, 2] == pytest.approx(expected - 3 + 1.6)
    flipped = electrooptic(frequency, -charges, -raman, eps)
    np.testing.assert_allclose(flipped["ionic_fixed_strain"], result["ionic_fixed_strain"])


def test_lo_correction_distinguishes_nac_and_electronic_field():
    frequencies = [8.0, 9.5]
    charges = [[1.5, 0, 0], [0, 0, 0]]
    raman = np.array([np.eye(3), np.zeros((3, 3))])
    eps = 4 * np.eye(3)
    chi2 = np.zeros((3, 3, 3))
    chi2[0, 0, 0] = 20.0
    along_x = longitudinal_raman(frequencies, charges, raman, eps, 100.0, [1, 0, 0], chi2)
    reversed_x = longitudinal_raman(frequencies, charges, raman, eps, 100.0, [-1, 0, 0], chi2)
    without_chi2 = longitudinal_raman(frequencies, charges, raman, eps, 100.0, [1, 0, 0], chi2*0)
    across_x = longitudinal_raman(frequencies, charges, raman, eps, 100.0, [0, 0, 1], chi2)
    np.testing.assert_allclose(along_x["frequencies_THz"], without_chi2["frequencies_THz"])
    np.testing.assert_allclose(across_x["frequencies_THz"], frequencies)
    np.testing.assert_allclose(across_x["raman_derivatives"], raman)
    np.testing.assert_allclose(along_x["raman_derivatives"], reversed_x["raman_derivatives"])
    polar_mode = int(np.argmax(np.abs(along_x["mode_charges_e_sqrt_amu"][:, 0])))
    assert along_x["frequencies_THz"][polar_mode] > frequencies[0]
    assert along_x["raman_derivatives"][polar_mode, 0, 0] < 1.0


def test_full_tensor_requires_both_strain_inputs():
    with pytest.raises(ValueError, match="both photoelastic and piezoelectric"):
        electrooptic([8.0], [[1, 0, 0]], np.zeros((1, 3, 3)), np.eye(3),
                      photoelastic=np.zeros((3, 3, 6)))
