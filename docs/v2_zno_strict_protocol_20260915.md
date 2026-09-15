# ZnO strict finite-strain protocol audit (2026-09-15)

This record promotes the direct electromechanical result of the wurtzite ZnO
v2 validation case.  It does not promote the still-separate BEC--internal-
strain reconstruction as an independently validated material observable.

## Protocol

The crystallographic reference is `P6_3mc` (`6mm`) under the project-wide
`symprec = 1e-3`.  ABACUS uses `symmetry = 1` only for the reference geometry.
Every finite-strain geometry uses `symmetry = 0` and still serializes
`symmetry_prec = 0.001`.  This avoids a backend symmetry projector treating a
physical strain of order `1e-3` as an unstrained reference geometry.

The ensemble has one reference and central `+/-` points for all six
engineering-Voigt strains.  Each geometry has one ABACUS calculation and one
PYATB calculation yielding all three Cartesian Berry-phase polarizations.
The strained cells used `scf_thr=1e-10`, `force_thr=1e-6 eV/Angstrom`, and
`relax_nmax=100`; all twelve have the ABACUS ionic-convergence marker and
final maximum force no greater than `9.779e-7 eV/Angstrom`.

## Accepted direct response

Projection of the measured proper tensor onto the exact `P6_3mc` allowed
subspace gives, in `C/m^2` and engineering-Voigt order
`(xx, yy, zz, 2yz, 2xz, 2xy)`,

```text
e = [[ 0,         0,         0,         0, -0.477138, 0],
     [ 0,         0,         0, -0.477138,  0,         0],
     [-0.615041, -0.615041,  1.267452,     0,  0,         0]] .
```

The independently measured pairs before projection are already close:
`|e31-e32| = 8.28e-5 C/m^2` and `|e15-e24| = 1.38e-4 C/m^2`.
The maximum removed forbidden raw component is `0.004014 C/m^2`; the
Frobenius relative projection residual is `0.00407`.  This is a numerical
finite-difference diagnostic, not the structural `symprec` criterion.  The
rank is complete and the direct polarization result is accepted with the
projection and raw residual both persisted.

The elastic matrix is positive definite (minimum eigenvalue `39.839 GPa`) and
has a relative symmetry-projection residual of `5.25e-4`.  Applying
`d = e (C^E)^-1` gives `d31=-5.96 pm/V`, `d33=12.46 pm/V`, and
`d15=-11.97 pm/V` in the same coordinate/sign convention.

## Remaining diagnostic

The unprojected internal-strain response has a `1.50%` relative symmetry
projection residual.  Its mean acoustic translation is only
`1.30e-10 Angstrom`, so this is not an acoustic-gauge artifact.  It is carried
forward as a separate convergence/reconstruction diagnostic for the
`Z* Lambda` pathway.  It does not enter the direct Berry-phase derivative used
for the accepted `e`, nor the elastic inversion used for `d`.

The collected machine-readable files are
`examples/3D_Bulk/wurtzite_ZnO_v2/results/summary.json` and
`examples/3D_Bulk/wurtzite_ZnO_v2/results/response_document.json`.
