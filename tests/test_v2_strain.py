from __future__ import annotations

from pathlib import Path
import shutil

import numpy as np
import pytest

from zstar.v2 import (
    StructureSpec,
    actual_strain,
    apply_strain,
    prepare_abacus_berry_stages,
    prepare_abacus_strain_ensemble,
    periodic_strain_indices,
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
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    result = prepare_abacus_strain_ensemble(
        tmp_path / "strain",
        structure=case / "STRU",
        input_template=case / "INPUT",
        kpt_template=case / "KPT",
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
    assert ensemble.metadata["reference_input_hash"]
    assert all(stage.input_hash for stage in ensemble.stages)


def test_abacus_strain_preparation_expands_positive_basis_vectors_to_ordered_pairs(tmp_path):
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    vectors = tuple((1.0e-3 * np.eye(6)[index]).tolist() for index in range(6))
    result = prepare_abacus_strain_ensemble(
        tmp_path / "six-components",
        structure=case / "STRU",
        input_template=case / "INPUT",
        kpt_template=case / "KPT",
        strain_vectors=vectors,
        symprec=1.0e-3,
    )
    stages = result["ensemble"].stages
    assert [stage.stage_id for stage in stages] == [
        f"strain-{index:03d}{sign}"
        for index in range(1, 7)
        for sign in ("-", "+")
    ]
    for index in range(6):
        np.testing.assert_allclose(stages[2 * index].requested_vector, -np.eye(6)[index] * 1.0e-3)
        np.testing.assert_allclose(stages[2 * index + 1].requested_vector, np.eye(6)[index] * 1.0e-3)


def test_periodic_strain_indices_only_include_intrinsic_low_dimensional_modes():
    assert periodic_strain_indices(("x", "y", "z")) == (0, 1, 2, 3, 4, 5)
    assert periodic_strain_indices(("x", "y")) == (0, 1, 5)
    assert periodic_strain_indices(("z",)) == (2,)
    with pytest.raises(ValueError, match="dimensionality=0"):
        periodic_strain_indices(())
    with pytest.raises(ValueError, match="periodic_axes"):
        periodic_strain_indices(("x", "x"))


def test_abacus_strain_preparation_limits_default_low_dimensional_strain_to_periodic_modes(tmp_path):
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    result = prepare_abacus_strain_ensemble(
        tmp_path / "slab-strain",
        structure=case / "STRU",
        input_template=case / "INPUT",
        kpt_template=case / "KPT",
        dimensionality=2,
        periodic_axes=("x", "y"),
    )
    ensemble = result["ensemble"]
    assert ensemble.periodic_axes == ("x", "y")
    assert ensemble.metadata["periodic_strain_indices"] == [0, 1, 5]
    assert len(ensemble.stages) == 6
    assert all(
        np.allclose(np.asarray(stage.requested_vector)[[2, 3, 4]], 0.0)
        for stage in ensemble.stages
    )
    with pytest.raises(ValueError, match="open-direction components"):
        prepare_abacus_strain_ensemble(
            tmp_path / "slab-open-strain",
            structure=case / "STRU",
            input_template=case / "INPUT",
            kpt_template=case / "KPT",
            dimensionality=2,
            periodic_axes=("x", "y"),
            strain_vectors=([0.0, 0.0, 1.0e-3, 0.0, 0.0, 0.0],),
        )
    with pytest.raises(ValueError, match="symmetry_reduce for dimensionality<3"):
        prepare_abacus_strain_ensemble(
            tmp_path / "slab-symmetry",
            structure=case / "STRU",
            input_template=case / "INPUT",
            kpt_template=case / "KPT",
            dimensionality=2,
            periodic_axes=("x", "y"),
            symmetry_reduce=True,
        )


def test_abacus_strain_preparation_can_use_symmetry_rank_plan(tmp_path):
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    result = prepare_abacus_strain_ensemble(
        tmp_path / "symmetry-reduced",
        structure=case / "STRU",
        input_template=case / "INPUT",
        kpt_template=case / "KPT",
        ion_relaxation="relaxed-ion",
        symmetry_reduce=True,
    )
    ensemble = result["ensemble"]
    assert len(ensemble.stages) == 8
    assert ensemble.metadata["symmetry_reduce"] is True
    plan = ensemble.metadata["symmetry_input_plan"]
    assert plan["complete"] is True
    assert plan["selected_indices"] == [0, 2, 3, 5]
    assert plan["output_kinds"] == ["polarization", "strain", "displacement"]
    assert [stage.stage_id for stage in ensemble.stages] == [
        f"strain-{index:03d}{sign}"
        for index in range(1, 5)
        for sign in ("-", "+")
    ]
    np.testing.assert_allclose(
        [ensemble.stage(f"strain-{index:03d}+").requested_vector for index in range(1, 5)],
        np.eye(6)[[0, 2, 3, 5]] * 1.0e-3,
    )


def test_abacus_strain_collection_rejects_changed_serialized_input_hash(tmp_path):
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    result = prepare_abacus_strain_ensemble(
        tmp_path / "hashed-strain",
        structure=case / "STRU",
        input_template=case / "INPUT",
        kpt_template=case / "KPT",
        strain_vectors=([1.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0],),
        symprec=1.0e-3,
    )
    stage_input = tmp_path / "hashed-strain" / "strain-001+" / "INPUT"
    stage_input.write_text(stage_input.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    from zstar.v2 import collect_abacus_strain_response

    with pytest.raises(ValueError, match="input hash mismatch"):
        collect_abacus_strain_response(tmp_path / "hashed-strain")


def test_input_hash_is_stable_when_stru_is_preserved_as_initial_alias(tmp_path):
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    result = prepare_abacus_strain_ensemble(
        tmp_path / "alias-strain",
        structure=case / "STRU",
        input_template=case / "INPUT",
        kpt_template=case / "KPT",
        strain_vectors=([1.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0],),
        symprec=1.0e-3,
    )
    from zstar.v2.strain import _input_hash

    stage = tmp_path / "alias-strain" / "strain-001+"
    before = _input_hash(stage)
    shutil.copy2(stage / "STRU", stage / "STRU_INITIAL")
    (stage / "STRU").unlink()
    expected = next(item.input_hash for item in result["ensemble"].stages if item.stage_id == "strain-001+")
    assert _input_hash(stage) == before == expected


def test_abacus_strain_preparation_marks_relaxed_ion_stages_and_sets_relax_input(tmp_path):
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    result = prepare_abacus_strain_ensemble(
        tmp_path / "relaxed-strain",
        structure=case / "STRU",
        input_template=case / "INPUT",
        kpt_template=case / "KPT",
        strain_vectors=([1.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0],),
        ion_relaxation="relaxed-ion",
        force_thr_ev=2.5e-4,
        symprec=1.0e-3,
    )
    ensemble = result["ensemble"]
    assert ensemble.metadata["ion_relaxation"] == "relaxed-ion"
    assert ensemble.metadata["force_thr_ev"] == 2.5e-4
    assert all("relaxed_structure" in stage.expected_outputs for stage in ensemble.stages)
    stage_input = (tmp_path / "relaxed-strain" / "strain-001+" / "INPUT").read_text()
    assert "calculation         relax" in stage_input
    assert "force_thr_ev        0.00025" in stage_input
    assert (tmp_path / "relaxed-strain" / "reference" / "INPUT").read_text().find("calculation         scf") >= 0


def test_abacus_strain_preparation_can_pin_scf_threshold_for_ionic_audit(tmp_path):
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    result = prepare_abacus_strain_ensemble(
        tmp_path / "tight-scf",
        structure=case / "STRU",
        input_template=case / "INPUT",
        kpt_template=case / "KPT",
        strain_vectors=([1.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0],),
        ion_relaxation="relaxed-ion",
        force_thr_ev=1.0e-4,
        scf_thr=1.0e-10,
    )
    ensemble = result["ensemble"]
    assert ensemble.metadata["scf_thr"] == 1.0e-10
    for stage_id in ("reference", "strain-001-", "strain-001+"):
        input_text = (tmp_path / "tight-scf" / stage_id / "INPUT").read_text()
        assert "scf_thr             1e-10" in input_text


def test_abacus_strain_preparation_rejects_invalid_scf_threshold(tmp_path):
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    with pytest.raises(ValueError, match="scf_thr"):
        prepare_abacus_strain_ensemble(
            tmp_path / "bad-scf",
            structure=case / "STRU",
            input_template=case / "INPUT",
            kpt_template=case / "KPT",
            strain_vectors=([1.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0],),
            scf_thr=0.0,
        )


def test_abacus_strain_preparation_rejects_unknown_ion_relaxation(tmp_path):
    case = Path("examples/3D_Bulk/tetragonal_BaTiO3/inputs").resolve()
    with pytest.raises(ValueError, match="ion_relaxation"):
        prepare_abacus_strain_ensemble(
            tmp_path / "bad",
            structure=case / "STRU",
            input_template=case / "INPUT",
            kpt_template=case / "KPT",
            strain_vectors=([1.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0],),
            ion_relaxation="unknown",
        )


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
    (source / "H.upf.gz").write_text("compressed pseudo\n", encoding="utf-8")
    (source / "H.orb.gz").write_text("compressed orbital\n", encoding="utf-8")
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
        assert (stage / "H.upf.gz").is_file()
        assert (stage / "H.orb.gz").is_file()
        assert (stage / "OUT.POLAR" / "POLAR-CHARGE-DENSITY.restart").is_file()
    manifest = (tmp_path / "berry" / "berry_ensemble.json").read_text()
    assert '"executed": false' in manifest
    assert str(tmp_path) not in manifest
    assert '"3": "gdir-3"' in manifest


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
