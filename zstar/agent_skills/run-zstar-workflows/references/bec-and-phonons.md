# BEC and phonon lanes

## Polarization and BEC

Prepare a PYATB-backed finite-displacement tree:

```bash
zstar bec pre --stru STRU
zstar bec run --root .
zstar bec stat --root .
zstar bec post --root .
```

ZStar defaults to a Unified, Phonopy-generated BEC/Gamma ensemble:
`0.no-move`, `disp-001`, etc., recorded in the compatibility manifest
`shared_response.json`. It adds
force output and reconstructs both responses from the same SCFs. Use actual
serialized vectors, not a rounded 0.01-Angstrom denominator. Default sign
selection is `auto`; `--ensemble cartesian` selects the archived x/y/z route.
Check installed help before assuming an older release has this feature.

The workflow executor option is `--dimensionality 0|1|2|3` (with `--dim` as an
alias); the agent-skill preflight uses the user-facing values
`molecule|1d|2d|bulk`. Use `--gap-mode path` by default or `--gap-mode mp` when a
denser insulation check is scientifically required.

For shell, Slurm, or Torque, generate one root driver:

```bash
zstar bec job --system shell --root . --dry-run
zstar bec job --system slurm --root . --dry-run
zstar bec job --system torque --root . --dry-run
```

Remove `--dry-run` only after checking the generated script and environment.
Use `--submit` only with explicit authorization.
Queue, resource directives, and modules belong in the selected job header.

For CP2K, use the independent serial lane:

```bash
zstar bec pre --calculator cp2k --input input.inp --root cp2k_bec
zstar bec run --root cp2k_bec --dry-run
zstar bec stat --root cp2k_bec
zstar bec post --root cp2k_bec
```

## Molecular atomic polar tensors

For an isolated molecule, use the default Unified ensemble with `--dim 0`.
ZStar reports
an atomic polar tensor (APT), the molecular analogue of a periodic BEC:

```bash
zstar bec pre --stru STRU --dim 0
zstar bec run --root .
zstar bec post --root .
```

The Unified collector records its joint APT and force-constant reconstruction
in `response_fit.json`; archived Cartesian/cube calculations may instead contain
`apt.json`. Inspect the raw and corrected translational sums. CP2K can run the same definition with
`zstar bec pre --calculator cp2k --dim 0`; compare rotationally invariant GAPT values
(`trace(APT)/3`) when molecular orientations differ.

## Two-dimensional BEC

Use `--dim 2` consistently in generation, execution, and collection. Generate
information spanning all Cartesian directions, through the Phonopy site
orbits or explicit Cartesian sampling. The out-of-plane response requires
reference and displaced charge-density cubes; audit a pair with:

```bash
zstar polar2d --reference-cube reference.cube \
  --displaced-cube displaced.cube --displacement 0.01
```

Do not replace the open-direction dipole with a vacuum-diluted 3D Berry
polarization.

## One-dimensional BEC

The production convention is a wire periodic along Cartesian `z`, with
orthogonal vacuum vectors along `x/y`:

```bash
zstar bec pre --stru STRU --input INPUT --dim 1
zstar bec run --root .
zstar bec stat --root .
zstar bec post --root .
```

ZStar integrates transverse dipoles from neutral ABACUS charge cubes and uses
only the periodic `z` Berry phase. Current PYATB builds evaluate all three
Berry loops, so ZStar pads the generated polarization mesh to at least two
points along every axis and records the compatibility change. Do not interpret
the transverse PYATB values as physical wire polarization. Keep the generated
`out_chg 1 10` setting: the documented ABACUS default cube precision is too
coarse for transverse dipole finite differences. ZStar unwraps boundary-
spanning wires around a weighted circular ionic center; retain the reference
structure and displaced structures in the same cell convention.

## Phonons and harmonic dielectric response

In a completed Unified ensemble, `zstar bec post` already writes `BORN`,
`FORCE_CONSTANTS`, `qpoints.yaml`, and `irreps.yaml`. Proceed directly to
`zstar phonon irrep` or `zstar dielectric static`; do not repeat Gamma SCFs.
Converge the Berry mesh for mixed seeds, inspect raw residuals and conditioning,
and retain full-precision polarization. Charge cubes must be private copies.
All stages must have matching polarization grids, valence counts, and occupied
bands. Negative optical frequencies must not be hidden in a static response.

For a finite-q supercell workflow, use a separate directory. The spectrum
variant also writes Phonopy band and DOS plots:

```bash
zstar phonon pre --spectrum --stru STRU --input INPUT --supercell "2 2 2" --physical-dim 3
zstar phonon run --root .
zstar phonon stat --root .
zstar phonon post --root . --stru STRU --physical-dim 3
cp path/to/bec/BORN .
zstar phonon spectrum --root . --nac
```

The `--input` option defaults to `INPUT` and can point to a user-owned ABACUS
CPU/GPU input. It is staged as `INPUT` in each displacement directory without
editing calculator-specific settings; require `cal_force 1`. For 3D bulk,
prefer MPI ranks with one OpenMP thread per rank. For lower-dimensional or
molecular cases, use the allocation that best matches the calculator.

If `--supercell` is omitted, repeat each periodic lattice vector until it is
strictly longer than 10 Angstrom. The band path is generated from Seekpath
and spglib labels. A bulk `BORN` archive produces separate w/o NAC and with
NAC plots plus a combined comparison plot; add `--band-only` for an additional
compact band-only comparison. Use `--omit-disconnected-tail` when a focused
figure should omit a disconnected trailing branch; `--no-nac` requests only
the first plot.
NAC is rejected for non-bulk dimensionalities.

For a 2D slab, use `--dim 2`. Omit `--thickness` for the vacuum-independent
sheet response; supply a physically justified thickness only when converting to
an effective 3D dielectric tensor.

The complete unpassivated BN(9,0) and Sb2S3 examples use the default unified
ensemble with `--dim 1`: do not rerun Gamma force SCFs. For diagnostics, use the
raw and projected tensors separately. `response.json` and `BEC.dat` have
displacement-first BEC axes, whereas `response_fit.json` stores the reconstruction
in polarization-first order. Rotate both tensor axes when changing coordinates.
For a tube, radial/tangential bases vary by atom; test neutrality in a common
Cartesian frame. Sb2S3 reference data use a different hybrid functional and do
not establish quantitative agreement of Raman intensities.

For a finite-q 1D wire calculation, generate a supercell only along the periodic direction and use
`zstar phonon post --physical-dim 1` without NAC. Then pass
`--dim 1 --periodic-axis z` to spectroscopy and dielectric post-processing. The
reported intrinsic response is a line polarizability in area units. Do not
claim finite-wavevector polar dispersion until a genuine 1D Coulomb-cutoff
kernel is available.
