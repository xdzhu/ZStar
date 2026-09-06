"""Validate independent phonons and archive measured Separate/Unified evidence."""
from pathlib import Path
import hashlib
import json
import tarfile

import numpy as np

from analyze_archive import static_response
from molecular_validation import molecular_response
from separate_force_benchmark import ROOT, SOURCES, save
from zstar.shared_response import (make_phonopy, read_structure, reconstruct_responses,
                                  symmetry_operations, project_response)


def fit(atoms, metadata, observations, reference):
    ph = make_phonopy(atoms, symprec=metadata['symprec_A'])
    raw = reconstruct_responses(len(atoms), observations,
        symmetry_operations(ph, dimension=metadata['dimension']), reference_forces=reference)
    ph.force_constants = project_response(raw).force_constants
    ph.run_qpoints([[0, 0, 0]], with_eigenvectors=True)
    return raw, ph.qpoints.frequencies[0] * 33.3564095198152


def response(raw, born, atoms, metadata, reference):
    hessian = raw.force_constants.transpose(0, 2, 1, 3).reshape(3*len(atoms), -1)
    if metadata['dimension'] == 0:
        return molecular_response(hessian, born, atoms.positions, atoms.masses, reference)
    return static_response(hessian, born, {'cell_A': atoms.cell, 'masses_amu': atoms.masses},
                           metadata['dimension'])


def main():
    summaries = {}
    for case, source in SOURCES.items():
        output = ROOT / case
        completion = json.loads((output / 'completed.json').read_text())
        metadata = json.loads((source / 'shared_response.json').read_text())
        unified = json.loads((source / 'shared_response_result.json').read_text())
        cartesian = json.loads((source.parent / 'cartesian/shared_response_result.json').read_text())
        atoms = read_structure(source / 'STRU')
        forces = json.loads((output / 'forces.json').read_text())
        observations = [{**item, 'forces_eV_A': force} for item, force
                        in zip(unified['observations'], forces)]
        u, uf = fit(atoms, metadata, unified['observations'], unified['reference_forces_eV_A'])
        s, sf = fit(atoms, metadata, observations, cartesian['reference_forces_eV_A'])
        ur = response(u, u.born, atoms, metadata, unified['reference_forces_eV_A'])
        sr = response(s, np.asarray(cartesian['born_raw_e']), atoms, metadata,
                      cartesian['reference_forces_eV_A'])
        report = {'case': case, 'force_source': str(output),
                  'bec_source': str(source.parent / 'cartesian'),
                  'separate': sr, 'unified': ur,
                  'max_projected_frequency_difference_cm1': float(np.max(np.abs(uf-sf))),
                  'force_initialization': 'atomic charge, independent SCFs',
                  'reference_force_source': 'retained Cartesian reference',
                  'timing': completion}
        if sr['status'] == ur['status'] == 'computed':
            a, b = np.asarray(sr['tensor']), np.asarray(ur['tensor'])
            report['static_response_relative_difference'] = float(np.linalg.norm(a-b)/np.linalg.norm(a))
            if metadata['dimension'] == 0:
                report['max_internal_frequency_difference_cm1'] = float(np.max(np.abs(
                    np.asarray(sr['frequencies_cm1']) - ur['frequencies_cm1'])))
        else:
            raise RuntimeError(f'Invalid static response: {case}: {sr["status"]}, {ur["status"]}')
        save(output / 'validation.json', report)
        summaries[case] = report
    save(ROOT / 'summary.json', summaries)
    paths = [ROOT / 'summary.json']
    for case in SOURCES:
        out = ROOT / case
        paths += [out / n for n in ('plan.json', 'completed.json', 'forces.json',
                                    'validation.json', 'component_times.jsonl', 'STRU', 'phonopy_disp.yaml')]
        for pattern in ('disp-*/INPUT', 'disp-*/STRU', 'disp-*/KPT', 'disp-*/completed.json',
                        'disp-*/OUT.*/running_scf.log'):
            paths.extend(out.glob(pattern))
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    save(ROOT / 'manifest.json', {'source_root': str(ROOT), 'files': hashes})
    with tarfile.open(ROOT / 'independent-force-evidence.tar.gz', 'w:gz') as archive:
        for path in paths + [ROOT / 'manifest.json']:
            archive.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
    print(json.dumps({case: {'SCFs': item['timing']['SCFs'],
        'core_h': item['timing']['independent_force_core_hours'],
        'static_difference_percent': 100*item['static_response_relative_difference']}
        for case, item in summaries.items()}, indent=2))


if __name__ == '__main__':
    main()
