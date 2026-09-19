import json
from pathlib import Path

import numpy as np
import pytest

from zstar.v2 import collect_vasp_strain_response
from zstar.v2.ensemble import PerturbationStage, ResponseEnsemble
from zstar.v2.strain import actual_strain
from zstar.structure_io import read_structure


POSCAR = """SiC\n1.0\n3.0 0 0\n0 3.0 0\n0 0 3.0\nSi C\n1 1\nDirect\n0 0 0\n0.25 0.25 0.25\n"""


def _poscar(a: float) -> str:
    return f"""SiC\n1.0\n{a:.10f} 0 0\n0 3.0 0\n0 0 3.0\nSi C\n1 1\nDirect\n0 0 0\n0.25 0.25 0.25\n"""


def _outcar(energy: float, a: float = 3.0, force_scale: float = 0.01) -> str:
    return f""" ions per type = 1 1
 direct lattice vectors                 reciprocal lattice vectors
 {a:.10f} 0 0 1 0 0
 0 3.0 0 0 1 0
 0 0 3.0 0 0 1
 FORCE on cell =-STRESS in cart. coord. units (eV)
 in kB 10 20 30 1 2 3
 free  energy   TOTEN  = {energy:.10f} eV
 POSITION                                       TOTAL-FORCE (eV/Angst)
 -----------------------------------------------------------------------------------
 0 0 0 {force_scale:.6f} 0 0
 1 1 1 {-force_scale:.6f} 0 0
 General timing and accounting informations for this job
"""


def _write_stage(path: Path, a: float, energy: float) -> None:
    path.mkdir(parents=True)
    (path / "POSCAR").write_text(_poscar(a), encoding="utf-8")
    (path / "OUTCAR").write_text(_outcar(energy, a=a), encoding="utf-8")


def _contcar(a: float, shifted: bool) -> str:
    z = 0.251 if shifted else 0.25
    return f"""SiC\n1.0\n{a:.10f} 0 0\n0 3.0 0\n0 0 3.0\nSi C\n1 1\nDirect\n0 0 0\n0.25 0.25 {z:.10f}\n"""


def test_collect_vasp_strain_response_packages_observations(tmp_path: Path):
    reference = tmp_path / "reference"
    _write_stage(reference, 3.0, -10.0)
    plus = tmp_path / "strain-001+"
    minus = tmp_path / "strain-001-"
    _write_stage(plus, 3.003, -9.9)
    _write_stage(minus, 2.997, -9.9)
    ref_structure = read_structure(reference / "POSCAR")
    stages = []
    for stage_id, path, sign in (("strain-001+", plus, "+"), ("strain-001-", minus, "-")):
        structure = read_structure(path / "POSCAR")
        vector = actual_strain(ref_structure.lattice_angstrom, structure.lattice_angstrom)
        stages.append(PerturbationStage(stage_id, "strain", tuple(vector), actual_vector=tuple(vector), sign=sign, status="complete", result_path=str(path)))
    ResponseEnsemble(reference_hash="synthetic", stages=tuple(stages), metadata={"ion_relaxation": "clamped-ion"}).write(tmp_path / "ensemble.json")
    document = collect_vasp_strain_response(tmp_path)
    assert document.backend == "vasp"
    assert document.quantity("stress_raw").boundary_conditions.stress_sign == "vasp-raw"
    assert document.quantity("energy").shape == (3,)
    np.testing.assert_allclose(document.quantity("strain_vector").values[:, 0], [0.0, 0.001, -0.001], atol=1e-10)


def test_collect_vasp_strain_response_rejects_failed_stage(tmp_path: Path):
    _write_stage(tmp_path / "reference", 3.0, -10.0)
    stage = PerturbationStage("strain-001+", "strain", (0.001, 0, 0, 0, 0, 0), actual_vector=(0.001, 0, 0, 0, 0, 0), status="failed", result_path="strain-001+")
    ResponseEnsemble(reference_hash="synthetic", stages=(stage,)).write(tmp_path / "ensemble.json")
    with pytest.raises(ValueError, match="failed"):
        collect_vasp_strain_response(tmp_path)


def test_collect_vasp_strain_response_keeps_relaxed_internal_displacement(tmp_path: Path):
    reference = tmp_path / "reference"
    _write_stage(reference, 3.0, -10.0)
    plus = tmp_path / "strain-001+"
    _write_stage(plus, 3.003, -9.9)
    (plus / "CONTCAR").write_text(_contcar(3.003, shifted=True), encoding="utf-8")
    ref_structure = read_structure(reference / "POSCAR")
    stage_structure = read_structure(plus / "POSCAR")
    vector = actual_strain(ref_structure.lattice_angstrom, stage_structure.lattice_angstrom)
    stage = PerturbationStage("strain-001+", "strain", tuple(vector), actual_vector=tuple(vector), sign="+", status="complete", result_path=str(plus))
    ResponseEnsemble(
        reference_hash="synthetic", stages=(stage,),
        metadata={"ion_relaxation": "relaxed-ion", "force_thr_ev": 0.02},
    ).write(tmp_path / "ensemble.json")
    document = collect_vasp_strain_response(tmp_path)
    assert document.quantity("forces_initial").ion_relaxation == "clamped-ion"
    displacement = document.quantity("internal_displacement").values
    assert displacement.shape == (2, 2, 3)
    np.testing.assert_allclose(displacement[0], 0.0)
    np.testing.assert_allclose(displacement[1, 1, 2], 0.003)
