"""The example shell launchers must not shadow the user's configuration."""

import importlib.util
from pathlib import Path


def test_example_shell_helpers_do_not_require_execute_permissions():
    root = Path(__file__).parents[1]/'examples'
    for path in root.rglob('*.sh'):
        if {'results', 'legacy', 'work'}.intersection(path.relative_to(root).parts):
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.lstrip()
            assert not line.startswith('export PYTHONPATH='), path
            if '.sh"' in line:
                assert not line.startswith(('exec "', '"')), (path, line)


def test_unified_spectroscopy_inputs_match_reference_geometry():
    import numpy as np
    from zstar.shared_response import read_structure
    root = Path(__file__).parents[1]/'examples/IR_Raman_Spectra'
    for case in ('Bulk_HfO2', '2D_MoS2', 'Nanowire_Sb2S3', 'Molecule_CH4'):
        actual = read_structure(root/case/'run/STRU')
        expected = read_structure(root/case/'results/Unified/inputs/STRU')
        assert actual.symbols == expected.symbols
        np.testing.assert_allclose(actual.cell, expected.cell, atol=1e-8)
        np.testing.assert_allclose(actual.positions, expected.positions, atol=1e-8)


def test_example_runtime_config_and_environment(tmp_path, monkeypatch):
    source = Path(__file__).parents[1] / "examples/common/runtime.py"
    spec = importlib.util.spec_from_file_location("example_runtime", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("ZSTAR_CONFIG", str(tmp_path / "missing.toml"))
    for key in ("ABACUS_COMMAND", "PYATB_COMMAND", "OMP_NUM_THREADS",
                "ZSTAR_ABACUS_EXECUTABLE", "ZSTAR_PYATB_EXECUTABLE"):
        monkeypatch.delenv(key, raising=False)
    config = tmp_path / ".zstar/config.toml"
    config.parent.mkdir()
    config.write_text('[executables]\nabacus="/opt/abacus"\npyatb="/opt/pyatb"\n'
                      '[execution]\nmpi=4\nomp=3\n')
    assert module.commands(tmp_path) == (
        "mpirun -np 4 /opt/abacus", "mpirun -np 4 /opt/pyatb", "3")
    monkeypatch.setenv("ABACUS_COMMAND", "custom-launch abacus")
    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    assert module.commands(tmp_path) == (
        "custom-launch abacus", "mpirun -np 4 /opt/pyatb", "2")
