# 3D SiC full central strain audit (VASP, 2026-09-13)

## Purpose and scope

This run validates the 3D strain ensemble, symmetry reduction, calculator-neutral
collection, and stress/energy elastic reconstructions.  It is a research audit,
not a released material database value.  The SiC primitive cell is oblique and
has space group `F-43m` (Hall 512); the six engineering-Voigt components use
`(xx, yy, zz, yz, xz, xy)` and a central amplitude of `1e-3`.

The stage cells were generated with the same Cartesian deformation gradient for
all lattice rows, `L' = L (I + eta)^T`, keeping fractional coordinates fixed.
The earlier one-vector shortcut was intentionally rejected by the collector and
is covered by a regression test.

## Provenance and resources

- backend: VASP 6.3.2 `vasp_std`, PAW-PBE Si/C inputs inherited from the
  existing v1 validation reference;
- `EDIFF=1e-8`, `NSW=0`, `IBRION=-1`, `ISIF=2`, `ISYM=0`, one SCF calculation
  per fixed-cell stage;
- reference plus 12 strain stages were run on the shared filesystem under
  `/home/zhuxd/zstar-v2-vasp-sic-fullstrain-20260913`;
- stages were distributed as four serial `40 MPI x 1 OpenMP` jobs each on
  `cu17`, `cu24`, and `cu26`; all 12 stages returned `rc=0`;
- elapsed compute was approximately 50.5 core-hours for the 12 strain stages
  (the reference calculation was reused from the preceding SiC smoke).

## Collection and symmetry

The VASP collector returned 13 observations (reference plus six positive and
six negative perturbations).  Every recovered strain matched its serialized
POSCAR vector to the collector tolerance.  Space-group reduction produced a
three-dimensional elastic basis, as expected for the chosen Cartesian
orientation of cubic `F-43m` SiC.  No polarization was inferred from VASP;
this audit concerns force/stress/energy only.

## Stress-derived elastic response

VASP's raw stress sign was explicitly audited from the tensile `eta_xx` pair and
converted as `compression-positive -> tension-positive`.  Fitting the stress
response in the 3-parameter space-group basis with major symmetry gave:

```text
input rank = 6, fitted rank = 3, allowed rank = 3
max residual = 0.0231 kbar (0.00231 GPa)
RMS residual = 0.00582 kbar (0.000582 GPa)
```

The resulting matrix is in GPa and follows the Cartesian axes of the input
cell (it is therefore not expected to have the textbook conventional-cubic
zero pattern):

```text
[[519.3805,  81.4418,  36.1457,  64.0583,   0.0000,   0.0000],
 [ 81.4418, 519.3805,  36.1457, -64.0583,  -0.0000,  -0.0000],
 [ 36.1457,  36.1457, 564.6766,  -0.0000,  -0.0000,  -0.0000],
 [ 64.0583, -64.0583,  0.0000, 173.6733,  -0.0000,  -0.0000],
 [  0.0000,  -0.0000,  0.0000,  -0.0000, 173.6733,  64.0583],
 [  0.0000,   0.0000,  -0.0000,  -0.0000,  64.0583, 218.9694]]
```

The eigenvalues are all positive (`128.38` to `636.97` GPa), so this sampled
clamped-ion response passes the numerical mechanical-stability check.

## Energy-derived cross-check

`fit_energy_elastic_response` now accepts the same symmetry-reduced elastic
basis.  It fitted the 13 energies with rank 3/3 and an energy residual of
`6.54e-8 eV` maximum (`4.27e-8 eV` RMS).  The energy-curvature matrix differs
from the stress result by at most `4.67 GPa` (about 0.9% of the largest entry):

```text
[[524.0533,  78.7577,  33.7996,  63.5804, 0, 0],
 [ 78.7577, 524.0533,  33.7996, -63.5804, 0, 0],
 [ 33.7996,  33.7996, 569.0114,  0,      0, 0],
 [ 63.5804, -63.5804,  0,       177.6897, 0, 0],
 [  0,       0,       0,         0,      177.6897, 63.5804],
 [  0,       0,       0,         0,       63.5804, 222.6478]]
```

This spread is a finite-step/backend work-conjugacy diagnostic.  It is not yet
an independent high-precision benchmark because the VASP and ABACUS input
settings, pseudopotentials, and cell representation have not been fully
matched.  A second strain amplitude, tighter convergence pair, and an ABINIT
or QE/thermo_pw reference remain required before Gate C can pass.

## Software consequence

The elastic fitters now correctly distinguish a full 28-parameter energy fit
from a symmetry-reduced fit.  A six-axis energy-only ensemble can remain rank
deficient for a conventional cell (for example, it may not probe `C12`); the
API reports that rank rather than silently claiming completeness.  The stress
fit can recover the reduced cubic basis from the same axis ensemble because
transverse stresses carry the cross-coupling information.
