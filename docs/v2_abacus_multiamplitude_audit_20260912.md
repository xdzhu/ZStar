# v2 multi-amplitude electromechanical audit (2026-09-12)

This is a correctness audit, not a production benchmark or workflow-
distribution test.  It uses the tetragonal BaTiO3 scratch directory
`/home/zhuxd/zstar-v2-tbto-relaxed40-20260912` and the ABACUS/PYATB backend.
The formal v2 ensemble is not promoted by this document.

## Scope and reproducibility

- backend: ABACUS 3.10.0-LTS, LCAO/PBEsol, 100 Ry, `scf_thr=1e-8`;
- all completed audit calculations: `40 MPI x 1 OpenMP`;
- polarization: one `pyatb_input --polar` call per geometry, followed by the
  v1-compatible precision adapter.  That one call writes the `a`, `b`, and
  `c` Berry-direction values in one `polarization.dat`;
- reference cell x lattice length: `3.899999742798442` (the common
  `LATTICE_CONSTANT` is included in the serialized structure);
- the actual strain values below are recovered from the serialized cells,
  not replaced by nominal amplitudes.

The `+2.5e-4` point was run on cu24 and the `-2.5e-4` point on cu25.  The
existing `+/-5e-4` formal points and independent `+/-1e-3` audits were kept
as separate provenance records.  No ABACUS NSCF triplet was used for the
production polarization values.

## Polarization observations

Values are in `C/m^2`, ordered `(a,b,c)` as written by PYATB.

| stage | actual `eta_xx` | node | `P_a` | `P_b` | `P_c` |
|---|---:|---|---:|---:|---:|
| reference | 0 | cu24 | 6.9986795559876629e-08 | 5.9494961253693324e-08 | 3.4874164326554113e-01 |
| -2.5e-4 | -2.4999999999984346e-4 | cu25 | 6.7294416430259803e-08 | 5.9541378281686516e-08 | 3.9500671626078887e-01 |
| +2.5e-4 | +2.4999997760543437e-4 | cu24 | 7.2687281234618340e-08 | 5.9612435719901118e-08 | 3.9501280344682177e-01 |
| -5.0e-4 | approximately -5.0e-4 | formal | 6.4571267012259431e-08 | 5.9328896802535588e-08 | 3.9502396831149383e-01 |
| +5.0e-4 | approximately +5.0e-4 | formal | 7.6318046049438127e-08 | 5.9662734452018508e-08 | 3.9513851140910727e-01 |
| -1.0e-3 | -1.0000000022498124e-3 | cu25 | 7.8994579468661843e-08 | 5.9611006971077096e-08 | 3.9510465067415301e-01 |
| +1.0e-3 | +9.9999997577499337e-4 | cu24 | 6.1462806014187150e-08 | 5.9641733333461846e-08 | 3.9516343273420246e-01 |

The `a`/`b`/`c` branch quanta remain near 2.00/2.00/2.10 `C/m^2`; the
printed values do not cross a quantum, so the large `c` offset is not a
Berry-branch jump in this audit.  A formal collector residual/rank report is
still withheld because the manually assembled scratch manifest has blank
input hashes and is not yet a complete v2 ensemble.

## Finite-difference diagnostic

Using the actual serialized `eta_xx` values, the central derivatives are:

| pair | `dP_a/deta_xx` | `dP_b/deta_xx` | `dP_c/deta_xx` |
|---|---:|---:|---:|
| +/-2.5e-4 | 1.07857296e-05 | 1.42114876e-07 | 1.21743721e-02 |
| +/-5.0e-4 | 1.17467790e-05 | 3.33837649e-07 | 1.14543098e-01 |
| +/-1.0e-3 | -8.76588673e-06 | 1.53631812e-08 | 2.93910300e-02 |

These derivatives do **not** converge with decreasing amplitude.  In
addition, the midpoint of every relaxed pair is displaced from the single
point reference by about `+4.63e-2 C/m^2` in `c`:

```text
mean(P(+eta), P(-eta)) - P(reference)
  c component: 0.0462681--0.0463924 C/m^2
```

This is a correctness failure for a relaxed-ion response claim, not evidence
for a large piezoelectric coefficient.

## Root cause and gate decision

The formal reference was only a single-point SCF.  Its final force block is

```text
Ba: (0, 0, +0.3567023281) eV/Angstrom
Ti: (0, 0, -0.2264863536) eV/Angstrom
O1: (0, 0, -0.3977774197) eV/Angstrom
O2: (0, 0, -0.3977774197) eV/Angstrom
O3: (0, 0, +0.6653388651) eV/Angstrom
```

