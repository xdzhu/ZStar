"""Canonical spectroscopy lifecycle over a Unified ABACUS displacement ensemble."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import time

import numpy as np

from . import spectra, workflow
from .project_manifest import read_manifest, write_manifest
from .pyatb_compat import (_OPTICAL_BLOCK_RE, _POLARIZATION_BLOCK_RE,
                          configure_optical_input, detect_pyatb_capabilities,
                          read_static_dielectric)
from .raman_response import reconstruct_raman_derivatives, project_raman_modes, internal_mode_indices
from .shared_abacus import MANIFEST, _digest, load_manifest, collect_shared_abacus
from .shared_response import read_structure, actual_displacement, make_phonopy, symmetry_operations


def prepare(root, response, *, kind='all', dimension=None):
    root, response = Path(root).resolve(), Path(response).resolve()
    if root == response or response.is_relative_to(root):
        raise ValueError('Use a separate spectra directory beside the BEC ensemble, not its parent')
    data = load_manifest(response)
    if dimension is not None and dimension != data['dimension']:
        raise ValueError('--dim disagrees with the Unified response ensemble')
    target = root/'.zstar/spectra.json'
    if target.exists():
        raise FileExistsError(f'{target} exists; use run/stat/post to resume or choose another --root')
    # Check geometric completeness before any electronic calculation.
    atoms = read_structure(response/'0.no-move/STRU')
    operations = symmetry_operations(make_phonopy(atoms, symprec=data['symprec_A']),
                                     dimension=data['dimension'])
    reconstruct_raman_derivatives(len(atoms),
        [{**s, 'delta_epsilon':np.zeros((3,3))} for s in data['stages']], operations)
    return write_manifest('spectra', root=root, calculator='abacus',
        dimensionality=data['dimension'], options=dict(kind=kind, method='unified',
        response=os.path.relpath(response, root), response_manifest_sha256=_digest(response/MANIFEST)))


def source(root):
    root = Path(root).resolve()
    options = read_manifest('spectra', root)['options']
    response = (root/options['response']).resolve()
    if _digest(response/MANIFEST) != options['response_manifest_sha256']:
        raise ValueError('Unified displacement manifest changed; prepare a new spectra workspace')
    return response, load_manifest(response), options


def _verify_done(folder, *, sources=True):
    marker = folder/'completed.json'
    if not marker.exists():
        return False
    data = json.loads(marker.read_text())
    for name, sha in data['outputs'].items():
        path = folder/name
        if not path.is_file() or _digest(path) != sha:
            raise ValueError(f'Changed or missing static response: {path}; use a new spectra workspace')
    if sources:
        for name, sha in data['sources'].items():
            if not (folder/name).is_file() or _digest(folder/name) != sha:
                raise ValueError(f'Reused electronic source changed: {name}; prepare a new spectra workspace')
    return True


def _static_stage(stage, reference, folder, *, command, caps, env, dry_run=False):
    """Private matrix copies prevent PYATB conversion/output from changing BEC data."""
    if _verify_done(folder):
        return 'completed'
    if dry_run:
        print(f'[DRY RUN] static dielectric: {stage.name} -> {folder}')
        return 'pending'
    from .abacus_assets import prepare_stru_assets
    origin = stage/'pyatb'
    template_path = reference/'pyatb/Input'
    optical = _OPTICAL_BLOCK_RE.search(template_path.read_text())
    if optical is None:
        raise ValueError('Reference lacks an optical block; complete `zstar bec run` first')
    text = (origin/'Input').read_text()
    text = _POLARIZATION_BLOCK_RE.sub('', _OPTICAL_BLOCK_RE.sub('', text)).rstrip()+'\n'+optical[0]+'\n'
    originals = [origin/'Input', origin/'STRU', template_path]
    matrices = []
    for key in ('HR_route','SR_route','rR_route'):
        match = re.search(r'(?m)^\s*'+key+r'\s+(\S+)\s*$', text)
        if not match:
            raise ValueError(f'Missing {key} in {origin}/Input')
        path = Path(match[1])
        path = path if path.is_absolute() else origin/path
        if not path.is_file():
            raise FileNotFoundError(f'{path}: regenerate electronic matrices before Raman postprocessing')
        originals.append(path.resolve())
        matrices.append(path.resolve())
        text = text[:match.start(1)]+path.name+text[match.end(1):]
    if len({p.name for p in matrices}) != 3:
        raise ValueError('Matrix basenames collide; use unique HR/SR/rR filenames')
    folder.mkdir(parents=True, exist_ok=True)
    for target in (folder, folder/'Input', folder/'STRU', folder/'.assets'):
        if target.is_symlink():
            raise ValueError(f'Symbolic links are not allowed in private response workspaces: {target}')
    assets = prepare_stru_assets(origin/'STRU', pp_dir=origin, orb_dir=origin,
                                 output_dir=folder/'.assets')
    originals.extend(assets.assets)
    hashes = {os.path.relpath(p.resolve(), folder):_digest(p) for p in originals}
    request = folder/'request.json'
    if request.exists() and json.loads(request.read_text()) != hashes:
        raise ValueError(f'Sources changed during an incomplete stage: {folder}; use a new workspace')
    request.write_text(json.dumps(hashes, indent=2)+'\n')
    for path in matrices+list(assets.assets):
        target = folder/path.name
        if target.is_symlink():
            raise ValueError(f'Symbolic links are not allowed in private matrix workspaces: {target}')
        shutil.copy2(path, target)
    shutil.copy2(assets.path, folder/'STRU')
    (folder/'Input').write_text(text)
    configure_optical_input(folder/'Input', capabilities=caps, static_only=True)
    record = dict(sources=hashes, success=False, additional_DFT_calls=0)
    started = time.monotonic()
    try:
        workflow._run_shell(command, cwd=folder, env=env, log_path=folder/'run.log', dry_run=False)
        epsilon, path = read_static_dielectric(folder)
        precision = path.parent/'zstar_static_precision.json'
        if not precision.is_file():
            raise ValueError('Lossless dielectric output is missing; run PYATB via zstar.pyatb_precision')
        for original, sha in hashes.items():
            if _digest(folder/original) != sha:
                raise ValueError(f'Electronic source changed during postprocessing: {original}')
        record.update(success=True, epsilon=epsilon.tolist(),
            outputs={p.relative_to(folder).as_posix():_digest(p)
                     for p in [path, precision, folder/'Input', folder/'STRU']})
    finally:
        record['wall_seconds'] = time.monotonic()-started
        (folder/('completed.json' if record['success'] else 'failed.json')).write_text(
            json.dumps(record, indent=2)+'\n')
    return 'completed'


def status(root):
    root = Path(root).resolve()
    response, data, options = source(root)
    rows = []
    for name in ['0.no-move']+[s['name'] for s in data['stages']]:
        stage = response/name
        rows.append(dict(stage=name, scf=workflow.scf_is_complete(stage),
            polarization=workflow.polarization_is_complete(stage),
            raman_static=None if options['kind']=='ir' else _verify_done(root/'static'/name)))
    return rows


def run(root, **kwargs):
    from .pyatb_precision import precision_command
    root = Path(root).resolve()
    response, data, options = source(root)
    lock = root/'.zstar/unified-spectra.lock'
    try:
        handle = lock.open('x')
    except FileExistsError:
        raise RuntimeError(f'Worker lock exists: {lock}. Check its process before removing a stale lock.') from None
    try:
        with handle:
            handle.write(f'{os.getpid()}\n')
        dry_run = kwargs.get('dry_run', False)
        states = status(root)
        reference = response/'0.no-move'
        if (not all(r['scf'] and r['polarization'] for r in states)
                or not workflow.dielectric_is_complete(reference)
                or not workflow.band_is_complete(reference)):
            workflow.run_serial_workflow(response, **kwargs)
        if not dry_run:
            gap = workflow.read_band_gap(response/'0.no-move/pyatb-band')
            if not gap.insulating:
                raise ValueError('Reference band gap is not insulating')
        if options['kind'] != 'ir':
            executable = kwargs.get('pyatb_executable', 'pyatb')
            command = precision_command(kwargs.get('pyatb_command', 'pyatb'), executable)
            caps = detect_pyatb_capabilities(executable)
            env = {**os.environ, 'OMP_NUM_THREADS':str(kwargs.get('omp_threads',1))}
            for row in states:
                _static_stage(response/row['stage'], response/'0.no-move', root/'static'/row['stage'],
                    command=command, caps=caps, env=env, dry_run=dry_run)
        return status(root)
    finally:
        lock.unlink()


def collect(root, *, temperature=300., laser=532., broadening=8., points=3001,
            max_frequency=None, incident_polarization=None,
            scattered_polarization=None, plot=True):
    root = Path(root).resolve()
    response, data, options = source(root)
    if not (response/'qpoints.yaml').exists() or not (response/'BEC.dat').exists():
        collect_shared_abacus(response)
    modes = spectra.load_gamma_modes(response/'qpoints.yaml')
    atoms = read_structure(response/'0.no-move/STRU')
    np.testing.assert_allclose(modes.lattice_angstrom, np.asarray(atoms.cell), atol=1e-6, rtol=0)
    if len(atoms) != len(modes.masses_amu):
        raise ValueError('Phonon modes and Unified ensemble have different atom counts')
    delta = modes.positions_fractional-np.asarray(atoms.scaled_positions)
    np.testing.assert_allclose((delta-np.rint(delta))@np.asarray(atoms.cell), 0., atol=1e-6)
    selected, audit = internal_mode_indices(modes, data['dimension'])
    numbers = (selected+1).tolist()
    common = dict(broadening_cm1=broadening, max_frequency_cm1=max_frequency,
                  points=points, allow_imaginary=True)
    # Imaginary rigid modes are excluded by overlap; internal modes must be positive.
    born = spectra.read_born_data(response/'BEC.dat', natoms=len(atoms),
                                   dielectric_path=response/'BORN')
    if options['kind'] in ('ir','all'):
        if data['dimension'] == 0:
            derivatives = spectra.mode_effective_charges(modes, born.tensors)[selected]*4.80320471257
            ir = spectra.calculate_molecular_ir_spectrum(modes, numbers, derivatives, **common)
            spectra.write_molecular_ir_outputs(root/'ir', ir, plot=plot)
        else:
            ir = spectra.calculate_ir_spectrum(modes, born, dimensionality=data['dimension'],
                                              mode_numbers=numbers, **common)
            spectra.write_ir_outputs(root/'ir', ir, plot=plot)
    report = dict(method='unified', dimension=data['dimension'], mode_selection=audit,
                  mode_numbers=numbers, source_manifest_sha256=_digest(response/MANIFEST))
    if options['kind'] != 'ir':
        static = root/'static'
        names = ['0.no-move']+[s['name'] for s in data['stages']]
        if not all(_verify_done(static/name) for name in names):
            raise ValueError('Static response stages incomplete; run `zstar spectra run` first')
        epsilon0, _ = read_static_dielectric(static/'0.no-move')
        observations = []
        for s in data['stages']:
            atom, vector = actual_displacement(atoms, read_structure(response/s['name']/'STRU'))
            if atom != s['atom'] or not np.allclose(vector, s['displacement_A'], atol=1e-10, rtol=0):
                raise ValueError(f"Displacement differs from manifest: {s['name']}")
            epsilon, _ = read_static_dielectric(static/s['name'])
            observations.append(dict(atom=atom, displacement_A=vector, delta_epsilon=epsilon-epsilon0))
        operations = symmetry_operations(make_phonopy(atoms, symprec=data['symprec_A']), dimension=data['dimension'])
        derivative, diagnostics = reconstruct_raman_derivatives(len(atoms), observations, operations)
        factor = {3:1., 2:modes.cell_height_angstrom, 1:modes.area_angstrom2/(4*np.pi),
                  0:modes.volume_angstrom3/(4*np.pi)}[data['dimension']]
        tensors = project_raman_modes(derivative, modes.eigenvectors, modes.masses_amu)[selected]*factor
        from .response_units import raman_convention
        convention = raman_convention(data['dimension'])
        raman = spectra.calculate_raman_spectrum(modes, numbers, tensors,
            tensor_kind=convention['tensor_unit'], temperature_K=temperature, laser_nm=laser, **common)
        spectra.write_raman_outputs(root/'raman', raman, plot=plot)
        if bool(incident_polarization) != bool(scattered_polarization):
            raise ValueError('Specify both incident and scattered polarizations')
        if incident_polarization:
            from .spectroscopy_analysis import calculate_polarized_raman_spectrum
            polarized = calculate_polarized_raman_spectrum(
                modes.frequencies_cm1[selected], tensors, mode_numbers=numbers,
                incident_polarization=incident_polarization,
                scattered_polarization=scattered_polarization,
                temperature_K=temperature, laser_nm=laser,
                broadening_cm1=broadening, max_frequency_cm1=max_frequency,
                points=points)
            spectra.write_native_line_spectrum_outputs(
                root/'raman/polarized', polarized, stem='raman_polarized', plot=plot)
        np.save(root/'raman/atomic_dielectric_derivatives.npy', derivative)
        report.update(raman_convention=convention, raman_diagnostics=diagnostics)
        from .response_schema import ResponseRecord, ResponseQuantity
        from .dimensions import dimension_spec
        quantities = [ResponseQuantity('raman_tensors', tensors, convention['tensor_unit'],
            convention['response_definition'], ('mode','row','column'),
            metadata={'mode_numbers':numbers}), ResponseQuantity('dielectric_displacement_derivatives',
            derivative, '1/angstrom', 'supercell', ('atom','row','column','displacement'))]
        base = response/'response.json'
        if base.exists():
            quantities = list(ResponseRecord.read(base).quantities)+quantities
        ResponseRecord(backend='abacus', dimensionality=dimension_spec(data['dimension']),
            quantities=tuple(quantities), provenance={'method':'unified', 'ensemble':str(response)},
            metadata={'scope':'Gamma, static nonresonant Placzek', **report}).write(root/'response.json')
    (root/'spectra_result.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def run_cli(action, arguments, root):
    from .configuration import launcher_command, resolve_executable, resolve_parallelism
    p = argparse.ArgumentParser(prog=f'zstar spectra {action}')
    p.add_argument('--root')
    if action == 'run':
        p.add_argument('--abacus-command')
        p.add_argument('--pyatb-command')
        p.add_argument('--pyatb-input')
        p.add_argument('--pyatb-executable')
        p.add_argument('--omp-threads', type=int)
        p.add_argument('--mp-density', type=float, default=.08)
        p.add_argument('--dry-run', action='store_true')
    elif action == 'post':
        p.add_argument('--temperature', type=float, default=300.)
        p.add_argument('--laser', '--laser-nm', dest='laser', type=float, default=532.)
        p.add_argument('--broadening', type=float, default=8.)
        p.add_argument('--points', type=int, default=3001)
        p.add_argument('--max-frequency', type=float)
        p.add_argument('--incident-polarization', type=float, nargs=3)
        p.add_argument('--scattered-polarization', type=float, nargs=3)
        p.add_argument('--no-plot', action='store_true')
    a = p.parse_args(arguments)
    if action == 'run':
        _, threads = resolve_parallelism(root, cpus_per_task=a.omp_threads)
        result = run(root, abacus_command=a.abacus_command or launcher_command('abacus',root=root),
            pyatb_command=a.pyatb_command or launcher_command('pyatb',root=root),
            pyatb_input=a.pyatb_input or 'pyatb_input',
            pyatb_executable=a.pyatb_executable or resolve_executable('pyatb',root=root),
            omp_threads=threads, mp_density=a.mp_density, dry_run=a.dry_run)
    elif action == 'stat':
        result = status(root)
    else:
        result = collect(root, temperature=a.temperature, laser=a.laser,
                         broadening=a.broadening, points=a.points,
                         max_frequency=a.max_frequency,
                         incident_polarization=a.incident_polarization,
                         scattered_polarization=a.scattered_polarization,
                         plot=not a.no_plot)
    print(json.dumps(result, indent=2))
