import importlib.util
from pathlib import Path

import numpy as np
from pymatgen.core import Lattice
import pytest

spec = importlib.util.spec_from_file_location('pzt_force_coordinate_audit', Path(__file__).parents[1]/'.codex-output/audit_pzt_force_coordinate_pairing.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_three_dimensional_periodic_wrap_and_cartesian_work():
    lattice = Lattice([[4,0,-.01],[0,4,0],[-.02,0,9]])
    moves = module.periodic_moves([[.999,.5,.4]], [[.001,.5,.401]], lattice)
    expected = np.array([[.002,0,.001]]) @ lattice.matrix
    assert moves == pytest.approx(expected)
    force = np.array([[.1,.2,.3]])
    assert -np.sum(force*moves) == pytest.approx(-np.sum(force*expected))


@pytest.mark.parametrize('after', [[[.1,.5,.4]],[[np.nan,.5,.4]],[[.1,.5]]])
def test_rejects_large_nonfinite_or_mismatched_moves(after):
    with pytest.raises(ValueError):
        module.periodic_moves([[0,.5,.4]], after, Lattice.cubic(4))


def test_direct_block_preserves_atom_order_and_requires_single_block():
    text = 'DIRECT COORDINATES\nheader\ntaud_Pb1 0 .5 1\ntaud_O1 1 0 .1\n'
    result = module.direct_block(text, ['Pb1','O1'])
    assert result == pytest.approx(np.array([[0,.5,1],[1,0,.1]]))
    with pytest.raises(ValueError,match='labels/order'):
        module.direct_block(text,['O1','Pb1'])
    with pytest.raises(ValueError,match='Exactly one'):
        module.direct_block(text+text,['Pb1','O1'])
