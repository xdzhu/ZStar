"""Installed workflow lifecycle for bulk piezoelectric response.

The ABACUS route evaluates stress, forces, relaxed internal coordinates, and
PYATB Berry-phase polarization for a central finite-strain ensemble.  The VASP
route is dispatched by the canonical CLI to VASP's native response workflow.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
from typing import Sequence

import numpy as np

from .configuration import launcher_command, normalize_execution_system, resolve_parallelism
from .job_headers import compose_job_script, torque_ppn
from .pyatb_precision import precision_command
from .v2.abacus import collect_pyatb_strain_response
from .v2.difference import fit_finite_difference_document
from .v2.ensemble import ResponseEnsemble
from .v2.strain import V2_SYMPREC, prepare_abacus_strain_ensemble
from .v2.units import convert_values
from .workflow import prepare_pyatb_assets


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def prepare_abacus_piezoelectric_workflow(
    root: str | Path,
    *,
    structure: str | Path,
    input_template: str | Path,
    kpt_template: str | Path,
    pp_dir: str | Path,
    orb_dir: str | Path,
    amplitude: float = 5.0e-3,
    profile: str = "production",
    method: str = "central",
    symprec: float = V2_SYMPREC,
    force_thr_ev: float | None = None,
    scf_thr: float | None = None,
    relax_nmax: int = 100,
    ion_relaxation: str = "relaxed-ion",
) -> Path:
    """Prepare a self-contained three-dimensional ABACUS strain ensemble."""

    output = Path(root).expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"piezoelectric output is not empty: {output}")
    if float(symprec) != V2_SYMPREC:
        raise ValueError(f"piezoelectric response requires symprec={V2_SYMPREC:g}")
    if profile == "production" and float(amplitude) != 5.0e-3:
        raise ValueError("production profile has fixed engineering strain amplitude 0.005")
    if profile == "verification" and float(amplitude) not in {5.0e-3, 1.0e-2}:
        raise ValueError("verification amplitude must be either 0.005 or 0.01")
    if method not in {"central", "forward"}:
        raise ValueError("method must be central or forward")

    result = prepare_abacus_strain_ensemble(
        output,
        structure=structure,
        input_template=input_template,
        kpt_template=kpt_template,
        pp_dir=pp_dir,
        orb_dir=orb_dir,
        dimensionality=3,
        amplitude=amplitude,
        symprec=symprec,
        ion_relaxation=ion_relaxation,
        profile=profile,
        force_thr_ev=force_thr_ev,
        scf_thr=scf_thr,
        relax_nmax=relax_nmax,
        symmetry_reduce=False,
        method=method,
    )
    metadata = {
        "schema": "zstar-piezo-case-preparation",
        "status": "inputs_prepared",
        "root": str(output),
        "ensemble": "ensemble.json",
        "symmetry": "symmetry.json",
        "amplitude_engineering_strain": float(amplitude),
        "convergence_profile": profile,
        "finite_difference": result["ensemble"].metadata["finite_difference"],
        "scf_thr": result["ensemble"].metadata["scf_thr"],
        "ion_relaxation": ion_relaxation,
        "force_thr_ev": result["ensemble"].metadata["force_thr_ev"],
        "relax_nmax": int(relax_nmax),
        "backend": "ABACUS + PYATB",
        "created_at": _utc_now(),
    }
    _write_json(output / "preparation.json", metadata)
    return output


def _stage_paths(root: Path) -> list[Path]:
    ensemble = ResponseEnsemble.read(root / "ensemble.json")
    paths = [root / "reference", *(root / stage.stage_id for stage in ensemble.stages)]
    missing = [str(path) for path in paths if not path.is_dir()]
    if missing:
        raise FileNotFoundError("missing piezoelectric stage directories: " + ", ".join(missing))
    return paths


def _input_value(path: Path, key: str) -> str | None:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("#", 1)[0].split()
        if len(fields) >= 2 and fields[0].lower() == key.lower():
            return fields[1]
    return None


def _abacus_complete(stage: Path) -> bool:
    if list(stage.glob(".abacus_done*")):
        return True
    logs = list(stage.glob("OUT.*/running_scf.log")) + list(stage.glob("OUT.*/running_relax.log"))
    markers = ("charge density convergence is achieved", "calculation finished", "relaxation is converged")
    return any(any(marker in log.read_text(encoding="utf-8", errors="ignore").lower() for marker in markers)
               for log in logs)


def _pyatb_complete(stage: Path) -> bool:
    folder = stage / "pyatb" / "Out" / "Polarization"
    return (folder / "polarization.dat").is_file() and (folder / "zstar_precision.json").is_file()


def piezoelectric_workflow_status(root: str | Path) -> list[dict[str, object]]:
    base = Path(root).expanduser().resolve()
    states = []
    for stage in _stage_paths(base):
        states.append({
            "stage": stage.name,
            "input": (stage / "INPUT").is_file() and (stage / "STRU").is_file(),
            "abacus": "completed" if _abacus_complete(stage) else "pending",
            "pyatb": "completed" if _pyatb_complete(stage) else "pending",
        })
    return states


def format_piezoelectric_status(states: Sequence[dict[str, object]]) -> str:
    lines = [f"{'stage':<20} {'input':<8} {'ABACUS':<11} {'PYATB':<11}"]
    for state in states:
        lines.append(
            f"{str(state['stage']):<20} {('ready' if state['input'] else 'missing'):<8} "
            f"{str(state['abacus']):<11} {str(state['pyatb']):<11}"
        )
    return "\n".join(lines)


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"


def _upf_valence(path: Path) -> float:
    text = path.read_text(encoding="utf-8", errors="ignore")[:100000]
    for pattern in (rf"z_valence\s*=\s*[\"']({_NUMBER})", rf"Z\s*valence\s*=\s*({_NUMBER})"):
        match = re.search(pattern, text, re.I)
        if match:
            return float(match.group(1).replace("D", "E").replace("d", "e"))
    raise ValueError(f"cannot determine z_valence from pseudopotential: {path}")


def infer_pyatb_valence(stage: str | Path) -> tuple[float, ...]:
    """Infer PYATB species valences from STRU-referenced UPF files."""

    root = Path(stage).resolve()
    lines = (root / "STRU").read_text(encoding="utf-8").splitlines()
    values: list[float] = []
    in_species = False
    section_names = {
        "ATOMIC_SPECIES", "NUMERICAL_ORBITAL", "ABFS_ORBITAL", "LATTICE_CONSTANT",
        "LATTICE_VECTORS", "ATOMIC_POSITIONS", "NUMERICAL_DESCRIPTOR",
    }
    for raw in lines:
        fields = raw.split("#", 1)[0].split()
        if not fields:
            continue
        key = fields[0].upper()
        if key in section_names:
            if in_species and key != "ATOMIC_SPECIES":
                break
            in_species = key == "ATOMIC_SPECIES"
            continue
        if in_species:
            if len(fields) < 3:
                break
            pseudo = Path(fields[2]).expanduser()
            if not pseudo.is_absolute():
                pseudo = root / pseudo
            values.append(_upf_valence(pseudo))
    if not values:
        raise ValueError("cannot infer PYATB valence list from STRU; pass --valence")
    return tuple(values)


def _run_command(command: str, *, cwd: Path, log: Path, env: dict[str, str], dry_run: bool) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"DRY-RUN cwd={cwd} command={command}\n")
        return
    with log.open("a", encoding="utf-8") as handle:
        completed = subprocess.run(command, cwd=cwd, env=env, shell=True, stdout=handle,
                                   stderr=subprocess.STDOUT, text=True)
    if completed.returncode:
        raise RuntimeError(f"command failed with exit code {completed.returncode}: {command}")


def run_abacus_piezoelectric_workflow(
    root: str | Path,
    *,
    abacus_command: str,
    pyatb_input: str = "pyatb_input",
    pyatb_command: str = "mpirun -np 1 pyatb",
    pyatb_executable: str = "pyatb",
    valence: Sequence[float] | None = None,
    omp_threads: int = 1,
    dry_run: bool = False,
    stop_after: int | None = None,
) -> list[dict[str, object]]:
    """Run prepared stages serially with stage-level restart markers."""

    base = Path(root).expanduser().resolve()
    stages = _stage_paths(base)
    species_valence = tuple(float(value) for value in valence) if valence else infer_pyatb_valence(stages[0])
    precise_command = precision_command(pyatb_command, pyatb_executable)
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(int(omp_threads))
    env.setdefault("MKL_NUM_THREADS", str(int(omp_threads)))
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    records: list[dict[str, object]] = []

    for index, stage in enumerate(stages):
        if stop_after is not None and index >= int(stop_after):
            break
        lock = stage / ".zstar-piezo.lock"
        if lock.exists():
            raise RuntimeError(f"active or stale piezoelectric stage lock: {lock}")
        if not dry_run:
            lock.mkdir()
        record = {"stage": stage.name, "started_at": _utc_now(), "status": "running"}
        log = base / ".zstar" / "logs" / f"{stage.name}.log"
        compat: Path | None = None
        try:
            if not _abacus_complete(stage):
                _run_command(abacus_command, cwd=stage, log=log, env=env, dry_run=dry_run)
                if not dry_run and not _abacus_complete(stage):
                    raise RuntimeError(f"ABACUS finished without a convergence marker: {stage.name}")
                if not dry_run:
                    (stage / ".abacus_done").touch()
            calculation = (_input_value(stage / "INPUT", "calculation") or "scf").lower()
            if calculation in {"relax", "cell-relax"} and not dry_run:
                relaxed = next(iter(stage.glob("OUT.*/STRU_ION_D")), None)
                if relaxed is None:
                    raise RuntimeError(f"relaxed structure is missing: {stage.name}")
                initial = stage / "STRU_INITIAL"
                if not initial.exists():
                    shutil.copy2(stage / "STRU", initial)
                shutil.copy2(relaxed, stage / "STRU")
                relax_log = next(iter(stage.glob("OUT.*/running_relax.log")), None)
                if relax_log is not None:
                    compat = relax_log.with_name("running_scf.log")
                    if not compat.exists():
                        shutil.copy2(relax_log, compat)
            if not _pyatb_complete(stage):
                pyatb_dir = stage / "pyatb"
                if not (pyatb_dir / "Input").is_file():
                    values = " ".join(f"{value:g}" for value in species_valence)
                    command = (
                        f"{shlex.quote(pyatb_input)} -i {shlex.quote(str(stage))} "
                        f"-o {shlex.quote(str(pyatb_dir))} --polar --valence {values}"
                    )
                    _run_command(command, cwd=stage, log=log, env=env, dry_run=dry_run)
                if not dry_run:
                    prepare_pyatb_assets(stage, pyatb_dir)
                _run_command(precise_command, cwd=pyatb_dir, log=log, env=env, dry_run=dry_run)
                if not dry_run and not _pyatb_complete(stage):
                    raise RuntimeError(f"PYATB precise polarization output is missing: {stage.name}")
                if not dry_run:
                    (stage / ".pyatb_done").touch()
            record.update(status="dry-run" if dry_run else "completed", finished_at=_utc_now())
        except Exception as exc:
            record.update(status="failed", error=str(exc), finished_at=_utc_now())
            records.append(record)
            _write_json(base / ".zstar" / "piezo_run.json", {"stages": records})
            raise
        finally:
            if compat is not None and compat.exists():
                compat.unlink()
            if lock.exists():
                lock.rmdir()
        records.append(record)
        _write_json(base / ".zstar" / "piezo_run.json", {"stages": records})
    return records


def collect_abacus_piezoelectric_workflow(
    root: str | Path,
    *,
    output: str | Path | None = None,
    method: str = "central",
) -> dict[str, object]:
    """Fit proper ``e``, elastic ``C``, and derived ``d`` tensors."""

    base = Path(root).expanduser().resolve()
    target = Path(output).expanduser().resolve() if output else base / "results"
    target.mkdir(parents=True, exist_ok=True)
    collected = collect_pyatb_strain_response(base, require_precision=True)
    gap_records = list(collected.provenance.get("stages", ()))
    missing = [str(item.get("name", "unknown")) for item in gap_records if not item.get("band_gap")]
    metallic = [str(item.get("name", "unknown")) for item in gap_records
                if item.get("band_gap") and not bool(item["band_gap"].get("insulating"))]
    if missing or metallic:
        details = []
        if missing:
            details.append("missing parseable istate.info gap: " + ", ".join(missing))
        if metallic:
            details.append("non-insulating stage: " + ", ".join(metallic))
        raise ValueError("piezoelectric collection requires insulating stages; " + "; ".join(details))
    fitted = fit_finite_difference_document(
        collected,
        method=method,
        stress_sign="compression-positive",
        enforce_major_symmetry=True,
        include_piezoelectric=True,
        include_proper_piezoelectric=True,
        include_elastic=True,
        include_gamma=True,
        include_internal_strain=True,
    )
    fitted.write(target / "response_document.json")
    piezo = fitted.quantity("piezoelectric_proper")
    elastic = fitted.quantity("elastic")
    elastic_gpa = convert_values(elastic.values, elastic.unit, "GPa")
    elastic_pa = convert_values(elastic.values, elastic.unit, "Pa")
    elastic_pa = 0.5 * (elastic_pa + elastic_pa.T)
    try:
        compliance = np.linalg.inv(elastic_pa)
    except np.linalg.LinAlgError as exc:
        raise ValueError("elastic tensor is singular; cannot derive piezoelectric d") from exc
    d_c_per_n = np.asarray(piezo.values, dtype=float) @ compliance
    d_pm_per_v = d_c_per_n * 1.0e12
    closure = float(np.max(np.abs(np.asarray(piezo.values) - d_c_per_n @ elastic_pa)))
    summary: dict[str, object] = {
        "schema": "zstar-piezo-result-summary",
        "status": "completed",
        "root": str(base),
        "backend": fitted.backend,
        "functional": fitted.functional,
        "finite_difference": dict(fitted.metadata["finite_difference"]),
        "fitted_stage_count": int(fitted.metadata["fitted_stage_count"]),
        "space_group": fitted.symmetry.get("space_group"),
        "piezoelectric_proper_C_per_m2": np.asarray(piezo.values).tolist(),
        "elastic_GPa": np.asarray(elastic_gpa).tolist(),
        "elastic_eigenvalues_GPa": np.linalg.eigvalsh(0.5 * (elastic_gpa + elastic_gpa.T)).tolist(),
        "mechanical_stable_positive_definite": bool(
            np.min(np.linalg.eigvalsh(0.5 * (elastic_gpa + elastic_gpa.T))) > 0.0
        ),
        "piezoelectric_d_C_per_N": d_c_per_n.tolist(),
        "piezoelectric_d_pm_per_V": d_pm_per_v.tolist(),
        "closure": {"relation": "e = d @ C^E", "max_C_per_m2": closure},
        "branch_shift_max": int(fitted.metadata.get("branch_shift_max", 0)),
        "branch_residual_max_C_per_m2": float(fitted.metadata.get("branch_residual_max", 0.0)),
        "created_at": _utc_now(),
    }
    _write_json(target / "summary.json", summary)
    return {"root": str(base), "output": str(target), "summary": summary}


def generate_piezoelectric_script(
    root: str | Path,
    *,
    backend: str = "shell",
    output: str | Path | None = None,
    job_name: str = "zstar-piezo",
    nodes: int = 1,
    tasks: int | None = None,
    cpus_per_task: int | None = None,
    walltime: str = "24:00:00",
    queue: str | None = None,
    account: str | None = None,
    env_script: str | Path | None = None,
    header_file: str | Path | None = None,
    abacus_command: str | None = None,
    pyatb_command: str | None = None,
    pyatb_input: str = "pyatb_input",
    valence: Sequence[float] | None = None,
    dry_run: bool = False,
) -> Path:
    """Write a shell, Slurm, or Torque/PBS piezoelectric driver."""

    base = Path(root).expanduser().resolve()
    _stage_paths(base)
    system = normalize_execution_system(backend)
    tasks, cpus_per_task = resolve_parallelism(base, tasks=tasks, cpus_per_task=cpus_per_task)
    if min(int(nodes), tasks, cpus_per_task) < 1:
        raise ValueError("nodes, tasks, and cpus_per_task must be positive")
    abacus_command = abacus_command or launcher_command("abacus", root=base, system=system, tasks=tasks)
    pyatb_command = pyatb_command or launcher_command("pyatb", root=base, system=system, tasks=tasks)
    suffix = {"shell": "sh", "slurm": "slurm", "torque": "pbs"}[system]
    target = Path(output).resolve() if output else base / f"run_zstar_piezo.{suffix}"
    header = ["#!/usr/bin/env bash", f"# ZStar piezoelectric execution system: {system}"]
    if system == "slurm":
        header.extend([
            f"#SBATCH --job-name={job_name}", f"#SBATCH --nodes={int(nodes)}",
            f"#SBATCH --ntasks={tasks}", f"#SBATCH --cpus-per-task={cpus_per_task}",
            f"#SBATCH --time={walltime}", f"#SBATCH --output={base}/.zstar/slurm-%j.out",
        ])
        if queue:
            header.append(f"#SBATCH --partition={queue}")
        if account:
            header.append(f"#SBATCH --account={account}")
    elif system == "torque":
        header.extend([
            f"#PBS -N {job_name}",
            f"#PBS -l nodes={int(nodes)}:ppn={torque_ppn(nodes, tasks, cpus_per_task)}",
            f"#PBS -l walltime={walltime}", f"#PBS -o {base}/.zstar/torque.out",
            f"#PBS -e {base}/.zstar/torque.err",
        ])
        if queue:
            header.append(f"#PBS -q {queue}")
        if account:
            header.append(f"#PBS -A {account}")
    body = ["set -euo pipefail", f"ROOT={shlex.quote(str(base))}", 'cd "$ROOT"']
    if env_script:
        body.append(f"source {shlex.quote(str(Path(env_script).expanduser().resolve()))}")
    command = [
        "zstar", "piezo", "run", "--root", '"$ROOT"',
        "--abacus-command", shlex.quote(abacus_command),
        "--pyatb-input", shlex.quote(pyatb_input),
        "--pyatb-command", shlex.quote(pyatb_command),
        "--omp-threads", str(cpus_per_task),
    ]
    if valence:
        command.extend(["--valence", *(f"{value:g}" for value in valence)])
    if dry_run:
        command.append("--dry-run")
    body.extend([
        " ".join(command) + ' 2>&1 | tee -a "$ROOT/.zstar/piezo.log"',
        *([] if dry_run else ['zstar piezo post --root "$ROOT" 2>&1 | tee -a "$ROOT/.zstar/piezo.log"']),
    ])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(compose_job_script(base, system, header, body, specified=header_file),
                      encoding="utf-8", newline="\n")
    if os.name != "nt":
        target.chmod(target.stat().st_mode | 0o111)
    return target
