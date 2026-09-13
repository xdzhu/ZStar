import numpy as np
import pytest

from zstar.v2 import convert_piezoelectric_forms


def test_electromechanical_forms_round_trip_in_si_convention():
    c_e = np.diag([100.0, 120.0, 140.0, 50.0, 55.0, 60.0]) * 1.0e9
    epsilon_s = np.diag([8.0, 9.0, 10.0]) * 8.8541878128e-12
    e = np.zeros((3, 6))
    e[0, 0] = 0.4
    e[1, 1] = 0.5
    e[2, 2] = 1.1
    e[0, 3] = 0.2
    result = convert_piezoelectric_forms(e, c_e, epsilon_s)

    np.testing.assert_allclose(result.d, result.e @ result.s_e, rtol=1e-13, atol=1e-30)
    np.testing.assert_allclose(result.g, result.beta_t @ result.d, rtol=1e-13, atol=1e-20)
    np.testing.assert_allclose(result.h, result.beta_s @ result.e, rtol=1e-13, atol=1e-20)
    np.testing.assert_allclose(result.e, result.d @ result.c_e, rtol=1e-13, atol=1e-12)
    np.testing.assert_allclose(result.d, result.epsilon_t @ result.g, rtol=1e-13, atol=1e-20)
    np.testing.assert_allclose(result.h, result.g @ result.c_d, rtol=1e-13, atol=1e-12)
    # Residuals involving h and C^D are reported in V/m and Pa and therefore
    # need a relative tolerance; the absolute values are still retained in
    # diagnostics for provenance.
    assert result.diagnostics["e_minus_d_c_e_max"] < 1.0e-10
    assert result.diagnostics["d_minus_e_s_e_max"] < 1.0e-30
    assert result.diagnostics["d_minus_epsilon_t_g_max"] < 1.0e-20
    assert result.diagnostics["h_minus_beta_s_e_max"] < 1.0e-10


def test_electromechanical_forms_convert_relative_dielectric_and_gpa():
    e = np.zeros((3, 6))
    e[2, 2] = 1.0
    result = convert_piezoelectric_forms(
        e,
        np.eye(6) * 100.0,
        np.eye(3) * 4.0,
        elastic_unit="GPa",
        dielectric_unit="relative",
    )
    np.testing.assert_allclose(result.c_e, np.eye(6) * 100.0e9)
    np.testing.assert_allclose(result.epsilon_s, np.eye(3) * 4.0 * 8.8541878128e-12)


def test_electromechanical_forms_rejects_raw_or_ambiguous_inputs():
    with pytest.raises(ValueError, match="proper"):
        convert_piezoelectric_forms(
            np.zeros((3, 6)), np.eye(6), np.eye(3), piezoelectric_kind="raw"
        )
    with pytest.raises(ValueError, match=r"C/m\^2"):
        convert_piezoelectric_forms(
            np.zeros((3, 6)), np.eye(6), np.eye(3), piezoelectric_unit="e/angstrom^2"
        )
    nonsymmetric = np.eye(6)
    nonsymmetric[0, 1] = 0.1
    with pytest.raises(ValueError, match="symmetric"):
        convert_piezoelectric_forms(np.zeros((3, 6)), nonsymmetric, np.eye(3))


def test_electromechanical_forms_rejects_nonengineering_voigt():
    with pytest.raises(ValueError, match="engineering"):
        convert_piezoelectric_forms(
            np.zeros((3, 6)), np.eye(6), np.eye(3),
            voigt_convention=("xx", "yy", "zz", "yz_tensorial", "xz_tensorial", "xy_tensorial"),
        )
