"""Public Unified Raman reconstruction: symmetry, real archives and integrity."""
import json
from pathlib import Path

import numpy as np
import pytest

from zstar.raman_response import reconstruct_raman_derivatives, internal_mode_indices
from zstar import spectra, unified_spectra
from tests.test_shared_response import GROUPS


@pytest.mark.parametrize('symbol', list(GROUPS))
def test_all_point_groups_rank_three_response(symbol):
    ops = GROUPS[symbol]
    raw = np.random.default_rng(514).normal(size=(3, 3, 3))
    raw = (raw + raw.swapaxes(0, 1))/2
    expected = sum(np.einsum('ia,jb,kc,abc->ijk', r, r, r, raw) for r, _ in ops)/len(ops)
    directions = np.array([[1,2,3], [2,-1,1], [3,1,-1.]])*.005291772
    observations = [dict(atom=0, displacement_A=u, delta_epsilon=expected@u) for u in directions]
    actual, diagnostics = reconstruct_raman_derivatives(1, observations, ops)
    np.testing.assert_allclose(actual[0], expected, atol=2e-14)
    assert diagnostics['acoustic_sum_rule_projected'] is False


def test_rank_deficient_response_is_rejected():
    obs = [dict(atom=0, displacement_A=[.01,0,0], delta_epsilon=np.eye(3))]
    with pytest.raises(ValueError, match='rank 1/3'):
        reconstruct_raman_derivatives(1, obs, GROUPS['1'])


def test_canonical_pre_run_and_job_use_unified(tmp_path, monkeypatch):
    from tests.test_shared_response import make_stru
    from zstar.shared_abacus import prepare_shared_abacus
    from zstar.spectra_frontend import run_spectra_cli
    from zstar.project_manifest import read_manifest
    make_stru(tmp_path/'STRU')
    response=tmp_path/'bec'
    prepare_shared_abacus(tmp_path/'STRU',root=response)
    monkeypatch.chdir(response)
    legacy_calls=[]
    run_spectra_cli(['pre'],legacy_calls.append)
    output=response/'spectra'
    assert read_manifest('spectra',output)['options']['method']=='unified'
    calls=[]
    monkeypatch.setattr(unified_spectra,'run',lambda root,**kw:calls.append(kw))
    run_spectra_cli(['run','--dry-run'],legacy_calls.append)
    assert calls[0]['pyatb_input']=='pyatb_input'
    assert calls[0]['dry_run']
    run_spectra_cli(['job','--system','slurm'],legacy_calls.append)
    script=(output/'run_zstar_spectra.slurm').read_text()
    assert 'zstar spectra run' in script and 'zstar spectra post' in script
    assert not legacy_calls
    with pytest.raises(ValueError,match='--dim'):
        unified_spectra.prepare(tmp_path/'other',response,dimension=0)


def test_canonical_mode_post_forwards_spectrum_options(monkeypatch):
    from zstar import spectra_frontend
    monkeypatch.setattr(
        spectra_frontend,
        '_saved',
        lambda *args, **kwargs: ('abacus', 'raman', 1, {'qpoints': 'qpoints.yaml'}),
    )
    calls = []
    spectra_frontend.run_spectra_cli([
        'post', '--root', 'raman', '--temperature', '80', '--laser', '633',
        '--broadening', '6', '--incident-polarization', '1', '0', '0',
        '--scattered-polarization', '0', '1', '0', '--no-plot',
    ], calls.append)
    command = calls[0]
    assert command[:3] == ['raman', 'spectrum', '--raman-dir']
    assert command[command.index('--laser-nm') + 1] == '633'
    assert command[command.index('--incident-polarization') + 1:
                   command.index('--incident-polarization') + 4] == ['1', '0', '0']
    assert '--no-plot' in command


def test_unified_post_accepts_polarized_geometry(tmp_path, monkeypatch, capsys):
    received = {}
    monkeypatch.setattr(
        unified_spectra,
        'collect',
        lambda root, **kwargs: received.update(kwargs) or {'ok': True},
    )
    unified_spectra.run_cli('post', [
        '--temperature', '80', '--laser-nm', '633', '--max-frequency', '900',
        '--incident-polarization', '1', '0', '0',
        '--scattered-polarization', '0', '1', '0', '--no-plot',
    ], tmp_path)
    assert received['laser'] == 633
    assert received['max_frequency'] == 900
    assert received['incident_polarization'] == [1.0, 0.0, 0.0]
    assert received['scattered_polarization'] == [0.0, 1.0, 0.0]
    assert received['plot'] is False
    assert '"ok": true' in capsys.readouterr().out


