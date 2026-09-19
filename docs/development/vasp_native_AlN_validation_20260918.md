# AlN Native VASP Acceptance Record

## Scope and Status

Status: native response and mixed-route Raman/IR acceptance passed on the
verified initial equilibrium geometry. Native DFPT electromechanical warnings
remain; accepted derived d uses native strain finite differences.
Branch: `codex/vasp-native-response`, baseline `9e0299a6`.
Case: `examples/VASP_Native_Response/AlN`.
hf Slurm jobs: `27719680`, `27719838`, `27719897`, `27719942`.
Remote root:
`/public/home/iai806/zstar-validation/vasp-native-20260918/code/examples/VASP_Native_Response/AlN`.

The seed was checked with spglib: space group 186, P6_3mc, point group 6mm.
It is centered in a hexagonal four-atom cell with Cartesian z parallel to +c
and an axial Al-to-N bond pointing along +c. Both cell and internal coordinate
must be relaxed before response calculations.

## Execution

- hf only; no 235 jobs.
- VASP 6.3.2, environment `/public/home/iai806/Software/VASP/env.sh 6.3.2`.
- 64 MPI x 1 OMP, mpirun, non-exclusive Slurm allocation, no fixed node.
- NCORE=4; no NPAR; ISYM=0 to retain an unchanged native k-point set.
- PBE PAW Al/N, ENCUT=600 eV, Gamma 8x8x6; historical relaxation and
  DFPT EDIFF=1e-8, accepted elastic and Raman EDIFF=1e-9;
  structural force stopping criterion 1e-4 eV/angstrom.
- Relaxation -> native electronic/ionic DFPT -> native elastic strain finite
  differences -> native dielectric mode derivatives for Raman.
- The Raman reference is reused from the completed elastic-response route.
- Public artifacts exclude POTCAR, CHGCAR, WAVECAR and licensed VASP source.

## Acceptance Order

1. Verify relaxation convergence, rank count and retained wurtzite structure.
2. Compare exported BEC/epsilon against raw OUTCAR and independent XML parsing.
3. Check BEC sum, 12 Gamma modes, nine stable optical modes and epsilon closure.
4. Check 6mm e tensor, internal-strain translation residual and elastic stability.
5. Verify d=e C^-1 and compare native DFPT with strain finite differences.
6. Compare e33/e31 with the PBE PAW reference, preserving polarity and conventions.
7. Complete all mode dielectric jobs, check IR/Raman activity and silent modes.
8. Preserve compact results, PP/input hashes, job accounting and bilingual instructions.

The earlier SiC calculation revealed a substantial native DFPT internal-strain
translation residual in this VASP build. This warning is retained explicitly;
healthy phonon frequencies or epsilon alone do not validate piezoelectricity.
Do not silently project native e/C or publish d when the quality gate rejects it.

## Verified Reference Locations

- de Jong et al., Scientific Data 2, 150053 (2015),
  DOI https://doi.org/10.1038/sdata.2015.53.
  Full text https://perssongroup.lbl.gov/papers/sdata2015-piezoprops.pdf.
  Methods: VASP PBE PAW, ENCUT=1000 eV, approximately 2000 k points per
  reciprocal atom; proper piezoelectric definition. Technical Validation:
  AlN e33=1.46 C/m2 and e31=-0.58 C/m2.
- Bernardini, Fiorentini and Vanderbilt, PRB 56, R10024 (1997),
  DOI https://doi.org/10.1103/PhysRevB.56.R10024.
  Full text https://www.physics.rutgers.edu/~dhv/pubs/local_copy/fb_nit.pdf.
  Table II: LDA ultrasoft, N axial Z=-2.70 e, e33=1.46, e31=-0.60 C/m2.
  Historical finite-polarization convention must not be conflated with modern
  proper tensors. No undocumented correction is applied to native VASP output.

## Completed Local Preflight

- Seed spglib space-group/point-group check passed.
- Shell syntax checks passed on hf before submission.
- Python validation-script syntax check passed.
- Native-response, spectroscopy-backend and acceptance-script tests: 61 passed.
- Full regression after the equilibrium-geometry and native-manifest fixes: 445 passed,
  one existing layout failure in
  `examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/run/input`.
  That separate in-progress example is unchanged; this does not justify
  weakening the layout test or claiming a fully green regression suite.

## Relaxed Structure

The 13-step relaxation converged. Retrieved structure:
`results/AlN_relaxed.vasp`. The relaxed structure still has P6_3mc / 6mm
at symprec=1e-5 angstrom. Lattice constants a=3.1280583 angstrom,
c=5.0151373 angstrom; axial internal separation u=0.38152065.
These are computed geometry results, not final response validation.

