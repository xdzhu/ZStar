"""Archive completed 1D results and compact native evidence without scratch arrays."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
from zstar.artifacts import resolve_artifact


def archive(root, output):
    state = json.loads((root / 'unified/worker.json').read_text())
    if state['status'] != 'finished-awaiting-response-and-mode-audit':
        raise ValueError('Response workflow has not completed')
    partitions = sorted((root / 'raman').glob('part-*/worker.json'))
    if not partitions or any(json.loads(p.read_text())['status'] !=
                             'completed-awaiting-tensor-audit' for p in partitions):
        raise ValueError('Raman workers have not completed')
    required = ['unified/response_fit.json', 'unified/qpoints.yaml', 'unified/BORN',
                'unified/BEC.dat', 'unified/FORCE_CONSTANTS', 'unified/STRU',
                'ir/ir_summary.json', 'raman_spectrum/raman_summary.json',
                'raman_spectrum/raman_tensors.npy', 'rigid-mode-audit.json',
                'relaxation-audit.json']
    paths = {resolve_artifact(root / name, explicit=False) for name in required}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    for directory in ['seed', 'response-seed', 'ir', 'raman_spectrum']:
        paths.update(p for p in (root / directory).rglob('*') if p.is_file())
    for pattern in ['*.json', 'unified/*', 'relaxation/INPUT', 'relaxation/KPT',
                    'relaxation/STRU', 'relaxation/worker.json',
                    'relaxation/OUT.*/running_cell-relax.log', 'relaxation/OUT.*/STRU_ION_D',
                    'unified/*/INPUT*', 'unified/*/STRU', 'unified/*/KPT',
                    'unified/*/zstar*.json', 'unified/*/OUT.*/running_scf.log',
                    'unified/*/pyatb*/Input', 'unified/*/pyatb*/zstar*.json',
                    'unified/*/pyatb*/Out/*/*.dat',
                    'raman/*.json', 'raman/part-*/*.json', 'raman/part-*/*.jsonl',
                    'raman/mode-*/*/INPUT*', 'raman/mode-*/*/STRU',
                    'raman/mode-*/*/KPT', 'raman/mode-*/*/OUT.*/running_scf.log',
                    'raman/mode-*/*/pyatb/Input', 'raman/mode-*/*/pyatb/zstar*.json',
                    'raman/mode-*/*/pyatb/Out/*/*.dat']:
        paths.update(p for p in root.glob(pattern) if p.is_file())
    records = []
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError(f'Archive must contain private regular files: {path}')
        records.append(dict(path=path.relative_to(root).as_posix(),
                            size=path.stat().st_size,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    metadata = dict(case=root.name, source=str(root), files=records,
                    scope='Completed computation evidence, not a claim of literature agreement.',
                    excluded='Charge cubes, sparse matrices, wavefunctions and executable binaries.')
    with output.open('xb') as stream, tarfile.open(fileobj=stream, mode='w:gz') as tar:
        for row in records:
            tar.add(root / row['path'], arcname=row['path'], recursive=False)
        payload = (json.dumps(metadata, indent=2) + '\n').encode()
        entry = tarfile.TarInfo('evidence_manifest.json')
        entry.size = len(payload)
        tar.addfile(entry, io.BytesIO(payload))
    print(json.dumps(dict(files=len(records), archive_bytes=output.stat().st_size,
                          archive_sha256=hashlib.sha256(output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case_root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    archive(args.case_root, args.output)
