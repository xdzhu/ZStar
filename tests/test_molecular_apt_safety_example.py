import csv
import json
from pathlib import Path

import numpy as np


def test_ch4_position_apt_validation_record_keeps_scope_and_raw_sum():
    root = Path(__file__).parents[1] / 'examples/Benchmarks/Molecular_APT_Safety/results/CH4_HSE_DZP'
    rows = [line.split() for line in (root / 'BEC.raw.dat').read_text().splitlines()
            if line and not line.startswith('#')]
    tensors = np.array([[float(value) for value in row[2:]] for row in rows]).reshape(5, 3, 3)
    assert len(rows) == 5
    assert np.max(np.abs(tensors.sum(axis=0))) < 2e-5
    result = json.loads((root / 'spectra_result.json').read_text())
    assert result['molecular_apt_validation']['sum_consistency'] == 'pass'
    assert result['molecular_apt_validation']['independent_accuracy_validated'] is False
    assert 'no self-consistent local-field screening' in result['response_scope']['raman_electronic_response']
    for filename in ('ir_modes.csv', 'raman_modes.csv'):
        with (root / filename).open(newline='', encoding='utf-8') as handle:
            records = list(csv.DictReader(handle))
        assert len(records) == 9
        assert all(float(row['frequency_cm-1']) > 0 for row in records)
