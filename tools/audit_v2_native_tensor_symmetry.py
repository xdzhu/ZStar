"""Read-only full e/C/d crystal-symmetry audit of frozen native response routes.

Research diagnostic only: never edits a structure, tensor, or acceptance gate.
Engineering strain A and work-conjugate tensorial stress B are distinct:
e A = R e, C A = B C, d B = R d, with B = A^{-T}.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys
import warnings

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from zstar.v2.fit import _major_symmetric_basis
from zstar.v2.mechanical import stress_representation
from zstar.v2.structure import (
    StructureSpec, allowed_response_basis, analyze_space_group,
    space_group_report_to_dict, strain_representation,
)
from zstar.v2.symmetry import intertwiner_basis, intertwining_residual


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def representations(report):
    rotations = tuple(op.rotation_cartesian for op in report.operations)
    strains = tuple(strain_representation(report, i) for i in range(report.operation_count))
    stresses = tuple(stress_representation(r) for r in rotations)
    assert all(np.max(np.abs(b.T @ a - np.eye(6))) < 1e-10
               for a, b in zip(strains, stresses)), "Stress/strain work-conjugacy failed"
    return rotations, strains, stresses


def tensor_audit(values, inputs, outputs, basis, unit):
    matrix = np.asarray(values, dtype=float)
    assert matrix.shape == (basis.output_dimension, basis.input_dimension)
    assert np.isfinite(matrix).all()
    flat = matrix.reshape(-1, order="F")
    # SVD basis gives an orthogonal least-squares projection in the declared
    # matrix-entry norm. No incorrect Din.T group average on engineering axes.
    allowed = basis.basis @ (basis.basis.T @ flat)
    projected = allowed.reshape(matrix.shape, order="F")
    residual = matrix - projected
    scale = np.linalg.norm(matrix)
    assert scale > 0
    forbidden = np.linalg.norm(basis.basis, axis=1) < 1e-10
    rows, cols = matrix.shape
    labels = [f"{index % rows + 1}{index // rows + 1}"
              for index in np.flatnonzero(forbidden)]
    return {
        "unit": unit,
        "norm_convention": "Frobenius norm of the declared engineering/tensorial Voigt matrix entries, not a rotationally invariant Cartesian tensor norm",
        "allowed_parameter_count": basis.parameter_count,
        "constraint_rank": basis.constraint_rank,
        "svd_cutoff_numerical_not_symprec": basis.tolerance,
        "max_projection_residual": float(np.max(np.abs(residual))),
        "relative_projection_residual": float(np.linalg.norm(residual) / scale),
        "max_intertwining_frobenius_residual": intertwining_residual(matrix, inputs, outputs),
        "projected_intertwining_frobenius_residual": intertwining_residual(projected, inputs, outputs),
        "forbidden_component_labels_in_original_frame": labels,
        "max_forbidden_component": float(np.max(np.abs(flat[forbidden]))) if forbidden.any() else None,
        "raw_values": matrix.tolist(),
        "diagnostic_projected_values": projected.tolist(),
        "residual_values": residual.tolist(),
        "projected_values_are_not_published_results": True,
    }


def audit_triplet(e, c, d, report):
    rotations, strains, stresses = representations(report)
    eb = allowed_response_basis(report, input_kind="strain", output_kind="polarization")
    cb = _major_symmetric_basis(allowed_response_basis(report, input_kind="strain", output_kind="stress"))
    db = intertwiner_basis(stresses, rotations)
    result = {
        "e": tensor_audit(e, strains, rotations, eb, "C/m^2"),
        "C": tensor_audit(c, strains, stresses, cb, "GPa"),
        "d": tensor_audit(d, stresses, rotations, db, "pm/V"),
    }
    # Explicit prefix identity: pm/V * GPa / 1000 = C/m^2.
    result["d_C_e_closure_max_C_m2"] = float(np.max(np.abs(d @ c / 1000 - e)))
    transformed_closures = []
    for r, a, b in zip(rotations, strains, stresses):
        et = r @ e @ np.linalg.inv(a)
        ct = b @ c @ np.linalg.inv(a)
        dt = r @ d @ np.linalg.inv(b)
        transformed_closures.append(float(np.max(np.abs(dt @ ct / 1000 - et))))
    result["all_operations_transformed_closure_max_C_m2"] = max(transformed_closures)
    assert result["d_C_e_closure_max_C_m2"] < 1e-8
    assert result["all_operations_transformed_closure_max_C_m2"] < 1e-8
    return result


def load_bounded(path: Path):
    if not path.is_file() or path.stat().st_size > 5_000_000:
        raise ValueError(f"Missing or oversized audit input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New exclusive research JSON")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    # Only actual VASP-file intake needs the optional parser; the algebra
    # tests and --help remain usable without installing pymatgen.
    from pymatgen.io.vasp import Poscar
    directory = ROOT / "outputs/pbe_database_comparison_20260918"
    aln = Path("D:/Work/Code/zstar-vasp-native/examples/VASP_Native_Response/AlN")
    cases = {
        "AlN_accepted": (aln / "results/elastic", aln / "results/AlN_relaxed.vasp"),
        "GaN_primary": (directory / "GaN_VASP", Path("E:/TEMP/zstar-pbe-database-20260918/domain-audit/GaN-VASP-POSCAR")),
        "GaN_symmetry_control": (directory / "GaN_VASP_symmetry_control", Path("E:/TEMP/zstar-pbe-database-20260918/domain-audit/GaN-VASP-POSCAR")),
        "ZnO_primary": (directory / "ZnO_VASP", Path("E:/TEMP/zstar-pbe-database-20260918/domain-audit-r2r/ZnO-VASP-POSCAR")),
        "PTO_primary": (directory / "PTO_VASP", Path("E:/TEMP/zstar-pbe-database-20260918/PTO-native-POSCAR")),
        "PZT_ordered001_primary": (directory / "PZT_VASP", directory / "PZT_VASP/reference_POSCAR"),
    }
    rows = []
    for name in ("native_ionic_contribution_reconstruction_audit.json",
                 "PTO_native_ionic_contribution_reconstruction_audit.json",
                 "PZT_native_ionic_contribution_reconstruction_audit.json"):
        audit_source = directory / name
        frozen = load_bounded(audit_source)
        assert frozen["native_acceptance_changed"] is False
        assert frozen["model"]["strain"] == "engineering [xx,yy,zz,2yz,2xz,2xy]"
        for calculation in frozen["calculations"]:
            case = calculation["case"]
            native_root, geometry = cases[case]
            native_source = native_root / "vasp_native_response.json"
            native = load_bounded(native_source)
            frozen_hashes = {str(Path(p).resolve()): digest
                             for p, digest in calculation["source_sha256"].items()}
            for source in (native_source, geometry):
                assert frozen_hashes[str(source.resolve())] == sha256(source), f"Frozen source changed: {source}"
            if not geometry.is_file() or geometry.stat().st_size > 100_000:
                raise ValueError(f"Missing or oversized POSCAR: {geometry}")
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                structure = Poscar.from_file(geometry, check_for_potcar=False, read_velocities=False).structure
                assert 1 <= len(structure) <= 20 and structure.is_ordered
                assert structure.lattice.pbc == (True, True, True)
                assert all(not site.specie.oxi_state if hasattr(site.specie, "oxi_state") else True for site in structure)
                assert float(np.min(structure.distance_matrix + np.eye(len(structure)) * 1e6)) > .3
                spec = StructureSpec(structure.lattice.matrix, structure.frac_coords,
                                     tuple(str(site.specie) for site in structure))
                report = analyze_space_group(spec)  # Fixed v2 1e-3 Å, no sweep.
            assert report.status == "stable" and report.symprec == 1e-3
            assert list(spec.symbols) == calculation["atom_order"]
            row = {"case": case, "dimensionality": 3, "periodic_axes": ["x", "y", "z"],
                   "coordinate_system": "original Cartesian frame; no atom/axis reordering or polar-domain reversal",
                   "backend": "VASP", "functional": "PBE", "ion_relaxation": "relaxed-ion",
                   "electric_boundary": "fixed macroscopic E", "normalization": "bulk cell volume",
                   "strain_axes": ["xx", "yy", "zz", "2yz", "2xz", "2xy"],
                   "stress_axes": ["xx", "yy", "zz", "yz", "xz", "xy"],
                   "sources_sha256": {str(p): sha256(p) for p in (audit_source, native_source, geometry)},
                   "parser_and_symmetry_warnings": [str(w.message) for w in caught],
                   "symmetry": space_group_report_to_dict(report), "routes": {},
                   "native_d_rejected_reason": native["diagnostics"].get("d_rejected_reason")}
            for route_name, route in calculation["routes"].items():
                e = np.asarray(route["e_total_diagnostic_C_m2"])
                c = np.asarray(route["C_total_diagnostic_GPa"])
                d = np.asarray(route["d_diagnostic_pm_V"])
                row["routes"][route_name] = audit_triplet(e, c, d, report)
            tensors = native["tensors"]
            rotations, strains, stresses = representations(report)
            row["native_e"] = tensor_audit(np.asarray(tensors["piezoelectric_total_C_m2"]), strains,
                                            rotations, allowed_response_basis(report, input_kind="strain", output_kind="polarization"), "C/m^2")
            row["native_C"] = tensor_audit(np.asarray(tensors["elastic_relaxed_GPa"]), strains,
                                            stresses, _major_symmetric_basis(allowed_response_basis(report, input_kind="strain", output_kind="stress")), "GPa")
            rows.append(row)
    result = {"schema": "native-full-tensor-spacegroup-audit/1", "calculations": rows,
              "algorithm_source_sha256": sha256(Path(__file__).resolve()),
              "packages": {n: version(n) for n in ("numpy", "spglib", "pymatgen")},
              "native_acceptance_changed": False, "new_DFT_calculations": 0,
              "standard_uncertainty": None, "input_error_distribution": "unknown",
              "limitations": ["Deterministic symmetry residual, not uncertainty or independent accuracy evidence.",
                              "Diagnostic projection is not used to replace any published native e/C/d.",
                              "No acceptance thresholds changed and no d scientific gate bypassed.",
                              "Local pymatgen is recorded, not silently upgraded to the skill snapshot."]}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    for row in rows:
        print(row["case"], row["symmetry"]["space_group"],
              {route: {k: value[k]["max_projection_residual"] for k in ("e", "C", "d")}
               for route, value in row["routes"].items()})


if __name__ == "__main__":
    main()
