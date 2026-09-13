"""Compact completed Wuzhen BEC families without copying raw ABACUS logs.

The compact archive is sufficient for local ZStar BEC post-processing and for
the force-only collector: it keeps each stage's STRU, PYATB polarization files,
input settings, and a synthetic SCF log containing the final energy, force
block, and completion markers.  It intentionally drops wavefunction, sparse
matrix, and iteration-level SCF output.

This script uses only Python 3.6-compatible syntax because Wuzhen's system
Python is 3.6.8.  It is an archival transport helper, not a replacement for
the authoritative raw calculation directory.
"""

from __future__ import print_function

import argparse
import json
import re
import shutil
from pathlib import Path


ENERGY_PATTERNS = (
    re.compile(r"!\s*FINAL_ETOT_IS\s+([-+0-9.]+(?:[eE][-+]?\d+)?)\s*eV", re.I),
    re.compile(r"FINAL_ETOT_IS\s+([-+0-9.]+(?:[eE][-+]?\d+)?)\s*eV", re.I),
    re.compile(r"final\s+etot\s+is\s+([-+0-9.]+(?:[eE][-+]?\d+)?)\s*eV", re.I),
)


def _stages(frame_root):
    return [frame_root / "0.no-move"] + sorted(frame_root.glob("disp-*"))


def _scf_log(stage):
    logs = sorted(stage.glob("OUT.*/running_scf.log"))
    if len(logs) != 1:
        raise RuntimeError("expected one OUT.*/running_scf.log in %s" % stage)
    return logs[0]


def _energy_and_forces(stage, natoms, reference_labels=None):
    text = _scf_log(stage).read_text(encoding="utf-8", errors="replace")
    energy = None
    for pattern in ENERGY_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            energy = float(matches[-1])
            break
    if energy is None:
        raise RuntimeError("missing final ABACUS energy in %s" % stage)
    marker = "TOTAL-FORCE (eV/Angstrom)"
    if marker not in text and stage.name == "0.no-move" and reference_labels is not None:
        # The reference BEC SCF is needed for the zero-displacement
        # polarization, but some production logs intentionally omit a force
        # block.  Carry the already validated parent DFT labels into the
        # compact archive; never rerun the reference SCF or synthesize zeros.
        ref_energy, ref_forces = reference_labels
        if len(ref_forces) != natoms:
            raise RuntimeError("parent reference force count does not match %s" % stage)
        return float(ref_energy), ref_forces
    if marker not in text:
        raise RuntimeError("missing ABACUS force block in %s" % stage)
    rows = []
    for line in text.rsplit(marker, 1)[1].splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        try:
            values = [float(value) for value in fields[-3:]]
        except ValueError:
            continue
        rows.append(values)
        if len(rows) == natoms:
            break
    if len(rows) != natoms:
        raise RuntimeError("force block has %d/%d rows in %s" % (len(rows), natoms, stage))
    return energy, rows


