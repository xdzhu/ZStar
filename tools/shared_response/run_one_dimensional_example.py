"""Portable, resumable runner for the archived unpassivated 1D examples."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import numpy as np
from phonopy.interface.abacus import read_abacus_output

from zstar import workflow
from zstar.pyatb_precision import precision_command
from zstar.shared_abacus import collect_shared_abacus, prepare_shared_abacus

# Load the installed package before exposing repository-only example helpers.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.shared_response.one_dimensional_spectra import collect, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--method', choices=['unified','mode'], default='unified')
    parser.add_argument('--stage', choices=['all', 'response', 'raman', 'post'], default='all')
    parser.add_argument('--abacus-command', default=os.environ.get('ABACUS_COMMAND', 'abacus'))
    parser.add_argument('--pyatb-command', default=os.environ.get('PYATB_COMMAND', 'pyatb'))
    parser.add_argument('--omp-threads', type=int, default=int(os.environ.get('OMP_NUM_THREADS', '1')))
    args = parser.parse_args()
    case = args.case.resolve()
    work = (args.work or case / 'work').resolve()
    if args.omp_threads < 1:
        parser.error('--omp-threads must be positive')
    if work == case or work in (case / 'run', case / 'results') or any(
            protected in work.parents for protected in [case / 'run', case / 'results']):
        parser.error('Work must not overwrite case inputs or archived results')
    seed = case / 'run'
    for name in ['STRU', 'INPUT', 'KPT']:
        if not (seed / name).is_file():
            parser.error(f'Missing input: {seed / name}')
    source = sorted(p for p in seed.iterdir() if p.is_file())
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
    print(json.dumps(dict(work=str(work), stage=args.stage, dimension=1,
                         abacus=args.abacus_command, pyatb=args.pyatb_command,
                         seed_sha256=hashes, dry_run=args.dry_run), indent=2))
    if args.dry_run:
        print('Reference + Phonopy displacements -> BEC and Gamma modes -> IR and Raman. No solver started.')
        return
    if not (work / 'seed_manifest.json').exists():
        if work.exists() and any(work.iterdir()):
            parser.error('Nonempty work directory has no matching seed manifest')
        (work / 'seed').mkdir(parents=True)
        for p in source:
            shutil.copy2(p, work / 'seed' / p.name)
        (work / 'seed_manifest.json').write_text(json.dumps(hashes, indent=2) + '\n')
    elif json.loads((work / 'seed_manifest.json').read_text()) != hashes:
        parser.error('Inputs changed since this work directory was seeded; choose a new --work')
    response = work / 'unified'
    if args.stage in ['all', 'response']:
        if not (response / 'shared_response.json').exists():
            prepare_shared_abacus(work / 'seed/STRU', root=response,
                                  scf_input=work / 'seed/INPUT', dimension=1,
                                  symprec=1e-5, method='auto')
        settings = dict(abacus_command=args.abacus_command,
            pyatb_command=precision_command(args.pyatb_command),
            dimensionality=1, omp_threads=args.omp_threads, mp_density=.08)
        workflow.run_serial_workflow(response, stop_after=1, **settings)
        log, = (response / '0.no-move').glob('OUT.*/running_scf.log')
        maximum = float(np.max(np.linalg.norm(read_abacus_output(str(log)), axis=1)))
        if maximum > .005:
            raise ValueError(f'Reference forces exceed the example gate: {maximum} eV/A')
        workflow.run_serial_workflow(response, **settings)
        collect_shared_abacus(response)
    if args.method == 'unified' and args.stage in ['all','raman','post']:
        from zstar import unified_spectra
        target=work/'spectra'
        if not (target/'.zstar/spectra.json').exists():
            unified_spectra.prepare(target,response)
        if args.stage != 'post':
            unified_spectra.run(target,abacus_command=args.abacus_command,
                pyatb_command=args.pyatb_command,omp_threads=args.omp_threads,mp_density=.08)
        unified_spectra.collect(target)
    elif args.stage in ['all', 'raman']:
        if not (work / 'raman/raman_manifest.json').exists():
            prepare(work, 1)
        workflow.run_raman_workflow(
            work / 'raman', reference_dir=response / '0.no-move',
            abacus_command=args.abacus_command,
            pyatb_command=precision_command(args.pyatb_command),
            dimensionality=1, omp_threads=args.omp_threads, mp_density=.08)
        collect(work)
    elif args.stage == 'post':
        collect(work)


if __name__ == '__main__':
    main()
