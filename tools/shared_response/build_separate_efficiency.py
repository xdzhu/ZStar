"""Combine actual BEC and independent-force ledgers without replacing old controls."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build(include_one_dimensional=False):
    old = json.loads((ROOT / 'docs/research/eight_system_efficiency.json').read_text())
    base = ROOT / 'examples/Benchmarks/independent_phonons/results'
    manifest = json.loads((base / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Independent force evidence changed: {name}')
    new = json.loads((base / 'summary.json').read_text())
    cases = {}
    for name, record in old['cases'].items():
        item = new.get(name, {})
        timing = item.get('timing', {})
        nforce = timing.get('SCFs', 0)
        force_cost = timing.get('independent_force_core_hours', 0.)
        if name != 'cubic_BaTiO3':
            if timing.get('status') != 'completed':
                raise ValueError(f'Missing completed independent force evidence: {name}')
            stage_cost = sum(json.loads(p.read_text())['core_hours']
                             for p in (base / name).glob('disp-*/completed.json'))
            if abs(stage_cost-force_cost) > 1e-10:
                raise ValueError(f'Completed-stage timing mismatch: {name}')
        separate = record['solver_core_hours']['Cartesian'] + force_cost
        unified = record['solver_core_hours']['Unified']
        cases[name] = {
            'BEC_Separate': record['counts']['Cartesian'][0],
            'BEC_Unified': record['counts']['Unified'][0],
            'SCF_Separate': record['counts']['Cartesian'][1] + nforce,
            'SCF_Unified': record['counts']['Unified'][1],
            'core_h_Separate': separate, 'core_h_Unified': unified,
            'speedup': separate/unified,
            'independent_force_core_h_added': force_cost,
            'static_response_relative_difference': item.get('static_response_relative_difference'),
        }
    sources = {}
    if include_one_dimensional:
        from tools.shared_response.verify_one_dimensional_example import verify_benchmark
        for name, folder in [('BN_9_0','Nanotube_BN_9_0'),('Sb2S3','Nanowire_Sb2S3')]:
            result=ROOT/'examples/IR_Raman_Spectra'/folder/'results'
            summary=result/'benchmark/benchmark_summary.json'
            if not summary.is_file():
                raise ValueError(f'Missing completed 1D benchmark: {name}')
            verify_benchmark(result)
            data=json.loads(summary.read_text())
            plan=data['plan']
            cases[name] = {
                'BEC_Separate':plan['cartesian_displacements'],
                'BEC_Unified':plan['unified_displacements'],
                'SCF_Separate':plan['cartesian_BEC_SCFs']+plan['independent_phonon_SCFs'],
                'SCF_Unified':plan['unified_BEC_and_phonon_SCFs'],
                'core_h_Separate':data['separate_total_core_h'],
                'core_h_Unified':data['unified_total_core_h'],
                'speedup':data['speedup'],
                'independent_force_core_h_added':data['separate_phonon_core_h'],
                'static_response_relative_difference':None,
            }
            sources[name]={'path':summary.relative_to(ROOT).as_posix(),
                           'sha256':hashlib.sha256(summary.read_bytes()).hexdigest()}
    return {'definition': 'Measured Separate BEC/APT and independent force SCFs versus Unified.',
            'caveat': 'Non-cubic-BaTiO3 retained BEC routes already requested forces. That output cost '
                      'was not subtracted; independent force tasks supply the Separate phonons.',
            'original_joint_control_record': 'eight_system_efficiency.json',
            'one_dimensional_sources':sources, 'cases': cases}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/research/separate_unified_efficiency.json')
    parser.add_argument('--include-one-dimensional', action='store_true',
                        help='Require and hash-check both completed 1D controls before merging.')
    args = parser.parse_args()
    data = build(args.include_one_dimensional)
    args.output.write_text(json.dumps(data, indent=2) + '\n')
    with args.output.with_suffix('.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['case', *next(iter(data['cases'].values()))])
        writer.writeheader()
        writer.writerows({'case': name, **value} for name, value in data['cases'].items())
    print(json.dumps(data, indent=2))
