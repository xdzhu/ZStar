from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools import prepare_v2_pbe_reference_campaign as campaign


def seed(tmp_path, monkeypatch, functional='PBE', paw_title='PAW_PBE Al 04Jan2001'):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'STRU').write_text('reviewed source geometry\n')
    (source / 'INPUT').write_text('INPUT_PARAMETERS\ndft_functional pbesol\n')
    (source / 'KPT').write_text('K_POINTS\n0\nGamma\n8 8 6 0 0 0\n')
    (source / 'Al.upf').write_text(f'<PP_HEADER functional="{functional}"/>\n')
    paw = tmp_path / 'licensed-paw' / 'Al'
    paw.mkdir(parents=True)
    (paw / 'POTCAR').write_text(f'TITEL = {paw_title}\n')
    atoms = SimpleNamespace(symbols=['Al'], cell=np.eye(3), scaled_positions=np.zeros((1, 3)))
    monkeypatch.setattr(campaign, 'read_structure', lambda path: atoms)
    calls = []

    def prepare_reference(root, **kwargs):
        calls.append(kwargs)
        root.mkdir(parents=True)
        (root / 'INPUT').write_text((source / 'INPUT').read_text())

    monkeypatch.setattr(campaign, 'prepare_abacus_reference_relaxation', prepare_reference)
    return {'aln': {'source': str(source), 'space_group': 186, 'paw': {'Al': 'Al'}}}, paw.parent, calls


def test_campaign_is_separate_and_uses_verified_pbe_assets(tmp_path, monkeypatch):
    sources, paws, calls = seed(tmp_path, monkeypatch)
    root = tmp_path / 'campaign'
    result = campaign.prepare(root, sources, paws)
    assert result['functional'] == 'PBE'
    assert result['response_plan']['strain_amplitude'] == .005
    assert result['response_plan']['difference_method'] == 'central'
    assert calls[0]['profile'] == 'production'
    assert calls[0]['symprec'] == .001
    parameters = dict(line.split()[:2] for line in (root / 'aln/abacus/R1/INPUT').read_text().splitlines() if len(line.split()) >= 2)
    assert parameters['dft_functional'] == 'pbe'
    assert 'pbesol' in (Path(sources['aln']['source']) / 'INPUT').read_text()
    incar = (root / 'aln/vasp/R1/INCAR').read_text()
    assert 'EDIFFG = -1e-4' in incar and 'NSW = 100' in incar
    assert 'ENCUT = 1000' in incar and 'GGA = PE' in incar
    assert (root / 'aln/vasp/R1/POTCAR').read_bytes() == (paws / 'Al/POTCAR').read_bytes()
    assert result['cases']['aln']['assets']['Al']['vasp_paw_sha256']


@pytest.mark.parametrize('functional,paw_title', [('PBEsol', 'PAW_PBE Al'), ('PBE', 'PAW_LDA Al')])
def test_campaign_rejects_unmatched_functional_before_writing(tmp_path, monkeypatch, functional, paw_title):
    sources, paws, calls = seed(tmp_path, monkeypatch, functional, paw_title)
    root = tmp_path / 'campaign'
    with pytest.raises(ValueError, match='Not a verified'):
        campaign.prepare(root, sources, paws)
    assert not root.exists() and not calls


def test_campaign_never_overwrites_existing_results(tmp_path, monkeypatch):
    sources, paws, _ = seed(tmp_path, monkeypatch)
    root = tmp_path / 'campaign'
    root.mkdir()
    previous = root / 'result.json'
    previous.write_text('protected result')
    with pytest.raises(FileExistsError):
        campaign.prepare(root, sources, paws)
    assert previous.read_text() == 'protected result'