def _compact_stage(source, target, reference_labels=None):
    target.mkdir(parents=True, exist_ok=True)
    for filename in ("STRU", "INPUT-scf"):
        source_file = source / filename
        if not source_file.is_file():
            raise RuntimeError("missing %s in %s" % (filename, source))
        shutil.copy2(source_file, target / filename)
    # Production BTO stages deliberately let ABACUS derive the mesh from
    # ``kspacing=0.1``.  A generated KPT would be a false fixed-mesh record;
    # retain it only for legacy stages that actually contain one.
    source_kpt = source / "KPT"
    if source_kpt.is_file():
        shutil.copy2(source_kpt, target / "KPT")
    pyatb = source / "pyatb" / "Out"
    if not (pyatb / "input.json").is_file() or not (pyatb / "Polarization" / "polarization.dat").is_file():
        raise RuntimeError("missing PYATB polarization outputs in %s" % source)
    for relative in (Path("input.json"), Path("Polarization") / "polarization.dat"):
        destination = target / "pyatb" / "Out" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pyatb / relative, destination)
    # The compact force parser only needs the number of force rows.  The
    # canonical BTO workflow is five atoms; count ATOMIC_POSITIONS entries
    # conservatively from the source structure's species blocks.
    text = (source / "STRU").read_text(encoding="utf-8")
    match = re.search(r"(?is)ATOMIC_POSITIONS.*", text)
    if not match:
        raise RuntimeError("cannot locate ATOMIC_POSITIONS in %s" % source)
    natoms = 0
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    coordinate = re.compile(r"^\s*%s\s+%s\s+%s\b" % (number, number, number))
    for line in match.group(0).splitlines():
        if coordinate.match(line):
            natoms += 1
    if natoms <= 0:
        raise RuntimeError("cannot count atoms in %s" % source)
    energy, forces = _energy_and_forces(source, natoms, reference_labels=reference_labels)
    out = target / "OUT.POLAR"
    out.mkdir(parents=True, exist_ok=True)
    lines = [
        "charge density convergence is achieved",
        "!FINAL_ETOT_IS %.16g eV" % energy,
        "TOTAL-FORCE (eV/Angstrom)",
    ]
    lines.extend(
        "%d 0.0 0.0 %.16g %.16g %.16g" % ((index + 1,) + tuple(row))
        for index, row in enumerate(forces)
    )
    lines.append("total time 1 sec")
    (out / "running_scf.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frame-id", action="append", default=[])
    parser.add_argument(
        "--parent-source-jsonl",
        type=Path,
        help="selected parent JSONL supplying existing DFT E/F labels for 0.no-move logs without force blocks",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    requested = set(str(item) for item in args.frame_id)
    reference_rows = {}
    if args.parent_source_jsonl is not None:
        for line in args.parent_source_jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            reference_rows[str(row["frame_id"])] = (
                float(row["energy"]),
                row["forces"],
            )
    report = {
        "schema": "zstar-wuzhen-bec-compact-archive",
        "frames": [],
        "failed": {},
        "reference_force_policy": (
            "selected-parent-dft-label for 0.no-move when the BEC reference log lacks TOTAL-FORCE"
            if args.parent_source_jsonl is not None else "requires force block in every stage"
        ),
    }
    frame_roots = sorted(args.batch_root.glob("frame-*"))
    for source_frame in frame_roots:
        frame_id = source_frame.name[len("frame-"):]
        if requested and frame_id not in requested:
            continue
        target_frame = args.output / source_frame.name
        try:
            target_frame.mkdir(parents=True, exist_ok=True)
            manifest_candidates = (
                source_frame / "shared_response.json",
                source_frame / ".zstar" / "shared_response.json",
            )
            manifest_path = next((path for path in manifest_candidates if path.is_file()), None)
            if manifest_path is None:
                raise RuntimeError("missing shared_response manifest")
            target_frame.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_frame / "STRU", target_frame / "STRU")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            # The compact archive deliberately drops immutable pseudopotential
            # and orbital binaries.  Keep only the structural/input hashes
            # needed by local response post-processing.
            manifest["input_hashes"] = {
                name: digest
                for name, digest in manifest.get("input_hashes", {}).items()
                if Path(name).name in ("STRU", "INPUT-scf", "KPT")
            }
            (target_frame / "shared_response.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            disp = source_frame / "phonopy_disp.yaml"
            if disp.is_file():
                shutil.copy2(disp, target_frame / "phonopy_disp.yaml")
            stages = _stages(source_frame)
            for stage in stages:
                _compact_stage(
                    stage,
                    target_frame / stage.name,
                    reference_labels=reference_rows.get(frame_id) if stage.name == "0.no-move" else None,
                )
            report["frames"].append(frame_id)
        except (OSError, RuntimeError, ValueError) as exc:
            report["failed"][frame_id] = str(exc)
            if target_frame.exists():
                shutil.rmtree(str(target_frame))
    report["frames"] = sorted(report["frames"], key=lambda item: int(item) if item.isdigit() else item)
    (args.output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
