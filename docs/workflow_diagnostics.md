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

| File | Contents |
| --- | --- |
| `.zstar/logs/<stage>.log` | Commands, working directories, streamed solver output, exit codes and elapsed times |
| `.zstar/progress.log` | Compact workflow events, failures and resume hints |
| `.zstar/workflow.jsonl` | Structured workflow events |
| `.zstar/stages/*.json` | Saved component state, active step, error and log path |
| `.zstar/symmetry.json` | Actual symmetry tolerance, rotation orthogonality and atom-mapping checks |
| `<stage>/zstar_insulation.json` | Reference or displaced-structure insulating-state verdict |
| `.zstar/gamma_modes.json` | Gamma eigenvector classifications and harmonic-response eligibility |

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
Mixed or non-translational negative modes are flagged, and large negative
translation drift also requires inspection.

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