def test_missing_band_gate_runs_and_failure_releases_lock(tmp_path, monkeypatch):
    from types import SimpleNamespace
    (tmp_path/'.zstar').mkdir()
    monkeypatch.setattr(unified_spectra,'source',lambda root:(tmp_path,{}, {'kind':'ir'}))
    monkeypatch.setattr(unified_spectra,'status',lambda root:[{'scf':True,'polarization':True}])
    monkeypatch.setattr(unified_spectra.workflow,'dielectric_is_complete',lambda p:True)
    monkeypatch.setattr(unified_spectra.workflow,'band_is_complete',lambda p:False)
    calls=[]
    monkeypatch.setattr(unified_spectra.workflow,'run_serial_workflow',lambda *a,**kw:calls.append(kw))
    monkeypatch.setattr(unified_spectra.workflow,'read_band_gap',lambda p:SimpleNamespace(insulating=True))
    unified_spectra.run(tmp_path)
    assert len(calls)==1
    lock=tmp_path/'.zstar/unified-spectra.lock'
    assert not lock.exists()
    lock.write_text('123')
    with pytest.raises(RuntimeError,match='Worker lock'):
        unified_spectra.run(tmp_path)
    lock.unlink()
    def fail(*a,**kw):
        raise RuntimeError('solver failure')
    monkeypatch.setattr(unified_spectra.workflow,'run_serial_workflow',fail)
    with pytest.raises(RuntimeError,match='solver failure'):
        unified_spectra.run(tmp_path)
    assert not lock.exists()


@pytest.mark.parametrize('case,dimension', [('HfO2',3),('MoS2',2),('Sb2S3',1),('CH4',0)])
def test_public_kernel_reproduces_retained_four_dimensional_evidence(case, dimension):
    from tools.spectroscopy_benchmark.collect import load
    root = Path(__file__).parents[1]/'docs/research/unified_spectroscopy_20260906/evidence'/case
    manifest, atoms, expected, _ = load(root/'unified')
    from zstar.shared_response import make_phonopy, symmetry_operations
    data = root/'unified'
    epsilon0 = np.array(json.loads((data/'0.no-move/completed.json').read_text())['epsilon'])
    observations = [{**s, 'delta_epsilon':np.array(json.loads((data/s['name']/'completed.json').read_text())['epsilon'])-epsilon0}
                    for s in manifest['stages']]
    actual, _ = reconstruct_raman_derivatives(len(atoms), observations,
        symmetry_operations(make_phonopy(atoms,symprec=manifest['symprec_A']),dimension=dimension))
    np.testing.assert_allclose(actual, expected, atol=1e-12)
    modes = spectra.load_gamma_modes(data/'qpoints.yaml')
    selected, audit = internal_mode_indices(modes, dimension)
    assert len(selected) == len(modes.frequencies_cm1) - (6 if dimension == 0 else 4 if dimension == 1 else 3)
    assert np.min(modes.frequencies_cm1[selected]) > 0
    assert len(audit['rigid_mode_numbers']) + len(selected) == len(modes.frequencies_cm1)


def test_cached_response_checks_output_and_source(tmp_path):
    source, output = tmp_path/'source', tmp_path/'result'
    source.write_text('input')
    output.write_text('output')
    from zstar.shared_abacus import _digest
    marker = dict(sources={'source':_digest(source)},outputs={'result':_digest(output)})
    (tmp_path/'completed.json').write_text(json.dumps(marker))
    assert unified_spectra._verify_done(tmp_path)
    source.write_text('modified')
    with pytest.raises(ValueError, match='source changed'):
        unified_spectra._verify_done(tmp_path)
    output.write_text('modified')
    with pytest.raises(ValueError, match='static response'):
        unified_spectra._verify_done(tmp_path)


@pytest.mark.parametrize('case', ['HfO2', 'MoS2', 'Sb2S3', 'CH4'])
def test_complete_public_postprocessing_from_retained_responses(tmp_path, monkeypatch, case):
    import shutil
    from zstar.shared_abacus import _digest
    evidence = Path(__file__).parents[1]/'docs/research/unified_spectroscopy_20260906/evidence'/case/'unified'
    response = tmp_path/'response'
    shutil.copytree(evidence, response)
    output = tmp_path/'spectra'
    output.mkdir()
    manifest = json.loads((response/'shared_response.json').read_text())
    # This fixture substitutes provenance loading only; numerical postprocessing
    # and output-source hashes still use actual retained research observations.
    monkeypatch.setattr(unified_spectra,'source',lambda root:(response,manifest,{'kind':'all'}))
    for name in ['0.no-move']+[s['name'] for s in manifest['stages']]:
        folder = output/'static'/name
        folder.mkdir(parents=True)
        source = response/name/'completed.json'
        record = json.loads(source.read_text())
        tensor = folder/'Out/Optical_Conductivity/static_dielectric_function.dat'
        tensor.parent.mkdir(parents=True)
        np.savetxt(tensor,np.array(record['epsilon']).reshape(1,9))
        marker = dict(epsilon=record['epsilon'], outputs={tensor.relative_to(folder).as_posix():_digest(tensor)},sources={str(source):_digest(source)})
        (folder/'completed.json').write_text(json.dumps(marker))
    report = unified_spectra.collect(output)
    assert report['method'] == 'unified'
    assert (output/'response.json').is_file()
    assert (output/'raman/atomic_dielectric_derivatives.npy').is_file()
    assert (output/'ir').is_dir()
