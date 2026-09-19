# VASP native ZnO exact-hexagonal validation (2026-09-19)

## Failure isolation

The original serialized wurtzite ZnO cell failed in VASP 6.3.2 with native
symmetry enabled, first at `ISYM=2` and then at the isolated `ISYM=1` control.
Both failures occurred in `GENERATE_KPOINTS_TRANS`; therefore the problem was
not specific to the `ISYM=2` mode and no further ISYM scan was performed.

The accepted control projected only the tiny serialization noise onto the
intended `P6_3mc` metric and Wyckoff orbit. The ordered four-site structure,
species order, polar domain and periodicity were preserved. With the fixed
project structure tolerance `symprec=1e-3 A` and angle tolerance 5 degrees,
both parent and child are `P6_3mc` number 186 with 12 symmetry operations.
The largest lattice correction is `6.59e-5 A`, the largest site correction is
`2.90e-5 A`, and the relative volume change is `-3.39e-7`.

The production response then used `IBRION=6`, `ISIF=3`, `LEPSILON=.TRUE.`,
`ISYM=2`, `NCORE=1`, VASP `SYMPREC=1e-4`, 32 MPI ranks and one OpenMP thread.
This VASP tolerance is separate from the structural `symprec=1e-3 A`.

- Slurm job: `27723364`, `node60`, exit code 0.
- Wall time: 952 s; allocated rank-wall cost: 8.462 core-hours.
- Remote archive: `/public/home/iai806/zstar-validation/pbe-native-piezo-20260918/zno-native-exacthex-f702793d-20260919`.
- Reference gap: 0.7195 eV.
- The final response OUTCAR contains neither `GENERATE_KPOINTS_TRANS` nor
  `LRF_COMMUTATOR internal error`.

## Tensor result

| component | exact-hexagonal ISYM=2 (C/m2) | de Jong VASP/PBE `mp-2133` (C/m2) | absolute relative difference |
| --- | ---: | ---: | ---: |
| `e31` | -0.536880 | -0.537510 | 0.12% |
| `e33` | 1.042050 | 1.036810 | 0.51% |
| `e15` | -0.399280 | -0.385000 | 3.71% |

The full matrix conversion gives `d31=-4.887327`, `d33=9.750071`, and
`d15=-10.827871 pm/V`. The relaxed elastic matrix is positive definite, with
minimum eigenvalue 36.8752 GPa and condition number 10.4614. The maximum
`e=d C` closure residual is `2.22e-16 C/m2`.

Relative to the earlier `ISYM=0` result on the unprojected serialized cell, the
full-tensor changes are small: maximum `|delta e|=0.00545 C/m2`, relative
Frobenius difference 0.802%; maximum `|delta C|=0.80338 GPa`, relative
Frobenius difference 0.567%; maximum `|delta d|=0.09029 pm/V`, relative
Frobenius difference 0.696%. In particular, `d33` changes from 9.714665 to
9.750071 pm/V. The projection fixes the native symmetry route without changing
the scientific conclusion.

## Diagnostics and conclusion

The displaced-atom internal-strain translation residual ratio is 0.002109 and
remains a warning; its reciprocity difference from the strained-cell block is
0.01454 eV/A. No raw internal-strain projection is used. Because total relaxed
`e`, relaxed `C`, elastic stability and `e=d C` closure pass independently,
the warning does not invalidate the algebraic `d=e C^-1` result.

ZnO therefore passes the native VASP e/C/d gate for the exact intended
wurtzite structure. The database comparison is matched in backend and PBE
functional, but it is not an identical-input reproduction because PAW files,
cutoff, k-density and optimized geometry are not all record-identical.
