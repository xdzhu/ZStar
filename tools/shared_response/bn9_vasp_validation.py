"""Prepare or execute the fixed-geometry BN(9,0) VASP BEC cross-check."""
import argparse
import hashlib
import json
from pathlib import Path

from zstar.structure_io import read_structure, write_poscar
from zstar.vasp_bec import prepare_vasp_bec, run_vasp_bec, collect_vasp_bec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--structure', type=Path, required=True)
    parser.add_argument('--potentials', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--vasp-command', default='vasp_std')
    args = parser.parse_args()
    root = args.root.resolve()
    inputs = root / 'input'
    workflow = root / 'workflow'
    atoms = read_structure(args.structure)
    assert atoms.symbols == ('B',)*18+('N',)*18, 'Expected B18N18 ordering for POTCAR'
    identity = hashlib.sha256(args.structure.read_bytes()).hexdigest()
    record = root / 'provenance.json'
    if record.exists():
        assert json.loads(record.read_text())['structure_sha256'] == identity
    else:
        inputs.mkdir(parents=True, exist_ok=False)
        write_poscar(inputs/'POSCAR', atoms)
        (inputs/'INCAR').write_text(
            'SYSTEM = BN(9,0) fixed-geometry PBE BEC validation\n'
            'GGA = PE\nENCUT = 500\nPREC = Accurate\nEDIFF = 1E-8\n'
            'NELM = 160\nALGO = Normal\nISMEAR = 0\nSIGMA = 0.03\n'
            'LREAL = .FALSE.\nLASPH = .TRUE.\nISYM = 2\nNCORE = 1\n',
            encoding='utf-8')
        (inputs/'KPOINTS').write_text('Matched axial grid\n0\nGamma\n1 1 12\n0 0 0\n')
        potential_bytes = [(args.potentials/s/'POTCAR').read_bytes() for s in ('B', 'N')]
        (inputs/'POTCAR').write_bytes(b''.join(potential_bytes))
        record.write_text(json.dumps({
            'structure_sha256': identity, 'geometry_source': str(args.structure),
            'structure_relaxed_in': 'ABACUS PBE; no additional VASP relaxation',
            'xc': 'PBE', 'kmesh': [1, 1, 12], 'cutoff_eV': 500,
            'potential_sha256': [hashlib.sha256(b).hexdigest() for b in potential_bytes],
            'potential_redistribution': False,
            'purpose': 'Independent DFPT BEC at the archived BN(9,0) geometry',
            'transverse_convention': 'Periodic supercell; no isolated-wire image correction',
        }, indent=2)+'\n')
    if not (workflow/'vasp_bec_manifest.json').exists():
        prepare_vasp_bec(inputs, workflow, method='dfpt', dimensionality=1, periodic_axes='z')
    if args.run:
        states = run_vasp_bec(workflow, vasp_command=args.vasp_command, omp_threads=1)
        if not all(s.status == 'completed' for s in states) or len(states) != 2:
            raise RuntimeError(str(states))
        collect_vasp_bec(workflow)
    print(workflow)


if __name__ == '__main__':
    main()
