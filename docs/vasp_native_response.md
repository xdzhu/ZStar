# VASP native response workflow

ZStar uses VASP's native solvers rather than imposing the ABACUS + PYATB
finite-displacement reconstruction on VASP calculations.

## Preparation and reuse

The native response extensions have been validated on 3C-SiC and wurtzite AlN.
Install the source checkout containing these extensions with
`pip install '.[vasp]'`; older published wheels may not expose the new switches. Prepare
`INCAR`, `POSCAR`, `KPOINTS`, and a licensed `POTCAR` in `input/`.

```bash
zstar bec pre --calculator vasp --input-dir input --root response --phonons
zstar bec job --root response --system slurm --header header.sh --tasks 64 \
  --vasp-command 'mpirun -np 64 vasp_std'
sbatch response/run_vasp_bec.slurm
zstar bec post --root response
```

The reference SCF is checked for an insulating gap before the native response
stage. For LDA/GGA, `--phonons` selects `LEPSILON = .TRUE.` and `IBRION = 8`.
Reference, native response and Raman inputs use `NCORE = 4` and remove `NPAR`;
the two parallelization tags must not be specified together. On hf, use
`mpirun -np 64 vasp_std` inside the Slurm allocation.
`ISYM = 0` keeps the electronic k-point set fixed across perturbations, avoiding
the VASP 6.3.2 k-point redistribution restriction with `NCORE > 1`. This removes
electronic point-group k-point reduction; it is a compatibility choice, not a
claim that all native phonon perturbations retain symmetry reduction.
The output includes `BORN`, `qpoints.yaml`, `FORCE_CONSTANTS`, `phonopy.yaml`,
`irreps.yaml`, the existing BEC
response record, and `vasp_native_response.json`. The latter separates electronic
and phonon dielectric tensors and clamped/ionic/total piezoelectric tensors.
The primitive-cell force constants determine Gamma modes, not a full phonon
dispersion. A dispersion requires a sufficiently large supercell.

The bulk IR and frequency-dependent phonon dielectric response use these
same tensors and modes, without additional displaced SCF jobs:

```bash
zstar dielectric freq --stru response/response/POSCAR \
  --qpoints response/qpoints.yaml --born response/BORN --outdir dielectric
```

Raman requires additional dielectric derivatives. The existing mixed route
uses positive and negative mode displacements with native dielectric response.
A completed native reference can be reused without another reference SCF:

```bash
zstar spectra pre --calculator vasp --response response --root raman
zstar spectra job --root raman --system slurm --header header.sh --tasks 64 \
  --command 'mpirun -np 64 vasp_std'
sbatch raman/run_zstar_spectra.slurm
zstar spectra post --root raman
```

Use `--kind ir` with `--response` for IR-only preparation; no Raman displacement
stages are generated and a completed reference needs no additional VASP calls.
All cache reuse uses ordinary file copies, not symlinks.
Reused mode sources are stored relative to the new reference directory, so
collection remains independent of the original response workspace.
Native post-processing exports frequency-ascending mode IDs. The matching
`spectra_results.json` retains source IDs as `native_mode_numbers`; reuse it
with the exported `qpoints.yaml`. A Raman subset `.npy` has no reliable mode-ID
mapping. Regenerate older native JSON with `zstar spectra post` if the index
convention is missing. This only repeats post-processing, not VASP calculations.

## Solver selection

### Piezoelectric e versus d

For relaxed-ion piezoelectric stress coefficients `e`, request the native ionic
response, not an external strain/polarization-difference ensemble:

```bash
zstar piezo pre --calculator vasp --input-dir input --root piezo
zstar piezo run --root piezo
zstar piezo post --root piezo
```

The dedicated family also computes Gamma force constants, so a separate
`--phonons` is unnecessary. For LDA/GGA this is the same native `IBRION=8` response used by
`--phonons`; both routes collect clamped, ionic and total `e`. The internal-strain
coupling is not itself a piezoelectric tensor: native VASP combines the ionic
relaxation response with BEC. ZStar reads the native contributions rather than
reconstructing them from another external displacement ensemble. The lower-level
`zstar bec ... --piezo [--elastic]` switches remain available for compatibility.

| Requested result | Preparation option | Native solver / reuse |
| --- | --- | --- |
| BEC and electronic dielectric tensor | no extra option | `LEPSILON` DFPT for LDA/GGA |
| Relaxed-ion piezoelectric `e` | `--piezo` | electric DFPT plus native Gamma ionic response |
| Gamma phonons, phonon dielectric and IR | `--phonons` | same native ionic response; IR is post-processing |
| Complete elastic `C` and derived `d` | `--elastic` | native ionic/strain finite differences; `d = e C^-1` |
| Raman | subsequent `zstar spectra pre --response ...` | additional mode-displaced native dielectric calculations |

