"""Copy compact original MoS2 spectroscopy evidence; no cubes or scratch files."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT = Path('/home/zhuxd/abacus/agent-runs')
SOURCE = ROOT / 'zstar_mos2_pbed3bj_response_20260831'
OUTPUT = ROOT / '20260904-independent-force-benchmark/mos2-spectroscopy-evidence.tar.gz'


def main():
    records = {}
    top_names = ('BORN', 'Z-BORN-symm.out', 'Z-BORN-reduced.out',
                 'Z-BORN-reduced-neutral.out', 'born_symmetry_report.json',
                 'born_symmetry_report.txt', 'gen_polar.out', 'reduced_atom.out',
                 'STRU', 'KPT', 'INPUT.seed', 'phonopy.yaml', 'irreps.yaml', 'qpoints.yaml')
    paths = [SOURCE / name for name in top_names]
    for pattern in ('*/zstar_2d_bec.json', '*/zstar_2d_bec.txt',
                    '0.no-move/INPUT*', '0.no-move/STRU', '0.no-move/KPT',
                    '0.no-move/*.upf', '0.no-move/*.orb',
                    '0.no-move/pyatb*/Input*', '0.no-move/pyatb*/Out/Polarization/*.dat',
                    '*/?+/INPUT*', '*/?+/STRU', '*/?+/KPT',
                    '*/?+/pyatb*/Input*', '*/?+/pyatb*/Out/Polarization/*.dat'):
        paths.extend(SOURCE.glob(pattern))
    with tarfile.open(OUTPUT, 'w:gz') as archive:
        for path in sorted(set(paths)):
            if not path.is_file():
                raise FileNotFoundError(path)
            relative = str(path.relative_to(SOURCE))
            records[relative] = {'size': path.stat().st_size,
                                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            archive.add(path, arcname=relative, recursive=False)
    manifest = OUTPUT.with_suffix('').with_suffix('.json')
    manifest.write_text(json.dumps({'source': str(SOURCE), 'files': records}, indent=2) + '\n')
    print(json.dumps({'files': len(records), 'archive_bytes': OUTPUT.stat().st_size}))


if __name__ == '__main__':
    main()
