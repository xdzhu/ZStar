"""Three-dimensional optical response versus acoustic diagnostic contamination.

These are synthetic algebra controls, not independent DFT validation. They
reuse v1's explicit response projection and the existing v2 unit-aware APIs.
"""
import numpy as np
import pytest

from zstar.shared_response import SharedResponse, project_response
from zstar.v2.algebra import (
    acoustic_sum_rule_diagnostics,
    relaxed_elastic,
    relaxed_piezoelectric,
    solve_internal_strain_response,
)
from zstar.v2.electromechanical import convert_piezoelectric_forms


def bulk_response():
    """Three atoms, all x/y/z displacements and all six engineering strains."""
    rng = np.random.default_rng(919)
    translations = np.tile(np.eye(3), (3, 1))/np.sqrt(3)
    projector = np.eye(9)-translations @ translations.T
    seed = rng.normal(size=(9, 9))
    raw_phi = seed.T @ seed+2*np.eye(9)
    raw_born = rng.normal(size=(3, 3, 3))
    raw = SharedResponse(raw_born, raw_phi.reshape(3, 3, 3, 3).transpose(0, 2, 1, 3), {})
    projected = project_response(raw)
    phi = projected.force_constants.transpose(0, 2, 1, 3).reshape(9, 9)
    gamma = .2*projector @ rng.normal(size=(9, 6))
    e0 = .3*rng.normal(size=(3, 6))
    c0 = np.diag([220., 230., 240., 90., 95., 100.])
    np.testing.assert_allclose(phi @ translations, 0, atol=1e-13)
    np.testing.assert_allclose(projected.born.sum(axis=0), 0, atol=1e-15)
    return translations, projector, phi, projected.born, gamma, e0, c0


def tensors(phi, born, gamma, e0, c0):
    c, lam, _ = relaxed_elastic(
        c0, phi, gamma, 120., energy_unit='eV', length_unit='angstrom',
        volume_unit='angstrom^3', elastic_unit='GPa')
    assert np.linalg.eigvalsh(c).min() > 0
    e, _ = relaxed_piezoelectric(e0, born, lam.reshape(3, 3, 6),
                               120e-30, internal_strain_unit='angstrom')
    d = convert_piezoelectric_forms(e, c, np.eye(3)*4,
                                   elastic_unit='GPa', dielectric_unit='relative').d
    return lam, e, c, d


@pytest.mark.parametrize('amplitude', [.01, 1., 10.])
def test_pure_translation_gamma_changes_diagnostic_not_full_e_c_d(amplitude):
    t, p, phi, born, gamma, e0, c0 = bulk_response()
    acoustic = amplitude*t @ np.arange(18).reshape(3, 6)/10
    contaminated = gamma+acoustic
    baseline = tensors(phi, born, gamma, e0, c0)
    changed = tensors(phi, born, contaminated, e0, c0)
    for index, (actual, expected) in enumerate(zip(changed, baseline)):
        np.testing.assert_allclose(actual, expected, rtol=1e-11,
                                   atol=1e-24 if index == 3 else 1e-12)
    diagnostic = acoustic_sum_rule_diagnostics(phi, contaminated)
    assert not diagnostic['strain_force_coupling_compatible']
    raw_solution = solve_internal_strain_response(phi, contaminated)
    np.testing.assert_allclose(raw_solution.equilibrium_residual, acoustic, atol=1e-12)
    assert raw_solution.residual_max > 1e-3
    with pytest.raises(ValueError, match='acoustic'):
        solve_internal_strain_response(phi, contaminated, check_acoustic=True)
    # Projection is explicit; passing projected data does not erase raw evidence.
    optical = solve_internal_strain_response(phi, p @ contaminated,
                                             check_acoustic=True, residual_tolerance=1e-12)
    assert optical.rank == 6 and optical.residual_max < 1e-12
    np.testing.assert_allclose(optical.lambda_response, baseline[0], atol=1e-12)


