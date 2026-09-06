"""Only the missing matched normal-mode Raman controls; never rerun BEC/forces."""
import argparse
import json
import os
from pathlib import Path
import socket
import sys
import time

import numpy as np
from zstar import spectra, workflow
from zstar.pyatb_compat import _OPTICAL_BLOCK_RE
from tools.spectroscopy_benchmark.run_optical_reuse import CASES, digest
from tools.spectroscopy_benchmark.collect import optical_indices


def run(root, case, part=1, parts=1):
    if case not in {'MoS2', 'CH4', 'HfO2'}:
        raise ValueError('Existing direct controls must be reused for the other cases')
    if socket.gethostname().split('.')[0] not in {'cu23','cu24','cu25','cu26'}:
        raise RuntimeError('Unauthorized compute node')
    dimension, source, _ = CASES[case]
    reference = source/'0.no-move'
    gap = workflow.read_band_gap(reference/'pyatb-band', threshold_eV=.01)
    if not gap.insulating:
        raise ValueError('Reference is not insulating')
    modes = spectra.load_gamma_modes(source/'qpoints.yaml')
    selected = optical_indices(modes, dimension)
    if np.any(modes.frequencies_cm1[selected] <= 0):
        raise ValueError('Unstable internal vibrations')
    output = root/case/'direct_control'
    if not 1 <= part <= parts or parts > len(selected):
        raise ValueError('Invalid mode partition')
    if parts > 1:
        selected = selected[part-1::parts]
        output = output/f'part-{part}'
    output.mkdir(parents=True, exist_ok=True)
    folder = output/'raman'
    files = [reference/'INPUT-scf', reference/'KPT']
    files += sorted(reference.glob('*.upf')) + sorted(reference.glob('*.orb'))
    protected = [source/'STRU', source/'qpoints.yaml', *files,
                 *workflow._reference_charge_files(reference)]
    hashes = {str(p):digest(p) for p in protected}
    if not (folder/'raman_manifest.json').exists():
        spectra.prepare_raman_displacements(source/'STRU',modes,folder,
            amplitude=.02,mode_numbers=(selected+1).tolist(),copy_files=files,
            allow_imaginary=dimension == 0)
    optical = _OPTICAL_BLOCK_RE.search((reference/'pyatb/Input').read_text())[0]
    (output/'protocol.json').write_text(json.dumps(dict(
        case=case, source=str(source), gap=gap.to_dict(), source_hashes=hashes,
        optical_template=optical, mode_numbers=(selected+1).tolist(),
        role='Missing matched conventional control, not the Unified production route',
        expected_new_SCF_calls=2*len(selected), mpi_ABACUS=1, omp_ABACUS=40,
        mpi_PYATB=40, omp_PYATB=1),indent=2)+'\n')
    original = workflow._run_shell
    abacus = 'mpirun -np 1 /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus'
    binary = Path(sys.executable).parent
    pyatb = f'mpirun -np 40 {sys.executable} -m tools.spectroscopy_benchmark.precision_static'

    def timed(command, **kwargs):
        kind = 'ABACUS' if command == abacus else 'PYATB' if command == pyatb else 'preparation'
        omp = 40 if kind == 'ABACUS' else 1
        kwargs['env'] = {**kwargs['env'], 'OMP_NUM_THREADS':str(omp),
                         'MKL_NUM_THREADS':str(omp),'OPENBLAS_NUM_THREADS':'1'}
        if kind == 'PYATB':
            # Match the static kernel and k grid to the reused atomic ensemble.
            path = Path(kwargs['cwd'])/'Input'
            text = path.read_text()
            if not _OPTICAL_BLOCK_RE.search(text):
                raise ValueError('Missing generated optical block')
            path.write_text(_OPTICAL_BLOCK_RE.sub(lambda _: optical,text))
        record = dict(kind=kind, command=command, cwd=str(kwargs['cwd']),
                      host=socket.gethostname(), success=False,
                      mpi=40 if kind == 'PYATB' else 1, omp=omp)
        start = time.monotonic()
        try:
            value = original(command,**kwargs)
            record['success'] = True
            return value
        finally:
            record['wall_seconds'] = time.monotonic()-start
            record['allocated_core_hours'] = record['wall_seconds']*40/3600
            with (output/'component_times.jsonl').open('a') as f:
                f.write(json.dumps(record)+'\n')
            print(case,kind,record['cwd'],record['success'],record['wall_seconds'],flush=True)

    workflow._run_shell = timed
    try:
        workflow.run_raman_workflow(folder, reference_dir=reference,
            abacus_command=abacus,pyatb_input=str(binary/'pyatb_input'),
            pyatb_executable=str(binary/'pyatb'),pyatb_command=pyatb,
            dimensionality=dimension,omp_threads=40,mp_density=.08,
            check_insulating=False)  # Read-only positive reference gap checked above.
        for path,sha in hashes.items():
            if digest(Path(path)) != sha:
                raise ValueError(f'Source changed: {path}')
        numbers,tensors,kind = spectra.collect_raman_tensors(folder,
            dimensionality=dimension,cell_height_angstrom=modes.cell_height_angstrom,
            cell_volume_angstrom3=modes.volume_angstrom3)
        np.save(output/'mode_numbers.npy',numbers)
        np.save(output/'raman_tensors.npy',tensors)
        result = spectra.calculate_raman_spectrum(modes,numbers,tensors,tensor_kind=kind,
            temperature_K=298,laser_nm=532,broadening_cm1=8,points=3001,
            allow_imaginary=dimension == 0)
        spectra.write_raman_outputs(output/'spectrum',result)
        (output/'completed.json').write_text(json.dumps(dict(success=True,
            source_hashes_unchanged=True,mode_count=len(numbers)),indent=2)+'\n')
    finally:
        workflow._run_shell = original


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--case',choices=['MoS2','CH4','HfO2'],required=True)
    p.add_argument('--part',type=int,default=1)
    p.add_argument('--parts',type=int,default=1)
    a=p.parse_args()
    run(a.root,a.case,a.part,a.parts)
