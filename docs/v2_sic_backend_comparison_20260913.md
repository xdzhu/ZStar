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

Using the input-cell Cartesian/engineering-Voigt convention, the largest
absolute componentwise difference between the stress-derived matrices is
`32.73 GPa`, or `5.80%` of the largest VASP component. The difference is
consistent with the deliberately unmatched pseudopotential/basis settings and
finite amplitudes; it is not evidence of a v2 algebra error. Both matrices are
positive definite under the sampled convention.

The ABACUS run used `scf_thr=1e-8`, 100 Ry, LCAO `genelpa`, ONCV Si/C and
13×13×13 KPT on cu25 with 40 MPI×1 OMP. The VASP run used PAW-PBE, `EDIFF=1e-8`,
fixed-cell `ISYM=0` stages on cu17/cu24/cu26. Raw logs and input hashes remain
in isolated scratch directories; only compact fit diagnostics are committed.

## Interpretation and next gate

Agreement of rank, tensor symmetry and positive-definiteness across two
collectors supports the representation and fit implementation. It does not
satisfy the independent high-precision oracle requirement because the two
electronic-structure settings are not matched and no DFPT result is available
on the current nodes. Before a formal C benchmark, repeat one backend with a
second amplitude and match cell orientation, pseudopotential family, k-point
density and convergence; then compare against ABINIT `anaddb` or QE/`thermo_pw`
when an executable and validated input are available.
