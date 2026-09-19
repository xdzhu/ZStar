"""3D scientific intake controls; documentation example is NOT a new DFT run."""
import numpy as np
import pytest

from tools.read_v2_vasp_lcalcpol import read_lcalcpol
from zstar.v2.polarization import match_polarization_branch
from zstar.v2.units import ELEMENTARY_CHARGE


def block(ion='1 2 3', elc='-.2 .4 -.6', unit='|e| Angst'):
    return (f'Ionic dipole moment: p[ion]=( {ion} ) {unit}\n'
            f'Total electronic dipole moment: p[elc]=( {elc} ) {unit}\n')


CELL = np.array([[4., .1, .2], [.3, 5., .4], [.2, .1, 6.]])


def test_full_3d_positive_unit_retains_raw_and_si_vector():
    result = read_lcalcpol(block(), lattice_rows_A=CELL, source='synthetic-3D')
    factor = ELEMENTARY_CHARGE * 1e20 / np.linalg.det(CELL)
    np.testing.assert_allclose(result['polarization']['value'], np.array([.8, 2.4, 2.4])*factor)
    assert result['raw_ionic_dipole']['unit'] == '|e| Angst'
    assert result['raw_electronic_dipole']['value'] == [-.2, .4, -.6]
    assert not result['accepted_full_tensor'] and not result['polarization']['branch_matched']
    assert result['standard_uncertainty'] is None


def test_old_official_naf_3d_example_negative_electron_charge():
    # https://vasp.at/wiki/index.php/LCALCPOL ; example's full 3D primitive cell.
    cell = 4.5102*np.array([[0, .5, .5], [.5, 0, .5], [.5, .5, 0]])
    a = read_lcalcpol(block('2.25510 2.25510 2.25510', '0 0 0', 'electrons Angst'), lattice_rows_A=cell)
    b = read_lcalcpol(block('2.25510 2.25510 1.93939', '0 0 .36061', 'electrons Angst'), lattice_rows_A=cell)
    delta = np.asarray(b['dipole']['value']) - a['dipole']['value']
    bec_z = delta[2] / (ELEMENTARY_CHARGE * .045102 * 1e-10)
    assert bec_z == pytest.approx(-.0449/.045102, abs=1e-12)
    np.testing.assert_allclose(delta[:2], 0)


def test_equal_raw_numbers_different_explicit_units_have_opposite_sign():
    a = read_lcalcpol(block(), lattice_rows_A=CELL)
    b = read_lcalcpol(block(unit='electrons Angst'), lattice_rows_A=CELL)
    np.testing.assert_allclose(a['polarization']['value'], -np.asarray(b['polarization']['value']))


def test_nonorthogonal_quantum_columns_reuse_existing_3d_branch_matcher():
    result = read_lcalcpol(block(), lattice_rows_A=CELL)
    q = np.asarray(result['polarization_quantum']['value'])
    np.testing.assert_allclose(q, ELEMENTARY_CHARGE*1e20*CELL.T/np.linalg.det(CELL))
    p = np.asarray(result['polarization']['value'])
    shifts = np.array([2, -3, 1])
    matched = match_polarization_branch(p, p+q@shifts, q)
    np.testing.assert_allclose(matched.matched, p, atol=1e-14)
    np.testing.assert_array_equal(matched.branch_shift, -shifts)


def test_all_cartesian_components_rotate_with_3d_lattice():
    axis = np.array([1., 2., 3.])/np.sqrt(14)
    cross = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    q = np.eye(3)*np.cos(.47)+(1-np.cos(.47))*np.outer(axis, axis)+np.sin(.47)*cross
    ion, elc = q@np.array([1, 2, 3]), q@np.array([-.2, .4, -.6])
    rotated = read_lcalcpol(block(' '.join(map(str, ion)), ' '.join(map(str, elc))), lattice_rows_A=CELL@q.T)
    original = read_lcalcpol(block(), lattice_rows_A=CELL)
    np.testing.assert_allclose(rotated['polarization']['value'], q@original['polarization']['value'])
    np.testing.assert_allclose(rotated['polarization_quantum']['value'], q@original['polarization_quantum']['value'])


def test_last_complete_pair_not_first_and_fortran_numbers():
    result = read_lcalcpol(block()+block('1D0 2d0 4.0', '0 0 0'), lattice_rows_A=CELL)
    assert result['complete_pair_count'] == 2
    assert result['raw_ionic_dipole']['value'] == [1, 2, 4]
    assert result['raw_ionic_dipole']['line_one_based'] == 3


