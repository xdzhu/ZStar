import numpy as np
import pytest
from pymatgen.core import Structure

from tools.audit_v2_pbe_polar_domains import aligned_axes, translation_fit, audit


def reference():
    return Structure(np.diag([3.8, 3.8, 4.6]), ['Pb', 'Ti', 'O', 'O', 'O'],
                     [[0, 0, .14], [.5, .5, .59], [0, .5, .49], [.5, 0, .49], [.5, .5, .976]])


def test_translation_and_same_species_permutation():
    ref = reference()
    order = [1, 0, 4, 2, 3]
    own = Structure(ref.lattice, [ref[i].specie for i in order],
                    ref.frac_coords[order] + [.23, .17, .42])
    assert translation_fit(own, ref)['rms_angstrom'] < 1e-12
    assert translation_fit(own, ref, True)['rms_angstrom'] > .1


def test_opposite_domain_not_hidden_by_translation():
    ref = reference()
    coords = ref.frac_coords.copy()
    coords[:, 2] *= -1
    own = Structure(ref.lattice, ref.species, coords)
    assert translation_fit(own, ref, True)['rms_angstrom'] < 1e-12
    assert translation_fit(own, ref)['rms_angstrom'] > .1


def test_unaligned_axes_require_explicit_rotation():
    ref = reference()
    aligned_axes(ref)
    ref = Structure([[0, 3.8, 0], [-3.8, 0, 0], [0, 0, 4.6]], ref.species, ref.frac_coords)
    with pytest.raises(ValueError, match='rotation required'):
        aligned_axes(ref)


def test_explicit_rotation_preserves_domain_and_does_not_round_cell():
    ref = reference()
    angle = .08
    rotation = np.array([[np.cos(angle),-np.sin(angle),0],
                         [np.sin(angle),np.cos(angle),0],[0,0,1]])
    own = Structure(ref.lattice.matrix@rotation, ref.species, ref.frac_coords)
    before = own.lattice.matrix.copy()
    with pytest.raises(ValueError, match='rotation required'):
        audit(own,ref,99)
    result = audit(own,ref,99,frame_rotation=rotation)
    assert result['coordinate_and_domain_verified']
    assert not result['cell_shear_removed']
    assert np.array_equal(before,own.lattice.matrix)
    with pytest.raises(ValueError, match='proper orthogonal'):
        audit(own,ref,99,frame_rotation=2*np.eye(3))
