## 0.3.2 - 2026-09-08

- Complete the canonical `zstar spectra post` option forwarding and add
  polarized Raman output to the Unified response route without additional SCFs.
- Parse current ABACUS force logs when Phonopy's legacy reader is unavailable,
  and select the built-in Phonopy force-constant solver across supported APIs.
- Verify 387 installed-package tests, 66 subtests, 30 CLI checks, three retained
  numerical archives, and dry runs for all 40 indexed public examples.
- Refresh the bilingual manuals, representative BEC/APT results, four-dimensional
  spectroscopy figure, citation labels, package metadata, and example checksums.
- Keep historical expert commands available while presenting the canonical
  BEC, phonon, spectra, dielectric, structure, data, and potential lifecycles.

## 0.3.1 - 2026-09-07

- Correct the Git-index spelling of `examples/3D_Bulk` so the documented
  bulk examples resolve on case-sensitive Linux filesystems.
- Add an explicit manifest-to-Git path-case regression test, including on
  Windows where filesystem lookups alone cannot reveal this mismatch.
- Keep the 0.3.0 numerical implementation and retained results unchanged;
  point installation, example links, and manuscript metadata to this patch.

## 0.3.0 - 2026-09-07

- Unify symmetry-adapted BEC/APT and zone-center phonon calculations, using
  actual written displacement vectors for tensor and force-constant reconstruction.
- Compute IR and static nonresonant Raman response from the Unified ensemble;
  reuse ABACUS electronic matrices without additional Raman SCFs.
- Support bulk, slab, wire, and molecular response conventions with retained
  raw data, explicit tensor units, and independent Separate/Unified benchmarks.
- Publish organized BEC, IR/Raman, and electrostatic-potential examples with
  clean run inputs, archived results, launchers, and basis-asset provenance.
- Standardize response output filenames while keeping historical readers;
  improve reference-first execution, header selection, private file copies,
  PYATB precision, and headless plotting.
- Refresh bilingual manuals, Agent Skill recipes, manuscript-quality figures,
  literature labels, and release acceptance tooling.
- Build wheels and source distributions in GitHub Actions, test independently
  installed wheels, and publish versioned releases with generated change notes.
- Keep examples in GitHub and exclude them from PyPI distributions.

## 0.3.0rc6 - 2026-09-06 (release acceptance candidate)

- Export IR/Raman figures without requiring a GUI backend or Tcl/Tk.
- Ensure PYATB input generation disables ABACUS gamma-only storage and exports
  both Hamiltonian/overlap and position matrices, including partial templates.
- Keep the current precision adapter when PYATB uses a different Python environment.
- Make example helper calls independent of executable permission preservation.
- Exercise installed ZStar in public examples without overriding it with source paths.
- Align methane spectroscopy rerun inputs with its relaxed Unified benchmark.
- Clarify example reproduction levels and prioritize Unified automation in the
  bilingual tutorials and manuscript. Retain external adapters as optional routes.
- Add independent wheel-install acceptance checks and editable Figure 1 assets.

## 0.3.0rc5 - 2026-09-06 (source snapshot, not uploaded)

- Integrate Unified IR/static nonresonant Raman into `zstar spectra`, reusing
  BEC displacement matrices with full-precision PYATB response output.
- Add rank-three dielectric-derivative reconstruction, overlap-based rigid-mode
  classification, private matrix copies, source/output validation and resume locks.
- Add matched four-dimensional spectroscopy costs, reproducible `results/Unified`
  archives, bilingual tutorials and an updated Agent Skill recipe.

- Preserve VASP physical dimensionality and periodic axes through preparation
  and response export; low-dimensional electronic tensors are explicitly labeled
  as supercell responses, without changing the solver boundary conditions.
- Organize BEC cases under `3D_Bulk`, `2D_Slab`, `1D_Nanowire`, and
  `0D_Molecules`; retain matched controls in the benchmark index and preserve
  original evidence hashes. Keep spectroscopy and electrostatic-potential cases
  in their dedicated directories.
- Add explicit response-only offline verification for the BN(9,0) and Sb2S3
  BEC/Gamma bundles; missing spectra still fail full-spectrum verification.
- Refresh the current-framework editable figures, appendix BEC tables, HSE
  source labels, dimensional normalization table, citation-key figure labels,
  and bilingual documentation from the final annotated manuscript review.

## 0.3.0rc4 - 2026-09-06 (source snapshot, not uploaded)

- Standardize new BEC outputs as `BEC.*`; retain read-only historical aliases
  and reject conflicting automatic matches without changing tensor precision.
