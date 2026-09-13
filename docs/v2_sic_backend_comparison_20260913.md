# 3D SiC backend comparison (ABACUS vs VASP, 2026-09-13)

This note compares two independently collected 3D SiC clamped-ion strain
ensembles using the same v2 strain vectors and the same `F-43m` symmetry basis.
It is a backend-consistency benchmark, not a converged material-constant
claim: ABACUS uses ONCV/SG15 LCAO orbitals while VASP uses PAW-PBE, so the
Hamiltonians and basis errors are not identical.

| quantity | ABACUS | VASP |
|---|---:|---:|
| strain stages | 13 | 13 |
| central amplitude | ±0.005 | ±0.001 |
| symmetry basis rank | 3 | 3 |
| stress fit rank | 3/3 | 3/3 |
| stress residual max | 0.4889 kbar | 0.0231 kbar |
| energy residual max | 6.14e-8 eV | 6.54e-8 eV |
| stress/energy C max difference | 0.358 GPa | 3.45 GPa |

The same ABACUS setup was also repeated at `±0.0025`.  In IEEE cubic axes,
the stress-derived `(C11,C12,C44)` changed from `(363.40,110.63,252.79)` to
`(363.24,110.57,252.73)` GPa (maximum change `0.16 GPa`, `0.054%`).  The
energy-derived values changed by at most `0.54 GPa` (`0.20%`).  This amplitude
check is the relevant finite-difference convergence evidence; it is stronger
than adding an unmatched third calculator.

Using the input-cell Cartesian/engineering-Voigt convention, the largest
absolute componentwise difference between the stress-derived matrices is
`32.73 GPa`, or `5.80%` of the largest VASP component. The difference is
consistent with the deliberately unmatched pseudopotential/basis settings and
finite amplitudes; it is not evidence of a v2 algebra error. Both matrices are
positive definite under the sampled convention.

## IEEE cubic-axis comparison

The primitive cell used in both runs is a rhombohedral representation of
3C-SiC.  For comparison with cubic literature values, each fitted fourth-rank
tensor was rotated to the IEEE cubic axes before extracting the three
independent constants.  The rotation is a post-processing coordinate change;
it does not alter the fitted response or impose cubic symmetry on a non-cubic
result.  The resulting off-cubic components are below `1e-7 GPa`.

| source | C11 (GPa) | C12 (GPa) | C44 (GPa) |
|---|---:|---:|---:|
| ABACUS (ONCV/SG15 LCAO, PBE) | 363.40 | 110.63 | 252.79 |
| VASP (PAW-PBE) | 383.49 | 126.74 | 264.27 |
| literature experimental anchor* | 390 | 142 | 256 |

Relative to the literature anchor, ABACUS differs by `-6.82%`, `-22.09%`,
`-1.25%` for `(C11,C12,C44)`, while VASP differs by `-1.67%`, `-10.75%`,
`+3.23%`.  The larger spread in `C12` is a useful warning that functional,
pseudopotential, equilibrium lattice constant, temperature and experimental
extraction method must be recorded; it is not a reason to declare either
backend universally accurate.  The commonly quoted `(390,142,256) GPa` values
are an ambient/room-temperature experimental literature anchor compiled from
single-crystal sound-velocity/Raman data, not a same-condition 0 K DFT oracle.

\* The anchor is cross-checked against the original cubic-SiC elastic studies
by Lambrecht *et al.* (PRB 44, 3685, DOI `10.1103/PhysRevB.44.3685`) and Wang
*et al.* (PRB 52, 3993, DOI `10.1103/PhysRevB.52.3993`), and the temperature
dependent single-crystal measurements of Li and Bradt (J. Mater. Sci. 22,
2557, DOI `10.1007/BF01082145`).  The exact provenance and temperature of an
anchor must be retained in a future benchmark manifest.

The ABACUS run used `scf_thr=1e-8`, 100 Ry, LCAO `genelpa`, ONCV Si/C and
13×13×13 KPT on cu25 with 40 MPI×1 OMP. The VASP run used PAW-PBE, `EDIFF=1e-8`,
fixed-cell `ISYM=0` stages on cu17/cu24/cu26. Raw logs and input hashes remain
in isolated scratch directories; only compact fit diagnostics are committed.

## Interpretation and next gate

Agreement of rank, tensor symmetry and positive-definiteness across two
collectors supports the representation and fit implementation. It does not
satisfy a same-Hamiltonian convergence study, because the two electronic-
structure settings are not matched.  It does, however, provide an independent
backend audit and a literature-anchored 3D benchmark without launching a third
DFT package.  The next numerical check is therefore a second strain amplitude
and matched settings on one backend; ABINIT/QE remain optional only if a later
material has no complete, definition-matched literature or database anchor.
