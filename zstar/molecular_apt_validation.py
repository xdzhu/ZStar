"""Provenance checks for a molecular APT consumed by downstream workflows."""

from __future__ import annotations

import json
from pathlib import Path

from .abacus_assets import sha256_file


RECEIPT = Path('.zstar/molecular_apt_validation.json')
PENDING = Path('.zstar/molecular_apt_validation.pending')
LEGACY_RECEIPT = Path('.zstar/legacy_molecular_apt_validation.json')
LEGACY_PENDING = Path('.zstar/legacy_molecular_apt_validation.pending')


def verify_molecular_apt_receipt(root: str | Path) -> dict:
    """Verify inputs and outputs; a passing sum rule is not accuracy proof."""
    root = Path(root).resolve()
    if (root / PENDING).exists():
        raise ValueError('A molecular APT collection is incomplete; rerun postprocessing before using BEC.dat')
    path = root / RECEIPT
    if not path.is_file():
        raise ValueError('No molecular APT validation receipt exists; a pre-existing 0D BEC.dat is unverified')
    data = json.loads(path.read_text(encoding='utf-8'))
    if (data.get('schema') != 'zstar-molecular-apt-validation'
            or data.get('version') != 1 or data.get('sum_consistency') != 'pass'
            or data.get('method') != 'abacus_r0_position_expectation_experimental'
            or data.get('independent_accuracy_validated') is not False):
        raise ValueError(f'Molecular APT validation receipt is invalid or failed: {path}')
    sources = data.get('source_sha256')
    if not isinstance(sources, dict) or not sources:
        raise ValueError('Molecular APT receipt lacks source fingerprints')
    outputs = data.get('output_sha256')
    required = {'shared_response.json', 'response_fit.json', 'BEC.dat', 'qpoints.yaml'}
    if (not isinstance(outputs, dict) or not required.issubset(outputs)
            or set(outputs) - required - {'BORN'}):
        raise ValueError('Molecular APT receipt lacks required output fingerprints')
    for name, digest in outputs.items():
        source = root / name
        if not source.is_file() or sha256_file(source) != digest:
            raise ValueError(f'Molecular APT output changed or is missing: {source}')
    for name, digest in sources.items():
        source = Path(name)
        if not source.is_absolute():
            source = (root / source).resolve()
            if not source.is_relative_to(root):
                raise ValueError(f'Molecular APT source leaves its root: {name}')
        if not source.is_file() or sha256_file(source) != digest:
            raise ValueError(f'Molecular APT source changed or is missing: {source}')
    return data


def verify_legacy_molecular_apt_receipt(root: str | Path) -> dict:
    """Verify legacy Cartesian source and output fingerprints before reuse."""
    root = Path(root).resolve()
    if (root / LEGACY_PENDING).exists():
        raise ValueError('Legacy molecular APT collection is incomplete')
    path = root / LEGACY_RECEIPT
    if not path.is_file():
        raise ValueError('Legacy molecular APT has no validation receipt')
    data = json.loads(path.read_text(encoding='utf-8'))
    if (data.get('schema') != 'zstar-legacy-molecular-apt-validation' or data.get('version') != 1
            or data.get('method') != 'abacus_r0_position_expectation_experimental'
            or data.get('sum_consistency') != 'pass' or data.get('independent_accuracy_validated') is not False):
        raise ValueError(f'Legacy molecular APT receipt is invalid or failed: {path}')
    outputs = data.get('output_sha256')
    if not isinstance(outputs, dict) or set(outputs) != {'BEC.raw.dat', 'BEC.dat', 'molecular_apt.json'}:
        raise ValueError('Legacy molecular APT receipt lacks required output fingerprints')
    for name, digest in outputs.items():
        source = root / name
        if not source.is_file() or sha256_file(source) != digest:
            raise ValueError(f'Legacy molecular APT output changed or is missing: {source}')
    records = data.get('source_sha256')
    if not isinstance(records, dict) or '0.no-move' not in records or len(records) < 2:
        raise ValueError('Legacy molecular APT receipt lacks source stages')
    for name, files in records.items():
        if not isinstance(files, dict) or not files:
            raise ValueError(f'Legacy molecular APT stage has no source fingerprints: {name}')
        for filename, digest in files.items():
            source = Path(filename)
            if not source.is_absolute():
                source = (root / source).resolve()
                if not source.is_relative_to(root):
                    raise ValueError(f'Legacy molecular APT source leaves its root: {filename}')
            if not source.is_file() or sha256_file(source) != digest:
                raise ValueError(f'Legacy molecular APT source changed or is missing: {source}')
    return data