and the diagonal stress is approximately `(75.2913, 75.2913, 41.4739) kbar`.
It is therefore not an ionic-equilibrium reference for a relaxed-ion
derivative.  The ± strain relaxations can fall into a different internal
minimum relative to that unrelaxed structure, producing the common `c`
offset and the non-convergent finite differences above.

**Gate C decision: blocked for material-response claims.**  The values above
must not be reported as validated `e`, `d`, `Lambda`, or relaxed-ion elastic
constants.  The next scientifically necessary step is to relax the reference
structure first, verify its force/stress and symmetry, then regenerate the
strain points around that relaxed reference and repeat the amplitude audit.

## Current follow-up

An isolated reference relaxation was started in
`reference-relaxed-audit-20260912` on cu17 with the same `40 MPI x 1 OpenMP`,
`scf_thr=1e-8`, PBEsol/LCAO settings and `force_thr_ev=0.0005`.  Its output is
now converged in 1209 s with maximum force `0.000488 eV/Angstrom` and final
energy `-3729.323887441615625 eV`.  The fixed-cell diagonal stress remains
approximately `(68.1855, 68.1855, 23.5694) kbar`; this is an internally
equilibrated fixed-cell reference, not a zero-stress volume optimization.  Its
single PYATB result is
`(6.9583213193e-08, 5.9093019978e-08, 3.9500998393e-01) C/m^2`, which aligns
with the c-polarization of the old relaxed ±strain points and confirms their
common `~0.395` offset was caused by the unrelaxed reference.

The next ±2.5e-4 points are being recomputed from this equilibrated internal
structure while preserving the actual ± strained cells.  An initial attempt
was discarded: a provenance check found that it had accidentally used the old
`STRU_INITIAL` (zero-strain cell) and therefore produced two zero-strain jobs.
Those outputs are archived as `OUT.POLAR_BAL_XX_{P025,M025}.wrong-cell-20260912`
and are excluded from all results.  No production CLI or workflow claim is
made from the corrected jobs until both their cells, ionic convergence and
polarization are independently checked.

The corrected balanced ±2.5e-4 pair has now converged in four ionic steps on
each node.  Its one-run PYATB values are:

```text
balanced -2.5e-4: (6.7765282793994102e-08, 5.9508557055927092e-08,
                   3.9516430111373685e-01) C/m^2
balanced +2.5e-4: (7.3194737617733333e-08, 5.9551595857878803e-08,
                   3.9519364467850548e-01) C/m^2
```

Relative to the equilibrated reference and using the serialized cell
denominator, this gives

```text
dP/deta_xx = (1.08589101e-05, 8.60776078e-08, 5.86871322e-02) C/m^2
midpoint(reference-subtracted) = (8.97e-10, 4.37e-10, 1.6899e-04) C/m^2
```

This is a meaningful improvement over the unbalanced-reference audit, but it
is not yet a convergence proof: the midpoint c offset is finite and the
balanced ±5e-4 pair is still running.  No response tensor is promoted until
the amplitude comparison is complete.

**Geometry-provenance correction.**  A later byte-level audit found that the
`STRU_INITIAL` files in this balanced/tight series still carried the old
strain-relaxed internal coordinates rather than the equilibrated reference
coordinates.  The cells had the intended strains, but the starting internal
coordinates differed by about `1e-5` in fractional units.  Those runs are
therefore retained only as diagnostic evidence and are superseded below; none
of their slopes is used as a material response.

The previously labeled balanced ±5e-4 pair subsequently converged (five and
six ionic steps, respectively).  Its PYATB values were:

```text
balanced -5e-4: (6.4821125358785923e-08, 5.9510018144139882e-08,
                 3.9518666020549947e-01) C/m^2
balanced +5e-4: (7.5789930695090023e-08, 5.9777588657804670e-08,
                 3.9519470456314332e-01) C/m^2
```

With actual serialized strains `-5.0000002056e-4` and `+4.9999999409e-4`,
the central result is

```text
dP/deta_xx = (1.09688052e-05, 2.67570510e-07, 8.04435753e-03) C/m^2
midpoint(reference-subtracted) = (7.22e-10, 5.51e-10, 1.8070e-04) C/m^2
```

The c derivative changes by about a factor of seven between balanced
`±2.5e-4` and `±5e-4`, so the response is still not numerically converged.
The final force residuals are also not uniform: the balanced points span about
`7.5e-5` to `3.6e-4 eV/Angstrom` under the nominal `5e-4` threshold.  Ionic
relaxation noise can therefore contaminate the small polarization differences;
the derivative discrepancy is not yet a clean physical-nonlinearity claim.
The balanced `±1e-3` pair is complete, but a tighter `force_thr_ev=1e-4`
±2.5e-4 audit is now running to separate force-convergence error from response
nonlinearity.  Until that comparison is made, the correct status remains
“algorithm audit blocked”.

