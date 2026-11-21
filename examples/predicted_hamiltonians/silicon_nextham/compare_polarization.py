from pathlib import Path
import argparse
import json
import math
import re


LIMIT = 0.001
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
LINE = re.compile(rf'direction is in ([abc]),\s*P\s*=\s*({NUMBER})\s*\(mod\s*({NUMBER})\)\s*C/m\^2')


def read_case(path):
    status_file = path / 'exit_status.txt'
    log = path / 'polarization.dat'
    if log.is_file() and not status_file.is_file():
        raise ValueError(f'Missing exit status for {path}')
    status = int(status_file.read_text().strip()) if status_file.is_file() else None
    result = {'exit_status': status, 'valid_output': False}
    if status != 0 or not log.is_file():
        return result
    values = LINE.findall(log.read_text())
    if len(values) != 3 or {axis for axis, _, _ in values} != {'a', 'b', 'c'}:
        raise ValueError(f'Expected one line for each of a, b, c in {log}')
    axes = {}
    for axis, reported, modulus in values:
        value, quantum = float(reported), float(modulus)
        if not (math.isfinite(value) and math.isfinite(quantum) and quantum > 0):
            raise ValueError(f'Invalid polarization or quantum for axis {axis} in {log}')
        reduced = value - round(value / quantum) * quantum
        axes[axis] = {'polarization_C_per_m2': value, 'quantum_C_per_m2': quantum,
                      'zero_branch_residual_C_per_m2': reduced}
    maximum = max(abs(axis['zero_branch_residual_C_per_m2']) for axis in axes.values())
    result.update(valid_output=True, axes=axes, max_abs_zero_branch_residual_C_per_m2=maximum,
                  zero_branch_passed=maximum <= LIMIT)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    root = parser.parse_args().directory
    results = dict(zero_branch_limit_C_per_m2=LIMIT,
                   systems={name: read_case(root / name) for name in ('predicted', 'initial')})
    text = json.dumps(results, indent=2) + '\n'
    (root / 'branch_residuals.json').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
