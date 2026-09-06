"""Traceable frequency comparison to Erba et al., Table I, n=6."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from zstar.spectra import load_gamma_modes


def compare(root):
    case = root / 'BN_6_0'
    modes = load_gamma_modes(case / 'evidence/unified/qpoints.yaml')
    with (case / 'ir/ir_modes.csv').open() as stream:
        rows = {int(row['mode']): row for row in csv.DictReader(stream)}
    # Only the seven IR-active branches: C6 and C7 are explicitly IR-inactive
    # in the reference discussion despite appearing in its broader Table I.
    mapping = [('A1*', 269.32, [9, 10], 'transverse'),
               ('A2 (RBM)', 414.41, [15], 'axial'),
               ('A3*', 537.33, [19, 20], 'transverse'),
               ('B4*', 794.75, [37, 38], 'transverse'),
               ('B5', 832.58, [39], 'axial'),
               ('C8', 1342.44, [68], 'axial'),
               ('C9*', 1458.33, [71, 72], 'transverse')]
    positions = modes.positions_fractional @ modes.lattice_angstrom
    positions[:, :2] -= np.average(positions[:, :2], axis=0, weights=modes.masses_amu)
    radial = positions.copy()
    radial[:, 2] = 0
    radial /= np.linalg.norm(radial, axis=1)[:, None]
    radial *= np.sqrt(modes.masses_amu[:, None])
    radial = radial.ravel() / np.linalg.norm(radial)
    rbm_overlap = float(abs(modes.eigenvectors[14].ravel().conj() @ radial) ** 2)
    if rbm_overlap < .9:
        raise ValueError('Proposed breathing mode does not have dominant radial overlap')
    comparison = []
    for branch, ref, numbers, direction in mapping:
        selected = [rows[n] for n in numbers]
        frequencies = [float(row['frequency_cm-1']) for row in selected]
        if np.ptp(frequencies) > 1:
            raise ValueError('Proposed degenerate branch is split by more than 1 cm^-1')
        axial = sum(float(row['intensity_z']) for row in selected)
        total = sum(float(row['intensity_total']) for row in selected)
        fraction = axial / total
        if (direction == 'axial' and fraction < .99) or (direction == 'transverse' and fraction > .01):
            raise ValueError('Proposed branch has incompatible IR polarization')
        frequency = float(np.mean(frequencies))
        comparison.append(dict(reference_branch=branch, zstar_modes=';'.join(map(str, numbers)),
                               multiplicity=len(numbers), polarization=direction,
                               zstar_PBE_cm1=frequency, reference_B3LYP_cm1=ref,
                               difference_cm1=frequency - ref,
                               relative_difference_percent=100 * (frequency / ref - 1)))
    output = case / 'comparison'
    output.mkdir(exist_ok=True)
    with (output / 'Erba2013_IR_frequencies.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparison[0]))
        writer.writeheader()
        writer.writerows(comparison)
    metadata = dict(
        source_doi='10.1063/1.4788831',
        title='The vibration properties of the (n,0) boron nitride nanotubes from ab initio quantum chemical simulations',
        authors=['A. Erba', 'M. Ferrabone', 'R. Orlando', 'R. Dovesi', 'M. Rerat'],
        source_url='https://iris.unito.it/bitstream/2318/130911/4/paperbntubivib.pdf',
        source_location='Author manuscript Table I, n=6; Section III identifies C6/C7 as IR-inactive.',
        reference_software='CRYSTAL', reference_xc='B3LYP', reference_basis='6-31G* with reoptimized diffuse sp exponents',
        assignment='Candidate branch correspondence by frequency order within each band, multiplicity and IR polarization; RBM additionally checked by mass-weighted radial overlap.',
        caveat='Not an eigenvector-to-eigenvector reference match or absolute-intensity validation. Reference A/B/C labels enumerate bands, not point-group irreducible representations.',
        rbm_radial_overlap=rbm_overlap, frequency_shift_cm1=0,
        max_absolute_relative_difference_percent=max(abs(row['relative_difference_percent']) for row in comparison))
    (output / 'Erba2013_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('campaign_root', type=Path)
    compare(parser.parse_args().campaign_root)
