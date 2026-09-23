"""Canonical command-family routing layered over the compatibility CLI.

The established command implementations remain the source of behavior.  This
module gives them a coherent public vocabulary while old commands continue to
work during the deprecation period.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Callable, Sequence

from .configuration import (
    config_report,
    initialize_config,
    launcher_command,
    load_config,
    resolve_executable,
    resolve_parallelism,
    set_config_value,
)
from .project_manifest import manifest_path, read_manifest, write_manifest


LegacyRunner = Callable[[Sequence[str]], None]

ACTION_ALIASES = {
    "prepare": "pre",
    "status": "stat",
    "collect": "post",
    "deal": "post",
    "script": "job",
}

FAMILY_HELP = {
    "bec": "pre, job, run, stat, post",
    "phonon": "pre, job, run, stat, post, irrep, spectrum",
    "spectra": "pre, job, run, stat, post",
    "piezo": "pre, job, run, stat, post",
    "dielectric": "static, freq, optics",
    "stru": "convert, wyckoff",
    "data": "db, qnep",
    "skill": "install, path, preflight",
    "config": "init, show, set, check",
}


def _print_family_help(family: str) -> None:
    print(f"usage: zstar {family} <action> [options]")
    print(f"actions: {FAMILY_HELP[family]}")


def _option(arguments: Sequence[str], *names: str, default=None):
    for index, token in enumerate(arguments):
        for name in names:
            if token == name and index + 1 < len(arguments):
                return arguments[index + 1]
            if token.startswith(name + "="):
                return token.split("=", 1)[1]
    return default


def _drop_options(arguments: Sequence[str], *names: str) -> list[str]:
    output: list[str] = []
    skip = False
    for token in arguments:
        if skip:
            skip = False
            continue
        if token in names:
            skip = True
            continue
        if any(token.startswith(name + "=") for name in names):
            continue
        output.append(token)
    return output


def _replace_option(arguments: Sequence[str], old: str, new: str) -> list[str]:
    output = []
    for token in arguments:
        if token == old:
            output.append(new)
        elif token.startswith(old + "="):
            output.append(new + "=" + token.split("=", 1)[1])
        else:
            output.append(token)
    return output


def _has_option(arguments: Sequence[str], *names: str) -> bool:
    return any(
        token in names or any(token.startswith(name + "=") for name in names)
        for token in arguments
    )


def _manifest_defaults(root: str, calculator: str | None, dimensionality: int | None):
    path = manifest_path(root, "bec")
    if path.is_file():
        saved = read_manifest("bec", root)
        calculator = calculator or str(saved["calculator"])
        dimensionality = (
            int(saved["dimensionality"])
            if dimensionality is None
            else dimensionality
        )
        options = dict(saved.get("options", {}))
    elif calculator is None and (Path(root) / "vasp_bec_manifest.json").is_file():
        saved = json.loads((Path(root) / "vasp_bec_manifest.json").read_text(encoding="utf-8"))
        if saved.get("backend") != "vasp":
            raise ValueError("Invalid backend in vasp_bec_manifest.json")
        calculator = "vasp"
        dimensionality = int(saved.get("dimensionality", 3)) if dimensionality is None else dimensionality
        options = {"method": saved["method"], "gamma_phonons": saved.get("phonons", False),
                   "elastic": saved.get("elastic", False)}
    else:
        options = {}
    return calculator or "abacus", 3 if dimensionality is None else dimensionality, options


def _run_bec(arguments: Sequence[str], legacy: LegacyRunner) -> None:
    if not arguments or arguments[0] in {"-h", "--help"}:
        _print_family_help("bec")
        return
    action = ACTION_ALIASES.get(arguments[0], arguments[0])
    if action not in {"pre", "run", "stat", "post", "job"}:
        raise SystemExit(f"Unknown zstar bec action: {arguments[0]}")
    rest = list(arguments[1:])
    calculator = _option(rest, "--calculator", "--calc")
    root = str(_option(rest, "--root", default="."))
    dim_text = _option(rest, "--dim", "--dimensionality")
    dimensionality = None if dim_text is None else int(dim_text)
    method = _option(rest, "--method")
    clean = _drop_options(rest, "--calculator", "--calc")

    if action == "pre":
        calculator = str(calculator or "abacus").lower()
        dimensionality = 3 if dimensionality is None else dimensionality
        if calculator == "abacus":
            clean = _drop_options(clean, "--root")
            manifest_root = str(Path(root).resolve())
            Path(manifest_root).mkdir(parents=True, exist_ok=True)
            previous = Path.cwd()
            try:
                os.chdir(manifest_root)
                legacy(["gen", *clean])
            finally:
                os.chdir(previous)
        elif calculator == "cp2k":
            legacy(["cp2k-bec", "prepare", *clean])
            manifest_root = root if root != "." else "cp2k_bec"
        elif calculator == "vasp":
            legacy(["vasp-bec", "prepare", *clean])
            manifest_root = root if root != "." else "vasp_bec"
        elif calculator == "qe":
            legacy(["qe-bec", "prepare", *clean])
            manifest_root = root if root != "." else "qe_response"
        else:
            raise SystemExit(f"Unsupported BEC calculator: {calculator}")
        from .shared_abacus import MANIFEST, load_manifest
        shared_options = {}
        if calculator == 'vasp' and (Path(manifest_root) / 'vasp_bec_manifest.json').is_file():
            native_data = json.loads((Path(manifest_root) / 'vasp_bec_manifest.json').read_text())
            shared_options = {'method': native_data['method'], 'gamma_phonons': native_data.get('phonons', False),
                              'piezo': native_data.get('piezo', False),
                              'elastic': native_data.get('elastic', False)}
        if calculator == 'abacus' and (Path(manifest_root) / MANIFEST).is_file():
            shared_data = load_manifest(manifest_root)
            shared_options = {
                'method': shared_data['method'],
                'ensemble': 'phonopy',
                'gamma_phonons': True,
                'displacement_angstrom': shared_data['nominal_distance_A'],
            }
        write_manifest(
            "bec",
            root=manifest_root,
            calculator=calculator,
            dimensionality=dimensionality,
            options={"method": method or {"cp2k": "central", "vasp": "dfpt"}.get(calculator, "forward"), **shared_options},
        )
        print(f"[MANIFEST] {manifest_path(manifest_root, 'bec')}")
        return

    calculator, dimensionality, saved_options = _manifest_defaults(
        root, None if calculator is None else str(calculator).lower(), dimensionality
    )
    if not _has_option(clean, "--root"):
        clean.extend(["--root", root])

    action_map = {
        "abacus": {
            "run": ["workflow", "run"],
            "stat": ["workflow", "status"],
            "post": ["deal"],
            "job": ["workflow", "script"],
        },
        "cp2k": {
            "run": ["cp2k-bec", "run"],
            "stat": ["cp2k-bec", "status"],
            "post": ["cp2k-bec", "collect"],
            "job": ["cp2k-bec", "script"],
        },
        "vasp": {
            "run": ["vasp-bec", "run"],
            "stat": ["vasp-bec", "status"],
            "post": ["vasp-bec", "collect"],
            "job": ["vasp-bec", "script"],
        },
        "qe": {
            "run": ["qe-bec", "run"],
            "stat": ["qe-bec", "status"],
            "post": ["qe-bec", "collect"],
            "job": ["qe-bec", "script"],
        },
    }
    try:
        target = action_map[calculator][action]
    except KeyError as exc:
        raise SystemExit(f"Unsupported BEC route: {calculator} {action}") from exc
    if action == "job":
        clean = _replace_option(clean, "--system", "--backend")
    system = str(_option(clean, "--backend", default="shell"))
    tasks, _ = resolve_parallelism(root, tasks=_option(clean, "--tasks"))
    if action == "run":
        if calculator == "abacus":
            if not _has_option(clean, "--abacus-command"):
                clean.extend(["--abacus-command", launcher_command("abacus", root=root)])
            if not _has_option(clean, "--pyatb-command"):
                clean.extend(["--pyatb-command", launcher_command("pyatb", root=root)])
        elif calculator == "cp2k" and not _has_option(clean, "--cp2k-command"):
            clean.extend(["--cp2k-command", launcher_command("cp2k", root=root)])
        elif calculator == "vasp" and not _has_option(clean, "--vasp-command"):
            clean.extend(["--vasp-command", launcher_command("vasp", root=root)])
        elif calculator == "qe":
            for flag, key in (
                ("--pw-command", "qe_pw"),
                ("--ph-command", "qe_ph"),
                ("--dynmat-command", "qe_dynmat"),
            ):
                if not _has_option(clean, flag):
                    clean.extend([flag, launcher_command(key, root=root)])
    elif action == "job":
        if calculator == "abacus":
            if not _has_option(clean, "--abacus-command"):
                clean.extend([
                    "--abacus-command",
                    launcher_command("abacus", root=root, system=system, tasks=tasks),
                ])
            if not _has_option(clean, "--pyatb-command"):
                clean.extend([
                    "--pyatb-command",
                    launcher_command("pyatb", root=root, system=system, tasks=tasks),
                ])
        elif calculator == "cp2k" and not _has_option(clean, "--cp2k-command"):
            clean.extend([
                "--cp2k-command",
                launcher_command("cp2k", root=root, system=system, tasks=tasks),
            ])
        elif calculator == "vasp" and not _has_option(clean, "--vasp-command"):
            clean.extend([
                "--vasp-command",
                launcher_command("vasp", root=root, system=system, tasks=tasks),
            ])
        elif calculator == "qe":
            for flag, key in (
                ("--pw-command", "qe_pw"),
                ("--ph-command", "qe_ph"),
                ("--dynmat-command", "qe_dynmat"),
            ):
                if not _has_option(clean, flag):
                    clean.extend([
                        flag,
                        launcher_command(key, root=root, system=system, tasks=tasks),
                    ])
    if calculator == "abacus":
        if action in {"run", "job"} and not _has_option(clean, "--dim", "--dimensionality"):
            clean.extend(["--dimensionality", str(dimensionality)])
        if action == "post":
            clean = _drop_options(clean, "--root")
            if not _has_option(clean, "--dim", "--dimensionality"):
                clean.extend(["--dim", str(dimensionality)])
            if not _has_option(clean, "--method"):
                clean.extend(["--method", str(saved_options.get("method", "forward"))])
            previous = Path.cwd()
            try:
                os.chdir(Path(root).resolve())
                legacy([*target, *clean])
            finally:
                os.chdir(previous)
            return
    legacy([*target, *clean])


def _piezo_manifest_defaults(root: str, calculator: str | None) -> tuple[str, dict]:
    path = manifest_path(root, "piezo")
    if path.is_file():
        saved = read_manifest("piezo", root)
        return calculator or str(saved["calculator"]), dict(saved.get("options", {}))
    native = Path(root) / "vasp_bec_manifest.json"
    if calculator in {None, "vasp"} and native.is_file():
        saved = json.loads(native.read_text(encoding="utf-8"))
        if saved.get("backend") == "vasp" and saved.get("piezo"):
            return "vasp", {"method": saved.get("method", "dfpt"), "elastic": saved.get("elastic", False)}
    return calculator or "abacus", {}


def _run_piezo(arguments: Sequence[str], legacy: LegacyRunner) -> None:
    if not arguments or arguments[0] in {"-h", "--help"}:
        _print_family_help("piezo")
        return
    action = ACTION_ALIASES.get(arguments[0], arguments[0])
    if action not in {"pre", "run", "stat", "post", "job"}:
        raise SystemExit(f"Unknown zstar piezo action: {arguments[0]}")
    rest = list(arguments[1:])
    calculator = str(_option(rest, "--calculator", "--calc", default="abacus")).lower()
    root = str(_option(rest, "--root", default="piezo_response"))

    if action == "pre" and calculator == "vasp":
        clean = _drop_options(rest, "--calculator", "--calc")
        if not _has_option(clean, "--root"):
            clean.extend(["--root", root])
        for flag in ("--piezo", "--elastic"):
            if not _has_option(clean, flag):
                clean.append(flag)
        legacy(["vasp-bec", "prepare", *clean])
        write_manifest(
            "piezo", root=root, calculator="vasp", dimensionality=3,
            options={"method": "dfpt", "piezo": True, "elastic": True},
        )
        print(f"[MANIFEST] {manifest_path(root, 'piezo')}")
        return

    if action == "pre":
        if calculator != "abacus":
            raise SystemExit("zstar piezo currently supports --calculator abacus or vasp")
        from .piezoelectric_workflow import prepare_abacus_piezoelectric_workflow

        parser = argparse.ArgumentParser(prog="zstar piezo pre")
        parser.add_argument("--calculator", "--calc", default="abacus")
        parser.add_argument("--source", default=None, help="directory containing INPUT, KPT, and STRU")
        parser.add_argument("--root", default="piezo_response")
        parser.add_argument("--stru", default="STRU")
        parser.add_argument("-i", "--input", dest="input_template", default="INPUT")
        parser.add_argument("--kpt", default="KPT")
        parser.add_argument("--pp", default=None)
        parser.add_argument("--orb", default=None)
        parser.add_argument("--amplitude", type=float, default=5.0e-3)
        parser.add_argument("--profile", choices=("production", "verification"), default="production")
        parser.add_argument("--method", choices=("central", "forward"), default="central")
        parser.add_argument("--symprec", type=float, default=1.0e-3)
        parser.add_argument("--force-thr-ev", type=float, default=None)
        parser.add_argument("--scf-thr", type=float, default=None)
        parser.add_argument("--relax-nmax", type=int, default=100)
        parser.add_argument("--ion-relaxation", choices=("clamped-ion", "relaxed-ion"), default="relaxed-ion")
        parser.add_argument("--valence", nargs="+", type=float, default=None)
        args = parser.parse_args(rest)
        source = Path(args.source).expanduser().resolve() if args.source else Path.cwd()
        config = load_config(args.root)
        assets = config.get("abacus", {})
        pp = args.pp or assets.get("pseudo_dir") or source
        orb = args.orb or assets.get("orbital_dir") or source

        def source_path(value: str) -> Path:
            path = Path(value).expanduser()
            return path.resolve() if path.is_absolute() else (source / path).resolve()

        output = prepare_abacus_piezoelectric_workflow(
            args.root,
            structure=source_path(args.stru),
            input_template=source_path(args.input_template),
            kpt_template=source_path(args.kpt),
            pp_dir=pp,
            orb_dir=orb,
            amplitude=args.amplitude,
            profile=args.profile,
            method=args.method,
            symprec=args.symprec,
            force_thr_ev=args.force_thr_ev,
            scf_thr=args.scf_thr,
            relax_nmax=args.relax_nmax,
            ion_relaxation=args.ion_relaxation,
        )
        write_manifest(
            "piezo", root=output, calculator="abacus", dimensionality=3,
            options={"method": args.method, "valence": args.valence or []},
        )
        print(f"[OUT] {output}")
        print(f"[MANIFEST] {manifest_path(output, 'piezo')}")
        return

    calculator, saved_options = _piezo_manifest_defaults(root, None if not _has_option(rest, "--calculator", "--calc") else calculator)
    if calculator == "vasp":
        clean = _drop_options(rest, "--calculator", "--calc")
        if not _has_option(clean, "--root"):
            clean.extend(["--root", root])
        target = {"run": "run", "stat": "status", "post": "collect", "job": "script"}[action]
        if action == "job":
            clean = _replace_option(clean, "--system", "--backend")
        if action == "run" and not _has_option(clean, "--vasp-command"):
            tasks, _ = resolve_parallelism(root, tasks=_option(clean, "--tasks"))
            clean = _drop_options(clean, "--tasks")
            clean.extend(["--vasp-command", launcher_command("vasp", root=root, tasks=tasks)])
        elif action == "job" and not _has_option(clean, "--vasp-command"):
            system = str(_option(clean, "--backend", default="shell"))
            tasks, _ = resolve_parallelism(root, tasks=_option(clean, "--tasks"))
            clean.extend([
                "--vasp-command",
                launcher_command("vasp", root=root, system=system, tasks=tasks),
            ])
        legacy(["vasp-bec", target, *clean])
        return
    if calculator != "abacus":
        raise SystemExit(f"Unsupported piezoelectric calculator: {calculator}")

    from .piezoelectric_workflow import (
        collect_abacus_piezoelectric_workflow,
        format_piezoelectric_status,
        generate_piezoelectric_script,
        piezoelectric_workflow_status,
        run_abacus_piezoelectric_workflow,
    )
    if action == "stat":
        parser = argparse.ArgumentParser(prog="zstar piezo stat")
        parser.add_argument("--root", default="piezo_response")
        parser.add_argument("--calculator", "--calc", default=None)
        args = parser.parse_args(rest)
        print(format_piezoelectric_status(piezoelectric_workflow_status(args.root)))
        return
    if action == "post":
        parser = argparse.ArgumentParser(prog="zstar piezo post")
        parser.add_argument("--root", default="piezo_response")
        parser.add_argument("--calculator", "--calc", default=None)
        parser.add_argument("--output", default=None)
        parser.add_argument("--method", choices=("central", "forward"), default=None)
        args = parser.parse_args(rest)
        result = collect_abacus_piezoelectric_workflow(
            args.root, output=args.output, method=args.method or str(saved_options.get("method", "central"))
        )
        print(f"[OUT] {result['output']}")
        return
    if action == "run":
        parser = argparse.ArgumentParser(prog="zstar piezo run")
        parser.add_argument("--root", default="piezo_response")
        parser.add_argument("--calculator", "--calc", default=None)
        parser.add_argument("--abacus-command", default=None)
        parser.add_argument("--pyatb-input", default="pyatb_input")
        parser.add_argument("--pyatb-command", default=None)
        parser.add_argument("--pyatb-executable", default=None)
        parser.add_argument("--valence", nargs="+", type=float, default=None)
        parser.add_argument("--tasks", type=int, default=None)
        parser.add_argument("--omp-threads", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--stop-after", type=int, default=None)
        args = parser.parse_args(rest)
        tasks, threads = resolve_parallelism(args.root, tasks=args.tasks, cpus_per_task=args.omp_threads)
        pyatb_executable = args.pyatb_executable or resolve_executable("pyatb", root=args.root)
        records = run_abacus_piezoelectric_workflow(
            args.root,
            abacus_command=args.abacus_command or launcher_command("abacus", root=args.root, tasks=tasks),
            pyatb_input=args.pyatb_input,
            pyatb_command=args.pyatb_command or launcher_command("pyatb", root=args.root, tasks=tasks),
            pyatb_executable=pyatb_executable,
            valence=args.valence or saved_options.get("valence") or None,
            omp_threads=threads,
            dry_run=args.dry_run,
            stop_after=args.stop_after,
        )
        print(format_piezoelectric_status(piezoelectric_workflow_status(args.root)))
        if any(record["status"] == "failed" for record in records):
            raise SystemExit(1)
        return

    parser = argparse.ArgumentParser(prog="zstar piezo job")
    parser.add_argument("--root", default="piezo_response")
    parser.add_argument("--calculator", "--calc", default=None)
    parser.add_argument("--system", "--backend", choices=("shell", "local", "slurm", "torque", "pbs"), default="shell")
    parser.add_argument("--output", default=None)
    parser.add_argument("--job-name", default="zstar-piezo")
    parser.add_argument("--nodes", type=int, default=1)
    parser.add_argument("--tasks", type=int, default=None)
    parser.add_argument("--cpus-per-task", type=int, default=None)
    parser.add_argument("--walltime", default="24:00:00")
    parser.add_argument("--queue", default=None)
    parser.add_argument("--account", default=None)
    parser.add_argument("--env-script", default=None)
    parser.add_argument("--header", default=None, help="Specified header; otherwise ./header.sh, then ~/.zstar/header.sh.")
    parser.add_argument("--abacus-command", default=None)
    parser.add_argument("--pyatb-input", default="pyatb_input")
    parser.add_argument("--pyatb-command", default=None)
    parser.add_argument("--valence", nargs="+", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(rest)
    output = generate_piezoelectric_script(
        args.root, backend=args.system, output=args.output, job_name=args.job_name,
        nodes=args.nodes, tasks=args.tasks, cpus_per_task=args.cpus_per_task,
        walltime=args.walltime, queue=args.queue, account=args.account,
        env_script=args.env_script, header_file=args.header,
        abacus_command=args.abacus_command, pyatb_command=args.pyatb_command,
        pyatb_input=args.pyatb_input,
        valence=args.valence or saved_options.get("valence") or None,
        dry_run=args.dry_run,
    )
    print(f"[OUT] {output}")


def _run_config(arguments: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(prog="zstar config")
    actions = parser.add_subparsers(dest="action", required=True)
    init = actions.add_parser("init")
    init.add_argument("--root", default=".")
    init.add_argument("--user", action="store_true")
    init.add_argument("--force", action="store_true")
    show = actions.add_parser("show")
    show.add_argument("--root", default=".")
    show.add_argument("--json", action="store_true")
    set_value = actions.add_parser("set")
    set_value.add_argument("key")
    set_value.add_argument("value")
    set_value.add_argument("--root", default=".")
    set_value.add_argument("--user", action="store_true")
    check = actions.add_parser("check")
    check.add_argument("--root", default=".")
    check.add_argument("--json", action="store_true")
    args = parser.parse_args(list(arguments))
    if args.action == "init":
        print(initialize_config(root=args.root, user=args.user, force=args.force))
    elif args.action == "set":
        print(set_config_value(args.key, args.value, root=args.root, user=args.user))
    elif args.action == "show":
        report = load_config(args.root)
        print(json.dumps(report, indent=2) if args.json else _format_config(report))
    elif args.action == "check":
        report = config_report(args.root)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for name, item in report["executables"].items():
                state = "available" if item["available"] else "missing"
                print(f"{name:<10} {state:<9} {item['command']}")
            print("ABACUS assets")
            for name, item in report.get("abacus_assets", {}).items():
                state = "available" if item["available"] else "missing"
                print(f"{name:<14} {state:<9} {item['path'] or '(not configured)'}")


def _format_config(data: dict) -> str:
    lines = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        lines.extend(f"{key} = {value}" for key, value in values.items())
        lines.append("")
    return "\n".join(lines).rstrip()


def _run_phonon(arguments: Sequence[str], legacy: LegacyRunner) -> None:
    if not arguments or arguments[0] in {"-h", "--help"}:
        _print_family_help("phonon")
        return
    action = ACTION_ALIASES.get(arguments[0], arguments[0])
    if action not in {"pre", "run", "stat", "post", "irrep", "job", "spectrum"}:
        raise SystemExit(f"Unknown zstar phonon action: {arguments[0]}")
    rest = list(arguments[1:])
    root = str(_option(rest, "--root", default="."))
    root_path = Path(root).resolve()
    if action == "spectrum":
        from .phonon_spectrum import run_phonon_spectrum

        parser = argparse.ArgumentParser(prog="zstar phonon spectrum")
        parser.add_argument("--root", default=".")
        parser.add_argument("--calculator", "--calc", default="abacus")
        parser.add_argument("--born", default=None)
        parser.add_argument("--npoints", type=int, default=101)
        parser.add_argument("--mesh", nargs=3, type=int, default=[20, 20, 20])
        parser.add_argument(
            "--nac",
            action="store_true",
            help="Require BORN and generate the NAC comparison outputs.",
        )
        parser.add_argument(
            "--no-nac",
            action="store_true",
            help="Generate only the without-NAC band and DOS plot.",
        )
        parser.add_argument(
            "--band-only",
            action="store_true",
            help="Also write a compact without-NAC/with-NAC band-only comparison.",
        )
        parser.add_argument(
            "--omit-disconnected-tail",
            action="store_true",
            help="Omit the first disconnected trailing path branch.",
        )
        args = parser.parse_args(rest)
        result = run_phonon_spectrum(
            args.root,
            calculator=args.calculator,
            born=args.born,
            npoints=args.npoints,
            mesh=args.mesh,
            require_nac=args.nac,
            no_nac=args.no_nac,
            band_only=args.band_only,
            omit_disconnected_tail=args.omit_disconnected_tail,
        )
        for name in result["outputs"]:
            print(f"[OUT] {Path(args.root).resolve() / name}")
        return

    if action in {"run", "stat", "job"}:
        from .phonon_workflow import (
            format_phonon_status,
            generate_phonon_script,
            phonon_workflow_status,
            run_phonon_workflow,
        )

        parser = argparse.ArgumentParser(prog=f"zstar phonon {action}")
        parser.add_argument('--root', default='.')
        if action == 'run':
            parser.add_argument('--command', default=None)
            parser.add_argument('--omp-threads', type=int, default=None)
            parser.add_argument('--dry-run', action='store_true')
            parser.add_argument('--stop-after', type=int, default=None)
            args = parser.parse_args(rest)
            _, args.omp_threads = resolve_parallelism(args.root, cpus_per_task=args.omp_threads)
            states = run_phonon_workflow(
                args.root,
                command=args.command,
                omp_threads=args.omp_threads,
                dry_run=args.dry_run,
                stop_after=args.stop_after,
            )
            print(format_phonon_status(states))
        elif action == 'stat':
            args = parser.parse_args(rest)
            print(format_phonon_status(phonon_workflow_status(args.root)))
        else:
            parser.add_argument('--system', '--backend', choices=['shell', 'local', 'slurm', 'torque', 'pbs'], default='shell')
            parser.add_argument('--output', default=None)
            parser.add_argument('--job-name', default='zstar-phonon')
            parser.add_argument('--nodes', type=int, default=1)
            parser.add_argument('--tasks', type=int, default=None)
            parser.add_argument('--cpus-per-task', type=int, default=None)
            parser.add_argument('--walltime', default='24:00:00')
            parser.add_argument('--queue', default=None)
            parser.add_argument('--account', default=None)
            parser.add_argument('--env-script', default=None)
            parser.add_argument('--header', default=None, help='Specified header; otherwise ./header.sh, then ~/.zstar/header.sh.')
            parser.add_argument('--command', default=None)
            parser.add_argument('--dry-run', action='store_true')
            args = parser.parse_args(rest)
            output = generate_phonon_script(
                args.root,
                backend=args.system,
                output=args.output,
                job_name=args.job_name,
                nodes=args.nodes,
                tasks=args.tasks,
                cpus_per_task=args.cpus_per_task,
                walltime=args.walltime,
                queue=args.queue,
                account=args.account,
                env_script=args.env_script,
                header_file=args.header,
                command=args.command,
                dry_run=args.dry_run,
            )
            print(f"[OUT] {output}")
        return

    calculator = _option(rest, "--calculator", "--calc")
    physical_dim_text = _option(rest, "--physical-dim", default=None)
    clean = _drop_options(rest, "--root", "--calculator", "--calc")
    if action == "pre":
        if _has_option(rest, "--spectrum"):
            from .phonon_spectrum import prepare_phonon_spectrum

            parser = argparse.ArgumentParser(prog="zstar phonon pre --spectrum")
            parser.add_argument("--spectrum", action="store_true", help=argparse.SUPPRESS)
            parser.add_argument("--root", default=".")
            parser.add_argument("--stru", default="STRU")
            parser.add_argument(
                "--input",
                default="INPUT",
                help="User-provided ABACUS input; copied as INPUT in each stage.",
            )
            parser.add_argument("--supercell", "--dim", dest="supercell", default=None)
            parser.add_argument("--physical-dim", type=int, default=3)
            parser.add_argument("--periodic-axes", default=None)
            parser.add_argument("--minimum-length", type=float, default=10.0)
            parser.add_argument("--symmprec", "--tol", type=float, default=1.0e-3)
            parser.add_argument("--calculator", "--calc", default="abacus")
            args = parser.parse_args(rest)
            metadata = prepare_phonon_spectrum(
                args.root,
                structure=args.stru,
                input_file=args.input,
                supercell=args.supercell,
                dimensionality=args.physical_dim,
                periodic_axes=args.periodic_axes,
                minimum_length=args.minimum_length,
                symm_tol=args.symmprec,
                calculator=args.calculator,
            )
            print(
                f"[SPECTRUM] supercell={' '.join(str(item) for item in metadata['supercell'])}; "
                f"generated={len(metadata['displacement_folders'])}"
            )
            return
        physical_dim = 3 if physical_dim_text is None else int(physical_dim_text)
        clean = _drop_options(clean, "--physical-dim")
        structure = Path(_option(clean, "--stru", default="STRU"))
        structure_path = structure if structure.is_absolute() else root_path / structure
        if calculator is None and structure_path.is_file():
            text = structure_path.read_text(encoding="utf-8", errors="ignore")
            calculator = "abacus" if "ATOMIC_SPECIES" in text else "vasp"
        calculator = str(calculator or "abacus").lower()
        root_path.mkdir(parents=True, exist_ok=True)
        previous = Path.cwd()
        try:
            os.chdir(root_path)
            legacy(["ph", *clean])
        finally:
            os.chdir(previous)
        write_manifest(
            "phonon",
            root=root_path,
            calculator=calculator,
            dimensionality=physical_dim,
            options={
                "supercell": str(_option(clean, "--dim", default="1 1 1")),
                "structure": str(_option(clean, "--stru", default="STRU")),
            },
        )
        print(f"[MANIFEST] {manifest_path(root_path, 'phonon')}")
        return

    if manifest_path(root_path, "phonon").is_file():
        saved = read_manifest("phonon", root_path)
        physical_dim = int(saved["dimensionality"])
        saved_options = dict(saved.get("options", {}))
    else:
        physical_dim = 3 if physical_dim_text is None else int(physical_dim_text)
        saved_options = {}
    previous = Path.cwd()
    try:
        os.chdir(root_path)
        if action == "post":
            if not _has_option(clean, "--physical-dim"):
                clean.extend(["--physical-dim", str(physical_dim)])
            if not _has_option(clean, "--stru") and saved_options.get("structure"):
                clean.extend(["--stru", str(saved_options["structure"])])
            legacy(["postph", *clean])
        else:
            clean = _drop_options(clean, "--physical-dim")
            legacy(["irrep", *clean])
    finally:
        os.chdir(previous)


def handle_canonical_cli(arguments: Sequence[str], legacy: LegacyRunner) -> bool:
    """Handle a canonical family and return whether it consumed the command."""

    if not arguments:
        return False
    family = arguments[0]
    rest = list(arguments[1:])
    if family == "bec":
        _run_bec(rest, legacy)
        return True
    if family == "piezo":
        _run_piezo(rest, legacy)
        return True
    phonon_actions = set(ACTION_ALIASES) | {"pre", "run", "stat", "post", "irrep", "job", "spectrum"}
    if family == "phonon" or (
        family == "ph" and rest and rest[0] in phonon_actions | {"-h", "--help"}
    ):
        _run_phonon(rest, legacy)
        return True
    if family == "spectra":
        if not rest or rest[0] in {"-h", "--help"}:
            _print_family_help("spectra")
            return True
        from .spectra_frontend import run_spectra_cli

        run_spectra_cli(rest, legacy)
        return True
    if family in {"dielectric", "diel"}:
        if not rest or rest[0] in {"-h", "--help"}:
            _print_family_help("dielectric")
            return True
        action = "static" if rest[0] == "zero" else rest[0]
        mapping = {"static": "calc", "freq": "freq", "optics": "optics"}
        if action not in mapping:
            raise SystemExit(f"Unknown zstar dielectric action: {rest[0]}")
        legacy([mapping[action], *rest[1:]])
        return True
    if family == "stru":
        if not rest or rest[0] in {"-h", "--help"}:
            _print_family_help("stru")
            return True
        mapping = {"convert": "vasp", "wyckoff": "wyckoff"}
        if rest[0] not in mapping:
            raise SystemExit(f"Unknown zstar stru action: {rest[0]}")
        tail = list(rest[1:])
        if rest[0] == "convert":
            target = _option(tail, "--to", default="vasp")
            if str(target).lower() not in {"vasp", "poscar"}:
                raise SystemExit("zstar stru convert currently supports only --to vasp")
            tail = _drop_options(tail, "--to")
        legacy([mapping[rest[0]], *tail])
        return True
    if family == "data":
        if not rest or rest[0] in {"-h", "--help"}:
            _print_family_help("data")
            return True
        if rest[0] not in {"qnep", "db"}:
            raise SystemExit(f"Unknown zstar data action: {rest[0]}")
        legacy(rest)
        return True
    if family == "skill":
        if not rest or rest[0] in {"-h", "--help"}:
            _print_family_help("skill")
            return True
        legacy(["agent-skill", *rest])
        return True
    if family == "config":
        _run_config(rest)
        return True
    return False
