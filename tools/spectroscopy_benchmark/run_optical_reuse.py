"""Add only static PYATB responses to private copies of completed DFT matrices."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

from zstar.pyatb_compat import _OPTICAL_BLOCK_RE, _POLARIZATION_BLOCK_RE, read_static_dielectric

BASE = Path('/home/zhuxd/abacus/agent-runs')
CASES = {
    'HfO2': (3, BASE/'20260904-shared-response-benchmark/hfo2/shared',
             BASE/'20260904-shared-response-benchmark/hfo2/cartesian'),
    'MoS2': (2, BASE/'20260904-eight-system-efficiency/MoS2/unified',
             BASE/'20260904-eight-system-efficiency/MoS2/cartesian'),
    'Sb2S3': (1, BASE/'20260905-one-dimensional/Sb2S3/unified',
              BASE/'20260906-one-dimensional-benchmark/Sb2S3/cartesian'),
    'CH4': (0, BASE/'20260904-molecular-relaxed-efficiency/CH4/unified',
            BASE/'20260904-molecular-relaxed-efficiency/CH4/cartesian'),
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def run(root, case, schemes):
    dimension, unified, cartesian = CASES[case]
    root = root.resolve() / case
    for scheme in schemes:
        source = unified if scheme == 'unified' else cartesian
        manifest = json.loads((source/'shared_response.json').read_text())
        reference_text = (source/'0.no-move/pyatb/Input').read_text()
        optical = _OPTICAL_BLOCK_RE.search(reference_text)
        if optical is None or not re.search(r'static_dielectric_only\s+1', optical[0]):
            raise ValueError(f'Reference lacks validated direct-static settings: {source}')
        out = root/scheme
        out.mkdir(parents=True, exist_ok=True)
        for name in ('STRU', 'shared_response.json', 'qpoints.yaml', 'phonopy.yaml', 'BORN', 'BEC.dat'):
            origin = source/name
            if name == 'BEC.dat' and not origin.exists():
                origin = next((source/alias for alias in ('bec.dat', 'Z-BORN-symm.out')
                               if (source/alias).is_file()), origin)
            shutil.copy2(origin, out/name)
        for stage in ['0.no-move'] + [s['name'] for s in manifest['stages']]:
            old = source/stage/'pyatb'
            private = out/stage
            completed = private/'completed.json'
            if completed.exists():
                saved = json.loads(completed.read_text())
                for filename, sha in saved['output_hashes'].items():
                    if digest(private/filename) != sha:
                        raise ValueError(f'Changed completed output: {private/filename}')
                continue
            if private.exists() and any(private.iterdir()):
                if not (private/'failed.json').is_file():
                    raise FileExistsError(f'Inspect incomplete private stage before retrying: {private}')
                private.rename(private.with_name(stage+'.failed-'+str(time.time_ns())))
            private.mkdir(parents=True, exist_ok=True)
            text = (old/'Input').read_text()
            text = _OPTICAL_BLOCK_RE.sub('', text)
            text = _POLARIZATION_BLOCK_RE.sub('', text).rstrip()+'\n\n'+optical[0]+'\n'
            hashes = {}
            for original in [old/'STRU', *old.glob('*.upf'), *old.glob('*.orb')]:
                shutil.copy2(original, private/original.name)
                hashes[str(original)] = digest(original)
            for key in ('HR_route', 'SR_route', 'rR_route'):
                match = re.search(r'(?m)^\s*'+key+r'\s+(\S+)\s*$', text)
                if not match:
                    raise ValueError(f'Missing {key}')
                original = Path(match[1])
                if not original.is_absolute():
                    original = old/original
                target = private/original.name
                hashes[str(original)] = digest(original)
                shutil.copy2(original, target)
                if target.is_symlink() or digest(target) != hashes[str(original)]:
                    raise ValueError('Private matrix copy is not identical')
                text = text[:match.start(1)] + target.name + text[match.end(1):]
            (private/'Input').write_text(text)
            (private/'source.json').write_text(json.dumps(dict(source=str(source/stage),
                source_input_sha256=digest(old/'Input'), matrices=hashes, dimension=dimension,
                additional_DFT_calls=0, optical_template=optical[0]), indent=2)+'\n')
            command = ['mpirun', '-np', '40', sys.executable, '-m',
                       'tools.spectroscopy_benchmark.precision_static']
            env = {**os.environ, 'OMP_NUM_THREADS':'1', 'MKL_NUM_THREADS':'1',
                   'OPENBLAS_NUM_THREADS':'1'}
            start = time.monotonic()
            record = dict(case=case, scheme=scheme, stage=stage, host=socket.gethostname(),
                          command=command, mpi=40, omp=1, additional_DFT_calls=0)
            try:
                with (private/'pyatb.log').open('w') as log:
                    subprocess.run(command, cwd=private, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, check=True)
                tensor, path = read_static_dielectric(private)
                for original, sha in hashes.items():
                    if digest(Path(original)) != sha:
                        raise ValueError('Source matrix changed during post-processing')
                record.update(success=True, epsilon=tensor.tolist(),
                              output_hashes={path.relative_to(private).as_posix():digest(path)})
            except Exception as error:
                record.update(success=False, error=str(error))
                raise
            finally:
                record['wall_seconds'] = time.monotonic()-start
                record['core_hours'] = record['wall_seconds']*40/3600
                with (out/'component_times.jsonl').open('a') as f:
                    f.write(json.dumps(record)+'\n')
                (private/('completed.json' if record['success'] else 'failed.json')).write_text(
                    json.dumps(record, indent=2)+'\n')
            print(case, scheme, stage, 'complete', record['core_hours'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--case', choices=list(CASES), required=True)
    p.add_argument('--schemes', nargs='+', choices=['unified', 'cartesian'], default=['unified', 'cartesian'])
    a = p.parse_args()
    run(a.root, a.case, a.schemes)
