# GaN/ZnO reference-relaxation failure audit (2026-09-18)

## Finding

The workflow incorrectly copied the Phonopy/spglib structure tolerance
`symprec=1e-3 Angstrom` into ABACUS INPUT as `symmetry_prec=0.001`.
These parameters belong to different algorithms and do not have interchangeable
semantics. ABACUS INPUT must omit both `symmetry_prec` and `symmetry_autoclose`.
The structure identification and atom mapping tolerance remains `1e-3 Angstrom`.

The installed ABACUS v3.10.0 reports commit `e84abb4`. Its matching local source
`source/module_cell/module_symmetry/symmetry.cpp`, function `analy_sys`, increases
the internal tolerance during `cell-relax` when the detected operation count
falls below its previous maximum. The failed logs show repeated symmetry
reanalysis and, for ZnO step 99, explicit enlargement from `0.001` to `0.002`.
Thus the configured input tolerance was not even the effective tolerance at
every ionic step. The source also reuses these tolerances in periodic position
matching; this is a calculator issue to diagnose independently of spglib's
response reconstruction.

## Evidence

Both original jobs reached electronic charge-density convergence at each late
ionic step. Their failures were in the reference `cell-relax`, before any
piezoelectric fitting.

- GaN: nearly unchanged serialized coordinates, but alternating cation z forces
  `+0.06905` and `-0.96405 eV/Angstrom`; the largest stress alternated between
  approximately `3.49` and `16.91 kbar`.
- ZnO: coordinates changed by approximately `1e-8` in fractional units at the
  late jump, while the maximum force jumped from `0.01238` to
  `3.75934 eV/Angstrom` and maximum stress to `29.44 kbar`.
- Cold-start single points on the same final structures, with symmetry enabled,
  disabled, and after a common periodic translation, did not reproduce those
  large forces. GaN's forces were about `0.069 eV/Angstrom`; ZnO's were about
  `0.012 eV/Angstrom`. This implicates the evolving relaxation/symmetry state,
  rather than an intrinsically bad electronic state at that geometry.

The earlier explanation attributing the failure specifically to a CG step-size
or line-search defect was too strong. No optimizer change was needed to recover
convergence. The numerical mechanism inside ABACUS is not proved down to an
individual faulty instruction; the demonstrated workflow error is the tolerance
override and its interaction with evolving calculator symmetry.

## Completed corrected reference calculations

Every recalculation used 40 MPI ranks and one OMP/MKL/OpenBLAS thread per rank,
the same PBEsol functional, pseudopotentials, orbitals, cutoff and k-point mesh
as its failed source. No SCF hyperconvergence was introduced.

```text
calculation   cell-relax
relax_method  cg
relax_nmax    100
force_thr_ev  1e-4
stress_thr    0.5
scf_thr       1e-8
symmetry      1
```

Neither of the two forbidden symmetry overrides appears in INPUT. The echoed
ABACUS defaults are `symmetry_prec=1e-6` and `symmetry_autoclose=1` for this
installed version; echoed defaults are provenance, not user-set INPUT fields.

| Material | Start | Node | Ionic steps | Max force (eV/Angstrom) | Max stress (kbar) | Wall time (s) |
|---|---|---|---:|---:|---:|---:|
| GaN | Original failed final structure | cu24 | 8 | 5.9841e-6 | 0.0051875 | 37 |
| ZnO | Original failed final structure | cu26 | 17 | 9.2690e-5 | 0.0398755 | 114 |
| GaN | Same structure, common origin translation | cu24 | 8 | 4.0508e-6 | 0.0085901 | 38 |
| ZnO | Same structure, common origin translation | cu26 | 11 | 9.3186e-5 | 0.0643573 | 78 |

All four jobs have the explicit `Relaxation is converged!` marker and satisfy
even the historical `0.1 kbar` stress gate. The stress-gate widening therefore
does not explain away the old large force/stress excursions. The two primary
original-origin reruns cost `1.678 core-hours`; the translated-origin controls
cost another `1.289 core-hours`. Additional cold single-point audit costs are
recorded separately in `diagnostic_results.json`.

The final structures identify as `P6_3mc` (No. 186) with spglib at
`symprec=1e-3 Angstrom`. ABACUS's internal operation count is recorded separately
and is not required to equal spglib's count.

## Reproducibility and subsequent response work

Remote audit root:
`235:/home/zhuxd/abacus/agent-runs/20260918-v2-gan-zno-root-cause`.
The primary reference directories are `gan/R1-raw-default` and
`zno/R1-raw-default`; translated controls are named `R1-default`.
Each contains INPUT, KPT, STRU, pseudopotentials/orbitals, complete calculator
logs, a final STRU_ION_D, and runtime/provenance records. Failed source trees
remain intact under the 20260917 campaign.

Promote only the converged primary references into separate R2r fixed-cell
relaxations, then generate one common zero-strain geometry and twelve
`+/-0.005` engineering-strain geometries. Every completed geometry gets one
PYATB calculation returning all three polarization directions. Only a complete
collection with ionic convergence, insulating paths, rank/residual, tensor
symmetry and mechanical-stability checks can be promoted as an updated `e/C/d`
benchmark. Reference relaxation convergence alone is not a piezoelectric result.

Previously converged stricter-stress results for other materials are retained;
this audit does not authorize rerunning them just to widen an acceptance gate.