## Preliminary Native DFPT Response

- epsilon-infinity diagonal: 4.474796, 4.474795, 4.690378.
- e31=-0.58342 C/m2, e33=1.46355 C/m2; e15=-0.30081 C/m2.
- PBE PAW literature context: e31=-0.58 C/m2, e33=1.46 C/m2,
  DOI 10.1038/sdata.2015.53. Agreement in these two components alone is
  insufficient to accept all electromechanical response.
- Harmonic static dielectric reconstruction differs by 4.23e-4 (max absolute).
- Native internal-strain translation residual: 0.73974 eV/angstrom,
  relative 0.06560. The collector correctly emits a warning.
- Native e15/e24 differ by 0.01253 C/m2. The complete piezoelectric response
  still requires the native finite-difference comparison and quality checks.

Raw DFPT tensors and their warnings are retained even when individual
components agree with literature. Accepted response does not validate the
warned internal-strain tensor.

## Targeted Native Finite-Difference Check

Job 27719680 completed DFT but exposed the XML dielectric-array placement and
an internal-strain translation residual of 0.00122476, above the 0.001 gate.
The original elastic calculation is preserved in `.work/elastic_ediff1e8`;
no result was overwritten or silently projected.

Job 27719838 repeated only native elastic response at EDIFF=1e-9. Its DFT
completed; the report writer then failed on a NumPy Boolean. After converting
check values to Python bool, native response validation passed without more DFT.

- e31=-0.58162, e33=1.46150, e15=-0.30952 C/m2.
- d31=-2.19017, d33=5.32440, d15=-2.76820 pm/V.
- Relative internal-strain translation residual: 0.00040346 (passes).
- Elastic eigenvalues are positive; the minimum is 111.813 GPa.
- Harmonic fixed-strain dielectric closure: 0.00032453 maximum absolute.
- DFPT/finite-difference optical-frequency difference: 0.13217 cm-1 maximum.

The clean case now uses EDIFF=1e-9 throughout, but historical relaxation and
DFPT retain 1e-8. Hashes of the actual stage inputs must accompany these data.

## Equilibrium Geometry and Mode-ID Audit

The native IBRION=6 XML final structure retains the last 0.01 angstrom
atomic displacement. Its point group is 3m, whereas the initial equilibrium
structure is P6_3mc / 6mm. The adapter now uses the XML initial structure,
with a regression test for this exact failure mechanism. No relaxation,
native BEC, Hessian or piezoelectric DFT needed repeating.

Job 27719897 was cancelled during Raman after this issue was identified.
Its files remain in `.work/raman_finalpos_invalid` and are not validation data.
Job 27719942 completed the correct equilibrium-mode ensemble and Raman.
Collection checks reference geometry and rejects the invalid old tree.

Post-processing now maps VASP source mode IDs to frequency-ascending exported
Gamma IDs. Both ID sets are recorded; JSON/qpoints round-trip tests passed.
Old native JSON without an index convention is rejected with regeneration
guidance. A raw Raman subset NPY must not be assigned to the first Gamma modes.

## Final Spectral and Delivery Acceptance

Job 27719942 completed in 19:40 with 64 allocated CPUs. All 18 positive/negative
native mode dielectric jobs terminated normally. Compact spectra, CSV tensors,
qpoints and PNG/PDF/SVG figures are retained in `results/`.

Both `validation.json` and `spectral_validation.json` pass. The equilibrium
irreps are 6mm: A1 and E1 are IR/Raman active, E2 is Raman-only, B1 is silent.
The maximum inactive relative activities are 2.797e-7 (IR) and 4.672e-8 (Raman).
Selection-rule checks do not establish experimental absolute intensities.

A clean Python 3.10 environment installed the built wheel, with NumPy 2.2.6,
Phonopy 4.5.0, spglib 2.7.0 and pymatgen 2025.10.7. Native post-processing,
SiC frequency dielectric and Raman JSON/qpoints round trips passed; the retained
AlN spectral acceptance also passed from the installed wheel outside the source
checkout. No PYATB or ABACUS installation was needed for these VASP postprocessors.

The private venv/source on hf remain isolated; main code and the separate v2
worktree are unchanged. No main-branch merge, PyPI upload or paper edit is
included in this acceptance. LDA, hybrid/meta-GGA and intrinsic low-dimensional
native conversions are not claimed as end-to-end validated by these PBE bulk cases.

The updated full AlN `run.sh` was then executed with `VASP_COMMAND=false`
and MPI_TASKS=64. Every retained DFT stage was reused, both acceptance reports
passed, and the script exited zero. `results/resume_validation.log` records
this end-to-end restart test; a missing DFT stage would have failed immediately.
