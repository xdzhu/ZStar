"""Diagnose fixed-origin sensitivity using already integrated electron counts.

This reads the original failed validation log; it does not recompute density,
change its normalization, overwrite results or promote an APT to production.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from zstar.spectra import load_gamma_modes


def shifted_apt(raw_apt, origin_angstrom, displacements, electron_counts):
    design = np.column_stack((np.ones(len(displacements)), np.asarray(displacements)))
    coefficient, _, rank, _ = np.linalg.lstsq(design, electron_counts, rcond=1e-10)
    if rank != 4:
        raise ValueError('Displacements cannot identify all three electron-count derivatives')
    derivative = coefficient[1:]
    return np.asarray(raw_apt) + np.outer(origin_angstrom, derivative), derivative


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--failed-log', type=Path, required=True)
    parser.add_argument('--cube-review', type=Path, required=True)
    parser.add_argument('--reference-qpoints', type=Path, required=True)
    args = parser.parse_args()
    log = args.failed_log.read_text(encoding='utf-8').split('\nTraceback', 1)[0]
    data = json.loads(log)
    review = json.loads(args.cube_review.read_text(encoding='utf-8'))
    displacements = [row['displacement_A'] for row in review['cube_results']]
    cell = load_gamma_modes(args.reference_qpoints).lattice_angstrom
    origin = np.asarray(data['center_fractional']) @ np.asarray(cell)
    shifted, derivative = shifted_apt(data['apt_cube_e'], origin, displacements,
                                      data['electron_count_raw'])
    expected = np.asarray(data['apt_position_e'])
    difference = shifted - expected
    print(json.dumps({
        'status': 'diagnostic_only',
        'original_validation_passed': data['passed'],
        'original_max_abs_difference_e': data['max_abs_difference_e'],
        'original_relative_difference': data['relative_frobenius_difference'],
        'fixed_origin_angstrom': origin.tolist(),
        'electron_count_derivative_per_angstrom': derivative.tolist(),
        'algebraically_shifted_apt_e': shifted.tolist(),
        'shifted_max_abs_difference_e': float(np.max(np.abs(difference))),
        'shifted_relative_difference': float(np.linalg.norm(difference) / np.linalg.norm(expected)),
        'interpretation': 'Origin sensitivity of finite-grid non-neutrality only; not independent accuracy validation.',
    }, indent=2))


if __name__ == '__main__':
    main()
