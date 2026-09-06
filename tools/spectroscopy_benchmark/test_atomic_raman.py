import json
from pathlib import Path
import numpy as np
import pytest

from tools.spectroscopy_benchmark.atomic_raman import reconstruct, mode_derivatives
from zstar.shared_response import read_structure, make_phonopy, symmetry_operations

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('folder,dimension', [
    ('3D_Bulk/t_HfO2/results/shared', 3),
    ('2D_Slab/MoS2_unified/results/unified', 2),
    ('1D_Nanowire/Sb2S3/results', 1),
    ('0D_Molecules/CH4_unified/results/unified', 0),
])
def test_exact_covariant_tensor_recovery(folder, dimension):
    root = ROOT/'examples'/folder
    atoms = read_structure(root/'STRU')
    operations = symmetry_operations(make_phonopy(atoms), dimension=dimension)
    rng = np.random.default_rng(16)
    random = rng.normal(size=(len(atoms), 3, 3, 3))
    random = (random+random.swapaxes(1, 2))/2
    expected = np.zeros_like(random)
    for r, perm in operations:
        expected[perm] += np.einsum('ia,jb,kc,nabc->nijk', r, r, r, random)
    expected /= len(operations)
    stages = json.loads((root/'shared_response.json').read_text())['stages']
    observations = [{**s, 'delta_epsilon':np.einsum('abc,c->ab',
                    expected[s['atom']], s['displacement_A'])} for s in stages]
    actual, report = reconstruct(len(atoms), observations, operations)
    np.testing.assert_allclose(actual, expected, atol=2e-12)
    assert all(s['rank'] == 3 for s in report['site_fits'])


def test_rank_deficiency_rejected():
    with pytest.raises(ValueError, match='rank 1/3'):
        reconstruct(1, [dict(atom=0, displacement_A=[.01, 0, 0],
                             delta_epsilon=np.eye(3))], [(np.eye(3),np.array([0]))])


def test_mass_weighted_projection():
    tensor = np.ones((2, 3, 3, 3))
    modes = np.zeros((1, 2, 3))
    modes[0, :, 0] = 1/np.sqrt(2)
    expected = np.ones((1, 3, 3))*(1/2+1/3)/np.sqrt(2)
    np.testing.assert_allclose(mode_derivatives(tensor, modes, np.array([4.,9.])), expected)


def test_no_symmetry_full_cartesian_ensemble():
    rng=np.random.default_rng(42)
    expected=rng.normal(size=(2,3,3,3))
    expected=(expected+expected.swapaxes(1,2))/2
    observations=[]
    for atom in range(2):
        for vector in np.eye(3)*.01058354421806:
            for sign in [-1,1]:
                u=sign*vector
                observations.append(dict(atom=atom,displacement_A=u,
                    delta_epsilon=np.einsum('abc,c->ab',expected[atom],u)))
    actual,report=reconstruct(2,observations,[(np.eye(3),np.arange(2))])
    np.testing.assert_allclose(actual,expected,atol=1e-12)
    assert not report['acoustic_sum_rule_projected']


def test_nonfinite_observation_rejected():
    with pytest.raises(ValueError,match='Nonfinite'):
        reconstruct(1,[dict(atom=0,displacement_A=[np.nan,0,0],
            delta_epsilon=np.eye(3))],[(np.eye(3),np.array([0]))])


def test_missing_equivalent_orbit_rejected():
    obs=[dict(atom=0,displacement_A=u,delta_epsilon=np.eye(3)) for u in np.eye(3)*.01]
    with pytest.raises(ValueError,match='Incomplete'):
        reconstruct(2,obs,[(np.eye(3),np.arange(2))])


def test_placzek_invariant_rotation_and_scale():
    from tools.spectroscopy_benchmark.validate_direct import placzek
    rng=np.random.default_rng(41)
    t=rng.normal(size=(5,3,3))
    t=(t+t.swapaxes(1,2))/2
    r,_=np.linalg.qr(rng.normal(size=(3,3)))
    rotated=np.einsum('ia,nab,jb->nij',r,t,r)
    np.testing.assert_allclose(placzek(rotated),placzek(t),rtol=1e-12)
    np.testing.assert_allclose(placzek(2*t),4*placzek(t),rtol=1e-12)
