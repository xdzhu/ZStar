from pathlib import Path
from types import SimpleNamespace
import json

import numpy as np
import pytest

from zstar.pyatb_precision import precision_command, write_precise_polarization
from zstar.deal_polar import _parse_pyatb_polar_file
from zstar.pyatb_precision import write_precise_dielectric


@pytest.mark.parametrize('legacy', [False, True])
def test_static_writer_preserves_tensor_precision(tmp_path, legacy):
    values = np.arange(9).reshape(3,3)*.0123456789123
    if legacy:
        source = tmp_path/'dielectric_function_real_part.dat'
        np.savetxt(source, np.vstack([np.r_[0,values.ravel()], np.r_[.1,values.ravel()]]), fmt='%.6f')
        response = SimpleNamespace(output_path=tmp_path, dielectric_function=np.column_stack([values.ravel(),values.ravel()]).astype(complex))
    else:
        source = tmp_path/'static_dielectric_function.dat'
        np.savetxt(source, values.reshape(1,9), fmt='%.6f')
        response = SimpleNamespace(output_path=tmp_path, static_epsilon=values)
    old = source.read_bytes()
    assert write_precise_dielectric(response)
    np.testing.assert_array_equal(np.loadtxt(tmp_path/'static_dielectric_function.dat').reshape(3,3),values)
    assert source.with_name(source.stem+'.rounded.dat').read_bytes() == old
    assert not json.loads((tmp_path/'zstar_static_precision.json').read_text())['numerical_kernel_changed']


def test_static_writer_rejects_nonfinite(tmp_path):
    with pytest.raises(ValueError, match='Invalid PYATB'):
        write_precise_dielectric(SimpleNamespace(output_path=tmp_path, static_epsilon=np.full((3,3),np.nan)))


def test_writer_preserves_full_precision_and_original(tmp_path):
    target = tmp_path/'polarization.dat'
    target.write_text('rounded original\n')
    p = np.array([.05018187246542, -.0499711887541, .05670998223])
    q = np.array([.15015422, .15015422, 1.097644])
    obj = SimpleNamespace(output_path=tmp_path, polarization=p, modulus=q,
                          polarization_ion=np.zeros(3), polarization_ele=p/q)
    write_precise_polarization(obj)
    np.testing.assert_array_equal(_parse_pyatb_polar_file(target), np.r_[p, q])
    assert (tmp_path/'polarization.rounded.dat').read_text() == 'rounded original\n'
    assert not json.loads((tmp_path/'zstar_precision.json').read_text())['numerical_kernel_changed']


def test_launcher_retains_mpi_arguments(monkeypatch):
    monkeypatch.setattr('shutil.which', lambda path: None)
    command = precision_command('mpirun -np 40 /opt/pyatb')
    assert command.startswith('mpirun -np 40 ')
    from zstar import pyatb_precision
    import shlex
    assert shlex.split(command)[-1] == str(Path(pyatb_precision.__file__).resolve())
    assert precision_command(command) == command


def test_opaque_launcher_requires_explicit_adapter():
    with pytest.raises(ValueError, match='full-precision'):
        precision_command('my-custom-wrapper')


def test_external_pyatb_interpreter_uses_current_adapter(tmp_path, monkeypatch):
    import shlex
    from zstar import pyatb_precision
    interpreter = tmp_path/'other-python'
    interpreter.write_text('external interpreter')
    launcher = tmp_path/'pyatb'
    launcher.write_text('#!'+interpreter.as_posix()+'\n')
    monkeypatch.setattr('shutil.which', lambda path: str(launcher))
    command = precision_command('mpirun -np 2 pyatb')
    assert shlex.split(command)[-2:] == [interpreter.as_posix(), str(Path(pyatb_precision.__file__).resolve())]
    assert '-m zstar.pyatb_precision' not in command
