"""Unvalidated molecular Berry results must not become production APT/IR."""

import pytest

from zstar.molecular_bec import collect_molecular_apts, collect_molecular_cube_apts
from zstar.shared_abacus import _dipole_changes
from zstar.spectra import collect_molecular_dipole_derivatives
from zstar import unified_spectra


def test_shared_0d_berry_rejected_before_reading_nonempty_output(tmp_path):
    polarization = tmp_path / '0.no-move/pyatb/Out/Polarization/polarization.dat'
    polarization.parent.mkdir(parents=True)
    polarization.write_text('nonempty, but not validated')
    with pytest.raises(ValueError, match='0D Berry dipole route is not validated'):
        _dipole_changes(tmp_path, {'dimension': 0, 'stages': []})


def test_legacy_berry_collector_is_not_a_production_result(tmp_path):
    with pytest.raises(ValueError, match='0D PYATB Berry dipole route is not validated'):
        collect_molecular_apts(tmp_path)
    assert not (tmp_path / 'BEC.dat').exists()


def test_legacy_cube_collector_cannot_silently_project_unchecked_data(tmp_path):
    with pytest.raises(ValueError, match='does not yet validate raw'):
        collect_molecular_cube_apts(tmp_path)
    assert not (tmp_path / 'BEC.dat').exists()


def test_legacy_molecular_ir_requires_explicit_diagnostic(tmp_path):
    with pytest.raises(ValueError, match='not validated for molecular IR'):
        collect_molecular_dipole_derivatives(tmp_path, cell_volume_angstrom3=1)
    assert not (tmp_path / 'molecular_ir_derivatives.json').exists()


def test_unified_ir_refuses_unverified_stale_bec(tmp_path, monkeypatch):
    (tmp_path / 'BEC.dat').write_text('old data')
    (tmp_path / 'qpoints.yaml').write_text('old data')
    monkeypatch.setattr(unified_spectra, 'source',
                        lambda root: (tmp_path, {'dimension': 0}, {'kind': 'ir'}))
    with pytest.raises(ValueError, match='pre-existing 0D BEC.dat'):
        unified_spectra.collect(tmp_path)


def test_historical_ch4_example_does_not_regenerate_unverified_ir(tmp_path):
    import importlib.util
    from pathlib import Path

    root = Path(__file__).parents[1]
    script = root / 'examples/common/reproduce_unified_spectra.py'
    spec = importlib.util.spec_from_file_location('reproduce_spectra_example', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match='molecular IR archive lacks'):
        module.reproduce(root / 'examples/IR_Raman_Spectra/Molecule_CH4', tmp_path / 'output')
    assert not (tmp_path / 'output/ir').exists()
