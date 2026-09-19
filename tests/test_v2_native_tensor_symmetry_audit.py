"""Three-dimensional checks of the research-only native tensor symmetry audit."""
import numpy as np

from tools import audit_v2_native_tensor_symmetry as audit
from zstar.v2.mechanical import stress_representation
from zstar.v2.structure import StructureSpec, analyze_space_group, strain_representation


def tetragonal(rotation=None):
    lattice = np.diag([4., 4., 4.3])
    positions = np.array([[0, 0, 0], [.5, .5, .55], [.5, .5, .1], [.5, 0, .65], [0, .5, .65]])
    if rotation is not None:
        lattice = lattice @ rotation.T
    return analyze_space_group(StructureSpec(lattice, positions, ("Pb", "Ti", "O", "O", "O")))


def tensors():
    c = np.diag([150., 150., 100., 40., 40., 45.])
    c[0, 1] = c[1, 0] = 60.
    c[0, 2] = c[2, 0] = c[1, 2] = c[2, 1] = 30.
    e = np.array([[0, 0, 0, 0, 2., 0], [0, 0, 0, 2., 0, 0], [1., 1., 3., 0, 0, 0]])
    d = 1000 * e @ np.linalg.inv(c)  # C/m², GPa -> pm/V.
    return e, c, d


def test_3d_polar_tetragonal_symmetry_rank_and_improper_operations():
    report = tetragonal()
    assert report.status == "stable" and report.space_group == "P4mm"
    assert report.symprec == 1e-3
    assert any(np.linalg.det(op.rotation_cartesian) < 0 for op in report.operations)
    result = audit.audit_triplet(*tensors(), report)
    assert [result[k]["allowed_parameter_count"] for k in ("e", "C", "d")] == [3, 6, 3]
    assert all(result[k]["max_projection_residual"] < 1e-10 for k in ("e", "C", "d"))
    assert result["all_operations_transformed_closure_max_C_m2"] < 1e-12


def test_3d_rotated_frame_d_uses_stress_not_engineering_strain():
    # General proper rotation, not only a Cartesian-axis permutation.
    q, _ = np.linalg.qr(np.array([[1., 2., 3.], [2., -1., 1.], [3., 1., -2.]]))
    if np.linalg.det(q) < 0:
        q[:, 0] *= -1
    basis = tetragonal()
    # Reuse the calculator-neutral engineering strain construction for q.
    from dataclasses import replace
    op = replace(basis.operations[0], rotation_cartesian=q)
    rotated_report = replace(basis, operations=(op,))
    a = strain_representation(rotated_report, 0)
    b = stress_representation(q)
    e, c, d = tensors()
    et, ct, dt = q @ e @ np.linalg.inv(a), b @ c @ np.linalg.inv(a), q @ d @ np.linalg.inv(b)
    assert np.max(np.abs(b.T @ a - np.eye(6))) < 1e-12
    assert np.max(np.abs(dt @ ct / 1000 - et)) < 1e-12
    wrong_dt = q @ d @ np.linalg.inv(a)
    assert np.max(np.abs(wrong_dt - dt)) > 1.
    result = audit.audit_triplet(et, ct, dt, tetragonal(q))
    assert all(result[k]["max_projection_residual"] < 1e-9 for k in ("e", "C", "d"))
    assert result["all_operations_transformed_closure_max_C_m2"] < 1e-12


def test_3d_forbidden_components_are_reported_not_erased():
    e, c, _ = tensors()
    e[2, 5] = .01
    d = 1000 * e @ np.linalg.inv(c)
    result = audit.audit_triplet(e, c, d, tetragonal())
    assert "36" in result["e"]["forbidden_component_labels_in_original_frame"]
    assert np.isclose(result["e"]["max_forbidden_component"], .01)
    assert np.isclose(result["d"]["max_forbidden_component"], 1000 * .01 / 45.)
    assert result["e"]["raw_values"][2][5] == .01
    assert result["e"]["projected_values_are_not_published_results"] is True
