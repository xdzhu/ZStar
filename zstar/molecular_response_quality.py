"""Diagnostics for unprojected molecular atomic polar tensors."""

from __future__ import annotations

import numpy as np


def assess_raw_apt(tensors, *, net_charge_e: float = 0.0) -> dict:
    """Measure the full-atom translational residual without changing the data.

    Axes are atom, dipole component, displacement component. A small residual
    is necessary for a localized molecule but is not an accuracy certificate.
    """
    values = np.asarray(tensors, dtype=float)
    if values.ndim != 3 or values.shape[1:] != (3, 3) or not len(values):
        raise ValueError('APT must have shape (natoms, 3, 3) with at least one atom')
    if not np.all(np.isfinite(values)) or not np.isfinite(net_charge_e):
        raise ValueError('APT and net charge must be finite')
    target = float(net_charge_e) * np.eye(3)
    total = values.sum(axis=0)
    residual = total - target
    correction = np.broadcast_to(residual / len(values), values.shape)
    norm = float(np.linalg.norm(values))
    correction_norm = float(np.linalg.norm(correction))
    return {
        'tensor_convention': 'atom,dipole,displacement',
        'units': 'e',
        'net_charge_e': float(net_charge_e),
        'raw_sum_e': total.tolist(),
        'expected_sum_e': target.tolist(),
        'sum_residual_e': residual.tolist(),
        'sum_residual_frobenius_e': float(np.linalg.norm(residual)),
        'sum_residual_max_abs_e': float(np.max(np.abs(residual))),
        'raw_tensor_frobenius_e': norm,
        'uniform_projection_frobenius_e': correction_norm,
        'uniform_projection_relative': correction_norm / norm if norm else None,
        'projection_applied': False,
        'accuracy_certified': False,
    }


def check_raw_apt_consistency(tensors, *, net_charge_e: float = 0.0,
                              absolute_sum_tolerance_e: float,
                              relative_projection_tolerance: float) -> dict:
    """Check declared tolerances without treating a pass as accuracy proof.

    A violation requires both a large absolute sum residual and a large
    relative uniform correction. The absolute tolerance supplies a stable floor
    for a physically near-zero tensor. Tolerances are explicit, not inferred
    from the size of a particular molecule or a single historical result.
    """
    for name, value in (('absolute_sum_tolerance_e', absolute_sum_tolerance_e),
                        ('relative_projection_tolerance', relative_projection_tolerance)):
        if not np.isfinite(value) or value < 0:
            raise ValueError(f'{name} must be finite and nonnegative')
    report = assess_raw_apt(tensors, net_charge_e=net_charge_e)
    relative = report['uniform_projection_relative']
    absolute_violation = report['sum_residual_frobenius_e'] > absolute_sum_tolerance_e
    # If all entries are zero but the charge target is nonzero, no relative
    # scale is available, and the absolute residual alone must fail.
    relative_violation = relative is None or relative > relative_projection_tolerance
    passed = not (absolute_violation and relative_violation)
    report.update({
        'absolute_sum_tolerance_e': float(absolute_sum_tolerance_e),
        'relative_projection_tolerance': float(relative_projection_tolerance),
        'sum_consistency': 'pass' if passed else 'fail',
        'independent_accuracy_validated': False,
    })
    return report
