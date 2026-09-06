import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from ase.io import read

from zstar.shared_response import read_structure
from zstar.shared_abacus import prepare_shared_abacus
from zstar.spectra import load_gamma_modes

REPO = Path(__file__).resolve().parents[2]
CASES = [('Nanotube_BN_6_0', 24, 68), ('Nanotube_BN_9_0', 36, 104),
         ('Nanowire_Sb2S3', 10, 26)]


@pytest.mark.parametrize('name,natoms,nmodes', CASES)
def test_archived_case_integrity(name, natoms, nmodes):
    case = REPO / 'examples/IR_Raman_Spectra' / name
    structure = read_structure(case / 'run/STRU')
    assert len(structure.symbols) == natoms
    assert 'H' not in structure.symbols
    positions = structure.scaled_positions
    assert (positions[:, :2].min(axis=0) + positions[:, :2].max(axis=0)) / 2 == pytest.approx([.5, .5], abs=1e-7)
    vasp = read(case / 'run/structure.vasp', format='vasp')
    assert vasp.get_chemical_symbols() == structure.symbols
    assert vasp.cell.array == pytest.approx(structure.cell)
    assert vasp.get_scaled_positions() == pytest.approx(structure.scaled_positions, abs=1e-8)
    modes = load_gamma_modes(case / 'results/qpoints.yaml')
    audit = json.loads((case / 'results/rigid-mode-audit.json').read_text())
    rigid = [row for row in audit if row['classified_rigid']]
    assert len(rigid) == 4
    assert sum(not row['classified_rigid'] for row in audit) == nmodes
    assert all(row['frequency_cm1'] > 0 for row in audit if not row['classified_rigid'])
    tensors = np.load(case / 'results/Raman/raman_tensors.npy')
    assert tensors.shape == (nmodes, 3, 3)
    assert np.isfinite(tensors).all()
    assert len(modes.frequencies_cm1) == 3 * natoms
    assert not list((case / 'run').rglob('*.cube'))
    assert not any(p.is_symlink() for p in case.rglob('*'))


@pytest.mark.parametrize('name,natoms,nmodes', CASES)
def test_runner_dry_run_does_not_create_work(name, natoms, nmodes, tmp_path):
    case = REPO / 'examples/IR_Raman_Spectra' / name
    work = tmp_path / 'work'
    p = subprocess.run([sys.executable, '-m', 'tools.shared_response.run_one_dimensional_example',
                        '--case', str(case), '--work', str(work), '--dry-run'],
                       cwd=REPO, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert 'No solver started' in p.stdout
    assert not work.exists()


def test_runner_rejects_results_as_workspace():
    case = REPO / 'examples/IR_Raman_Spectra/Nanotube_BN_6_0'
    p = subprocess.run([sys.executable, '-m', 'tools.shared_response.run_one_dimensional_example',
                        '--case', str(case), '--work', str(case / 'results'), '--dry-run'],
                       cwd=REPO, capture_output=True, text=True)
    assert p.returncode != 0
    assert 'must not overwrite' in p.stderr


@pytest.mark.parametrize('name,expected', [('Nanotube_BN_6_0', 20),
                                          ('Nanotube_BN_9_0', 56), ('Nanowire_Sb2S3', 20)])
def test_packaged_inputs_recreate_response_ensemble(name, expected, tmp_path):
    seed = REPO / 'examples/IR_Raman_Spectra' / name / 'run'
    manifest = prepare_shared_abacus(seed / 'STRU', root=tmp_path / 'unified',
                                     scf_input=seed / 'INPUT', dimension=1,
                                     symprec=1e-5, method='auto')
    assert len(manifest['stages']) == expected
    reference = tmp_path / 'unified/0.no-move'
    assert len(list(reference.glob('*.upf'))) == 2
    assert len(list(reference.glob('*.orb'))) == 2
