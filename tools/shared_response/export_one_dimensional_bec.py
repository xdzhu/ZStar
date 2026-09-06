"""Export coordinate-explicit 1D BEC tables without rounding the source tensors."""

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'examples/IR_Raman_Spectra'


def read_case(name):
    path = BASE / name / 'results/response.json'
    record = json.loads(path.read_text())
    q, = [q for q in record['quantities'] if q['name'] == 'born_effective_charge']
    if q['axes'] != ['atom', 'displacement', 'polarization']:
        raise ValueError('Unexpected tensor convention')
    structure = record['structure']
    positions = np.array(structure['scaled_positions']) @ np.array(structure['cell_angstrom'])
    tensors = np.asarray(q['values']).transpose(0, 2, 1)
    return structure, positions, tensors, hashlib.sha256(path.read_bytes()).hexdigest()


def cylindrical_tensors(positions, cell, tensors):
    radial = positions.copy()
    radial[:, :2] -= np.diag(cell)[:2] / 2
    radial[:, 2] = 0
    norms = np.linalg.norm(radial, axis=1)
    if np.any(norms < 1e-10):
        raise ValueError('Cylindrical basis undefined on tube axis')
    radial /= norms[:, None]
    axial = np.tile([0., 0., 1.], (len(positions), 1))
    tangent = np.cross(axial, radial)
    basis = np.stack([radial, tangent, axial], axis=1)
    return basis @ tensors @ basis.transpose(0, 2, 1)


def sb_reference(structure, positions):
    root = BASE / 'Nanowire_Sb2S3/results/reference/B3LYP-D3'
    geometry = root / 'structure/sb2s3_fc_b3lyp-d3_opt2.f34'
    lines = geometry.read_text().splitlines()
    offset = 5 + 4 * int(lines[4])
    rows = [line.split() for line in lines[offset+1:offset+11]]
    symbols = np.array(['S' if int(row[0]) % 100 == 16 else 'Sb' for row in rows])
    p = np.array([[float(v) for v in row[1:4]] for row in rows])[:, [1, 2, 0]]
    # Match relaxed structures using transverse coordinates, species and axial
    # fractional phase. Different optimized periods must not appear as drift.
    period = float(lines[1].split()[0])
    p[:, :2] -= (p[:, :2].max(axis=0) + p[:, :2].min(axis=0)) / 2
    target = positions.copy()
    target[:, :2] -= np.diag(structure['cell_angstrom'])[:2] / 2
    dz = target[:, None, 2] / structure['cell_angstrom'][2][2] - p[None, :, 2] / period
    dz -= np.rint(dz)
    costs = np.linalg.norm(target[:, None, :2] - p[None, :, :2], axis=2)
    costs += np.abs(dz) * period
    costs[np.array(structure['symbols'])[:, None] != symbols[None, :]] = 1e6
    rr, cc = linear_sum_assignment(costs)
    if np.max(costs[rr, cc]) > .25 or not np.array_equal(rr, np.arange(10)):
        raise ValueError('Source atom mapping requires manual review')
    born_file = root / 'gamma-point/sb2s3_fc_b3lyp-d3_freq.born.dat'
    raw = np.loadtxt(born_file).reshape(10, 3, 3)
    # Only diagonal entries are compared: CRYSTAL text and born.dat transpose
    # off-diagonal entries, so no unverified off-diagonal convention is implied.
    diagonal = np.diagonal(raw, axis1=1, axis2=2)[:, [1, 2, 0]][cc]
    return diagonal, dict(reference_atom_1based=(cc + 1).tolist(),
                         matching_residual_A=costs[rr, cc].tolist(),
                         reference_source_sha256=hashlib.sha256(born_file.read_bytes()).hexdigest(),
                         reference_geometry_sha256=hashlib.sha256(geometry.read_bytes()).hexdigest())


def write_csv(path, fields, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    report = {'tensor_convention': 'Rows polarization, columns displacement; transposed from response.json.',
              'unit': 'e', 'reference_doi': '10.17632/6tntvw37tr.1'}
    for case in ('Nanotube_BN_9_0', 'Nanowire_Sb2S3'):
        structure, positions, tensors, digest = read_case(case)
        output = BASE / case / 'results/BEC_comparison'
        output.mkdir(exist_ok=True)
        info = dict(response_sha256=digest,
                    exported_tensor_axes=['atom', 'polarization', 'displacement'],
                    exported_unit='e',
                    raw_source='../BEC.raw.dat', projected_source='../response.json',
                    max_projected_ASR_e=float(np.max(np.abs(tensors.sum(axis=0)))))
        full = [dict(atom=i+1, species=s, **{f'Z{a}{b}':float(tensors[i,j,k])
                for j,a in enumerate('xyz') for k,b in enumerate('xyz')})
                for i,s in enumerate(structure['symbols'])]
        write_csv(output / 'full_tensors.csv', list(full[0]), full)
        if case == 'Nanotube_BN_9_0':
            local = cylindrical_tensors(positions, structure['cell_angstrom'], tensors)
            rows = []
            for s in ('B', 'N'):
                values = local[np.array(structure['symbols']) == s]
                for j, axis in enumerate(('rr', 'tt', 'zz')):
                    component = values[:, j, j]
                    rows.append(dict(species=s, component=axis, mean_e=float(component.mean()),
                                     min_e=float(component.min()), max_e=float(component.max())))
            info['local_frame_summary'] = rows
            write_csv(output / 'cylindrical_summary.csv', list(rows[0]), rows)
        else:
            reference, audit = sb_reference(structure, positions)
            info.update(audit)
            rows = [dict(atom=i+1, species=structure['symbols'][i], component=a+a,
                         zstar_PBE_D3BJ_e=float(tensors[i,j,j]),
                         reference_B3LYP_D3BJ_e=float(reference[i,j]))
                    for i in (6,7,0,1,2) for j,a in enumerate('xyz')]
            info['diagonal_comparison'] = rows
            write_csv(output / 'diagonal_comparison.csv', list(rows[0]), rows)
        (output / 'metadata.json').write_text(json.dumps(info, indent=2) + '\n')
        report[case] = info
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
