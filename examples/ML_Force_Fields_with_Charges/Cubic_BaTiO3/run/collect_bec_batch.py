"""Collect completed per-frame BEC workflows and annotate a sparse dataset.

The script is deliberately scheduler-neutral: ABACUS/PYATB outputs are
prepared and run externally (for example by ``wuzhen_bec_array.slurm``), then
this collector runs the lightweight ZStar ``--bec-only`` post-processing on
each completed frame. Incomplete frames are reported and skipped rather than
being converted into zero tensors.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from typing import List, Optional, Tuple
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


_ENERGY_PATTERNS = (
    re.compile(r"!\s*FINAL_ETOT_IS\s+([-+0-9.]+(?:[eE][-+]?\d+)?)\s*eV", re.I),
    re.compile(r"FINAL_ETOT_IS\s+([-+0-9.]+(?:[eE][-+]?\d+)?)\s*eV", re.I),
    re.compile(r"final\s+etot\s+is\s+([-+0-9.]+(?:[eE][-+]?\d+)?)\s*eV", re.I),
)


def _scf_log(stage: Path) -> Path:
    logs = sorted(stage.glob("OUT.*/running_scf.log"))
    if len(logs) != 1:
        raise RuntimeError(f"expected exactly one OUT.*/running_scf.log in {stage}")
    return logs[0]


def _read_abacus_energy(stage: Path) -> float:
    """Read the final ABACUS total energy in eV from a completed SCF log."""
    text = _scf_log(stage).read_text(encoding="utf-8", errors="replace")
    for pattern in _ENERGY_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            return float(matches[-1])
    raise RuntimeError(f"no final ABACUS total energy found in {stage}")


def _read_kpoints_label(stage: Path) -> str:
    """Preserve the actual frame KPT policy instead of assuming a primitive mesh."""
    path = stage / "KPT"
    if path.is_file():
        lines = [line.split() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
        for index, fields in enumerate(lines):
            if len(fields) >= 3:
                try:
                    nx, ny, nz = (int(float(value)) for value in fields[:3])
                except ValueError:
                    continue
                kind = "Gamma"
                for previous in lines[max(0, index - 2):index]:
                    if previous and previous[0].lower().startswith("monk"):
                        kind = "Monkhorst-Pack"
                return f"{kind} {nx}x{ny}x{nz}"
    for candidate in (stage / "INPUT-scf", stage / "INPUT"):
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
            fields = line.split("#", 1)[0].split()
            if len(fields) >= 2 and fields[0].lower() == "kspacing":
                return f"ABACUS automatic kspacing={fields[1]} (1/bohr)"
    return "unknown"


def _response_stages(frame_root: Path) -> List[Path]:
    stages = [frame_root / "0.no-move"] + sorted(frame_root.glob("disp-*"))
    manifest = _response_manifest(frame_root)
    if manifest is not None:
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            expected = ["0.no-move"] + [str(item["name"]) for item in payload.get("stages", [])]
            actual = [stage.name for stage in stages]
            if expected != actual:
                raise RuntimeError(
                    f"incomplete displacement stage set in {frame_root}: "
                    f"expected {expected}, found {actual}"
                )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"invalid response manifest in {frame_root}: {exc}") from exc
    if not stages or not all(stage.is_dir() for stage in stages):
        raise RuntimeError(f"incomplete displacement stage set in {frame_root}")
    return stages


def _response_manifest(frame_root: Path) -> Optional[Path]:
    for candidate in (
        frame_root / ".zstar" / "shared_response.json",
        frame_root / ".zstar" / "bec.json",
        frame_root / "shared_response.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def _parent_labels_in_stage_order(parent, atoms):
    """Return parent DFT forces reordered to the ABACUS ``STRU`` atom order.

    ExtXYZ sources commonly group atoms as Ba/O/Ti, whereas ABACUS writes
    ``STRU`` in its species-block order (Ba/Ti/O).  A raw array copy would
    silently attach forces to the wrong species.  Match by species and
    minimum wrapped fractional-coordinate distance, then return both the
    reordered forces and the parent-index permutation for provenance.
    """
    if parent.forces is None:
        raise RuntimeError(f"parent frame {parent.frame_id} has no force labels for 0.no-move fallback")
    parent_symbols = [str(symbol) for symbol in parent.chemical_symbols]
    stage_symbols = [str(symbol) for symbol in atoms.symbols]
    if len(parent_symbols) != len(stage_symbols):
        raise RuntimeError(f"reference atom count does not match parent frame {parent.frame_id}")
    parent_cell = np.asarray(parent.cell, dtype=float)
    stage_cell = np.asarray(atoms.cell, dtype=float)
    if not np.allclose(parent_cell, stage_cell, atol=2.0e-5, rtol=0.0):
        raise RuntimeError(f"reference cell does not match parent frame {parent.frame_id}")
    inv_cell = np.linalg.inv(stage_cell)
    parent_frac = np.asarray(parent.positions, dtype=float) @ np.linalg.inv(parent_cell)
    stage_frac = np.asarray(atoms.positions, dtype=float) @ inv_cell
    available = set(range(len(parent_symbols)))
    permutation = []
    for stage_index, symbol in enumerate(stage_symbols):
        candidates = [index for index in available if parent_symbols[index] == symbol]
        if not candidates:
            raise RuntimeError(f"reference atom order/species does not match parent frame {parent.frame_id}")
        distances = []
        for index in candidates:
            delta = stage_frac[stage_index] - parent_frac[index]
            delta -= np.round(delta)
            distances.append((float(np.linalg.norm(delta)), index))
        distance, index = min(distances)
        if distance > 2.0e-4:
            raise RuntimeError(
                f"reference geometry does not match parent frame {parent.frame_id} "
                f"(atom {stage_index}, wrapped fractional distance {distance:.3g})"
            )
        permutation.append(index)
        available.remove(index)
    reordered = np.asarray(parent.forces, dtype=float)[np.asarray(permutation, dtype=int)]
    return reordered, permutation


def _collect_force_only_frames(parent_row: dict, frame_root: Path):
    """Extract PBEsol SCF force/energy frames from one completed BEC family.

    BEC is deliberately not copied to these auxiliary frames.  The parent
    frame is retained in metadata so train/validation/test splitting can be
    performed by family rather than by correlated finite-displacement frame.
    """
    from zstar.charge_aware_dataset import ChargeAwareFrame
    from zstar.shared_abacus import read_forces
    from zstar.shared_response import actual_displacement, read_structure
    from zstar.workflow import scf_is_complete

    stages = _response_stages(frame_root)
    if not all(scf_is_complete(stage) for stage in stages):
        raise RuntimeError(f"one or more SCF stages are incomplete in {frame_root}")
    reference = read_structure(stages[0] / "STRU")
    parent = ChargeAwareFrame.from_mapping(parent_row)
    manifest = _response_manifest(frame_root)
    rows = []
    for stage in stages:
        atoms = read_structure(stage / "STRU")
        if stage.name == "0.no-move":
            # The reference SCF is part of the BEC workflow only to provide
            # the zero-displacement polarization.  In the WZ run its
            # OUT.POLAR log contains the converged energy but not a
            # TOTAL-FORCE block.  Reuse the already validated parent DFT
            # labels instead of launching another SCF or inventing a force
            # tensor.  This keeps the BEC workflow cost-neutral for the
            # force dataset and preserves the user's original values.
            forces, parent_force_permutation = _parent_labels_in_stage_order(parent, atoms)
            energy = float(parent.energy) if parent.energy is not None else _read_abacus_energy(stage)
            force_source = "selected-parent-dft-label"
            energy_source = "selected-parent-dft-label"
            displacement_id = "0.no-move"
            displaced_atom_index = None
            displacement_vector = [0.0, 0.0, 0.0]
        else:
            forces = read_forces(stage)
            energy = _read_abacus_energy(stage)
            force_source = "bec-workflow-abacus-scf"
            energy_source = "bec-workflow-abacus-scf"
            displaced_atom_index, vector = actual_displacement(reference, atoms)
            displacement_id = stage.name
            displacement_vector = [float(x) for x in vector]
        metadata = dict(parent.metadata or {})
        metadata.update({
            "source_format": "zstar-bec-workflow",
            "label_family": "abacus-pbesol-force-only",
            "data_role": "finite-displacement-force-only-support",
            "bec_support_frame": True,
            "parent_frame_id": parent.frame_id,
            "parent_structure_id": parent.structure_id,
            "parent_atom_order": list(parent.chemical_symbols),
            "bec_workflow_stage": stage.name,
            "displacement_id": displacement_id,
            "displaced_atom_index": displaced_atom_index,
            "displacement_vector_A": displacement_vector,
            "stress_available": False,
            "source_scf_log": str(_scf_log(stage).resolve()),
            "force_source": force_source,
            "energy_source": energy_source,
            "parent_force_atom_permutation": parent_force_permutation if stage.name == "0.no-move" else None,
            "correlation_group": f"bec-family:{parent.frame_id}",
        })
        rows.append(ChargeAwareFrame(
            frame_id=f"{parent.frame_id}::{stage.name}",
            structure_id=f"{parent.structure_id}:{stage.name}",
            chemical_symbols=[str(symbol) for symbol in atoms.symbols],
            cell=np.asarray(atoms.cell, dtype=float).tolist(),
            positions=np.asarray(atoms.positions, dtype=float).tolist(),
            pbc=[True, True, True],
            total_charge=parent.total_charge,
            energy=energy,
            forces=np.asarray(forces, dtype=float).tolist(),
            stress=None,
            polarization=None,
            dipole=None,
            born_effective_charges=None,
            born_effective_charges_available=False,
            calculator="ABACUS",
            exchange_correlation="PBEsol",
            pseudopotential="WZ baseline UPF (see provenance)",
            orbital="WZ baseline numerical orbital (see provenance)",
            kpoints=_read_kpoints_label(stage),
            ecut=100.0,
            temperature=parent.temperature,
            phase_label=parent.phase_label,
            source_directory=str(stage.resolve()),
            source_manifest=str(manifest.resolve()) if manifest else None,
            source_commit=parent.source_commit,
            units={"length": "angstrom", "energy": "eV", "force": "eV/angstrom", "bec": "e"},
            coordinate_convention="cartesian_A",
            atom_order=[str(symbol) for symbol in atoms.symbols],
            validation_status="imported",
            split=None,
            metadata=metadata,
        ))
    return rows


def _complete(frame_root: Path) -> bool:
    manifests = (
        frame_root / ".zstar" / "shared_response.json",
        frame_root / ".zstar" / "bec.json",
        # Older generated workflows keep this record at the batch root.
        frame_root / "shared_response.json",
    )
    if not any(candidate.is_file() for candidate in manifests):
        return False
    stages = [frame_root / "0.no-move"] + sorted(frame_root.glob("disp-*"))
    return bool(stages) and all(
        (stage / "pyatb/Out/Polarization/polarization.dat").is_file()
        and (stage / "OUT.POLAR/running_scf.log").is_file()
        for stage in stages
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected", required=True, type=Path, help="selected sparse-source JSONL")
    parser.add_argument("--batch-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="annotated JSONL output")
    parser.add_argument("--map-output", required=True, type=Path, help="generated frame_id,bec CSV")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--force-only-output",
        type=Path,
        help="optional JSONL output for energy/force frames extracted from BEC SCF stages",
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.selected.read_text(encoding="utf-8").splitlines() if line.strip()]
    args.map_output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    mappings: List[Tuple[str, str]] = []
    skipped: List[str] = []
    failed = {}
    force_only_frames = []
    force_only_failed = {}
    for row in rows:
        frame_id = str(row["frame_id"])
        frame_root = args.batch_root / f"frame-{frame_id}"
        bec_path = frame_root / "BEC.dat"
        resumed_bec = args.resume and bec_path.is_file()
        if resumed_bec:
            mappings.append((frame_id, str(bec_path.resolve())))
        if args.force_only_output is not None:
            try:
                force_only_frames.extend(_collect_force_only_frames(row, frame_root))
            except (OSError, RuntimeError, ValueError) as exc:
                # Do not emit a partial finite-displacement family: a force
                # dataset must not contain an apparently complete parent with
                # missing SCF members.
                force_only_failed[frame_id] = str(exc)
        if not _complete(frame_root):
            skipped.append(frame_id)
            continue
        if resumed_bec:
            continue
        try:
            # Keep the example runnable directly from a source checkout even
            # when the per-frame subprocess changes cwd into its workflow.
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
            subprocess.run(
                [sys.executable, "-m", "zstar.cli", "deal", "--dim", "3", "--pyatb", "--bec-only", "--stru", "STRU"],
                cwd=frame_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            if not bec_path.is_file():
                raise RuntimeError("bec postprocessing completed without BEC.dat")
            mappings.append((frame_id, str(bec_path.resolve())))
        except subprocess.CalledProcessError as exc:
            failed[frame_id] = (exc.stdout or str(exc))[-4000:]
        except (OSError, RuntimeError) as exc:
            failed[frame_id] = str(exc)
    with args.map_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["frame_id", "bec"])
        for frame_id, path in mappings:
            writer.writerow([frame_id, path])
    annotation = None
    if mappings:
        from zstar.charge_aware_dataset import annotate_bec_dataset

        annotation = annotate_bec_dataset(args.selected, args.output, args.map_output)
    force_only_manifest_path = None
    if args.force_only_output is not None:
        from zstar.charge_aware_dataset import dataset_manifest, write_charge_dataset

        write_charge_dataset(force_only_frames, args.force_only_output)
        force_only_manifest = dataset_manifest(force_only_frames, args.force_only_output)
        parent_row_counts = {}
        for frame in force_only_frames:
            parent_id = str((frame.metadata or {}).get("parent_frame_id", ""))
            parent_row_counts[parent_id] = parent_row_counts.get(parent_id, 0) + 1
        force_only_manifest.update({
            "schema": "zstar-bec-force-only-extraction",
            "parent_frames": len({
                str(frame.metadata.get("parent_frame_id"))
                for frame in force_only_frames
                if frame.metadata and frame.metadata.get("parent_frame_id") is not None
            }),
            "scf_rows_per_parent": parent_row_counts,
            "scf_stage_policy": "reference 0.no-move plus every manifest-listed finite-displacement stage",
            "failed_parent_frames": force_only_failed,
            "split_warning": "split by parent_frame_id to avoid finite-displacement leakage",
        })
        force_only_manifest_path = args.force_only_output.with_suffix(args.force_only_output.suffix + ".manifest.json")
        force_only_manifest_path.write_text(json.dumps(force_only_manifest, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema": "zstar-bec-batch-collection",
        "requested_frames": len(rows),
        "bec_labeled_frames": len(mappings),
        "skipped_incomplete": skipped,
        "failed_postprocessing": failed,
        "annotation": annotation,
        "map_output": str(args.map_output.resolve()),
        "force_only_output": str(args.force_only_output.resolve()) if args.force_only_output else None,
        "force_only_manifest": str(force_only_manifest_path.resolve()) if force_only_manifest_path else None,
        "force_only_frames": len(force_only_frames),
        "force_only_parent_frames": len({
            str(frame.metadata.get("parent_frame_id"))
            for frame in force_only_frames
            if frame.metadata and frame.metadata.get("parent_frame_id") is not None
        }),
        "force_only_failed": force_only_failed,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
