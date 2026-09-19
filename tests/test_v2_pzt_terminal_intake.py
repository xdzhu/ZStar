"""Do not collect a running/failed job or silently repair malformed provenance."""
import importlib.util
from pathlib import Path

import pytest

_path = Path(__file__).resolve().parents[1]/'.codex-output/collect_pzt_exactsym_full.py'
_spec = importlib.util.spec_from_file_location('pzt_terminal_intake', _path)
intake = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(intake)


def test_terminal_accounting():
    row = intake.terminal_accounting('27722088|COMPLETED|0:0|7000|node47|32|\n', '27722088')
    assert row[3:6] == ['7000', 'node47', '32']


@pytest.mark.parametrize('text', [
    '27722088|RUNNING|0:0|7000|node47|32|\n',
    '27722088|FAILED|1:0|7000|node47|32|\n',
    '27722088|COMPLETED|0:0|7000|node47|40|\n',
    '27722088.batch|COMPLETED|0:0|7000|node47|32|\n',
    '27722088|COMPLETED|0:0|7000|node47|32|\n'*2,
])
def test_nonterminal_or_ambiguous_rejected(text):
    with pytest.raises(ValueError):
        intake.terminal_accounting(text, '27722088')


@pytest.mark.parametrize('text', ['{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}'])
def test_invalid_json_provenance(tmp_path, text):
    path = tmp_path/'provenance.json'
    path.write_text(text)
    with pytest.raises(ValueError):
        intake.load_json(path)