def test_optical_gamma_error_changes_full_e_c_d_after_translation_projection():
    _, p, phi, born, gamma, e0, c0 = bulk_response()
    perturbation = .1*p @ np.random.default_rng(71).normal(size=(9, 6))
    baseline = tensors(phi, born, gamma, e0, c0)
    changed = tensors(phi, born, gamma+perturbation, e0, c0)
    # Negative control: the test is not insensitive to every kind of Gamma error.
    for actual, expected in zip(changed, baseline):
        assert np.linalg.norm(actual-expected) > 1e-14


def test_extra_optical_zero_mode_is_not_repaired_by_acoustic_projection():
    _, p, phi, _, _, _, _ = bulk_response()
    eigenvalues, eigenvectors = np.linalg.eigh(phi)
    optical_null = eigenvectors[:, 3]
    assert eigenvalues[3] > 1
    singular_phi = phi-eigenvalues[3]*np.outer(optical_null, optical_null)
    incompatible_gamma = np.outer(optical_null, np.arange(1., 7.))
    projected_gamma = p @ incompatible_gamma
    assert acoustic_sum_rule_diagnostics(singular_phi, projected_gamma)['compatible']
    solution = solve_internal_strain_response(singular_phi, projected_gamma, check_acoustic=True)
    assert solution.rank == 5 and solution.residual_max > .1
    with pytest.raises(ValueError, match='equilibrium residual'):
        solve_internal_strain_response(singular_phi, projected_gamma,
                                      check_acoustic=True, residual_tolerance=1e-10)


def test_rigid_lambda_gauge_invariance_requires_charge_neutral_bec():
    t, _, phi, born, gamma, e0, c0 = bulk_response()
    lam = tensors(phi, born, gamma, e0, c0)[0]
    rigid = t @ np.ones((3, 6))
    base, _ = relaxed_piezoelectric(e0, born, lam.reshape(3, 3, 6), 120e-30,
                                  internal_strain_unit='angstrom')
    shifted, _ = relaxed_piezoelectric(e0, born, (lam+rigid).reshape(3, 3, 6), 120e-30,
                                     internal_strain_unit='angstrom')
    np.testing.assert_allclose(shifted, base, atol=1e-15)
    nonneutral = born.copy()
    nonneutral[0] += .1*np.eye(3)
    bad_base, _ = relaxed_piezoelectric(e0, nonneutral, lam.reshape(3, 3, 6), 120e-30,
                                      internal_strain_unit='angstrom')
    bad_shifted, _ = relaxed_piezoelectric(e0, nonneutral, (lam+rigid).reshape(3, 3, 6),
                                         120e-30, internal_strain_unit='angstrom')
    assert np.max(np.abs(bad_shifted-bad_base)) > 1e-3


def test_full_3d_d_finite_change_decomposes_e_and_elastic_routes_exactly():
    rng = np.random.default_rng(819)
    ea = rng.normal(size=(3, 6))
    eb = ea+.01*rng.normal(size=(3, 6))
    ca = np.diag([190., 190., 20., 8., 8., 70.])  # GPa; soft but stable
    perturbation = .2*rng.normal(size=(6, 6))
    cb = ca+(perturbation+perturbation.T)/2
    assert np.linalg.eigvalsh(cb).min() > 0
    da, db = [convert_piezoelectric_forms(e, c, np.eye(3)*4,
              elastic_unit='GPa', dielectric_unit='relative').d*1e12
              for e, c in ((ea, ca), (eb, cb))]  # C/N -> pm/V
    sb = np.linalg.inv(cb)  # 1/GPa
    electric = 1000*(eb-ea) @ sb
    mechanical = -da @ (cb-ca) @ sb
    np.testing.assert_allclose(electric+mechanical, db-da, rtol=1e-11, atol=1e-12)
    assert np.max(np.abs(electric)) > .1 and np.max(np.abs(mechanical)) > .1
