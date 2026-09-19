#!/usr/bin/env python3
"""Prepare isolated PBE reference optimizations; never run a calculator.

Research campaign helper, not a public CLI. Both backends start from the same
geometry, but must optimize their own PBE reference before response sampling.
Licensed POTCAR files stay on the user's compute filesystem, outside Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zstar.shared_response import read_structure
from zstar.v2.strain import prepare_abacus_reference_relaxation, _set_input_parameter


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root: Path, sources: dict, paw_root: Path) -> dict:
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Campaign target is not empty: {root}")
    # Validate every species before generating any calculation directory.
    inventories = {}
    for material, spec in sources.items():
        source = Path(spec['source'])
        atoms = read_structure(source / 'STRU')
        species = tuple(dict.fromkeys(atoms.symbols))
        assets = {}
        for element in species:
            pseudo = source / f'{element}.upf'
            header = pseudo.read_text(errors='replace').split('</PP_HEADER>', 1)[0]
            if not re.search(r'functional\s*=\s*[\"\']PBE[\"\']', header, re.I):
                raise ValueError(f"Not a verified PBE pseudopotential: {pseudo}")
            paw = paw_root / spec['paw'][element] / 'POTCAR'
            content = paw.read_text(errors='replace')
            title = re.search(r'TITEL\s*=\s*([^\n]+)', content)
            if title is None or 'PAW_PBE' not in title.group(1):
                raise ValueError(f"Not a verified PAW-PBE dataset: {paw}")
            assets[element] = {
                'abacus_pseudo_path': str(pseudo), 'abacus_pseudo_sha256': sha256(pseudo),
                'vasp_paw_path': str(paw), 'vasp_paw_sha256': sha256(paw),
                'vasp_paw_title': title.group(1).strip(),
            }
        kpt = (source / 'KPT').read_text().splitlines()
        if len(kpt) < 4 or kpt[2].strip().lower() != 'gamma':
            raise ValueError(f"Expected reviewed Gamma mesh: {source / 'KPT'}")
        mesh = tuple(int(x) for x in kpt[3].split()[:3])
        inventories[material] = (atoms, species, assets, mesh)
    root.mkdir(parents=True)
    manifest = {'schema': 'zstar-v2-pbe-reference-campaign', 'functional': 'PBE',
                'status': 'references_prepared_not_executed', 'cases': {},
                'response_plan': {'strain_amplitude': .005, 'difference_method': 'central',
                                  'geometries_per_backend': 13, 'outputs': ['e', 'C_E', 'd'],
                                  'd_definition': 'e @ inverse(C_E)',
                                  'vasp_e_reference': 'DFPT electronic + ionic contributions',
                                  'd33_comparison': 'same phase, axes, functional and relaxation'},
                'structural_symprec_angstrom': .001, 'mpi': 40, 'omp': 1}
    for material, spec in sources.items():
        source = Path(spec['source'])
        atoms, species, assets, mesh = inventories[material]
        abacus = root / material / 'abacus' / 'R1'
        prepare_abacus_reference_relaxation(
            abacus, structure=source / 'STRU', input_template=source / 'INPUT',
            kpt_template=source / 'KPT', pp_dir=source, orb_dir=source,
            profile='production', symprec=.001)
        _set_input_parameter(abacus / 'INPUT', 'dft_functional', 'pbe')
        # A distinct functional must never inherit a cached charge density.
        _set_input_parameter(abacus / 'INPUT', 'init_chg', 'auto')
        vasp = root / material / 'vasp' / 'R1'
        vasp.mkdir(parents=True)
        lines = [f'ZStar v2 {material} PBE independent reference', '1.0']
        lines += [' '.join(f'{x:.16g}' for x in row) for row in atoms.cell]
        lines += [' '.join(species), ' '.join(str(list(atoms.symbols).count(s)) for s in species), 'Direct']
        lines += [' '.join(f'{x:.16g}' for x in row) for row in atoms.scaled_positions]
        (vasp / 'POSCAR').write_text('\n'.join(lines) + '\n')
        (vasp / 'POTCAR').write_bytes(b''.join(Path(assets[s]['vasp_paw_path']).read_bytes() for s in species))
        (vasp / 'KPOINTS').write_text('Matched input mesh\n0\nGamma\n' + ' '.join(map(str, mesh)) + '\n0 0 0\n')
        # 1000 eV follows de Jong's database settings; no ultra-tight force gate.
        (vasp / 'INCAR').write_text(
            'GGA = PE\nPREC = Accurate\nENCUT = 1000\nEDIFF = 1e-8\nEDIFFG = -1e-4\n'
            'NSW = 100\nIBRION = 2\nISIF = 3\nISYM = 2\nPOTIM = 0.2\n'
            'ISMEAR = 0\nSIGMA = 0.02\nLREAL = .FALSE.\nLASPH = .TRUE.\n'
            'ADDGRID = .TRUE.\nALGO = Normal\nNELM = 200\nISPIN = 1\n'
            'LWAVE = .FALSE.\nLCHARG = .FALSE.\nNCORE = 4\n')
        manifest['cases'][material] = {
            'source': str(source), 'source_structure_sha256': sha256(source / 'STRU'),
            'expected_space_group': spec['space_group'], 'model_note': spec.get('model_note', ''),
            'assets': assets, 'mesh': mesh, 'abacus_reference': str(abacus),
            'vasp_reference': str(vasp), 'force_threshold_eV_per_angstrom': 1e-4,
            'stress_acceptance_kbar': .5, 'max_ionic_steps': 100,
            'abacus_scf_threshold': 1e-8, 'vasp_ediff_eV': 1e-8,
            'vasp_encut_eV': 1000,
            'vasp_input_sha256': {name: sha256(vasp / name) for name in ('POSCAR', 'INCAR', 'KPOINTS', 'POTCAR')},
            'status': 'prepared_not_run',
        }
    (root / 'campaign.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--sources', required=True, type=Path)
    parser.add_argument('--paw-root', required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.root, json.loads(args.sources.read_text()), args.paw_root)
    print(json.dumps({'root': str(args.root), 'cases': list(result['cases']), 'reference_jobs': 2 * len(result['cases'])}))
