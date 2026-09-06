"""Export source-backed extra bulk tensors used in the manuscript appendix."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from zstar.spectra import read_born_data


def audit(root):
    rows = []
    for path, phase, xc, symbols in (
        ('3D_Bulk/BaTiO3/results', 'tetragonal P4mm BaTiO3', 'PBEsol', ['Ba', 'Ti', 'O', 'O', 'O']),
        ('3D_Bulk/SiC/results/shared', 'cubic 3C-SiC', 'PBE', ['Si', 'C']),
    ):
        folder = root / 'examples' / path
        source = folder / 'BEC.dat'
        data = read_born_data(source, natoms=len(symbols), dielectric_path=folder/'BORN')
        tensors = np.asarray(data.tensors)
        rows.append({'phase': phase, 'xc': xc, 'symbols': symbols, 'units': 'e',
                     'path': source.relative_to(root).as_posix(),
                     'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                     'diagonals_e': np.diagonal(tensors, axis1=1, axis2=2).tolist(),
                     'all_offdiagonal_max_abs_e': float(np.max(np.abs(
                         tensors * (1 - np.eye(3))[None, :, :]))),
                     'display_decimals': 3})
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    encoded = json.dumps(audit(args.root), indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded, encoding='utf-8')
    print(encoded)
