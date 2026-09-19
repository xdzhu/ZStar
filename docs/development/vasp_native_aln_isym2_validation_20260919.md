# AlN VASP native response with symmetry enabled

Date: 2026-09-19

## Scope and provenance

This is a controlled rerun of the retained wurtzite AlN PBE/PAW input with the
same POSCAR, KPOINTS, POTCAR, cutoff, and electronic convergence. The response
route changed from the historical `ISYM=0, NCORE=4` setting to the documented
native route:

```text
IBRION=6  ISIF=3  NFREE=2  POTIM=0.01 A
LEPSILON=.TRUE.  ISYM=2  NCORE=1
```

- HF Slurm job: `27723215`, node338, `32 MPI x 1 OMP`.
- State/exit: completed, exit code 0.
- Wall time: 682 s; allocation: 6.0622 rank-wall core-hours.
- Code: native branch `30f5d54a`; the same implementation is integrated into
  `codex/v2-native-integration` and extended at `f702793d`.
- Input and result hashes are retained in the job `completed.json`.
- VASP reported all `20/20` native finite-difference evaluations complete.

## Tensor result

All quantities are bulk, fixed-macroscopic-E, engineering-Voigt tensors. The
reported e tensor is the relaxed-ion total and d is derived from the same
native relaxed-ion e and C through `d = e C^-1`.

| quantity | ISYM=2 result | retained ISYM=0 result | absolute change |
|---|---:|---:|---:|
| e31, C/m2 | -0.581490 | -0.581620 | 0.000130 |
| e33, C/m2 | 1.461400 | 1.461500 | 0.000100 |
| e15, C/m2 | -0.309530 | -0.309520 | 0.000010 |
| d33, pm/V | 5.323688 | 5.324396 | 0.000708 |

The maximum full relaxed elastic-matrix difference is `0.03717 GPa`. The
symmetry-enabled result makes the 6mm-forbidden piezoelectric entries exactly
zero at output precision, rather than leaving the `1e-5--1e-4 C/m2` noise in
the unsymmetrized result.

The relative internal-strain translation residual improves from
`4.0346e-4` to `3.1106e-4`, below the existing `1e-3` quality gate. The relaxed
elastic tensor remains positive definite; its minimum eigenvalue is about
`111.814 GPa`. The e/d/C closure and elastic major symmetry checks pass.

## de Jong VASP/PBE comparison

Reference: de Jong et al., *Scientific Data* 2, 150053 (2015),
DOI `10.1038/sdata.2015.53`, AlN entry `mp-661`, VASP/PAW/PBE.

| component | ZStar VASP/PBE | database VASP/PBE | absolute relative difference |
|---|---:|---:|---:|
| e31, C/m2 | -0.581490 | -0.580060 | 0.247% |
| e33, C/m2 | 1.461400 | 1.461150 | 0.017% |
| e15, C/m2 | -0.309530 | -0.289305 | 6.991% |

The database does not directly report a matched d33. The retained ZStar d33
must therefore be presented as an internally closed same-run e/C result, not as
a direct database reproduction. The database used a higher cutoff and a
different k-point-density protocol, so this is a same-functional, same-backend,
same-phase comparison rather than identical-input replication.

## Decision

The symmetry-enabled native route is the accepted production candidate for
AlN. It reproduces the historical physical components, removes forbidden
component noise, passes the internal response gates, and agrees with the
same-functional external database. The historical ISYM=0 result remains only
as provenance and a regression baseline.