- Correct example launcher configuration and molecular IR orchestration;
  match HfO2 inputs to the manuscript's PBEsol/9-au results.
- Add the converged nonpolar GeS control, six-panel potential comparison,
  four-row spectroscopy figure, bibliography-key labels, and refreshed manuals.
- Verify 410 tests and 66 subtests, Linux alias/shell behavior, and retained
  one-dimensional tensor, spectrum and timing evidence.

## Earlier development - One-dimensional publication examples

- Add unpassivated BN nanotube and Sb2S3-chain unified BEC/Gamma results,
  complete IR/Raman calculations, private input assets and resumable examples.
- Export BN(9,0) Cartesian/local cylindrical BEC data and site-matched Sb2S3
  diagonal comparisons against the explicitly identified public CRYSTAL dataset.
- Add an equal-scale structure/IR/Raman comparison with original unshifted
  Sb2S3 reference samples, retaining relative-intensity disagreement.
- Correct the example documentation's response.json tensor-axis description;
  add coordinate-covariance, reference-mapping and joint-observation tests.
- Complete matched independent BEC/phonon controls: BN(9,0) uses 270.41 versus
  125.04 successful solver core-hours (2.16-fold speedup), Sb2S3 41.67 versus
  18.95 (2.20-fold). Preserve the unmeasured BN9 interrupted attempt separately.
- Add read-only native-evidence, tensor/eigensystem, spectrum and timing-ledger
  verification, including compatibility with Phonopy 2.36, 2.44 and 4.4.

## 0.3.0rc2 - 2026-09-04

- Correct a platform-specific test assertion to use pathlib rather than a
  Windows-only path separator. The response kernel is unchanged from rc1.
- Track setup instructions inside the VASP SiC input directory so a clean Git
  checkout retains it; the example still requires the declared local VASP files.
- Describe the HfO2 numerical basis by its actual per-element orbital counts.
- Retain the complete Unified workflow, eight measured benchmark pairs, header
  selection and response-unit fixes described below. The initial rc1 GitHub
  release was blocked by these repository/test checks and published no wheel.

## 0.3.0rc1 - 2026-09-04

Submission candidate; this tag is a GitHub prerelease, not a PyPI publication.

- Add the Unified symmetry-adapted ABACUS + PYATB BEC/APT and Gamma
  force-constant workflow, using actual displacement vectors, rank checks,
  phase-wrapped polarization differences, and separate raw/projected outputs.
- Complete eight matched Cartesian/Unified benchmarks: cubic BaTiO3, 3C-SiC,
  tetragonal HfO2, alpha-In2Se3, hBN, MoS2, H2O, and CH4. Successful solver
  timings give 1.60-3.47-fold speedups under the documented per-case controls.
  Molecular results use relaxed structures and internal-coordinate validation;
  cubic BaTiO3 retains its physical harmonic instability.
- Add reproducible inputs, PP/ORB assets, response observations, force records,
  timing ledgers, and offline verifiers to the GitHub example library. Include
  refined MoS2 Berry-grid evidence and PBEsol In2Se3/HSE molecular APT records.
- Implement Specified -> Current -> Global job-header selection across BEC,
  phonon and spectroscopy generators; honor configured MPI/OMP/executables in
  both generated scripts and direct runs. Test shell, Slurm and Torque syntax
  and mocked execution without claiming a new native scheduler validation.
- Make low-dimensional response fields and Raman normalization explicit.
  Add opt-in macroscopic slab boundary conversion with coupled tensor support;
  preserve source-field normalization for independent-particle PYATB outputs.
- Correct STRU Cartesian length-unit conversion, improve PYATB output precision,
  and preserve byte-identical archived evidence across Git checkouts.
- Synchronize bilingual manuals, response conventions, and citation metadata;
  validate 319 package tests with both Phonopy 2.36 and 4.4, plus 50 research
  regressions. GitHub CI tests both dependency profiles before building wheels.

- Add `--pp` and `--orb` to ABACUS BEC preparation, with global directory
  defaults, exact-or-unique asset matching, immutable source `STRU` handling,
  staged ordinary file copies, and SHA256 provenance in `.zstar/assets.json`.
- Remove the obsolete site-specific `job_scripts/` templates; shell, Slurm,
  and Torque drivers are generated by the canonical `job` actions with
  per-job resource options and optional environment initialization.

## 0.2.1 - 2026-09-02

- Publish the curated reproducible example library in the GitHub repository,
  covering 1D wires, 2D slabs, bulk materials, molecules, CP2K, and VASP.
