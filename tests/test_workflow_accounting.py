import subprocess

import pytest

from zstar.workflow import StageState
from zstar.workflow_accounting import estimate_remaining_work, slurm_allocation_accounting


def test_slurm_allocation_uses_single_exact_row_and_advisory_budget(monkeypatch):
    def fake_run(command, **kwargs):
        assert command[:3] == ['sacct', '--jobs', '123_4']
        return subprocess.CompletedProcess(command, 0, '123_4|RUNNING|32|1800|\n123_4.batch|RUNNING|32|1800|\n', '')

    monkeypatch.setattr('zstar.workflow_accounting.subprocess.run', fake_run)
    report = slurm_allocation_accounting('123_4', budget_core_hours=20)
    assert report['allocated_core_hours'] == 16
    assert report['budget_remaining_core_hours'] == 4
    assert report['budget_enforced'] is False
    assert 'not a hard budget cap' in report['scope']
    with pytest.raises(ValueError, match='numeric Slurm'):
        slurm_allocation_accounting('123;echo bad')


def test_slurm_unavailable_or_ambiguous_does_not_fabricate_usage(monkeypatch):
    monkeypatch.setattr('zstar.workflow_accounting.subprocess.run',
                        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, '', ''))
    with pytest.raises(ValueError, match='accounting may not yet be available'):
        slurm_allocation_accounting('123')


def test_remaining_estimate_requires_two_completed_displacement_samples():
    def state(name, status, start=None, end=None):
        return StageState(name=name, path=name, status=status, started_at=start, finished_at=end)

    begin = '2026-11-02T00:00:00+00:00'
    states = [state('0.no-move', 'completed', begin, '2026-11-02T00:10:00+00:00'),
              state('disp-001', 'completed', begin, '2026-11-02T00:01:00+00:00'),
              state('disp-002', 'completed', begin, '2026-11-02T00:03:00+00:00'),
              state('disp-003', 'pending'), state('disp-004', 'failed')]
    report = estimate_remaining_work(states)
    assert report['completed_timing_samples'] == 2
    assert report['median_completed_stage_wall_seconds'] == 120
    assert report['estimated_remaining_wall_seconds'] == 240
    states[2].status = 'pending'
    assert estimate_remaining_work(states)['estimated_remaining_wall_seconds'] is None