The previously labeled tight ±2.5e-4 pair converged to maximum forces `6.9e-5`
and `6.7e-5 eV/Angstrom`.  The PYATB values were:

```text
tight -2.5e-4: (6.7414277063059204e-08, 5.9259598491561052e-08,
                 3.9518396295534186e-01) C/m^2
tight +2.5e-4: (7.2839502300388326e-08, 5.9566599934170212e-08,
                 3.9519489232006028e-01) C/m^2
```

The corresponding c derivative was approximately `0.02186 C/m^2`, between the
previous loose-threshold ±2.5e-4 and ±5e-4 values.  Because these directories
also used the stale internal-coordinate provenance, this comparison is not a
physical convergence result.

### Tight-reference rerun

To remove both sources of bias, the fixed-cell reference was relaxed again at
`force_thr_ev=1e-5` with `scf_thr=1e-8` and 40 MPI ranks.  It reached maximum
force `4e-6 eV/Angstrom` in 639 s.  One PYATB run on that final structure gave

```text
P_ref_tight = (7.0412637142603995e-08, 5.9921365322784574e-08,
               3.9517389498898037e-01) C/m^2
```

New ±5e-4 stages were generated with exactly this reference coordinate set,
the serialized cells were checked, and each stage used `force_thr_ev=1e-4`.
The final force residuals were `4.1e-5` and `3.8e-5 eV/Angstrom`; one PYATB
run per geometry gave

```text
ref2 -5e-4: (6.5281396392918726e-08, 5.9770030118344904e-08,
              3.9516830487328963e-01) C/m^2
ref2 +5e-4: (7.6547520848236592e-08, 5.9706773500892990e-08,
              3.9518430381022912e-01) C/m^2
```

Using the actual serialized strains `-5.0000002056e-4` and
`+4.9999999409e-4`,

```text
dP/deta_xx = (1.12661243e-05, -6.32566165e-08, 1.59989367e-02) C/m^2
midpoint(reference-subtracted) = (5.02e-10, -1.83e-10, 2.409e-06) C/m^2
```

The same tight-reference construction was repeated at ±2.5e-4.  The final
force residuals were `1.6e-5` and `1.5e-5 eV/Angstrom`; the PYATB values were

```text
ref2 -2.5e-4: (6.7595660032537516e-08, 5.9460527138700451e-08,
                3.9517076276840774e-01) C/m^2
ref2 +2.5e-4: (7.2455969387483921e-08, 5.8917281937069007e-08,
                3.9517858422843849e-01) C/m^2
```

With actual serialized strains `-2.499999999998e-4` and
`+2.499999776054e-4`,

```text
dP/deta_xx = (9.72061915e-06, -1.08649045e-06, 1.56429208e-02) C/m^2
midpoint(reference-subtracted) = (-3.87e-10, -7.32e-10, 7.785e-07) C/m^2
```

The c slopes differ by about 2.2%, while both midpoint offsets are below
`3e-6 C/m^2`.  This is the first internally consistent amplitude check; it
supports a converged `P(eta_xx)` slope for this audit geometry, but it is not
yet a promoted material tensor until the remaining symmetry, stress, unit and
independent-backend checks are complete.

### SCF-threshold paired audit

To test whether the SCF threshold was limiting the ionic-force accuracy, two
fixed-geometry single-point calculations were run on the same tight-reference
structure, both with 40 MPI ranks and identical settings apart from
`scf_thr`.  The `1e-8` and `1e-10` jobs took 115 s and 129 s, respectively.  The
largest force components were `2.34e-6` and `3.46e-6 eV/Angstrom`; the latter is
not smaller, so the observed force difference is below the numerical noise of
this comparison rather than evidence that `1e-8` is insufficient.

One PYATB run per geometry gave

```text
P(1e-8)  = (7.0379899249822762e-08, 5.9888627603100969e-08,
            3.9517389583268531e-01) C/m^2
P(1e-10) = (7.0379881935181222e-08, 5.9888609555555952e-08,
            3.9517389948059312e-01) C/m^2
delta    = (-1.73e-14, -1.80e-14, 3.65e-09) C/m^2
```

The polarization change is many orders of magnitude below the current
`P(eta_xx)` finite-difference error.  `scf_thr=1e-8` is therefore retained for
the present audit; a future material or basis set can trigger the same paired
test before changing the production threshold.
