"""Compare offline reconstructed spectra with their distributed reference arrays."""
import argparse
import json
from pathlib import Path

import numpy as np


CASES = ('Bulk_HfO2', '2D_MoS2', 'Nanowire_Sb2S3', 'Molecule_CH4')
ARRAYS = ('ir/ir_spectrum.dat', 'raman/raman_spectrum.dat',
          'raman/atomic_dielectric_derivatives.npy', 'raman/raman_tensors.npy')


def compare(root):
    records = []
    for case in CASES:
        folder = root / 'examples/IR_Raman_Spectra' / case
        for name in ARRAYS:
            reader = np.load if name.endswith('.npy') else np.loadtxt
            expected = reader(folder / 'results/Unified' / name)
            actual = reader(folder / 'work-unified-post' / name)
            np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-12,
                                       err_msg=f'{case}/{name}')
            records.append(dict(case=case, array=name, shape=list(actual.shape),
                                max_absolute_difference=float(np.max(np.abs(actual-expected)))))
    return dict(scope='Offline reconstruction from identical retained inputs, not independent DFT',
                rtol=1e-10, atol=1e-12, comparisons=records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.root)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