@pytest.mark.parametrize('text', ['', 'Total electronic dipole moment: p[elc]=( 0 0 0 ) |e| Angst',
    block()+'Ionic dipole moment: p[ion]=( 1 2 3 ) |e| Angst',
    block(ion='1 2'), block(ion='1 2 3 4'), block(ion='nan 0 0'), block(elc='inf 0 0'),
    block(unit='e Angst'), block().replace(') |e| Angst', ') electrons Angst', 1),
    block()+'Ionic dipole moment: p[ion]=( broken',
    'Ionic dipole moment: p[ion]=( 1 2 3 ) |e| Angst\n'*2+block()])
def test_missing_malformed_truncated_or_mixed_units_rejected(text):
    with pytest.raises(ValueError):
        read_lcalcpol(text, lattice_rows_A=CELL)


@pytest.mark.parametrize('cell', [np.zeros((3, 3)), -CELL, np.ones((2, 3)), CELL*np.nan])
def test_invalid_cell_rejected(cell):
    with pytest.raises(ValueError):
        read_lcalcpol(block(), lattice_rows_A=cell)


def test_slab_normalization_not_invented():
    with pytest.raises(ValueError, match='3D bulk'):
        read_lcalcpol(block(), lattice_rows_A=CELL, periodic_axes=(True, True, False))


@pytest.mark.parametrize('h', [.005, .01])
def test_deformed_3d_quanta_connect_raw_dipoles_to_full_response(h):
    # A controlled linear Cartesian response, NOT a material benchmark.
    from zstar.v2.fit import fit_piezoelectric_ensemble
    from zstar.v2.mechanical import voigt_to_strain_tensor
    from zstar.v2.polarization import match_polarization_ensemble
    from zstar.v2.strain import actual_strain
    from zstar.v2.units import convert_values

    expected = np.arange(18).reshape(3, 6)/10  # C/m^2 per engineering strain
    p0 = np.array([.1, -.05, .2])  # C/m^2, fixed Cartesian reference branch
    requested = np.vstack((np.zeros(6), -h*np.eye(6), h*np.eye(6)))
    actual, wrapped, quanta, shifts = [], [], [], []
    for index, eta in enumerate(requested):
        # Round-trip the row lattice exactly as a high-precision text writer.
        generated = CELL @ (np.eye(3)+voigt_to_strain_tensor(eta)).T
        cell = np.asarray([[float(f'{value:.16g}') for value in row] for row in generated])
        measured = actual_strain(CELL, cell)
        physical = p0 + expected@measured
        volume_m3 = np.linalg.det(cell)*float(convert_values(1., 'angstrom', 'm'))**3
        # Use the tested reader to obtain this stage's 3D quantum matrix.
        zero = read_lcalcpol(block('0 0 0', '0 0 0'), lattice_rows_A=cell)
        quantum = np.asarray(zero['polarization_quantum']['value'])
        shift = np.zeros(3, int) if index == 0 else (-1)**index*np.array([2, -3, 1])
        printed_p = physical + quantum@shift
        raw_dipole = printed_p*volume_m3/float(convert_values(1., 'e_angstrom', 'C*m'))
        record = read_lcalcpol(block('0 0 0', ' '.join(f'{v:.17g}' for v in raw_dipole)),
                               lattice_rows_A=cell)
        actual.append(measured)
        wrapped.append(record['polarization']['value'])
        quanta.append(record['polarization_quantum']['value'])
        shifts.append(shift)
    matched = match_polarization_ensemble(actual, wrapped, quanta)
    np.testing.assert_array_equal(matched.branch_shifts, -np.asarray(shifts))
    result = fit_piezoelectric_ensemble(matched)
    assert result.fit_rank == result.allowed_rank == 18 and result.complete
    np.testing.assert_allclose(result.matrix, expected, atol=1e-11)
    assert result.residual_max < 1e-12
    # Same-cell quantum reuse makes a spurious derivative in a strained cell.
    wrong = match_polarization_ensemble(actual, wrapped, quanta[0])
    wrong_fit = fit_piezoelectric_ensemble(wrong, residual_tolerance=1.)
    assert np.max(np.abs(wrong_fit.matrix-expected)) > .1
