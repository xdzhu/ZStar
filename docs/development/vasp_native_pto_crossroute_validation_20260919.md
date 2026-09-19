# PTO PBE native versus central-strain validation (2026-09-19)

## Question and controls

This audit compares two VASP 6.3.2 routes on the same five-atom tetragonal
PbTiO3 parent POSCAR and PBE/PAW numerical settings.

1. Native response: `IBRION=6`, `ISIF=3`, `LEPSILON=.TRUE.`, `POTIM=0.01`,
   `ISYM=2`, `NCORE=1`.
2. Independent finite strain: full 13-structure central engineering strain
   `+/-0.5%`, relaxed ions, Berry-phase `LCALCPOL`, `ISYM=1`, `NCORE=1`.

The independent route uses an exact P4mm Reynolds projection of the same parent
structure. The maximum lattice and site changes are `4.86e-5 A` and
`3.44e-5 A`, so this is a serialization/symmetry control, not a new equilibrium
structure. Both routes use `ENCUT=1000 eV`, `EDIFF=1e-8`, and the relaxation
force gate `1e-4 eV/A`. Structural symmetry is analyzed only at the fixed
spglib `symprec=1e-3 A`.

## Completion and resource accounting

| route | job | node | wall time | MPI x OMP | allocated rank-wall core-hours |
| --- | --- | --- | ---: | ---: | ---: |
| native | 27723306 | node47 | 00:49:40 | 32 x 1 | 26.489 |
| independent 0.5% | 27723065 | node43 | 01:53:27 | 32 x 1 | 60.507 |

Both jobs exited with code 0. The native reference gap is 1.9272 eV. The
independent route has 13/13 completed observations, minimum gap 1.9192 eV and
maximum final force `9.721e-5 eV/A`.

The earlier independent job 27722735 stopped at one failed force/gap intake
gate. Its `failure.json` is retained. Job 27723065 is a single audited
continuation of `strain-002-plus`; it did not change the thresholds. The result
records both the old failure and the completed continuation instead of deleting
the failure marker.

Pymatgen reads the serialized off-diagonal VASP stresses with a maximum
antisymmetry of `2.0e-7 kbar`, only `1.25e-7` relative to the affected stress.
The postprocessor applies the physical Cauchy-stress operation
`(sigma+sigma.T)/2` only after absolute and relative `1e-6` gates pass, and
records every per-stage correction.

## Results

| route | e31 | e33 | e15 | d31 | d33 | d15 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| VASP native | 1.670070 | 2.439520 | 2.795970 | -5.234363 | 63.994672 | 87.429280 |
| VASP central 0.5% | 1.573594 | 2.058918 | 2.868509 | -3.412592 | 52.203773 | 89.581709 |
| ABACUS/PYATB central 0.5% | 1.710979 | 2.114819 | 2.895233 | -1.465454 | 49.084674 | 97.529358 |

`e` is C/m2 and `d` is pm/V (=pC/N). Every d value is the full matrix solve
`d=e(C^E)^-1`, not `e33/C33`.

The native and independent VASP elastic matrices agree closely: maximum
component difference 0.3371 GPa and Frobenius relative difference 0.300%.
Nevertheless their full e tensors differ by 7.999% and full d tensors by
8.838%; `d33` differs by 18.42% relative to native. The independent VASP route
is closer to the ABACUS/PYATB result for e (4.049% full-tensor difference) than
the native route (6.875%), while ABACUS versus independent VASP d differs by
8.757% in full-tensor norm and `d33` by -5.98% relative to the independent
VASP value.

Against the de Jong VASP/PBE `mp-20459` piezoelectric archive, the native
`e31/e33/e15` absolute relative differences are 1.61%/12.63%/14.23%; the
independent 0.5% values differ by 4.26%/26.26%/12.01%. The database has no
matching elastic entry for this material ID, so no database d33 is invented.

## Internal checks

The native route has minimum elastic eigenvalue 26.5045 GPa, condition number
10.3808 and `e=dC` closure `4.44e-16 C/m2`. Its internal-strain translation
ratio is `7.33e-4`, below the `1e-3` diagnostic threshold.

The independent route has minimum elastic eigenvalue 26.4204 GPa, condition
number 10.4016 and closure `8.88e-16 C/m2`. Proper-e and C fit relative
residuals are 0.477% and 2.138%; P4mm symmetry projection relative residuals
are 0.0187% and 0.0125%. The raw tensors, not projected tensors, are reported.

## Qualification decision

Both PTO routes are internally complete and mathematically consistent, but the
cross-route e/d difference is too large to call PTO native e/C/d quantitatively
validated. The native result is retained as a completed conditional result,
not discarded and not silently replaced by the central-strain result.

The next bounded scientific discriminator is an independent central `+/-1%`
PTO calculation on the same exact P4mm structure. It can separate finite-strain
amplitude effects from the native internal-strain contraction. Until that audit
is complete, production recommendations remain central `+/-0.5%`; no parameter
scan or automatic workflow retry is introduced.
