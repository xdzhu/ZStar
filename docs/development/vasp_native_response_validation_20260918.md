# Native VASP Response Acceptance

Baseline: 9e0299a6, frozen with zstar-before-vasp-native-20260918.
Development: codex/vasp-native-response, separate worktree
`D:/Work/Code/zstar-vasp-native`. Main and the independent v2 worktree are untouched.

## Actual Calculation Coverage

| Quantity | Solver and reconstruction | Evidence | Status |
|---|---|---|---|
| BEC and electronic dielectric | Native LEPSILON electric DFPT | SiC and wurtzite AlN, raw OUTCAR/XML | Accepted PBE PAW cases |
| Gamma phonons | Native IBRION=8 DFPT and IBRION=6 ionic finite differences | Matched optical frequencies | SiC within 0.05 cm-1; AlN within 0.133 cm-1 |
| Phonon/static dielectric and IR | Native BEC + modes, no extra SCF | Native ionic dielectric closure and selection rules | Maximum closure below 5e-4 |
| Proper piezoelectric e | Native clamped + ionic terms | AlN 6mm pattern and PBE literature | Accept strain-FD route; retain DFPT internal-strain warning |
| Elastic C and derived d | Native strain finite differences, stable C, d=e C^-1 | Positive eigenvalues, force balance, e=dC | Accepted SiC and AlN strain routes |
| Static nonresonant Raman | Native dielectric derivatives on +/- normal modes | SiC T2 triplet; AlN A1/E1/E2 active, B1 silent | Six SiC and eighteen AlN additional mode jobs completed |

This is native-solver validation, not a cross-calculator efficiency benchmark.
Raman is not supplied by one DFPT calculation. The primitive Gamma force
constants are not a finite-wavevector dispersion. Directional NAC/LO branches,
intrinsic low-dimensional native conversion, hybrids and meta-GGA were not
validated by these two bulk PBE cases. Unsupported slab spectroscopy remains gated.

## Runtime and Restart Evidence

hf Slurm, VASP 6.3.2; 64 MPI x 1 OMP, NCORE=4, no NPAR, no exclusive allocation
or fixed node. Intel mpirun is used, avoiding the singleton startup seen with
an unsuitable srun/PMI setup. ISYM=0 avoids the native k-point redistribution
restriction with NCORE>1; native symmetry acceleration is not claimed.

Valid SiC calculation jobs: 27719579 (native DFPT), 27719605 (native strain FD),
27719639 (completed mixed spectra). Some jobs terminated in a postprocessing
error after DFT completed; valid outputs were reused rather than recomputed.

AlN job 27719680 completed relaxation/DFPT/strain DFT, but exposed an overly
large native strain residual and an XML adapter issue. Job 27719838 repeated
only strain response at EDIFF=1e-9. Raman job 27719897 was cancelled after
finding the wrong final-displacement geometry in the adapter. The correct
Raman ensemble completed in job 27719942. Rejected private trees are preserved
and excluded from public validation data.

Both updated full case runners were executed with VASP_COMMAND=false and
MPI_TASKS=64. They reused every completed DFT stage, collected results, passed
their acceptance scripts and exited zero. A missing stage would have failed
instead of silently launching another calculation. Logs and Slurm accounting
are retained separately from clean run inputs.

## Repaired Failure Mechanisms

- The XML final structure in native finite differences can retain the last
  displaced atom. Use the initial equilibrium structure, validate reference
  geometry, and reject previously generated wrong-geometry Raman trees.
- Native source IDs and ascending exported Gamma IDs differ. Retain both;
  JSON/qpoints round-trip tests prevent assigning optical Raman tensors to acoustic modes.
- Native strain XML epsilon can sit outside pymatgen's final calculation block;
  the independent acceptance parser checks the actual XML dielectric array.
- Convert NumPy Boolean check values before writing JSON reports.
- A newly rejected derivative removes stale owned quantities from response.json.
- Derived d is not volume-normalized. Raw force-strain tensors also have no
  hidden volume normalization; proper e is not corrected a second time.
- A root containing only the native VASP manifest must not silently route
  bec post to ABACUS when hidden CLI metadata are absent.
- Nonzero/metal-rejected workflow states return a failing CLI exit code.
- Restart copies use CHGCAR, not incompatible WAVECAR, for mode displacements;
  no source output is symlinked. Tighter user EDIFF is retained.

## Clean Delivery

The built wheel excludes examples and licensed VASP files. A fresh Python 3.10
environment installed it with NumPy 2.2.6, Phonopy 4.5.0, spglib 2.7.0 and
pymatgen 2025.10.7. Native collection and the SiC dielectric/Raman round trips
passed outside the source tree; AlN retained spectral checks also passed.
No ABACUS/PYATB dependency is needed by these VASP postprocessors.

Unit and retained-result tests cover routing, precision controls, tensor axes,
Voigt order, units, cache guards, source safety, mode geometry, mode numbering,
force-balance gates, stale-record removal, irreps and selection rules.
The full suite retains one pre-existing layout failure at
`examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/run/input`; this unrelated
in-progress case is not modified and the test is not weakened.
Final counts: 61 focused tests passed; 445 full-suite tests passed and one
pre-existing layout failure. Code/document diffs pass whitespace checks;
solver-generated CSV/structure/YAML output formatting is retained as data.

No main merge, public release, PyPI upload or manuscript edit is included here.
