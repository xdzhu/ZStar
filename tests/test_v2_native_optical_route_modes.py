"""Full 3D spectral attribution controls, no calculator/structure parser."""
import numpy as np
import pytest

from tools.audit_v2_native_optical_route_modes import _load, block_response, exact_d_parts
from zstar.v2.units import convert_values


def test_degenerate_optical_block_invariant_under_basis_rotation_and_sign():
    rng = np.random.default_rng(31)
    q = np.linalg.qr(rng.normal(size=(9, 3)))[0]
    z, x = rng.normal(size=(3, 9)), rng.normal(size=(9, 6))
    rotation = np.linalg.qr(rng.normal(size=(3, 3)))[0]
    original = block_response(q, np.ones(3)*2, z, x, 100.)
    for changed in (q @ rotation, q * [-1, 1, -1]):
        for actual, expected in zip(block_response(changed, np.ones(3)*2, z, x, 100.), original):
            np.testing.assert_allclose(actual, expected, atol=1e-13, rtol=1e-12)


def test_all_spectral_blocks_reconstruct_3d_response_and_exact_d_difference():
    rng = np.random.default_rng(53)
    q = np.linalg.qr(rng.normal(size=(9, 6)))[0]
    k = np.arange(1., 7.)
    z = rng.normal(size=(3, 9))
    xa = rng.normal(size=(9, 6))*.1
    xb = xa+rng.normal(size=(9, 6))*.003
    ea, ca = block_response(q, k, z, xa, 100.)
    eb, cb = block_response(q, k, z, xb, 100.)
    c0, e0 = np.eye(6)*100, rng.normal(size=(3, 6))
    da = 1000*np.linalg.solve((c0+ca).T, (e0+ea).T).T
    db = 1000*np.linalg.solve((c0+cb).T, (e0+eb).T).T
    parts = []
    for i in range(6):
        eai, cai = block_response(q[:, i:i+1], k[i:i+1], z, xa, 100.)
        ebi, cbi = block_response(q[:, i:i+1], k[i:i+1], z, xb, 100.)
        parts.append(sum(exact_d_parts(ebi-eai, cbi-cai, da, c0+cb)))
    np.testing.assert_allclose(sum(parts), db-da, atol=1e-12, rtol=1e-10)
    # Direct Cartesian inverse and unit layer provide a separate contraction.
    inverse = (q/k) @ q.T
    expected_c = -convert_values(xa.T @ inverse @ xa/100., 'eV/angstrom^3', 'GPa')
    expected_e = convert_values(z @ inverse @ xa, 'e*angstrom', 'C*m')/(100.*float(convert_values(1., 'angstrom', 'm'))**3)
    np.testing.assert_allclose(ca, expected_c, atol=1e-14)
    np.testing.assert_allclose(ea, expected_e, atol=1e-14)


@pytest.mark.parametrize('k,volume', [([0.], 100.), ([-1.], 100.), ([1.], 0.)])
def test_unstable_optical_mode_or_invalid_volume_is_not_repaired(k, volume):
    with pytest.raises(ValueError, match='Positive volume and stable'):
        block_response(np.eye(9)[:, :1], np.array(k), np.ones((3, 9)), np.ones((9, 6)), volume)


def test_near_degenerate_block_keeps_each_actual_curvature_not_average():
    q = np.eye(9)[:, :2]
    k = np.array([1., 1.+1e-8])
    z, x = np.ones((3, 9)), np.ones((9, 6))
    x[1] *= 3  # Unequal coupling makes averaging observably wrong at first order.
    actual = block_response(q, k, z, x, 100.)
    pieces = [block_response(q[:, i:i+1], k[i:i+1], z, x, 100.) for i in range(2)]
    for index in range(2):
        np.testing.assert_allclose(actual[index], sum(p[index] for p in pieces), atol=1e-14, rtol=1e-13)
    averaged = block_response(q, np.full(2, k.mean()), z, x, 100.)
    assert np.max(np.abs(actual[1]-averaged[1])) > 1e-9


@pytest.mark.parametrize('text', ['{"unit":"GPa","unit":"Pa"}', '{"value":NaN}'])
def test_bounded_json_rejects_ambiguous_keys_and_nonfinite_constants(tmp_path, text):
    path = tmp_path/'audit.json'
    path.write_text(text, encoding='utf-8')
    with pytest.raises(ValueError):
        _load(path)
