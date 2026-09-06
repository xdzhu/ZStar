"""Merge independently timed normal-mode subsets without counting preparation."""
import argparse
import json
from pathlib import Path
import numpy as np


def merge(root, parts=4):
    numbers, tensors, times = [], [], []
    for i in range(1, parts+1):
        part = root/f'part-{i}'
        complete = json.loads((part/'completed.json').read_text())
        if not complete['success'] or not complete['source_hashes_unchanged']:
            raise ValueError(f'Invalid control {part}')
        protocol = json.loads((part/'protocol.json').read_text())
        assert [protocol[k] for k in ('mpi_ABACUS','omp_ABACUS','mpi_PYATB','omp_PYATB')] == [1,40,40,1]
        ns = np.load(part/'mode_numbers.npy')
        assert set(ns) == set(protocol['mode_numbers'])
        numbers.extend(ns)
        tensors.extend(np.load(part/'raman_tensors.npy'))
        rows = [json.loads(line) for line in (part/'component_times.jsonl').read_text().splitlines()]
        successful = [r for r in rows if r['success'] and r['kind'] in ('ABACUS','PYATB')]
        for kind in ('ABACUS','PYATB'):
            selected = [r for r in successful if r['kind'] == kind]
            assert len(selected) == 2*len(ns)
            assert len({r['cwd'] for r in selected}) == len(selected)
        times.extend(rows)
    assert len(numbers) == len(set(numbers))
    order = np.argsort(numbers)
    np.save(root/'mode_numbers.npy',np.array(numbers)[order])
    np.save(root/'raman_tensors.npy',np.array(tensors)[order])
    (root/'component_times.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in times))
    result = dict(success=True,source_hashes_unchanged=True,mode_count=len(numbers),
                  parts=parts,matched_parallelism=True)
    (root/'completed.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('root',type=Path)
    args=p.parse_args()
    merge(args.root)
