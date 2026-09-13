# VASP 3D SiC strain collector smoke (2026-09-13)

## Scope

This is a calculator/collector integration smoke, not a published elastic
constant benchmark.  It uses the existing 3D SiC VASP reference inputs and a
single central pair for the Cartesian `eta_xx` perturbation.  The run was
performed on `cu17` with `40 MPI x 1 OpenMP`, serializing the three stages to
avoid competing with other users.

## Geometry audit

The first attempt changed only the first lattice vector.  For the oblique SiC
cell this does **not** represent a pure Cartesian `eta_xx`; recovering the
strain from the serialized cells produced additional shear components.  The
v2 collector rejected that ensemble as designed.  The inputs were regenerated
with the same deformation gradient for all lattice rows,

\[
 F = I + \eta, \qquad L' = L F^T,
\]

with `eta_xx = +0.001` and `-0.001`, while fractional coordinates were kept
fixed.  The corrected ensemble passed the exact-geometry check:

```text
reference       [ 0,      0, 0, 0, 0, 0 ]
strain-001+     [ 0.001,  0, 0, 0, 0, 0 ]
strain-001-     [-0.001,  0, 0, 0, 0, 0 ]
```

## Run provenance

- backend: VASP 6.3.2 (`vasp_std`)
- functional/potentials: inherited from the existing SiC reference (PAW-PBE)
- k mesh and cutoff: inherited unchanged from the reference input
- `EDIFF = 1e-8`, `NSW = 0`, `IBRION = -1`, `ISIF = 2`, `ISYM = 0`
- stage wall times: reference 6m21s, corrected `+` 6m32s, corrected `-`
  6m32s (cu17, 40 MPI ranks)
- scratch directory on the shared filesystem:
  `/home/zhuxd/zstar-v2-vasp-sic-strain-20260913`

The raw inputs and outputs remain in that scratch directory; only compact
metadata and parsed observations are kept outside the repository under
`E:\TEMP\zstar-v2-vasp-sic-strain-20260913`.

## Parsed observations

The calculator-neutral VASP collector successfully read three complete OUTCAR
files (energy, stress, final force block, lattice, atom count) and reconstructed
the actual strain vectors from the serialized cells.  The reference cell volume
is 20.999167 Å³.  Maximum force magnitudes are 0, 0.00613 and 0.006221
eV/Å for reference, `+`, and `-`, respectively; these are clamped-ion forces,
not ionic-relaxation convergence evidence.

For the one-dimensional audit direction, the raw VASP stress slope is
`-5193.73 kbar`; applying the explicitly deferred tension-positive conversion
gives `519.373 GPa`.  The central energy curvature gives `524.31 GPa` after
using `E = E0 + 1/2 Omega C eta²` and converting eV/Å³ to GPa.  The ~1% spread
is a useful work-conjugacy/finite-step diagnostic, not a final SiC `C11`
claim: a full tensor requires a symmetry-complete 3D ensemble, explicit VASP
stress-sign verification, and independent ABACUS/DFPT or literature
cross-checks.

## Consequence for Gate C

This run passes the geometry, parser, and collector smoke gates for an
independent backend.  It does **not** yet satisfy the quantitative independent
backend gate for v2 piezo/elastic results because the reference settings are
not matched to the ABACUS validation and only one strain direction has been
sampled.  No CLI or v1 file was changed, and no material tensor was published.
