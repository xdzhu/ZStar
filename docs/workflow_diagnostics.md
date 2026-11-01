# Workflow Logs and Failure Diagnosis

ABACUS + PYATB BEC and Raman runs print flushed progress messages and stream
external stdout and stderr to the terminal. Generated Shell, Slurm and PBS
drivers retain this output in the scheduler log and `.zstar/workflow.log`.
Regenerate an existing job script with `zstar bec job --system slurm` after
upgrading to obtain the unbuffered environment and failure-location hint.

```text
[time] [disp-002] [stage-start] [START] index=3; total=7; path=...
[time] [disp-002] [ABACUS SCF] [START] cwd=...; log=...; command=...
... ABACUS stdout and stderr ...
[time] [disp-002] [ABACUS SCF] [PASS] exit=0; elapsed=42.1s; log=...
[time] [disp-002] [INSULATION] [PASS] SCF-mesh gap=1.234000 eV; ...
[time] [disp-002] [PYATB polarization/dielectric] [START] ...
```

## Locate the Last Step

```bash
zstar bec stat
zstar bec stat --json
tail -n 80 .zstar/workflow.log
```

The status table includes `last_step`. Failed and last-recorded running stages
show their update time and exact log path. The JSON form supports batch
inspection without parsing a formatted table. A `running` record describes the
last saved state; check Slurm/PBS if a process was killed or reached its wall
time, since an externally killed process cannot always write a final failure.
Completed stages whose required files are missing are shown as `stale`; this
read-only status check does not rewrite the saved state. A rough remaining
serial wall-time estimate is shown only after at least two completed
displacement timings are available; it excludes scheduler queue time.

For a Slurm allocation, optionally query actual allocated CPUs and elapsed
time via `sacct`:

```bash
zstar bec stat --job-id 123456 --budget-core-hours 100
zstar bec stat --job-id 123456 --budget-core-hours 100 --json
```

The core-hour figure is allocated CPUs multiplied by elapsed wall time for
**one job**, not CPU utilization, site billing or a total over a multi-job
campaign. The budget comparison is an advisory monitor: it does not cancel the
job or enforce a hard limit. Set scheduler walltime and resource limits
separately. If `sacct` is unavailable or has not recorded the allocation,
ZStar reports that condition instead of inventing usage.

| File | Contents |
| --- | --- |
| `.zstar/logs/<stage>.log` | Commands, working directories, streamed solver output, exit codes and elapsed times |
| `.zstar/progress.log` | Compact workflow events, failures and resume hints |
| `.zstar/workflow.jsonl` | Structured workflow events |
| `.zstar/stages/*.json` | Saved component state, active step, error and log path |
| `.zstar/symmetry.json` | Actual symmetry tolerance, rotation orthogonality and atom-mapping checks |
| `<stage>/zstar_insulation.json` | Reference or displaced-structure insulating-state verdict |
| `.zstar/gamma_modes.json` | Gamma eigenvector classifications and harmonic-response eligibility |
| `.zstar/force_constants_diagnostics.json` | Raw and projected Hessian residuals and rigid/internal coupling |
| `.zstar/molecular_apt_diagnostic.json` | Unprojected molecular APT and charge-sum diagnostics |
| `.zstar/molecular_apt_validation.json` | Experimental molecular APT source and output fingerprints |

Repeat `zstar bec run` after correcting the cause. Completed outputs are
checked and reused; `SKIP` identifies these stages. For Unified Raman static
responses, each private `static/<stage>/run.log` contains PYATB output and a
`failed.json` records a caught error. An explicit redirection inside a custom
solver command, such as `abacus > other.log`, still sends that solver's output
to the chosen file rather than stdout.

## Interpret the Checks

**Insulating state.** The reference reports both the PYATB path/MP diagnostic
and the ABACUS SCF-mesh gap, the threshold, fractional occupations and occupied
band count. Each displacement checks its SCF mesh and consistency with the
reference occupied manifold. `PASS`, `FAIL`, `SKIP` and `DRY-RUN` are distinct;
a dry run does not certify an insulating state.
For an isolated molecule, the reference check instead verifies the explicit
Gamma SCF occupations and gap; a crystalline band path is not applicable.