- Add bilingual example indexes, case READMEs, compact reference results, and
  an example manifest while keeping solver scratch and licensed files out of
  the repository and release artifacts.
- Refresh the bilingual README PDFs and synchronize the public release
  documentation with the reorganized example layout.

- Add a production `dim=0` molecular atomic-polar-tensor workflow for
  ABACUS/PYATB, including symmetry expansion, translational-sum correction,
  per-atom GAPT values, and normalized response records.
- Extend `zstar cp2k-bec` to nonperiodic molecular dipoles and validate H2O and
  CH4 against CP2K 2025.2 native APT across displacement and field-strength
  convergence scans.
- Recover small molecular PYATB polarization signals from ionic/electronic
  phases only when their printed precision improves on the final polarization
  line, while preserving the established bulk parser behavior.
- Add an end-to-end `dim=1` ABACUS/PYATB workflow for `z`-periodic wires:
  transverse cube-dipole polarization, longitudinal Berry polarization,
  line-polarizability normalization, Gamma-point IR/Raman, and explicit
  rejection of bulk non-analytic phonon corrections.
- Work around PYATB's unconditional three-axis Berry loops by recording and
  applying a minimum `2 x 2 x N` polarization grid for 1D inputs while using
  only the physical periodic-axis Berry result.
- Request ten-digit ABACUS charge-density cubes in low-dimensional workflows
  so transverse dipole finite differences are numerically resolved.
- Unwrap open-direction charge densities around a weighted circular ionic
  center, keeping slabs and wires contiguous when they cross a cell boundary.
- Enforce the canonical BEC convention (rows are atomic displacement/force;
  columns are polarization/electric field) in low-dimensional collection,
  mode-charge contraction, and MD dipole reconstruction.
- Preserve eight decimal places in reduced, symmetry-reconstructed, and
  Phonopy BEC artifacts so high-precision finite differences are not truncated
  before symmetry reconstruction or acoustic-sum correction.
- Validate the complete 1D route on a hydrogen-passivated GaAs nanowire with
  49 BEC stages, 40 phonon-force stages, all-mode IR, selected-mode Raman, and
  coordinate-matched VASP and archived Quantum ESPRESSO comparisons.
- Extend the bundled `run-zstar-workflows` skill and JSON preflight to route
  supported 1D BEC and Gamma-spectroscopy calculations with finite-q cutoff
  limitations kept explicit.

## 0.2.0 - 2026-08-26

- Add the versioned `zstar-response` 1.0 schema, calculator backend registry,
  ABACUS/VASP/CP2K/Phonopy importers, and explicit `dim=0/1/2/3` normalization.
- Add a resumable Quantum ESPRESSO `pw.x -> ph.x -> dynmat.x` backend with an
  insulating-gap gate, native BEC/dielectric/IR collection, and scheduler scripts.
- Add shared VASP/QE/CP2K cube adapters for open-direction dipoles, polarized
  Raman geometries, dielectric-derived optical constants, dimensional NAC
  guards, and external-command/plugin BEC providers for `zstar md`.
- Add the standards-compliant `run-zstar-workflows` agent skill, packaged in
  both wheels and source distributions, with CLI installation and JSON
  preflight checks for BEC, phonon, spectroscopy, dielectric, MD, CP2K, and
  database workflows.
- Add `zstar db init/collect` for provenance-aware Born-charge and High-K
  database collection with full-cell tensor scope, acoustic diagnostics, and
  strict separation of 3D, 2D, and molecular responses.
- Add a reproducible collaboration-bundle builder with validated bulk, 2D,
  and molecular examples, batch templates, checksums, and offline smoke tests.
- Add a CP2K finite-displacement BEC backend with periodic-dipole branch
  unwrapping, serial restart reuse, resumable state, CP2K 2025.2+ native APT
  comparison, bilingual documentation, and direct-node numerical validation.
- Add a VASP BEC backend with native `LEPSILON` and `LCALCEPS` routes,
  insulating-gap gating, resumable shell/Slurm/Torque execution, normalized
  tensor comparison, finite-field safeguards, and VASP 6.3.2 SiC validation.
- Add unified `zstar spectra` workflows for VASP mode-displaced dielectric
  responses and CP2K native vibrational IR/Raman intensities, with resumable
  execution, bilingual guides, plots, and explicit 2D physical guards.
- Correct two-sided slab vacuum analysis by averaging local surface-adjacent
  plateau windows instead of entire half-vacuum regions that may contain a
  dipole-correction reset.
