# VASP native GaN symmetry-enabled validation (2026-09-19)

## Scope and provenance

This is a three-dimensional wurtzite GaN PBE/PAW native-response validation.
It tests the production symmetry policy rather than changing the physical
settings: `IBRION=6`, `ISIF=3`, `LEPSILON=.TRUE.`, `ISYM=2`, `NCORE=1`,
32 MPI ranks and one OpenMP thread. `SYMPREC` was absent, so VASP's default was
retained; the spglib/Phonopy structure tolerance remained the separate fixed
`symprec=1e-3 A` policy.

- Slurm job: `27723293`, `node72`, completed with exit code 0.
- Wall time: 1109 s; allocated rank-wall cost: 9.858 core-hours.
- Remote archive: `/public/home/iai806/zstar-validation/pbe-native-piezo-20260918/gan-native-f702793d-20260919`.
- Reference gap: 1.71 eV.
- Native finite-difference sequence: 20/20 completed.

## Tensor result

The relaxed-ion proper piezoelectric stress coefficients are

| component | ZStar/VASP PBE (C/m2) | de Jong VASP/PBE `mp-804` (C/m2) | absolute relative difference |
| --- | ---: | ---: | ---: |
| `e31` | -0.264450 | -0.289820 | 8.75% |
| `e33` | 0.422860 | 0.464510 | 8.97% |
| `e15` | -0.146180 | -0.139315 | 4.93% |

The same run gives `d31=-0.895809`, `d33=1.583054`, and
`d15=-1.637415 pm/V` from the complete matrix solve `d=e C^-1`.
The relaxed elastic matrix is positive definite (minimum eigenvalue
89.2749 GPa), has condition number 5.7174, and reconstructs `e=d C` with a
maximum closure residual of `5.6e-17 C/m2`.

Relative to the earlier `ISYM=0` control, the independent `e` changes are only
`+0.00304`, `+0.00291`, and `+0.00057 C/m2` for `e31`, `e33`, and `e15`.
The symmetry-enabled result removes forbidden-component noise without changing
the physical conclusion.

## Internal-strain diagnostic versus derived d

The displaced-atom internal-strain block has a translation residual ratio of
0.003304, while the independently printed strained-cell internal-strain sum is
zero. This warning remains in the result and the raw tensor is not projected.
It is not, however, a mathematical prerequisite for converting VASP's printed
total relaxed-ion `e` and relaxed-ion `C` to `d`. ZStar therefore now gates the
derived `d` on elastic symmetry/stability and piezoelectric contribution
closure, records the condition number and `e=d C` closure, and retains the
internal-strain residual as an independent warning.

## Conclusion

GaN passes the native VASP e/C/d response gate under symmetry-enabled
production settings. The comparison is a matched-backend and matched-functional
PBE database comparison, not an identical-input reproduction: PAW datasets,
cutoff, k-density and relaxed geometry are not all record-identical.
