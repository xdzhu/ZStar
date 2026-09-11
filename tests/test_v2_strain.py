from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from zstar.v2 import (
    StructureSpec,
    actual_strain,
    apply_strain,
    prepare_abacus_berry_stages,
    prepare_abacus_strain_ensemble,
)


def test_apply_strain_preserves_fractional_sites_and_recovers_actual_vector():
    structure = StructureSpec(
        lattice=np.diag([4.0, 5.0, 6.0]),
        fractional_positions=np.array([[0.1, 0.2, 0.3]]),
        symbols=("X",),
    )
    strained = apply_strain(structure, [0.01, -0.02, 0.03, 0.004, 0.006, 0.008])
    np.testing.assert_allclose(strained.fractional_positions, structure.fractional_positions)
    np.testing.assert_allclose(
        actual_strain(structure.lattice, strained.lattice),
        [0.01, -0.02, 0.03, 0.004, 0.006, 0.008],
        atol=1.0e-14,
    )


def test_abacus_strain_preparation_is_dry_run_and_serializes_actual_vectors(tmp_path):
    case = Path("examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/run").resolve()
    result = prepare_abacus_strain_ensemble(
        tmp_path / "strain",
        structure=case / "STRU",
        input_template=case / "INPUT",
        kpt_template=case / "KPT",
        pp_dir=case / "assets",
        orb_dir=case / "assets",
        strain_vectors=([1.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0],),
        symprec=1.0e-3,
    )
    ensemble = result["ensemble"]
    assert result["root"] == str((tmp_path / "strain").resolve())
    assert result["symmetry"].status == "stable"
    assert len(ensemble.stages) == 2
    assert all(stage.actual_vector is not None for stage in ensemble.stages)
    assert (tmp_path / "strain" / "reference" / "STRU").is_file()
    assert (tmp_path / "strain" / "reference" / "INPUT").is_file()
    input_text = (tmp_path / "strain" / "reference" / "INPUT").read_text()
    assert "cal_force           1" in input_text
    assert "cal_stress          1" in input_text
    assert (tmp_path / "strain" / "ensemble.json").is_file()
    assert (tmp_path / "strain" / "symmetry.json").is_file()
    assert all((tmp_path / "strain" / stage.stage_id / "STRU").is_file() for stage in ensemble.stages)


def test_abacus_berry_preparation_copies_restart_and_sets_nscf_inputs(tmp_path):
    source = tmp_path / "scf"
    (source / "OUT.POLAR").mkdir(parents=True)
    (source / "INPUT").write_text(
        "INPUT_PARAMETERS\ncalculation scf\nsuffix POLAR\nsymmetry 1\ninit_chg auto\n",
        encoding="utf-8",
    )
    (source / "STRU").write_text("fake structure\n", encoding="utf-8")
    (source / "KPT").write_text("K_POINTS\n", encoding="utf-8")
    (source / "H.upf").write_text("pseudo\n", encoding="utf-8")
    (source / "H.orb").write_text("orbital\n", encoding="utf-8")
    (source / "OUT.POLAR" / "POLAR-CHARGE-DENSITY.restart").write_text("restart\n", encoding="utf-8")

    result = prepare_abacus_berry_stages(source, tmp_path / "berry", gdirs=(3, 1, 2))
    assert result["suffix"] == "POLAR"
    assert result["manifest"].endswith("berry_ensemble.json")
    for direction in (1, 2, 3):
        stage = tmp_path / "berry" / f"gdir-{direction}"
        text = (stage / "INPUT").read_text()
        assert "calculation         nscf" in text
        assert "init_chg            file" in text
        assert "read_file_dir       OUT.POLAR/" in text
        assert "berry_phase         1" in text
        assert f"gdir                {direction}" in text
        assert "symmetry            0" in text
        assert (stage / "H.upf").is_file()
        assert (stage / "H.orb").is_file()
        assert (stage / "OUT.POLAR" / "POLAR-CHARGE-DENSITY.restart").is_file()
    assert '"executed": false' in (tmp_path / "berry" / "berry_ensemble.json").read_text()


def test_abacus_berry_preparation_rejects_missing_restart_and_nonempty_output(tmp_path):
    source = tmp_path / "scf"
    source.mkdir()
    for name in ("INPUT", "STRU", "KPT"):
        (source / name).write_text("INPUT_PARAMETERS\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="charge restart"):
        prepare_abacus_berry_stages(source, tmp_path / "berry")

    (source / "OUT.POLAR").mkdir()
    (source / "OUT.POLAR" / "POLAR-CHARGE-DENSITY.restart").write_text("restart\n", encoding="utf-8")
    output = tmp_path / "berry-existing"
    output.mkdir()
    (output / "keep").write_text("do not overwrite\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="not empty"):
        prepare_abacus_berry_stages(source, output)
