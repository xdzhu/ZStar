"""Collect compact evidence from the independent methane acceptance run."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import zipfile

import numpy as np


def collect(root):
    case = root/'examples/IR_Raman_Spectra/Molecule_CH4'
    work = case/'work-rc6'
    events = [json.loads(line) for line in (work/'.zstar/workflow.jsonl').read_text().splitlines()]
    counts = Counter(item['event'] for item in events)
    states = [json.loads(p.read_text()) for p in sorted((work/'.zstar/stages').glob('*.json'))]
    assert len(states) == 4 and all(s['status'] == 'completed' for s in states)
    assert counts['scf-skip'] >= 4 and counts['pyatb-skip'] >= 4
    static = list((work/'spectra/static').glob('*/completed.json'))
    assert len(static) == 4
    rows = {}
    for name, folder in [('reference', case/'results/Unified'), ('rerun', work/'spectra')]:
        with (folder/'raman/raman_modes.csv').open() as stream:
            rows[name] = list(csv.DictReader(stream))
    frequencies = [np.array([float(row['frequency_cm-1']) for row in rows[name]])
                   for name in ('reference', 'rerun')]
    activities = [np.array([float(row['activity_normalized']) for row in rows[name]])
                  for name in ('reference', 'rerun')]
    np.testing.assert_allclose(frequencies[0], frequencies[1], rtol=0, atol=1e-3)
    np.testing.assert_allclose(activities[0], activities[1], rtol=0, atol=1e-4)
    comparison = dict(max_frequency_difference_cm1=float(np.max(np.abs(frequencies[0]-frequencies[1]))),
                      max_normalized_activity_difference=float(np.max(np.abs(activities[0]-activities[1]))),
                      note='Powder activities are basis invariant; individual tensors in degenerate subspaces need not coincide.')
    report = dict(scope='Fresh reference SCF and three displaced SCFs; repeat run resumes completed responses',
                  stages=states, workflow_event_counts=dict(counts), static_completed=4,
                  raman_mode_tables=rows, comparison=comparison,
                  environment='Private wheel venv using icu_copy solver dependencies; not the clean Windows dependency environments')
    (root/'methane-acceptance.json').write_text(json.dumps(report, indent=2)+'\n')
    selected = []
    for directory in (work/'.zstar', work/'spectra'):
        selected.extend(p for p in directory.rglob('*') if p.is_file() and
                        p.suffix in {'.json', '.jsonl', '.log', '.csv', '.dat', '.npy', '.pdf'} and
                        p.stat().st_size < 5_000_000)
    selected.extend(work/name for name in ('STRU', 'INPUT-scf', 'KPT', 'BEC.dat', 'BORN',
                                          'qpoints.yaml', 'shared_response.json'))
    selected.extend(p for p in work.glob('*/OUT.*/running_scf.log'))
    selected.extend(root/name for name in ('methane-acceptance.json', 'offline-spectra-comparison.json'))
    with zipfile.ZipFile(root/'cluster-evidence.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(selected)):
            if path.is_file():
                archive.write(path, path.relative_to(root))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    collect(parser.parse_args().root.resolve())
