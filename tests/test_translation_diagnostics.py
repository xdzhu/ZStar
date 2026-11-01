import numpy as np
import pytest

from zstar.structure_io import StructureData
from zstar.translation_diagnostics import TranslationStage, compare_translation_stages, read_translation_stage


def _stage(positions, forces, *, calculator='abacus', energy=-1.0, inputs=None):
    structure = StructureData(np.diag([10., 10., 5.]), np.asarray(positions), ('C', 'H'))
    return TranslationStage(structure, np.asarray(forces), energy, {},
                            inputs or {'INPUT': 'abc', 'KPT': None}, calculator)


def test_global_translation_with_periodic_wrapping_preserves_printed_force_differences():
    reference = _stage([[0.4, 0.4, 0.95], [0.5, 0.5, 0.05]], [[0, 0, 0], [1, 0, 0]])
    shifted = _stage([[0.6, 0.4, 0.05], [0.7, 0.5, 0.15]], [[0, 0.02, 0], [1, 0, 0]], energy=-0.9)
    report = compare_translation_stages(reference, shifted, dimensionality=1)
    np.testing.assert_allclose(report['translation_A'], [2, 0, 0.5])
    assert report['geometry_max_residual_A'] < 1e-12
    assert report['max_atom_force_delta_eV_A'] == pytest.approx(0.02)
    assert report['energy_difference_eV'] == pytest.approx(0.1)
    assert report['input_file_hashes_equal'] == {'INPUT': True, 'KPT': None}
    assert 'drift correction' in report['interpretation']


def test_nonrigid_change_and_different_backends_are_rejected():
    reference = _stage([[0.4, 0.4, 0.95], [0.5, 0.5, 0.05]], np.zeros((2, 3)))
    changed = _stage([[0.6, 0.4, 0.05], [0.71, 0.5, 0.15]], np.zeros((2, 3)))
    with pytest.raises(ValueError, match='not related by a rigid translation'):
        compare_translation_stages(reference, changed, dimensionality=1)
    other = _stage(reference.structure.positions_fractional, np.zeros((2, 3)), calculator='vasp')
    with pytest.raises(ValueError, match='same calculator'):
        compare_translation_stages(reference, other, dimensionality=1)


def test_vasp_stage_checks_static_geometry_and_parses_native_forces(tmp_path):
    from tests.test_v2_vasp_observations import _outcar

    (tmp_path / 'INCAR').write_text('NSW = 0\n')
    (tmp_path / 'POSCAR').write_text('fixture\n1\n3 0 0\n0 3.1 0\n0 0 3.2\n'
                                     'C H\n1 1\nCartesian\n0 0 0\n1 1 1\n')
    (tmp_path / 'OUTCAR').write_text(_outcar())
    stage = read_translation_stage(tmp_path, calculator='vasp')
    np.testing.assert_allclose(stage.forces_eV_A[0], [0.01, 0.02, 0.03])
    assert stage.energy_eV == pytest.approx(-12.3456789)
    assert stage.input_hashes['POTCAR'] is None
    (tmp_path / 'POSCAR').write_text('fixture\n1\n3 0 0\n0 3.1 0\n0 0 3.2\n'
                                     'C H\n1 1\nCartesian\n0 0 0\n1.1 1 1\n')
    with pytest.raises(ValueError, match='force-block positions differ'):
        read_translation_stage(tmp_path, calculator='vasp')
