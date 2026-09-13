"""Collect existing ABACUS SCF energy/force rows without changing labels.

This collector intentionally uses only completed output logs.  It does not
rerun SCF, infer energies, apply offsets, or normalize energy zeros.  It is
kept dependency-light so it can run on the Wuzhen Python 3.6 environment.
"""

import argparse
import json
import re
from pathlib import Path


BOHR_ANGSTROM = 0.529177210903
ENERGY_RE = re.compile(r"FINAL_ETOT_IS\s+([-+0-9.eE]+)\s*eV", re.I)


def read_stru(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    try:
        a0 = float(lines[next(i for i, line in enumerate(lines) if line.strip().upper() == "LATTICE_CONSTANT") + 1].split()[0])
        start = next(i for i, line in enumerate(lines) if line.strip().upper() == "LATTICE_VECTORS") + 1
        cell = [[float(x) * a0 * BOHR_ANGSTROM for x in lines[start + j].split()[:3]] for j in range(3)]
        pos_start = next(i for i, line in enumerate(lines) if line.strip().upper() == "ATOMIC_POSITIONS") + 1
    except (StopIteration, ValueError, IndexError) as exc:
        raise ValueError("cannot parse ABACUS STRU header: %s" % path) from exc
    mode = lines[pos_start].strip().lower()
    if mode != "direct":
        raise ValueError("only Direct ABACUS STRU coordinates are supported: %s" % path)
    i = pos_start + 1
    symbols, scaled = [], []
    while i < len(lines):
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break
        symbol = lines[i].split()[0]
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        i += 1  # magnetization/relaxation flag
        while i < len(lines) and not lines[i].strip():
            i += 1
        count = int(lines[i].split()[0])
        i += 1
        for _ in range(count):
            while i < len(lines) and not lines[i].strip():
                i += 1
            fields = lines[i].split()
            scaled.append([float(x) for x in fields[:3]])
            symbols.append(symbol)
            i += 1
    # Cartesian positions = scaled positions times row-vector cell.
    positions = []
    for frac in scaled:
        positions.append([
            sum(frac[j] * cell[j][k] for j in range(3)) for k in range(3)
        ])
    return symbols, cell, positions


def read_stage(stage):
    symbols, cell, positions = read_stru(stage / "STRU")
    logs = sorted((child for child in stage.iterdir() if child.is_dir() and child.name.startswith("OUT.")), key=str)
    if len(logs) != 1:
        raise ValueError("expected one OUT directory in %s" % stage)
    log = logs[0] / "running_scf.log"
    text = log.read_text(encoding="utf-8", errors="replace")
    energies = ENERGY_RE.findall(text)
    if not energies:
        raise ValueError("missing FINAL_ETOT_IS in %s" % log)
    marker = "TOTAL-FORCE (eV/Angstrom)"
    if marker not in text:
        raise ValueError("missing force block in %s" % log)
    rows = []
    for line in text.rsplit(marker, 1)[1].splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        try:
            rows.append([float(x) for x in fields[-3:]])
        except ValueError:
            continue
        if len(rows) == len(symbols):
            break
    if len(rows) != len(symbols):
        raise ValueError("force row count mismatch in %s" % log)
    return {
        "chemical_symbols": symbols,
        "cell": cell,
        "positions": positions,
        "energy": float(energies[-1]),
        "forces": rows,
        "source_scf_log": str(log),
    }


def collect(parent):
    manifest = parent / ".zstar" / "shared_response.json"
    if not manifest.is_file():
        manifest = parent / ".zstar" / "bec.json"
    if not manifest.is_file():
        manifest = parent / "shared_response.json"
    if not manifest.is_file():
        raise ValueError("missing shared_response.json in %s" % parent)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("stages"):
        stages = ["0.no-move"] + [str(item["name"]) for item in data.get("stages", [])]
    else:
        stages = ["0.no-move"] + sorted(
            child.name for child in parent.iterdir()
            if child.is_dir() and child.name.startswith("disp-")
        )
    rows = []
    for stage_name in stages:
        stage = parent / stage_name
        if not stage.is_dir():
            raise ValueError("missing stage %s" % stage)
        record = read_stage(stage)
        frame_id = parent.name.replace("frame-", "") + "::" + stage_name
        rows.append({
            "frame_id": frame_id,
            "structure_id": frame_id,
            "chemical_symbols": record["chemical_symbols"],
            "cell": record["cell"],
            "positions": record["positions"],
            "pbc": [True, True, True],
            "total_charge": 0.0,
            "energy": record["energy"],
            "forces": record["forces"],
            "stress": None,
            "polarization": None,
            "dipole": None,
            "born_effective_charges": None,
            "born_effective_charges_available": False,
            "calculator": "ABACUS",
            "exchange_correlation": "PBEsol",
            "pseudopotential": "Wuzhen baseline UPF",
            "orbital": "Wuzhen baseline numerical orbital",
            "kpoints": "Gamma 9x9x9",
            "ecut": 100.0,
            "temperature": None,
            "phase_label": None,
            "source_directory": str(parent.resolve()),
            "source_manifest": str(manifest.resolve()),
            "source_commit": None,
            "units": {"length": "angstrom", "energy": "eV", "force": "eV/angstrom", "bec": "e"},
            "coordinate_convention": "cartesian_A",
            "atom_order": record["chemical_symbols"],
            "validation_status": "imported_raw_dft",
            "metadata": {
                "parent_frame_id": parent.name.replace("frame-", ""),
                "bec_workflow_stage": stage_name,
                "source_scf_log": record["source_scf_log"],
                "label_family": "abacus-pbesol-force-only",
                "energy_policy": "copied verbatim from FINAL_ETOT_IS; no shift or normalization",
            },
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", required=True, type=Path)
    parser.add_argument("--frame-list", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    rows, failed = [], {}
    ids = [line.strip() for line in args.frame_list.read_text(encoding="utf-8").splitlines() if line.strip()]
    for frame_id in ids:
        parent = args.batch_root / (frame_id if frame_id.startswith("frame-") else "frame-" + frame_id)
        try:
            rows.extend(collect(parent))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            failed[frame_id] = str(exc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    report = {
        "schema": "zstar-abacus-raw-force-collection",
        "requested_parent_frames": len(ids),
        "collected_parent_frames": len(set(row["metadata"]["parent_frame_id"] for row in rows)),
        "collected_rows": len(rows),
        "failed_parent_frames": failed,
        "energy_policy": "raw FINAL_ETOT_IS copied verbatim; no offsets, shifts, or normalization",
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
