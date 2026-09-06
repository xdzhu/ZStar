"""Count successful PYATB calls in the production components of Tables 14/15."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tarfile

from tools.shared_response.example_paths import CASE_PATHS

ROOT = Path(__file__).resolve().parents[2]


def records(path, member=None):
    if member is None:
        payload = path.read_bytes()
    else:
        with tarfile.open(path) as archive:
            payload = archive.extractfile(member).read()
    rows = [json.loads(line) for line in payload.decode().splitlines() if line.strip()]
    return rows, {
        'path': path.relative_to(ROOT).as_posix(), 'member': member,
        'sha256': hashlib.sha256(payload).hexdigest(),
    }


def summarize(path, member=None, static=False):
    rows, source = records(path, member)
    counts = Counter()
    costs = Counter()
    for row in rows:
        if not row.get('success', True):
            continue
        kind = row.get('kind')
        if kind not in ('ABACUS', 'PYATB', 'preparation', 'independent_force_scf'):
            command = row['command']
            if static:
                if 'tools.spectroscopy_benchmark.precision_static' not in command:
                    raise ValueError(f'Unexpected static command: {command}')
                kind = 'PYATB'
            elif command.rstrip().endswith('/abacus'):
                kind = 'ABACUS'
            elif 'pyatb_input' in command:
                kind = 'preparation'
            elif command.rstrip().endswith('/pyatb') or '-m zstar.pyatb_precision' in command:
                kind = 'PYATB'
            else:
                raise ValueError(f'Unclassified command: {command}')
        if kind == 'preparation':
            continue
        if kind not in ('ABACUS', 'PYATB', 'independent_force_scf'):
            raise ValueError(f'Unknown solver kind: {kind}')
        counts[kind] += 1
        cost = row.get('allocated_core_hours', row.get('core_hours', row.get('reserved_core_hours')))
        if cost is None:
            cost = row['wall_seconds'] * row['allocated_cores'] / 3600
        costs[kind] += cost
    return {'calls': dict(counts), 'costs': dict(costs), 'source': source}


def close(actual, expected):
    if abs(actual - expected) > 1e-8:
        raise ValueError(f'Production cost mismatch: {actual} != {expected}')


def build():
    baseline = json.loads((ROOT/'docs/research/separate_unified_efficiency.json').read_text())['cases']
    original = json.loads((ROOT/'docs/research/eight_system_efficiency.json').read_text())['cases']
    tables = {'BEC_phonon': {}, 'IR_Raman': {}}
    for case, expected in baseline.items():
        evidence = {}
        if case in CASE_PATHS:
            for scheme in ('Separate', 'Unified'):
                pieces = []
                for oldpath, digest in original[case]['timing_sha256'].items():
                    relative = Path(oldpath).relative_to(case)
                    is_unified = relative.parts[1] in ('unified', 'shared')
                    if is_unified != (scheme == 'Unified'):
                        continue
                    part = summarize(ROOT/'examples'/CASE_PATHS[case]/relative)
                    if part['source']['sha256'] != digest:
                        raise ValueError(f'Changed production ledger: {oldpath}')
                    pieces.append(part)
                evidence[scheme] = pieces
        else:
            folder = 'Nanotube_BN_9_0' if case == 'BN_9_0' else 'Nanowire_Sb2S3'
            result = ROOT/'examples/IR_Raman_Spectra'/folder/'results'
            evidence['Unified'] = [summarize(result/'native_evidence.tar.gz', 'unified/component_times.jsonl')]
            evidence['Separate'] = [summarize(result/'benchmark/benchmark_evidence.tar.gz',
                                            f'{case}/cartesian/component_times.jsonl')]
        row = {'components': evidence}
        for scheme, parts in evidence.items():
            measured = sum(sum(p['costs'].values()) for p in parts)
            if scheme == 'Separate' and case != 'cubic_BaTiO3':
                measured += expected['independent_force_core_h_added']
            close(measured, expected[f'core_h_{scheme}'])
            row[f'NSCF_{scheme}'] = sum(p['calls'].get('PYATB', 0) for p in parts)
        tables['BEC_phonon'][case] = row

    spec = ROOT/'docs/research/unified_spectroscopy_20260906'
    for expected in json.loads((spec/'summary.json').read_text())['records']:
        case = expected['case']
        base = tables['BEC_phonon']['t_HfO2' if case == 'HfO2' else case]
        extra = summarize(spec/'evidence'/case/'unified/component_times.jsonl', static=True)
        if case == 'Sb2S3':
            direct = summarize(ROOT/'examples/IR_Raman_Spectra/Nanowire_Sb2S3/results/native_evidence.tar.gz',
                               'raman/part-1/component_times.jsonl')
        else:
            direct = summarize(spec/'evidence'/case/'direct_control/component_times.jsonl')
        close(sum(extra['costs'].values()), expected['new_static_postprocessing_core_h'])
        close(sum(direct['costs'].values()), expected['old_mode_Raman_core_h'])
        if direct['calls']['ABACUS'] != expected['Raman_mode_SCF_old']:
            raise ValueError(f'Raman SCF mismatch: {case}')
        tables['IR_Raman'][case] = {
            'NSCF_Separate': base['NSCF_Separate'] + direct['calls']['PYATB'],
            'NSCF_Unified': base['NSCF_Unified'] + extra['calls']['PYATB'],
            'components': {'additional_Separate': direct, 'additional_Unified': extra},
        }
    return {'definition': 'N_NSCF counts successful PYATB solver invocations in the timed production '
            'components, including the reference band check. Multiple observables in one invocation '
            'count once; input preparation, failed attempts and unrelated validation are excluded. '
            'This is not an ABACUS NSCF or k-point count. Independent force-only SCFs add no PYATB calls.',
            'tables': tables}


def check_manuscript(path, data):
    text = path.read_text(encoding='utf-8')
    layouts = [
        ('tab:unified_efficiency', 'BEC_phonon',
         ['cubic_BaTiO3', 'SiC', 't_HfO2', 'alpha_In2Se3', 'hBN', 'MoS2',
          'BN_9_0', 'Sb2S3', 'H2O', 'CH4']),
        ('tab:unified_spectra_efficiency', 'IR_Raman', ['HfO2', 'MoS2', 'Sb2S3', 'CH4']),
    ]
    for label, table, cases in layouts:
        block = text.split('\\label{' + label + '}', 1)[1].split('\\end{table}', 1)[0]
        body = block.split('\\midrule', 1)[1].split('\\bottomrule', 1)[0]
        rows = [r.strip() for r in re.split(r'\\\\', body) if r.strip()]
        if len(rows) != len(cases):
            raise ValueError(f'Unexpected table rows: {label}')
        for row, case in zip(rows, cases):
            cells = [c.strip() for c in row.split('&')]
            expected = data['tables'][table][case]
            if len(cells) != 10 or [int(cells[i]) for i in (5, 6)] != [
                    expected['NSCF_Separate'], expected['NSCF_Unified']]:
                raise ValueError(f'Manuscript NSCF mismatch: {case}')
    print('Manuscript: all 14 NSCF pairs agree with production ledgers.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--manuscript', type=Path)
    args = parser.parse_args()
    data = build()
    if args.manuscript:
        check_manuscript(args.manuscript, data)
    if args.output:
        args.output.write_text(json.dumps(data, indent=2) + '\n')
    for table, rows in data['tables'].items():
        print(table)
        for case, row in rows.items():
            print(f"  {case}: {row['NSCF_Separate']} / {row['NSCF_Unified']}")
