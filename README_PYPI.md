# ZStar

<p align="center"><img src="https://raw.githubusercontent.com/xdzhu/ZStar/main/docs/logo.png" alt="ZStar logo" width="176"></p>

[![PyPI](https://img.shields.io/pypi/v/zstar)](https://pypi.org/project/zstar/)
[![Python](https://img.shields.io/pypi/pyversions/zstar)](https://pypi.org/project/zstar/)
[![License](https://img.shields.io/badge/license-GPL--3.0-green)](https://www.gnu.org/licenses/gpl-3.0.html)

ZStar is an automated toolkit for polarization, Born effective charges, dielectric
response, and infrared and Raman spectra calculations. Its principal workflow
uses ABACUS, PYATB, and Phonopy.

## Quick Start

Install ZStar and download the public examples:

```bash
pip install -U zstar
git clone https://github.com/xdzhu/ZStar.git
```

The `pip install` command alone is sufficient when the reproducible examples
are not needed; examples are distributed through GitHub rather than the wheel.

Follow the [calculator configuration guide](https://github.com/xdzhu/ZStar/blob/main/docs/cli_reference.md#calculator-configuration)
to set ABACUS, PYATB, and MPI/OMP, then confirm the two executables with
`zstar config check`.

The supplied two-atom 3C-SiC case is the shortest complete route to BEC,
Gamma-point phonons, IR, and Raman results:

```bash
cd zstar/examples/3D_Bulk/SiC
cp -r run work
cd work

zstar bec pre --stru STRU
zstar bec run --dry-run
zstar bec run
zstar bec stat
zstar bec post

zstar spectra pre --root spectra --response .
zstar spectra run --root spectra
zstar spectra stat --root spectra
zstar spectra post --root spectra
```

The BEC stages construct BEC and Gamma force constants from the common
displacements. The spectroscopy stages obtain IR from the BEC and modes and
run the additional PYATB responses required for Raman. Repeated runs resume
completed stages. Expect opposite Si/C BEC values near 2.70 e and a triply
degenerate optical mode near 773 cm^-1; matching spectra are archived in the
GitHub case.

For agent-assisted use, run `zstar skill install`, open a new agent session,
and use:

```text
Use $run-zstar-workflows to reproduce the 3C-SiC Quick Start in
examples/3D_Bulk/SiC. Run the preflight first, then execute the zstar bec and
zstar spectra stages individually if ABACUS and PYATB are available. Explain
each stage and report the BEC table, optical-mode frequencies, and spectrum paths.
```

## Highlights

- Unified symmetry-adapted BEC/APT, Gamma force constants and static nonresonant
  Raman derivatives from the same calculations. Retained electronic matrices
  supply additional PYATB responses without additional SCFs.
- Molecular atomic polar tensors (APT) from ABACUS + PYATB or CP2K dipoles.
- Symmetry reduction, full-cell reconstruction, and acoustic-sum-rule correction.
- Serial and resumable `0.no-move -> displacements` execution.
- Reuse of the converged reference charge density.
- A one-time insulating-state gate using a normal band path by default.
- Shell, Slurm, and Torque/PBS drivers with Specified, Current, or Global headers.
- Legacy and direct-static-response PYATB compatibility.
- Hybrid 1D BECs: transverse charge-density dipoles plus longitudinal Berry polarization.
- Hybrid 2D BECs: Berry-phase in-plane response plus cube-integrated out-of-plane dipole.
- IR, Raman, and static/frequency-dependent dielectric response.
- A packaged `run-zstar-workflows` agent skill with JSON preflight.
- Slab electrostatic-potential maps, directional profiles, and local two-sided
  vacuum diagnostics.

## Examples

![IR and Raman spectra for bulk, slab, wire, and molecular examples](https://raw.githubusercontent.com/xdzhu/ZStar/main/docs/paper_figures/spectroscopy_across_dimensions.png)

The four-dimensional examples compare calculated spectra with literature
frequencies or published curves. Relative Raman intensities for Sb2S3 remain
different from the reference; the examples document this limitation explicitly.
Full inputs, results, and bilingual tutorials are in the
[GitHub example library](https://github.com/xdzhu/ZStar/tree/main/examples).

Representative archived results include `Z*(Ti) = 7.440 e` for cubic BaTiO3,
`Z*(B,parallel) = 2.702 e` for monolayer hBN,
`(Zrr,Ztt,Zzz)_B = (0.397,1.256,2.745) e` for BN(9,0), and
`q_GAPT(O) = -0.481 e` for H2O. Periodic values are BEC components; the molecular
value is the APT invariant `Tr(A)/3`.

## Installation

Install or upgrade the latest stable release:

```bash
pip install -U zstar
zstar --version
```

Python 3.9 or newer is required. Phonopy is installed as a Python dependency;
ABACUS and PYATB must be available for workflows that use them. The core
installation uses `spglib` for symmetry and does not require `pymatgen`.

For VASP `vasprun.xml`, `CHGCAR/POTCAR`, or legacy smodes/Wyckoff adapters, install the optional extra:

```bash
pip install -U "zstar[vasp]"
```

Configure external executables in `.zstar/config.toml` and verify them:

```bash
zstar config init
zstar config set executables.abacus /opt/abacus/bin/abacus
zstar config set execution.mpi 1
zstar config set execution.omp 20
zstar config check
zstar backend list --check
```

For ABACUS cases whose pseudopotentials and numerical orbitals are stored in
shared libraries, provide their directories during preparation:

```bash
zstar bec pre --stru STRU \
  --pp /path/to/PSEUDO \
  --orb /path/to/ORBITAL
```

Frequently used directories can be configured globally with
`abacus.pseudo_dir` and `abacus.orbital_dir`.
ZStar preserves the source `STRU`, writes a resolved copy to
`.zstar/STRU.resolved`, records selected files and checksums in
`.zstar/assets.json`, and stops with an actionable error when matching files
are missing or ambiguous.

## agent skill

Install the bundled agent skill and open a new agent session:

```bash
zstar skill install
zstar skill preflight --root . --lane bec --dim bulk
```

Invoke it explicitly as `$run-zstar-workflows`. The skill preserves ZStar's
dimensional conventions, resumable state, permission boundaries, and
artifact-based completion checks. Use `zstar skill install --force` after
upgrading the package.

## Serial BEC Workflow

```bash
# Generate 0.no-move and displacement folders
zstar bec pre --stru STRU

# Run one resumable serial chain
zstar bec run

# Inspect progress
zstar bec stat --root .

# Construct symmetry-consistent BEC tensors
zstar bec post --root .
```

For a `z`-periodic 1D wire, use `--dim 1` throughout. ZStar obtains the two
transverse polarization columns from high-precision charge-density cubes and
the longitudinal column from PYATB Berry polarization:

```bash
zstar bec pre --stru STRU --dim 1
zstar bec run --root .
zstar bec post --root .
```

The source snapshot includes complete BN(9,0) nanotube and Sb2S3-chain examples
with clean `run/` inputs, `results/` archives and resumable `run.sh` scripts.
Their BECs and Gamma force constants come from the same symmetry-adapted SCFs.
Additional normal-mode polarizability derivatives provide Raman spectra.
The Sb2S3 comparison retains original public reference curves and the observed
Raman-intensity differences; its reference is a computational dataset, not a
verified associated journal article. See the
[one-dimensional guide](https://github.com/xdzhu/ZStar/blob/main/docs/one_dimensional_workflow.md).

For an isolated molecule, `--dim 0` generates and collects atomic polar
tensors in units of `e`. The name is deliberate: an APT is the molecular
analogue of a periodic-crystal BEC.

```bash
zstar bec pre --stru STRU --dim 0
zstar bec run --root .
zstar bec post --root .
```

For a 2D slab, use `--dim 2` in generation, execution, and post-processing.
Full `x/y/z` displacements are required because the out-of-plane polarization
column is obtained from the real-space slab dipole. The slab normal must
currently align with Cartesian `z`.

Run a complete two-dimensional response calculation through the canonical BEC
lifecycle:

```bash
zstar bec pre --stru STRU --dim 2
zstar bec run
zstar bec post
```

The low-level `zstar polar2d` command is retained only for auditing an existing
reference/displaced cube pair.

The default insulating gate runs only for `0.no-move` and uses:

```bash
pyatb_input --band
```

The path gate is a lightweight fail-fast check and cannot exclude an off-path metallic pocket. Use `--gap-mode mp` when a stricter MP-grid check is desired.

Generate one environment-specific driver:

```bash
zstar bec job --system shell
zstar bec job --system slurm --queue compute --tasks 28
zstar bec job --system torque --queue batch --tasks 28
```

Shell/Torque default to `mpirun -np N`; Slurm defaults to
`srun --ntasks=N`. Use `--dry-run` for an environment and state-output smoke
test without launching an electronic-structure calculation.

## Phonon, IR, and Dielectric Response

```bash
# INPUT must contain: cal_force 1
zstar phonon pre --stru STRU --dim "2 2 2"
zstar phonon run --root .
zstar phonon stat --root .
zstar phonon post --root .
zstar phonon irrep --root . --file irreps.yaml --mode db

# Copy BORN and Z-BORN-symm.out from the BEC workflow.
zstar dielectric static --qpoints qpoints.yaml --born Z-BORN-symm.out --dielectric BORN
zstar dielectric freq --qpoints qpoints.yaml --born Z-BORN-symm.out --dielectric BORN
zstar spectra pre --calculator abacus --kind ir --root ir_spectrum \
  --qpoints qpoints.yaml --born Z-BORN-symm.out --dielectric BORN
zstar spectra post --root ir_spectrum
```

`zstar dielectric freq` writes the zero-frequency tensor, real and imaginary response
tables, and PNG/PDF/SVG plots by default. Use `--no-plot` for data-only
post-processing.

For `--dim 1`, dielectric/IR response is reported as an `Angstrom^2` line
polarizability; for `--dim 2`, it is a sheet polarizability unless an effective
`--thickness` is supplied. Gamma-point 1D IR/Raman is supported, while finite-q
polar phonons still require a genuine 1D Coulomb cutoff and must not use bulk NAC.

## Raman Workflow

The ABACUS + PYATB Unified route now uses the same displacement SCFs for
BEC/APT, Gamma phonons, IR and static nonresonant Raman. In a prepared BEC
directory, use `zstar spectra pre`, `zstar spectra run`, and `zstar spectra post`.
Raman adds dielectric postprocessing of retained matrices, not additional SCFs.
`--response PATH` selects another completed ensemble; `--method mode` keeps
explicit normal-mode finite differences for comparison. Other calculators
retain their documented native response workflows.

```bash
zstar spectra pre --calculator abacus --kind raman --root raman \
  --stru STRU --qpoints qpoints.yaml \
  --modes "4-12" --copy INPUT-scf --copy KPT

zstar spectra run --root raman --reference 0.no-move
zstar spectra post --root raman
```

The Raman runner reuses the reference insulating gate and charge density, records every `plus`/`minus` stage, collects central-difference dielectric derivatives, and writes a Placzek spectrum.

### Isolated molecules (`--dim 0`)

The same mode-pair workflow can calculate normalized molecular IR and Raman
spectra in one resumable run:

```bash
zstar spectra pre --calculator abacus --kind all --root raman --dim 0 \
  --stru STRU --qpoints qpoints.yaml --modes "4-12" \
  --copy INPUT-scf --copy KPT
zstar spectra run --root raman --reference 0.no-move \
  --spectrum-outdir raman_spectrum --ir-outdir ir_spectrum
zstar spectra post --root raman
```

ZStar converts Berry polarization through `dmu/dQ = V*dP/dQ` and the
dilute-supercell dielectric response through
`dalpha/dQ = V/(4*pi)*d(epsilon_r)/dQ`. Existing prepared mode-pair results can
be checked with `zstar spectra stat` and reprocessed with `zstar spectra post`.

## Electrostatic Potential Diagnostics

```bash
zstar pot --cube OUT.ABACUS/ElecStaticPot.cube \
  --axes z --plane xy --plane-average \
  --direction a+b --mirror-test \
  --vacuum-sides --vacuum-exclude 6.0 --vacuum-window 0.75 \
  --polar-arrow auto --outdir potential
```

For a dipole-corrected polar slab, the two vacuum levels are averaged in local
windows next to the surface exclusion boundaries. This avoids contaminating a
surface plateau with the potential-reset segment. Directional profiles such as
`--direction a+b` and `--direction a-b` are inspection diagnostics rather than
polarization magnitudes.

## Main Outputs

| File | Meaning |
| --- | --- |
| `BEC.rep.raw.dat` | Raw explicitly calculated representative tensors. |
| `BEC.raw.dat` / `BEC.dat` | Full-cell raw / symmetry-reconstructed and neutral BEC tensors. |
| `BORN` | Electronic dielectric tensor plus Phonopy-order BECs. |
| `response.json` | Calculator-neutral responses, dimensionality, field conventions and provenance. |
| `response_fit.json` | Unified raw/projected BECs and joint reconstruction diagnostics. |
| `FORCE_CONSTANTS` / `qpoints.yaml` | Gamma force constants and the zone-center eigensystem. |
| `ir_spectrum/` | Mode charges, IR spectrum, static tensor, and complex line/sheet/bulk response. |
| `static_response.json` | Zero-frequency tensor with dimensional convention and electronic-background provenance. |
| `dielectric_response.pdf` / `.svg` | Editable real/imaginary frequency-response plots. |
| `raman_spectrum/` | Raman activities, tensors, and broadened spectrum. |

## License

ZStar is distributed under GPL-3.0.
