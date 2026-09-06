"""Audit measured 1D costs and independent BEC/phonon reconstruction evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import tarfile

import numpy as np
from zstar.spectra import GammaModes
from tools.shared_response.one_dimensional_spectra import rigid_mode_audit
from zstar.shared_response import (make_phonopy, read_structure, reconstruct_responses,
                                  symmetry_operations, project_response)

DEFAULT_ROOT = Path('/home/zhuxd/abacus/agent-runs/20260906-one-dimensional-benchmark')
DEFAULT_SOURCE = Path('/home/zhuxd/abacus/agent-runs/20260905-one-dimensional')


def read(path):
    return json.loads(path.read_text())


def timing(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    return timing_records(rows)


def timing_records(rows):
    for row in rows:
        cost = row.get('allocated_core_hours', row.get('core_hours'))
        seconds = row.get('wall_seconds')
        cores = row.get('allocated_cores', row.get('mpi',0)*row.get('omp',0))
        if cost is None or seconds is None or cores <= 0 or not np.isfinite([cost,seconds]).all():
            raise ValueError('Incomplete or nonfinite timing evidence')
        if seconds < 0 or not np.isclose(cost,seconds*cores/3600,rtol=1e-10,atol=1e-12):
            raise ValueError('Recorded core-hours disagree with wall time and allocation')
    included = [r for r in rows if r.get('success') and r['kind'] != 'preparation']
    costs = {kind: sum(r.get('allocated_core_hours', r.get('core_hours', 0))
                      for r in included if r['kind'] == kind)
             for kind in ('ABACUS','PYATB','independent_force_scf')}
    return dict(successful_SCFs=sum(r['kind'] in ('ABACUS','independent_force_scf') for r in included),
                costs=costs, failed_calls=sum(not r.get('success') for r in rows),
                failed_core_hours=sum(r.get('allocated_core_hours', r.get('core_hours',0))
                                      for r in rows if not r.get('success')))


def fit(atoms, manifest, observations, f0):
    ph = make_phonopy(atoms, symprec=manifest['symprec_A'])
    raw = reconstruct_responses(len(atoms), observations,
        symmetry_operations(ph, dimension=1), reference_forces=f0)
    projected = project_response(raw)
    ph.force_constants = projected.force_constants
    ph.run_qpoints([[0,0,0]], with_eigenvectors=True)
    modes = GammaModes(
        frequencies_thz=np.asarray(ph.qpoints.frequencies[0]),
        eigenvectors=np.asarray(ph.qpoints.eigenvectors[0]).T.reshape(-1,len(atoms),3),
        masses_amu=atoms.masses, lattice_angstrom=np.asarray(atoms.cell),
        symbols=tuple(atoms.symbols), positions_fractional=atoms.scaled_positions)
    return raw, projected, modes


def internal_frequencies(modes):
    audit = rigid_mode_audit(modes)
    rigid = [r for r in audit if r['classified_rigid']]
    internal = [r['frequency_cm1'] for r in audit if not r['classified_rigid']]
    if len(rigid) != 4 or any(abs(r['frequency_cm1']) > 20 for r in rigid):
        raise ValueError('Rigid-mode classification requires review')
    if not internal or min(internal) <= 0:
        raise ValueError('Unstable internal Gamma mode requires review')
    return np.sort(internal), rigid


def audit(root, source, case):
    out, original = root/case, source/case/'unified'
    cart = out/'cartesian'
    force = root/'independent_phonon'/case
    plan = read(out/'plan.json')
    u, c, f = (timing(p/'component_times.jsonl') for p in (original,cart,force))
    state = dict(case=case, plan=plan, unified=u, cartesian=c, independent_phonon=f,
                 complete=False)
    if (force/'recovery.json').exists():
        state['recovery']=read(force/'recovery.json')
    if not (cart/'response_fit.json').exists() or not (force/'completed.json').exists():
        return state
    if c['successful_SCFs'] != plan['cartesian_BEC_SCFs'] or f['successful_SCFs'] != plan['independent_phonon_SCFs']:
        raise ValueError('Completed outputs and timed SCF counts disagree')
    if u['successful_SCFs'] != plan['unified_BEC_and_phonon_SCFs']:
        raise ValueError('Production timing completeness mismatch')
    ur, cr = read(original/'response_fit.json'), read(cart/'response_fit.json')
    manifest = read(original/'shared_response.json')
    atoms = read_structure(original/'STRU')
    forces = read(force/'forces.json')
    if len(forces) != len(ur['observations']):
        raise ValueError('Independent force observations incomplete')
    observations = [{**o, 'forces_eV_A':ff} for o,ff in zip(ur['observations'],forces)]
    raw_u, proj_u, modes_u = fit(atoms,manifest,ur['observations'],ur['reference_forces_eV_A'])
    raw_s, proj_s, modes_s = fit(atoms,manifest,observations,cr['reference_forces_eV_A'])
    freq_u, freq_s = modes_u.frequencies_cm1, modes_s.frequencies_cm1
    internal_u, rigid_u = internal_frequencies(modes_u)
    internal_s, rigid_s = internal_frequencies(modes_s)
    # Dipoles in this force-only reconstruction are only an unchanged carrier;
    # the actual Separate BEC tensor must come from the Cartesian calculation.
    separate_born = np.asarray(cr['born_raw_e'])
    unified_cost = sum(u['costs'].values())
    bec_cost = sum(c['costs'].values())
    phonon_cost = sum(f['costs'].values())
    separate_cost = bec_cost + phonon_cost
    state.update(complete=True, separate_BEC_core_h=bec_cost,
                 separate_phonon_core_h=phonon_cost, separate_total_core_h=separate_cost,
                 unified_total_core_h=unified_cost, speedup=separate_cost/unified_cost,
                 saved_fraction=1-unified_cost/separate_cost,
                 max_raw_BEC_difference_e=float(np.max(abs(separate_born-np.asarray(ur['born_raw_e'])))),
                 max_projected_frequency_difference_cm1=float(np.max(abs(freq_s-freq_u))),
                 max_internal_frequency_difference_cm1=float(np.max(abs(internal_s-internal_u))),
                 internal_modes=len(internal_u),
                 rigid_mode_audit={'unified':rigid_u,'separate':rigid_s},
                 independent_force_Hessian_relative_difference=float(np.linalg.norm(
                     raw_s.force_constants-raw_u.force_constants)/np.linalg.norm(raw_u.force_constants)),
                 separate_Gamma_frequencies_cm1=freq_s.tolist(),
                 unified_Gamma_frequencies_cm1=freq_u.tolist(),
                 reference_force_max_difference_eV_A=float(np.max(abs(
                     np.asarray(cr['reference_forces_eV_A'])-ur['reference_forces_eV_A']))),
                 scope='BEC and Gamma Hessian; exclude relaxation and Raman; retain rigid modes in this diagnostic.',
                 raw_BEC_convention=cr['tensor_convention'])
    (out/'benchmark_summary.json').write_text(json.dumps(state,indent=2)+'\n')
    return state


def archive(root, case):
    out = root/case
    force = root/'independent_phonon'/case
    paths = [out/'plan.json', out/'benchmark_summary.json']
    for directory in (out/'cartesian', force):
        for pattern in ('*.json','*.jsonl','STRU','*.yaml','bec*.dat','BORN','FORCE_CONSTANTS*',
                        '0.no-move/OUT.*/running_scf.log','disp-*/OUT.*/running_scf.log',
                        '*/INPUT*','*/STRU','*/KPT','*/completed.json'):
            paths.extend(directory.glob(pattern))
    if (force/'recovery').exists():
        paths.extend(p for p in (force/'recovery').rglob('*') if p.is_file()
                     and (p.suffix in ('.json','.log') or p.name in ('INPUT','STRU','KPT','abandoned-worker.lock')))
    paths = sorted({p for p in paths if p.is_file()})
    manifest = {str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in paths}
    checksum = out/'benchmark_manifest.json'
    checksum.write_text(json.dumps(manifest,indent=2)+'\n')
    with tarfile.open(out/'benchmark_evidence.tar.gz','w:gz') as tar:
        for path in paths+[checksum]:
            if path.is_symlink():
                raise ValueError('Archive sources must not be symlinks')
            tar.add(path,arcname=path.relative_to(root).as_posix(),recursive=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    parser.add_argument('--source',type=Path,default=DEFAULT_SOURCE)
    parser.add_argument('--case',choices=['BN_9_0','Sb2S3'],required=True)
    parser.add_argument('--archive',action='store_true')
    args=parser.parse_args()
    report=audit(args.root,args.source,args.case)
    if report['complete'] and args.archive:
        archive(args.root,args.case)
    print(json.dumps(report,indent=2))