For `d`, use `--elastic` instead of `--piezo`. It includes the required ionic
response; neither `--piezo` nor `--phonons` alone supplies the complete elastic
matrix. VASP performs these strain finite differences internally; ZStar does
not generate a second external strain ensemble. The SiC/AlN examples compare
both native routes for validation, not because routine `e` calculations require
both. Raman is not obtained for free from the electric/phonon DFPT run.

The [LEPSILON documentation](https://vasp.at/wiki/LEPSILON) specifies the
clamped-ion electric response; the [phonon DFPT documentation](https://vasp.at/wiki/Phonons_from_density-functional-perturbation_theory)
describes internal strain and the missing clamped elastic strain perturbation.
The [native finite-difference documentation](https://vasp.at/wiki/Phonons_from_finite_differences)
describes the complete elastic route.

`--method auto` is the default: native electric-field DFPT for LDA/GGA,
native finite electric fields for hybrid or meta-GGA functionals. An explicit
incompatible `--method dfpt` fails with guidance rather than silently changing
the functional. For the finite-field route, native ionic finite differences
replace phonon DFPT. These choices require end-to-end validation for each
functional; selecting a route is not a claim of universal functional support.

`--elastic` is restricted to bulk and selects `IBRION = 6, ISIF = 3` because
VASP does not implement the clamped elastic strain perturbation in DFPT.
Electric response remains native DFPT for LDA/GGA. Elastic units are converted
from kbar to GPa, and both piezoelectric columns and elastic rows/columns are
reordered to `(xx, yy, zz, yz, xz, xy)` with engineering shear strains.
The derived `d` is emitted only for a mechanically stable, sufficiently
symmetric elastic matrix and a reliable internal-strain translation residual.
Missing internal-strain data are not treated as a passed check. Electronic and
ionic piezoelectric contributions must both be present; an explicitly printed
total must agree with their sum to within 1e-4 C/m2. These are consistency gates,
not substitutes for cutoff, k-mesh or response convergence tests.
The collector preserves raw tensors and warns about failed force balance;
it does not silently project native electromechanical contributions.
A native piezoelectric tensor is not subjected to
the geometric correction for an improper finite-polarization derivative.
`vasp_native_response.json` and the common response record retain solver
provenance, distinguishing native DFT responses from the algebraic `d`
conversion and IR post-processing. A failed check keeps the raw native tensors
and its reason; it does not silently switch solvers or launch another job.

Low-dimensional native dielectric and piezoelectric outputs remain explicitly
labelled as periodic-supercell responses; they are not intrinsic bulk constants.
The existing 2D spectroscopy guard is retained until its boundary conditions
and conversion are validated. `LOPTICS` electronic optical spectra are a
separate approximation and must not be conflated with local-field-inclusive
DFPT electronic dielectric data.

## Slurm header example

```bash
#!/usr/bin/env bash
#SBATCH --partition=hfacnormal01
#SBATCH --nodes=1
#SBATCH --ntasks=64
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
source /public/home/iai806/Software/VASP/env.sh 6.3.2
```

No `--exclusive` or fixed node is requested. Header precedence is Specified,
Current (`./header.sh`), then Global (`~/.zstar/header.sh`).
Licensed VASP pseudopotentials are not distributed in Git: assemble `POTCAR`
locally in POSCAR species order from `$VASP_PSEUDO_ROOT/PBE/<species>/POTCAR`.

## Tested routes

The [3C-SiC example](../examples/VASP_Native_Response/3C_SiC/README.md)
contains computed native BEC, dielectric, Gamma-mode and elastic records,
plus IR and mixed-route Raman spectra from VASP 6.3.2 / PBE PAW.
An IR-cache execution with the launcher deliberately set to `false` completes
without a VASP call. Optical Raman triplet activities agree within 0.02%,
with depolarization ratios near 0.75. These are internal consistency checks,
not a demonstration of arbitrary-functional convergence.

## Polar bulk example: AlN

The [wurtzite AlN case](../examples/VASP_Native_Response/AlN/README.md)
starts from structural relaxation and compares native DFPT with native strain
finite differences before computing IR and mode-derivative Raman spectra.
Its coordinate convention and verification script cover the independent
`e31`, `e33` and `e15` components, dielectric closure and `e = d C`.
The retained PBE PAW response and spectral selection-rule checks pass:
e31=-0.582 and e33=1.462 C/m2, with d33=5.324 pm/V from the quality-checked
native strain route. Native DFPT internal-strain warnings remain visible.
See the [acceptance record](development/vasp_native_AlN_validation_20260918.md)
for provenance, convergence settings and limitations.

## Primary references

- [VASP LEPSILON](https://vasp.at/wiki/LEPSILON)
- [VASP LCALCEPS](https://vasp.at/wiki/LCALCEPS)
- [VASP DFPT phonons](https://vasp.at/wiki/Phonons_from_density-functional-perturbation_theory)
- [VASP finite-difference phonons and elastic response](https://vasp.at/wiki/Phonons_from_finite_differences)
