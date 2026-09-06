"""Read-only reproduction of archived 1D tensors and spectra, without DFT."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import tarfile

import numpy as np

from tools.shared_response.one_dimensional_spectra import rigid_mode_audit
from tools.shared_response.report_one_dimensional_benchmark import timing_records, fit, internal_frequencies
from zstar import spectra
from zstar.shared_response import (read_structure, make_phonopy, symmetry_operations,
                                  reconstruct_responses, project_response)


def difference(actual, expected, tolerance, name):
    actual, expected = np.asarray(actual), np.asarray(expected)
    if actual.shape != expected.shape or not np.isfinite(actual).all() or not np.isfinite(expected).all():
        raise ValueError(f'{name}: shape/nonfinite mismatch')
    error = float(np.max(np.abs(actual-expected)))
    if error > tolerance:
        raise ValueError(f'{name}: maximum error {error:g} exceeds {tolerance:g}')
    return error


def verify_archive(path):
    with tarfile.open(path) as archive:
        manifest = json.load(archive.extractfile('evidence_manifest.json'))
        expected = {entry['path']: entry for entry in manifest['files']}
        members = archive.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)) or set(names) != set(expected) | {'evidence_manifest.json'}:
            raise ValueError('Archive member set differs from evidence manifest')
        for member in members:
            if not member.isfile():
                raise ValueError(f'Non-regular archive member: {member.name}')
            if member.name in expected:
                data = archive.extractfile(member).read()
                item = expected[member.name]
                if len(data) != item['size'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                    raise ValueError(f'Archive digest mismatch: {member.name}')
    return len(expected)


def verify_benchmark(result):
    folder = result/'benchmark'
    summary = json.loads((folder/'benchmark_summary.json').read_text())
    manifest = json.loads((folder/'benchmark_manifest.json').read_text())
    case = summary['case']
    if not summary['complete']:
        raise ValueError('Benchmark is not complete')
    with tarfile.open(folder/'benchmark_evidence.tar.gz') as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)) or set(names) != set(manifest) | {f'{case}/benchmark_manifest.json'}:
            raise ValueError('Benchmark archive member set mismatch')
        for member in members:
            if not member.isfile():
                raise ValueError('Benchmark archive includes nonregular members')
            data=archive.extractfile(member).read()
            if member.name in manifest and hashlib.sha256(data).hexdigest() != manifest[member.name]:
                raise ValueError(f'Benchmark digest mismatch: {member.name}')
        if json.load(archive.extractfile(f'{case}/benchmark_summary.json')) != summary:
            raise ValueError('External and archived benchmark summaries differ')
        cart=json.load(archive.extractfile(f'{case}/cartesian/response_fit.json'))
        forces=json.load(archive.extractfile(f'independent_phonon/{case}/forces.json'))
        for key, path in [('cartesian',f'{case}/cartesian/component_times.jsonl'),
                          ('independent_phonon',f'independent_phonon/{case}/component_times.jsonl')]:
            rows = [json.loads(line) for line in archive.extractfile(path).read().splitlines()]
            if timing_records(rows) != summary[key]:
                raise ValueError(f'Benchmark timing ledger mismatch: {key}')
    with tarfile.open(result/'native_evidence.tar.gz') as archive:
        rows=[json.loads(line) for line in archive.extractfile('unified/component_times.jsonl').read().splitlines()]
        if timing_records(rows) != summary['unified']:
            raise ValueError('Unified timing differs from native evidence')
    separate = sum(summary['cartesian']['costs'].values()) + sum(summary['independent_phonon']['costs'].values())
    unified = sum(summary['unified']['costs'].values())
    difference([separate,unified,separate/unified],
               [summary['separate_total_core_h'],summary['unified_total_core_h'],summary['speedup']],
               1e-10,'benchmark totals')
    plan=summary['plan']
    for key,count in [('cartesian',plan['cartesian_BEC_SCFs']),
                      ('independent_phonon',plan['independent_phonon_SCFs']),
                      ('unified',plan['unified_BEC_and_phonon_SCFs'])]:
        if summary[key]['successful_SCFs'] != count:
            raise ValueError(f'Benchmark SCF count mismatch: {key}')
    original=json.loads((result/'response_fit.json').read_text())
    shared_manifest=json.loads((result/'shared_response.json').read_text())
    atoms=read_structure(result/'STRU')
    raw_u, _, modes_u=fit(atoms,shared_manifest,original['observations'],original['reference_forces_eV_A'])
    raw_c, _, _=fit(atoms,shared_manifest,cart['observations'],cart['reference_forces_eV_A'])
    if len(forces) != len(original['observations']):
        raise ValueError('Independent force observations incomplete')
    observations=[{**o,'forces_eV_A':f} for o,f in zip(original['observations'],forces)]
    raw_s, _, modes_s=fit(atoms,shared_manifest,observations,cart['reference_forces_eV_A'])
    difference(raw_c.born,cart['born_raw_e'],1e-9,'Cartesian reconstructed BEC')
    internal_u,_=internal_frequencies(modes_u)
    internal_s,_=internal_frequencies(modes_s)
    residuals=dict(max_raw_BEC_difference_e=float(np.max(abs(raw_c.born-raw_u.born))),
                   independent_force_Hessian_relative_difference=float(np.linalg.norm(
                       raw_s.force_constants-raw_u.force_constants)/np.linalg.norm(raw_u.force_constants)),
                   max_internal_frequency_difference_cm1=float(np.max(abs(internal_s-internal_u))))
    for key,value in residuals.items():
        difference([value],[summary[key]],1e-5 if key.endswith('cm1') else 1e-9,key)
    return dict(evidence_files=len(manifest),separate_core_hours=separate,
                unified_core_hours=unified,speedup=separate/unified,
                unrecorded_interrupted_attempts=summary.get('recovery',{}).get('unrecorded_interrupted_attempts',0),
                independently_reconstructed_differences=residuals)


def verify(case, archive=False, response_only=False):
    result = Path(case) / 'results'
    manifest = json.loads((result/'shared_response.json').read_text())
    recorded = json.loads((result/'response_fit.json').read_text())
    if manifest['dimension'] != 1 or manifest['displacement_scheme'] != 'phonopy':
        raise ValueError('Expected a unified 1D ensemble')
    atoms = read_structure(result/'STRU')
    ph = make_phonopy(atoms, symprec=manifest['symprec_A'])
    observations = recorded['observations']
    if [o['name'] for o in observations] != [s['name'] for s in manifest['stages']]:
        raise ValueError('Manifest/observation ordering differs')
    for stage, observation in zip(manifest['stages'], observations):
        if stage['atom'] != observation['atom']:
            raise ValueError('Displaced atom differs')
        difference(stage['displacement_A'], observation['displacement_A'],1e-12,'displacement')
    raw = reconstruct_responses(len(atoms), observations,
        symmetry_operations(ph,dimension=1), reference_forces=recorded['reference_forces_eV_A'])
    projected = project_response(raw)
    errors = {'raw_BEC_e':difference(raw.born,recorded['born_raw_e'],1e-9,'raw BEC'),
              'projected_BEC_e':difference(projected.born,recorded['born_projected_e'],1e-9,'projected BEC')}
    response = json.loads((result/'response.json').read_text())
    q = {q['name']:q for q in response['quantities']}
    if q['born_effective_charge']['axes'] != ['atom','displacement','polarization']:
        raise ValueError('Unexpected response-record BEC convention')
    errors['record_BEC_e'] = difference(projected.born.transpose(0,2,1),
        q['born_effective_charge']['values'],1e-9,'response record BEC')
    errors['record_force_constants_eV_A2'] = difference(projected.force_constants,
        q['force_constants']['values'],1e-9,'response record force constants')
    modes = spectra.load_gamma_modes(result/'qpoints.yaml')
    difference(modes.masses_amu,atoms.masses,1e-7,'mode masses')
    difference(modes.lattice_angstrom,atoms.cell,1e-7,'mode lattice')
    difference(modes.positions_fractional,atoms.scaled_positions,1e-7,'mode positions')
    ph.force_constants=projected.force_constants
    # Older Phonopy releases alias matrix storage when also returning eigenvectors.
    ph.run_qpoints([[0,0,0]],with_dynamical_matrices=True)
    errors['Gamma_frequency_THz']=difference(ph.qpoints.frequencies[0],
        modes.frequencies_thz,1e-6,'Gamma frequencies')
    dynamical=np.asarray(ph.qpoints.dynamical_matrices[0])
    eigenvalues=np.linalg.eigvalsh(dynamical)
    vectors=modes.eigenvectors.reshape(3*len(atoms),-1).T
    errors['eigenvector_orthonormality']=difference(vectors.conj().T@vectors,
        np.eye(len(eigenvalues)),1e-10,'eigenvector orthonormality')
    errors['dynamical_eigenvector_residual']=difference(dynamical@vectors,
        vectors*eigenvalues[None,:],1e-9,'dynamical eigenvectors')
    rigid = rigid_mode_audit(modes)
    selected = [r['mode'] for r in rigid if not r['classified_rigid']]
    if len(selected) != 3*len(atoms)-4 or any(
            r['frequency_cm1'] <= 0 for r in rigid if not r['classified_rigid']):
        raise ValueError('Rigid/internal mode classification requires review')
    if not response_only:
        born = spectra.read_born_data(result/'BEC.dat',natoms=len(atoms),dielectric_path=result/'BORN')
        ir = spectra.calculate_ir_spectrum(modes,born,dimensionality=1,mode_numbers=selected,
                                           broadening_cm1=8,points=3001)
        computed = np.column_stack([ir.frequency_grid_cm1,ir.spectrum,ir.spectrum.sum(axis=1)])
        errors['IR_spectrum'] = difference(computed,np.loadtxt(result/'IR/ir_spectrum.dat'),1e-9,'IR')
        with (result/'Raman/raman_modes.csv').open() as handle:
            numbers = [int(row['mode']) for row in csv.DictReader(handle)]
        if numbers != selected:
            raise ValueError('Raman archive does not cover all nonrigid modes in order')
        tensors = np.load(result/'Raman/raman_tensors.npy')
        raman = spectra.calculate_raman_spectrum(modes,numbers,tensors,temperature_K=298,
                                                 laser_nm=532,broadening_cm1=8,points=3001)
        errors['Raman_spectrum'] = difference(np.column_stack([raman.frequency_grid_cm1,raman.spectrum]),
            np.loadtxt(result/'Raman/raman_spectrum.dat'),1e-9,'Raman')
    return dict(case=Path(case).name, verified=True, displacement_SCFs=len(observations),
                reference_SCFs=1, nonrigid_modes=len(selected), maximum_errors=errors,
                evidence_files_verified=verify_archive(result/'native_evidence.tar.gz') if archive else None,
                benchmark=verify_benchmark(result) if archive and (result/'benchmark').exists() else None,
                spectra_verified=not response_only,
                scope=('Offline tensor and Gamma-mode reconstruction only.' if response_only else
                       'Offline tensor reconstruction and spectral contraction; not an independent electronic-structure calculation or literature-intensity validation.'))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--verify-archive',action='store_true')
    parser.add_argument('--response-only',action='store_true',
                        help='Verify a BEC/Gamma case without claiming IR/Raman validation.')
    args=parser.parse_args()
    print(json.dumps(verify(args.case,args.verify_archive,args.response_only),indent=2))
