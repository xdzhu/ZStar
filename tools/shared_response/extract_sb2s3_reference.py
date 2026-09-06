"""Extract identifiable CRYSTAL tables without fitting or shifting any peaks."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

import numpy as np


def rotation_audit(text, structure):
    """Audit printed classical displacements in the reference's original axes."""
    lines = structure.read_text().splitlines()
    start = 5 + 4 * int(lines[4])
    count = int(lines[start])
    records = [line.split() for line in lines[start + 1:start + 1 + count]]
    numbers = [int(row[0]) % 200 for row in records]
    masses = np.array([{16: 32.06, 51: 121.76}[number] for number in numbers])
    positions = np.array([[float(x) for x in row[1:4]] for row in records])
    positions -= np.average(positions, weights=masses, axis=0)
    rotation = (np.cross([1., 0., 0.], positions) * np.sqrt(masses[:, None])).ravel()
    rotation /= np.linalg.norm(rotation)
    table = text.split('NORMAL MODES NORMALIZED TO CLASSICAL AMPLITUDES (IN BOHR)', 1)[1]
    pattern = re.compile(r'^\s*(?:AT\.\s+(\d+)\s+(\w+)\s+)?([XYZ])\s+(.+)$')
    results = []
    for block in table.split('FREQ(CM**-1)')[1:6]:
        rows = block.splitlines()
        frequencies = [float(x) for x in rows[0].split()]
        components = []
        for line in rows[1:]:
            match = pattern.match(line)
            if match is None:
                continue
            atom, symbol, axis, values = match.groups()
            expected_atom = len(components) // 3
            if axis != 'XYZ'[len(components) % 3]:
                raise ValueError('Unexpected CRYSTAL displacement component ordering')
            if atom is not None:
                if int(atom) != expected_atom + 1 or symbol.upper() != {16: 'S', 51: 'SB'}[numbers[expected_atom]]:
                    raise ValueError('CRYSTAL geometry and mode atom ordering differ')
            vector = [float(x) for x in values.split()]
            if len(vector) != len(frequencies):
                raise ValueError('Incomplete printed mode block')
            components.append(vector)
            if len(components) == 3 * count:
                break
        if len(components) != 3 * count:
            raise ValueError('Missing reference eigenvectors')
        vectors = np.array(components).T * np.repeat(np.sqrt(masses), 3)
        vectors /= np.linalg.norm(vectors, axis=1)[:, None]
        overlaps = abs(vectors @ rotation) ** 2
        offset = len(results)
        results.extend(dict(mode=offset + j + 1, frequency_printed_cm1=f,
                            axial_rotation_overlap=float(p))
                       for j, (f, p) in enumerate(zip(frequencies, overlaps)))
    if len(results) != 3 * count:
        raise ValueError('Incomplete reference rotation audit')
    return dict(modes=results, method='mass-weighted normalized overlap with rigid x-axis rotation',
                precision='Displacements printed to four decimal places; overlaps approximate.',
                source_structure_sha256=hashlib.sha256(structure.read_bytes()).hexdigest(),
                filtering_applied=False)


def extract(root):
    source = root / 'B3LYP-D3/gamma-point/sb2s3_fc_b3lyp-d3_freq.out'
    text = source.read_text()
    table = text.split('    MODES         EIGV', 1)[1].split('<RAMAN>', 1)[0]
    pattern = re.compile(
        r'^\s*(\d+)-\s*(\d+)\s+\S+\s+([-\d.]+)\s+[-\d.]+\s+'
        r'\((\w+)\s*\)\s+([AI])\s+\(\s*([-\d.]+)\)\s+([AI])', re.M)
    rows = []
    for match in pattern.finditer(table):
        first, last, frequency, irrep, ir, intensity, raman = match.groups()
        if first != last:
            raise ValueError('A degenerate table needs explicit multiplicity handling')
        rows.append(dict(mode=int(first), frequency_cm1=float(frequency), irrep=irrep,
                         ir_active=ir == 'A', ir_km_mol=float(intensity),
                         raman_active=raman == 'A', raman_relative_total=0.))
    if [row['mode'] for row in rows] != list(range(1, 31)):
        raise ValueError('Expected all thirty modes of the ten-atom reference')
    table = text.split('AVERAGED ISOTROPIC INTENSITIES (ARBITRARY UNITS)', 1)[1]
    table = table.split('DIRECTIONAL INTENSITIES', 1)[0]
    pattern = re.compile(r'^\s*(\d+)-\s*(\d+)\s+([-\d.]+)\s+\((\w+)\s*\)\s+([-\d.]+)', re.M)
    count = 0
    for match in pattern.finditer(table):
        first, last, frequency, irrep, intensity = match.groups()
        row = rows[int(first) - 1]
        if first != last or not row['raman_active'] or row['irrep'] != irrep:
            raise ValueError('Raman and frequency tables do not match')
        if abs(row['frequency_cm1'] - float(frequency)) > 1e-5:
            raise ValueError('Inconsistent reference frequency')
        row['raman_relative_total'] = float(intensity)
        count += 1
    if count != sum(row['raman_active'] for row in rows):
        raise ValueError('Missing Raman intensity rows')
    output = root / 'extracted'
    output.mkdir(exist_ok=True)
    with (output / 'reference_modes.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metadata = dict(source_doi='10.17632/6tntvw37tr.1', license='CC BY 4.0',
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    software='CRYSTAL', xc='B3LYP-D3(BJ)', model='isolated full-chain Sb4S6',
                    temperature_K=298, laser_nm=532, frequency_shift_cm1=0,
                    source_periodic_axis='x', zstar_periodic_axis='z',
                    spectrum_kind='isotropic relative Raman; integrated IR in km/mol',
                    modes=len(rows), raman_modes=count,
                    caveat='Rigid-rotation overlap and low-frequency stability must be audited before mode matching.')
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    audit = rotation_audit(text, source.with_suffix('.f34'))
    (output / 'reference_rotation_audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('reference_root', type=Path)
    extract(parser.parse_args().reference_root)
