import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('pzt_trajectory_audit', Path(__file__).parents[1] / '.codex-output' / 'audit_pzt_relaxation_trajectory.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def frame(step, force=0.00008, label='O1'):
    return f'''STEP OF RELAXATION : {step}
LCAO ALGORITHM ION= {step} ELEC= 1
E_KohnSham -10 {-100 - step}.0
charge density convergence is achieved
TOTAL-FORCE (eV/Angstrom)
Pb1 {force} {force} 0
{label} {-force} {-force} 0
TOTAL-STRESS (KBAR)
Largest gradient in force is {force:.6f} eV/A.
'''


def test_3d_force_norm_is_not_maximum_component():
    result = module.audit(frame(1) + frame(2), 2, 1e-4)
    assert result['final_component_meets_threshold']
    assert not result['final_atomic_norm_meets_threshold']
    assert not result['accepted_response_point']
    assert result['steps'][-1]['max_atomic_norm_eV_per_angstrom'] == pytest.approx(2**0.5 * 8e-5)
    assert result['late_energy_increments_eV'] == [-1.0]
    assert result['standard_uncertainty'] is None


@pytest.mark.parametrize('text', [frame(1) + frame(1), frame(1) + frame(3), frame(1).replace('ION= 1', 'ION= 2')])
def test_rejects_bad_step_pairing(text):
    with pytest.raises(ValueError):
        module.audit(text, 2, 1e-4)


def test_rejects_electronic_failure_and_atom_reordering():
    with pytest.raises(ValueError, match='convergence record'):
        module.audit(frame(1).replace('charge density convergence is achieved', ''), 2, 1e-4)
    with pytest.raises(ValueError, match='order changed'):
        module.audit(frame(1) + frame(2, label='Ti1'), 2, 1e-4)


def test_rejects_gradient_not_matching_force_and_missing_energy():
    with pytest.raises(ValueError, match='gradient does not match'):
        module.audit(frame(1).replace('is 0.000080', 'is 0.000090'), 2, 1e-4)
    with pytest.raises(ValueError, match='Missing SCF energy'):
        module.audit(frame(1).replace('E_KohnSham', 'OtherEnergy'), 2, 1e-4)
