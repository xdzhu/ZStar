"""Three-dimensional controls for the bounded cross-archive reference audit."""
import numpy as np
import pytest

from tools.audit_v2_pbe_reference_pairing import cross_archive_d, geometry_difference, strict_json


def test_complete_hexagonal_tensor_units_and_shear():
    c = np.array([[400, 150, 100, 0, 0, 0], [150, 400, 100, 0, 0, 0],
                  [100, 100, 350, 0, 0, 0], [0, 0, 0, 120, 0, 0],
                  [0, 0, 0, 0, 120, 0], [0, 0, 0, 0, 0, 125]], dtype=float)
    e = np.zeros((3, 6))
    e[0, 4] = e[1, 3] = -.25
    e[2, :3] = [-.5, -.5, 1.5]
    result = cross_archive_d(e, c)
    d = np.asarray(result['value'])
    np.testing.assert_allclose(d@c/1000, e, atol=1e-14)
    assert d[0, 4] == pytest.approx(-.25/120*1000)
    assert d[1, 3] == pytest.approx(-.25/120*1000)
    expected_d33 = (1.5+100/550)/(350-20000/550)*1000
    assert d[2, 2] == pytest.approx(expected_d33)
    assert result['same_calculation_paired_reference'] is False
    assert result['standard_uncertainty'] is None


def test_full_3d_periodic_origin_and_species_mapping_not_dilation():
    core = pytest.importorskip('pymatgen.core')
    lattice = core.Lattice.hexagonal(3, 5)
    p = core.Structure(lattice, ['Ga', 'Ga', 'N', 'N'],
                       [[1/3, 2/3, 0], [2/3, 1/3, .5],
                        [1/3, 2/3, .375], [2/3, 1/3, .875]])
    order = [2, 0, 3, 1]
    c = core.Structure(lattice, [p[i].specie for i in order],
                       p.frac_coords[order]+np.array([.12, -.27, .19]))
    audit = geometry_difference(p, c)
    assert audit['same_geometry_at_serialization_precision']
    assert audit['internal_comparison']['max_difference_angstrom'] < 1e-12
    inverted = core.Structure(lattice, c.species, -c.frac_coords)
    inversion_audit = geometry_difference(p, inverted)
    assert inversion_audit['internal_comparison']['max_difference_angstrom'] > .5
    assert inversion_audit['inversion_related_internal_comparison']['max_difference_angstrom'] < 1e-12
    assert not inversion_audit['same_geometry_at_serialization_precision']
    enlarged = core.Structure(core.Lattice.hexagonal(3.003, 5.005), c.species, c.frac_coords)
    audit = geometry_difference(p, enlarged)
    assert not audit['same_geometry_at_serialization_precision']
    assert audit['elastic_minus_piezo_volume_percent'] == pytest.approx(100*(1.001**3-1))
    assert audit['internal_comparison']['max_difference_angstrom'] < 1e-12


@pytest.mark.parametrize('c', [np.diag([1, 1, 1, 1, 1, -1]), np.zeros((6, 6)),
                              np.eye(6)+np.eye(6, k=1)])
def test_reject_unstable_or_nonmajor_symmetric_reference(c):
    with pytest.raises(ValueError):
        cross_archive_d(np.zeros((3, 6)), c)


@pytest.mark.parametrize('raw', ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_strict_archive_json(raw):
    with pytest.raises(ValueError):
        strict_json(raw)