**Symmetry.** Preparation, execution and collection report the selected
`--symmprec`, operation count, maximum Cartesian `|R^T R - I|` and atom-mapping
error. ZStar does not silently change the tolerance or orthogonalize a rejected
operation. A failure prints the measured error and suggests a stricter
`--symmprec` or refinement of the structure. A smaller tolerance may reduce
symmetry and require more displacements: prepare a new workspace rather than
mixing results from different displacement ensembles.

**Gamma stability.** `zstar bec post` saves the eigenvector audit alongside
the BEC and force constants. The classification uses mass-weighted overlap
with rigid translation (and rigid rotation for molecules), not the sign or
index of a frequency alone. The default 20 cm^-1 imaginary tolerance applies
to translational drift; it does not hide a small imaginary optical mode.
The heuristic rigid-overlap threshold is 0.99; mode projections within a
degenerate subspace depend on the chosen basis. For 1D systems the axial
rotation is reported as a candidate and is not an automatic exemption for a
negative mode. Mixed or non-translational negative modes and large negative
translation drift require inspection. The raw Hessian report also shows
reciprocity, translation residuals and rigid/internal coupling. A positive
internal block alone does not establish stability of the complete Hessian or
the phonons away from Gamma.

To examine existing results without submitting calculations:

```bash
zstar phonon inspect --dim 1 --qpoints qpoints.yaml \
  --force-constants FORCE_CONSTANTS.raw \
  --projected-force-constants FORCE_CONSTANTS --json gamma_review.json
zstar phonon compare --dim 1 --reference abacus/qpoints.yaml \
  --candidate vasp/qpoints.yaml --json mode_comparison.json
zstar phonon translation-check --calculator abacus --dim 1 \
  --reference reference_scf --translated translated_scf --json translation_check.json
```

`compare` requires the same cell, atom order, masses and geometry (apart from
a global translation), and matches nearly degenerate subspaces by their
eigenvector overlaps. Adjust the geometry and degeneracy tolerances only when
their meaning is justified. `translation-check` reads two existing completed
static ABACUS or VASP calculations; it does not generate or run either one.
It reports the printed-force difference and available input fingerprints, but
cannot infer whether a calculator already removed force drift. Neither tool
certifies an entire band structure or proves agreement of IR/Raman intensities.

**Molecular APT.** The experimental ABACUS Unified 0D path uses Gamma-point
closed-shell position matrices and checks the unprojected APT sum before
projection. It records source hashes and the size of the correction. A passed
sum-rule check is necessary, not independent evidence of accuracy or vacuum
convergence. Old 0D Berry-based `BEC.dat` files without a matching validation
record cannot be silently reused for Unified IR; retain the original SCFs and
recollect when compatible source matrices are available. Spin-polarized,
charged and non-Gamma cases are not supported by this position-matrix route.

## BEC Exists but the Dielectric Directory Does Not

`bec run` and `bec post` do not themselves calculate the total harmonic
dielectric response. After successful BEC collection, run:

```bash
zstar dielectric static
# or:
zstar dielectric freq
```

The electronic background in `BORN` is not the total static dielectric tensor.
If a dielectric command fails, its state is retained as
`.zstar/stages/dielectric-static.json` or `dielectric-freq.json`, even if no
output directory was created. `zstar bec stat` includes these attempted steps
when they were run in the same workspace. Inspect the reported error and the
Gamma audit:

```bash
zstar phonon inspect --qpoints qpoints.yaml --json gamma_review.json
```

A `BLOCKED` Gamma verdict explains why a stable harmonic dielectric response
was refused while the BEC data remain available. `--allow-imaginary` is an
explicit override for analysis of selected stable modes, not a remedy for an
unstable equilibrium structure or a validated equilibrium static permittivity.
