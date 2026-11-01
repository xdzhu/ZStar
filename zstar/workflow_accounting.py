"""Optional Slurm allocation accounting and cautious progress estimates."""

from __future__ import annotations

from datetime import datetime
import math
import os
import re
import statistics
import subprocess
from typing import Iterable

from .workflow import StageState


def estimate_remaining_work(states: Iterable[StageState]) -> dict:
    """Estimate unfinished serial displacements from completed displacement times."""
    states = [state for state in states if state.name != '0.no-move' and not state.name.startswith('dielectric-')]
    unfinished = [state for state in states if state.status != 'completed']
    durations = []
    for state in states:
        if state.status != 'completed' or not state.started_at or not state.finished_at:
            continue
        try:
            elapsed = (datetime.fromisoformat(state.finished_at) - datetime.fromisoformat(state.started_at)).total_seconds()
        except (ValueError, TypeError):
            continue
        if elapsed > 0 and math.isfinite(elapsed):
            durations.append(elapsed)
    # A running displacement is counted in full: this is an estimate rather
    # than a prediction of remaining scheduler allocation or billed time.
    median = statistics.median(durations) if len(durations) >= 2 else None
    return {'unfinished_displacements': len(unfinished), 'completed_timing_samples': len(durations),
            'median_completed_stage_wall_seconds': median,
            'estimated_remaining_wall_seconds': None if median is None else median * len(unfinished),
            'scope': 'Rough serial estimate from completed displacement stages; running stages counted in full. '
                     'Queue time and future stage variability are not included.'}


def slurm_allocation_accounting(job_id: str | None = None, *, budget_core_hours: float | None = None) -> dict:
    """Query exactly one Slurm allocation; budget is advisory and not enforced."""
    job = str(job_id or os.environ.get('SLURM_JOB_ID', '')).strip()
    if not re.fullmatch(r'\d+(?:_\d+)?', job):
        raise ValueError('Provide a numeric Slurm --job-id (optionally array job_index)')
    if budget_core_hours is not None and (not math.isfinite(budget_core_hours) or budget_core_hours <= 0):
        raise ValueError('budget_core_hours must be positive and finite')
    command = ['sacct', '--jobs', job, '--parsable2', '--noheader', '--allocations',
               '--format=JobIDRaw,State,AllocCPUS,ElapsedRaw']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f'Cannot query Slurm sacct for {job}: {exc}') from exc
    if result.returncode:
        raise RuntimeError(f'Slurm sacct failed for {job}: {result.stderr.strip()}')
    rows = [line.strip().split('|') for line in result.stdout.splitlines() if line.strip()]
    matches = [row for row in rows if len(row) >= 4 and row[0] == job]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one Slurm allocation row for {job}; accounting may not yet be available')
    try:
        cores, seconds = int(matches[0][2]), int(matches[0][3])
    except ValueError as exc:
        raise ValueError(f'Incomplete Slurm allocation accounting for {job}') from exc
    if cores < 0 or seconds < 0:
        raise ValueError('Slurm allocation accounting contains negative resources')
    allocated = cores * seconds / 3600.0
    return {'scheduler': 'slurm', 'job_id': job, 'state': matches[0][1], 'allocated_cpus': cores,
            'elapsed_seconds': seconds, 'allocated_core_hours': allocated,
            'budget_core_hours': budget_core_hours,
            'budget_remaining_core_hours': None if budget_core_hours is None else budget_core_hours - allocated,
            'budget_exceeded': None if budget_core_hours is None else allocated > budget_core_hours,
            'budget_enforced': False,
            'scope': 'One Slurm allocation only; allocated CPUs multiplied by elapsed wall time. '
                     'Not scheduler billing, not a campaign total, and not a hard budget cap.'}
