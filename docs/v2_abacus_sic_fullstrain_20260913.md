# 3D SiC full central strain audit (ABACUS, 2026-09-13)

## Scope

This is the ABACUS cross-backend audit of the calculator-neutral v2 elastic
response path. It uses the existing v1 3C-SiC primitive cell (two atoms,
oblique primitive vectors, space group `F-43m`, Hall 512) and six engineering
Voigt strain components `(xx, yy, zz, yz, xz, xy)`. The central amplitude is
`±0.005`; fractional coordinates are fixed, so this is a clamped-ion response.
No polarization or piezoelectric value is inferred from this run.

The generated cells use `L' = L (I + eta)^T`; the collector uses the recovered
strain from those cells, not the nominal amplitude. The source v1 example was
copied read-only into:

```text
235:/home/zhuxd/abacus/agent-runs/20260913-zstar-v2-sic-elastic
```

## Input and resource provenance

- ABACUS 3.10.0-LTS, LCAO `genelpa`, PBE, 100 Ry, SG15/ONCV Si/C
  pseudopotentials and 7-au numerical orbitals copied from
  `examples/3D_Bulk/SiC/run`.
- Gamma-centered `13 x 13 x 13` KPT; `calculation scf`, `cal_force 1`,
  `cal_stress 1`, `scf_thr 1e-8`, Gaussian smearing `sigma=0.01`; identical
  settings and fixed ionic coordinates in all stages.
- Reference plus 12 strain stages completed on **cu25**, each with
  `mpirun -np 40`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`,
  `OPENBLAS_NUM_THREADS=1`. Every stage returned a convergence marker and a
  `TOTAL-STRESS (KBAR)` block.
- Summed wall time was 448.56 s, approximately 4.984 core-hours at 40 MPI
  ranks. Reference: 22.26 s; strain stages: 26.39--46.47 s.

## Collection and symmetry audit

`collect_abacus_strain_response` returned 13 observations (reference plus six
positive/negative pairs), with force, raw stress and energy present for every
stage. Input hashes and serialized strain vectors passed validation. Space-group
analysis was stable at `symprec=1e-3, 1e-4, 1e-5`, yielding `F-43m`/Hall 512
with 24 operations. The stress representation has a three-dimensional allowed
basis. Because the primitive Cartesian axes are rotated relative to conventional
cubic axes, the reconstructed matrix is not expected to have the textbook cubic
zero pattern.

## Stress-derived elastic response

ABACUS `TOTAL-STRESS` is treated as compression-positive and explicitly
converted by `fit_elastic_response` to the tension-positive thermodynamic
convention. After subtracting the reference stress, the symmetry-constrained
fit has rank `3/3`:

```text
max residual = 0.4889 kbar (0.0489 GPa)
RMS residual = 0.1294 kbar (0.0129 GPa)
```

The matrix is in GPa, in the input-cell Cartesian/engineering-Voigt convention:

```text
[[489.8088, 68.4934, 26.3579, 59.5886, 0,       0      ],
 [ 68.4934,489.8088, 26.3579,-59.5886, 0,       0      ],
 [ 26.3579,26.3579,531.9443, 0,       0,       0      ],
 [ 59.5886,-59.5886,0,      168.5222, 0,       0      ],
 [ 0,      0,      0,        0,      168.5222,59.5886],
 [ 0,      0,      0,        0,       59.5886,210.6577]]
```

The symmetrized eigenvalues are `126.39, 143.01, 252.79, 446.83, 505.59,
584.66 GPa`, all positive for this sampled clamped-ion response.

## Energy-curvature cross-check

The 13 final energies were fitted with the same three-parameter,
major-symmetric basis. The energy fit has rank `3/3`, with maximum residual
`6.14e-8 eV` and RMS residual `3.16e-8 eV`. Its largest entry differs from the
stress-derived matrix by `0.358 GPa` (about `0.07%`):

```text
[[489.6423, 68.8269, 26.7162, 59.5535, 0,       0      ],
 [ 68.8269,489.6423, 26.7162,-59.5535, 0,       0      ],
 [ 26.7162,26.7162,531.7530, 0,       0,       0      ],
 [ 59.5535,-59.5535,0,      168.2970, 0,       0      ],
 [ 0,      0,      0,        0,      168.2970,59.5535],
 [ 0,      0,      0,        0,       59.5535,210.4077]]
```

This close stress/energy agreement is an internal consistency result, not yet
a universal SiC elastic constant. A second amplitude, a matched high-precision
backend, and an independent DFPT oracle (ABINIT or QE) are still required
before Gate C can pass. The current input retains `symmetry 1` from the v1
source; a follow-up audit should repeat the fit with `symmetry 0` to exclude any
symmetry-restoration contribution in the strained cells.

## Reproducible run command

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
mpirun -np 40 /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus \
  > abacus.stdout 2> abacus.stderr
```

Compact logs, inputs, and provenance remain in the remote scratch; large
charge/matrix files are not copied into the repository.

## Symmetry-off follow-up (failure audit)

A matched second ensemble was prepared with `symmetry 0` to test whether the
automatic symmetry path affected the result. The reference and first two strain
stages completed with the same 40-rank launch. The next stage (`strain-002+`)
then remained in ABACUS initialization for more than ten minutes: MPI children
were active but no `E_Harris`, SCF-convergence, or stress block was written
after `DONE : INIT SCF`. The process group was stopped only after verifying its
working directory was exclusively this scratch; its partial log is retained
remotely as a failed run and is excluded from every fit. This is a runtime
compatibility/blocking observation for the `symmetry=0` + 40-MPI LCAO
combination, not evidence that the elastic tensor changed. A future symmetry-off
audit should first try a validated ABACUS decomposition (or a smaller smoke
rank count) before another full ensemble. As a control, the same
`strain-002+` inputs completed at `4 MPI x 1 OMP` in 32.12 s with identical
convergence, stress, and energy markers; the blocker is therefore parallel
decomposition/scaling rather than malformed v2 serialization.
