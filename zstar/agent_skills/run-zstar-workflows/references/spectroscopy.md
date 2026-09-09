# Spectroscopy lane

## ABACUS/PYATB IR and Raman

Use the Unified ensemble recorded by `shared_response.json`:

```bash
zstar spectra pre
zstar spectra run --dry-run
zstar spectra stat
```

Use `--response PATH` to select another BEC ensemble. Geometry and dimension
are inherited; do not pass competing `--stru` or mode-preparation options.
After authorization, run without `--dry-run`, then `zstar spectra post`.
Reference/displaced SCFs are resumed, never deliberately repeated for Raman.
Additional PYATB static responses use private matrix copies and full-precision
output. Never symlink cubes or edit source matrices. Missing matrices, changed
source hashes, unstable internal modes and ambiguous rigid-motion overlaps
are blockers, not reasons to fabricate or silently normalize results.
This route covers Gamma IR and static nonresonant Placzek Raman in dim 0/1/2/3.

### Explicit mode-difference control

Prepare one manifest-aware workflow. `--kind` may be `ir`, `raman`, or `all`:

```bash
zstar spectra pre --method mode --kind all --root raman \
  --stru STRU --qpoints qpoints.yaml \
  --born BEC.dat --dielectric BORN \
  --modes "4-12" --copy INPUT-scf --copy KPT
zstar spectra job --root raman --system shell --dry-run
zstar spectra stat --root raman
```

Inspect the inputs and dry-run driver, then execute the same serial chain
without `--dry-run`. Finish with:

```bash
zstar spectra post --root raman
```

Use `--dim 2` for sheet response and `--dim 0` for an isolated molecule.
In this Separate control, molecular IR and Raman share the same positive/negative
normal-mode tree.

The legacy mode-difference and native backend routes reject substantive Gamma-point imaginary modes below
-20 cm-1 by default. Relax or verify the structure first. Override with
`--allow-imaginary` only when analysis of stable branches of an unstable phase
is intentional.

## VASP and CP2K calculators

For VASP, start from an `IBRION=5/6` vibrational `vasprun.xml` and converged
input directory:

```bash
zstar spectra pre --calculator vasp --input-dir vasp_input \
  --modes-xml phonon/vasprun.xml --root vasp_spectra --dim 3
zstar spectra job --root vasp_spectra --system shell --dry-run
zstar spectra stat --root vasp_spectra
```

For CP2K molecular native intensities:

```bash
zstar spectra pre --calculator cp2k --input molecule.inp \
  --root cp2k_spectra --dim 0
zstar spectra job --root cp2k_spectra --system shell --dry-run
```

Repeat without `--dry-run` only after inspecting generated inputs. Finish with
`zstar spectra post --root WORK`. Native VASP/CP2K spectroscopy accepts
`--dim 0` or `--dim 3`, not `--dim 2`.