- Report plateau standard deviations, point counts, and averaging width; add
  `--vacuum-window` to both `zstar pot` entry points.
- Add reproducible MoS2, alpha-In2Se3, SnS, SnSe, and SnTe potential examples
  and a publication-ready CPC manuscript figure.
- Extend Agent Skill preflight to represent 1D records while explicitly
  blocking unimplemented end-to-end 1D BEC and Coulomb-cutoff phonon claims.
- Restrict pytest discovery to the maintained `tests/` tree so ignored delivery
  and verification workspaces cannot cause duplicate-module collection errors.

## 0.1.2 - 2026-07-31

- Add a production `--dim 0` workflow for isolated-molecule IR and Raman
  spectra in periodic vacuum supercells.
- Convert branch-wrapped Berry polarization to molecular dipole derivatives
  and dilute-cell dielectric derivatives to molecular polarizability
  derivatives, including non-orthogonal lattice directions.
- Add resumable paired PYATB optical/polarization response calculations and
  regression tests for molecular central differences and output files.
- Add bilingual molecular spectroscopy guides and reproducible CH4/CO2
  benchmark examples for frequencies, degeneracies, and selection rules.

## 0.1.1 - 2026-07-23

- Add `zstar polar2d` for a reproducible reference/displaced cube-pair charge
  profile, slab-dipole difference, and out-of-plane effective-charge audit.
- Export IR and Raman plots as publication-ready PDF and SVG in addition to
  PNG, and archive the BTO/In2Se3 manuscript figures with compact source data.
- Add backend-aware shell, Slurm, and Torque launch defaults, dry-run driver
  generation, backend manifests, deterministic scheduler output paths, and
  corrected multi-node Torque resource allocation.
- Document and validate the full tetragonal BTO Raman mode set and all three
  serial workflow backends.

## 0.1.0 - 2026-07-23

- Add deterministic, resumable `0.no-move -> displacements` BEC workflows
  with shared reference charge density and shell, Slurm, and Torque drivers.
- Add a one-time insulating reference gate. The default uses a standard PYATB
  band path, while a Monkhorst-Pack check remains available explicitly.
- Add hybrid two-dimensional BEC analysis: Berry-phase in-plane polarization
  and cube-integrated out-of-plane slab dipoles.
- Add phonon input validation, robust force collection, Gamma-mode IR spectra,
  harmonic dielectric response, and finite-difference Placzek Raman spectra.
- Add fixed- and frame-resolved BEC post-processing for MD dielectric response.
- Add automatic compatibility with legacy and direct-static PYATB dielectric
  interfaces.
- Add electrostatic-potential cube analysis and rendered slab examples.
- Require Python 3.9 or newer and add SciPy as a runtime dependency.

## 0.0.8 — 2026-03-24

- Fix the anomaly enormous delta_P result when two Polarization values are too close.

## 0.0.7 — 2025-12-19

- Really support auto detected Cartesian coordinates for STRU.

## 0.0.6 — 2025-12-19

- Fix auto detected Cartesian support for STRU.

## 0.0.5 — 2025-12-16

- Implemented central FD method for second-order precision, set to `--method=central` in both `zstar gen` and `zstar deal` to run it, defalut still set as `--method=forward` to save computing resources.

## 0.0.4 — 2025-12-12

- Remove `out_chg 1 10` style, just use `out_chg 1`.
  
## 0.0.3 — 2025-12-11

- Fix bugs in the post-processing of Born effective charges (BEC) for the ABACUS NSCF backend, including symmetry reconstruction and automatic generation of `Z-BORN-symm.out`.

## 0.0.2 — 2025-12-08

- Publish on PyPi.

## 0.0.1 — 2024-09-24

- Obtain software copyright (former name: PyKAPPA).


## 0.3.0rc3 - 2026-09-04

Local manuscript-revision candidate; not a PyPI publication.

- Standardize new outputs as `bec.dat`, `bec.raw.dat`, representative tables,
  `response.json`, `response_fit.json`, `force_fit.json`, and `apt.json`.
  Keep bidirectional filename fallback for old archives without rewriting them.
  Write `BORN` once, removing its redundant long-name copy.
- Complete 30 independent force SCFs to measure Separate versus Unified
  workflows for all eight benchmark systems. Retain the original combined
  Cartesian controls and disclose force-output overhead in their BEC timing.
- Archive the matching PBE+D3(BJ) MoS2 BEC and dielectric evidence alongside
  its IR/Raman results, correcting the manuscript's older dataset index.
- Update bilingual output documentation and redraw the potential figure from
  source as four panels with a single-cell GeS map.
