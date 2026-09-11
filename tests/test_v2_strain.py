from __future__ import annotations

from pathlib import Path

import numpy as np

from zstar.v2 import (
    StructureSpec,
    actual_strain,
    apply_strain,
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
    assert (tmp_path / "strain" / "ensemble.json").is_file()
    assert (tmp_path / "strain" / "symmetry.json").is_file()
    assert all((tmp_path / "strain" / stage.stage_id / "STRU").is_file() for stage in ensemble.stages)
