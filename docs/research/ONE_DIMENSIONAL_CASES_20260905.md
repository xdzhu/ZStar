# Unpassivated one-dimensional validation

Scope: BN (6,0), BN (9,0), and an isolated Sb2S3 chain. The third case was
explicitly added by the user after the original two-case goal was created.

## Execution and evidence checklist

- [x] Prepare physically connected structures centered in transverse xy vacuum.
- [x] Optimize atomic positions and axial period, preserving transverse vacuum.
- [x] Audit forces, stress, basis, k sampling and insulating band structure.
- [x] Compute polarization and forces from unified displacements; reconstruct BEC
      and zone-center force constants with rank and residual checks.
- [x] Calculate IR intensities and Raman derivatives, not just frequencies.
- [x] Check numerical convergence, stability and appropriate 1D normalization.
      Baseline reference-force k/vacuum and D3 checks only; not a claim of exhaustive
      convergence of all BEC or Raman derivatives, or of finite-q stability.
- [x] Compare like structures and report XC/boundary-condition differences.
      Raman relative-intensity disagreement is retained, not called validation success.
- [x] Package independent run/results folders, assets, run.sh and README files.
- [x] Record actual elapsed time and allocated core-hours, including failures.
      The cu20 interruption is recorded explicitly; its lost elapsed time is unknown.

## Final Delivery State

All three relaxation, reference-insulation, unified BEC/Gamma phonon and full
nonrigid-mode IR/Raman calculations completed. Public example paths:

- `examples/IR_Raman_Spectra/Nanotube_BN_6_0`
- `examples/IR_Raman_Spectra/Nanotube_BN_9_0`
- `examples/IR_Raman_Spectra/Nanowire_Sb2S3`

Each contains optimized centered inputs, original relaxation inputs, private PP/ORB,
VASP-format visualization structures, results, bilingual documentation and `run.sh`.
Native evidence archives were SHA256-verified before packaging, including all 2269
members of BN(9,0); its archive SHA256 is
`68f3ca59f8a1ca22730fa1cccd7b0157c36ca617f015d6e5da48990c312350a4`.
The CC BY 4.0 Sb2S3 reference data and a directly runnable comparison plot script
are included. Journal PDFs are not redistributed. No source cube was symlinked.

Verification: 93 focused spectroscopy/shared-response/example tests passed locally.
Tests include regeneration of the exact 20/56/20 displacement counts from packaged
inputs, coordinate/atom-order checks for VASP exports, finite tensors, mode selection,
read-only dry runs and protected result paths. Actual Linux `bash run.sh --dry-run`
passed for all three cases in a clean deployment copy. The portable wrapper was
not used to repeat all expensive DFT stages; the underlying native solver workflow
and all-mode collection were executed during production.

A pre-existing raw-Hessian comparison test required a Phonopy compatibility fix:
2.21 uses None to select the traditional solver, whereas the installed modern
version exposes `traditional`. The test now checks supported calculator names,
without weakening its asymmetric raw-tensor comparison.

Total recorded optimization + ABACUS/PYATB response + Raman costs: BN(6,0)
160.3612 core-hours; BN(9,0) 441.7097; Sb2S3 85.0892. Preparation and numerical
convergence probes are separately recorded and excluded from these totals.
BN(9,0)'s interrupted PYATB call is additionally unrecorded, so its total is not
the full billed cost. No additional DFT job, commit, push or release was made
as part of final packaging. Existing manuscript and unrelated worktree changes
were preserved.

The following sections are chronological research notes, not current job status.

Authorized nodes: cu20, cu23, cu24, cu25, cu26 via ssh 235. Inspect current
processes before assigning workers. Never alter other users' calculations.
Each ABACUS relaxation uses one MPI rank and 40 OpenMP threads.

Initial BN baseline uses existing PBE ONCV pseudopotentials and matching DZP
orbitals from the hBN example. It is not described as an XC-matched reproduction
of LDA or hybrid references. The axial cell-relax constraint is fixed_axes=ab.

## Primary references

- BN lattice dynamics: https://doi.org/10.1103/PhysRevB.68.045425
- BN Raman: https://doi.org/10.1103/PhysRevB.71.241402
- Zigzag BN vibration study: https://doi.org/10.1063/1.4788831
- Sb2S3 bulk and isolated-chain source data, Gianfranco Ulian (2026):
  https://doi.org/10.17632/6tntvw37tr.1
  The dataset landing page explicitly lists optimized 1D structures, Gamma
  IR/Raman data and dispersions with CRYSTAL B3LYP-D3 and HSE06-D3. Download and
  inspect the actual nanorod files before selecting an input or comparing peaks.

## Verified execution state

Remote root: `/home/zhuxd/abacus/agent-runs/20260905-one-dimensional`.
All three ABACUS processes were observed alive with iterative SCF output after
launch; launch markers alone were not used as evidence.

| Case | Node | Worker PID | ABACUS PID | Initial atoms | Initial axial period (A) |
| --- | --- | --- | --- | --- | --- |
| BN (6,0) | cu20 | 55345 | 55434 | 24 | 4.350 |
| BN (9,0) | cu23 | 187941 | 188030 | 36 | 4.350 |
| Sb2S3 | cu25 | 58162 | 58251 | 10 | 3.826 |

These PIDs are historical observations, not a substitute for fresh process
checks. Each case has a private `seed` and `relaxation` folder. No source cube
was linked or changed. Relaxation workers do not automatically start response
calculations: final forces, stress, cell constraints and centering need auditing.

The user selected PBE+D3 for Sb2S3. The downloaded CRYSTAL output explicitly says
`DFT-D3(BJ)` (B3LYP structure output line 479), so the ABACUS baseline uses
`dft_functional pbe` and `vdw_method d3_bj`, with SG15 PBE and 9-au DZP orbitals.
No new HSE calculation was launched. Reference HSE files are downloaded data only.

The Sb2S3 full-chain structure has ten atoms (Sb4S6). CRYSTAL's periodic x is
rotated to ZStar's z by the proper cyclic permutation
`(x_new, y_new, z_new) = (y_old, z_old, x_old)`. Its transverse image separation
is initially 20 A. All three structures are connected with no added hydrogen;
every BN atom has three nearest neighbours. Bounding-box xy centers equal the
cell centers to floating-point precision. Six unit tests verify periodic-cut
unwrapping, pair-vector preservation, idempotence, skew-cell rejection, rejection
of live relaxations and the final force/axial-stress acceptance thresholds.

The initial Phonopy counts are 20, 56 and 20 displacement structures respectively.
They are not final optimized-structure counts. The 3D vacuum cell's space group
captures only a subgroup of a nanotube's full rod symmetry; do not claim full
rod-group reduction or use its irreps as complete nanotube labels.

## Acquired reference evidence

`tools/shared_response/fetch_sb2s3_reference.py` retrieved 21 non-image files,
including CRYSTAL structures, full outputs, BEC, IR/Raman tensors and sampled
spectral curves. Every file was checked against the repository SHA-256 metadata.
Local raw data and provenance are in
`.codex-tmp/one-dimensional-20260905/reference/Sb2S3` pending final case archival.
The original data remain separate from ZStar results. The Raman output states
532 nm and provides both isotropic and directional intensities; matching the
temperature, units and tensor coordinate convention still requires review.

Current status: both BN relaxations accepted and unified response calculations
running; Sb2S3 still optimizing. No complete spectrum or BEC tensor
set is yet accepted as a result of this three-case task.

## Response-stage preflight

The new research driver provides `prepare-response`, `response` and
`launch-response` actions. Preparation requires a terminated relaxation worker,
maximum atomic force <= 0.005 eV/A, absolute axial stress <= 0.05 kbar, unchanged
transverse lattice and atom ordering, and an orthogonal final cell. Each solver
invocation records host, command, MPI/OMP layout, elapsed time and success/failure.
Preparation calls are classified separately from solver costs.

All three initial structures passed actual native `prepare_shared_abacus`
generation in `.codex-tmp/one-dimensional-20260905/preflight`. This includes the
reconstruction rank gate and private pseudopotential/orbital copies. These are
input-only preflights, not accepted final geometries or calculated responses.
The generated Sb2S3 INPUT-scf retains PBE and d3_bj, force output, 10-digit charge
output and the supplied 1x1x12 KPT. Final response seeds remove relaxation-only
keywords before generation.

## D3 cutoff audit

On cu26, three same-geometry SCFs compared pair cutoffs 16, 18 and 50.271835 A,
all with a 15 A coordination-number cutoff. STRU SHA-256 hashes match across
the three runs. Against 18 A, maximum force-component differences are
8.2765e-6 and 8.6469e-6 eV/A for 16 and 50.271835 A respectively; total-energy
differences are +0.000363877 and -0.001125226 eV. Total cost is 2.148 core-hours.
Raw comparison: remote `Sb2S3/d3-check/comparison.json`, local
`.codex-tmp/one-dimensional-20260905/sb2s3_d3_comparison.json`.

Production Sb2S3 response inputs use pair cutoff 18 A and coordination cutoff
15 A, avoiding transverse images. Initial-geometry distances lie at least
0.091 A from the 18 A pair boundary. Recheck on the final geometry and validate
reference forces after the change; this SCF comparison is not a full phonon
convergence proof. No change was made to the running relaxation inputs.

Do not use `vdw_cutoff_type period` as an unverified workaround. Local ABACUS
source `/home/zhuxd/Software/abacus/LTS/abacus-develop`, git describe
`LTSv3.10.0-5-ge84abb4`, initializes rthr2/cn_thr2 only in the radius branch;
their header defaults are zero while distance filtering is unconditional.
This is source-level evidence of a period-branch risk, not a separately verified
runtime bug report. The calculations use the radius branch.

## First accepted relaxation

BN(6,0): axial period 4.321140372 A, maximum force 0.00289546 eV/A, axial stress
-0.0169094 kbar, relaxation wall time 1221.18 s (13.5686 core-hours). Transverse
lattice unchanged. Generated 20 displacement stages plus reference. Response
worker launched on cu20 with PID 61923; check its live status before any restart.

The BN(6,0) reference band gap is 2.79895286 eV (report as 2.799 eV), with
VBM -5.32701644 eV and CBM -2.52806358 eV. Its insulation JSON points to the
actual PYATB band.dat file. Reference SCF, static electronic response and the
first three displacement responses finished successfully. The optimized seed
and relaxation audit were downloaded locally; an equal-scale VASP-format
geometry is available in `BN_6_0/response-seed/structure.vasp` under the local
campaign directory. This is a format conversion, not an additional VASP run.

## Spectroscopy execution support

`one_dimensional_spectra.py` prepares full IR intensities from BEC and Gamma
eigenvectors, then central-difference Raman tasks with disjoint mode partitions
for independent nodes. It collects the 1D line-polarizability derivatives using
the existing ZStar A_perp/(4*pi) normalization and writes spectra at 298 K,
532 nm and 8 cm^-1 broadening. It refuses incomplete Raman stages.

Selection first audits mass-weighted overlap with three rigid translations and
axial rigid rotation. Mixed or unexpectedly high-frequency rigid motion is
flagged for review; nonrigid imaginary modes stop preparation. No eigenvalue is
silently changed and no physically soft mode is excluded merely to improve a
comparison. Nine unit tests now cover centering, relaxation gates, and phase-
invariant rigid-motion identification. End-to-end spectroscopy validation still
awaits the actual response calculations.

Sb2S3 reference extraction produced all 30 frequencies/IR strengths and 15
Raman-active intensities with matching mode indices. Original sampled IR and
Raman curves remain available separately. No peak was shifted or fitted.
The two Wirtz primary papers were downloaded from the author institution and
hashed for internal reference; their PDFs will not be redistributed in examples.

## Second accepted relaxation

BN(9,0): axial period 4.338385175 A, maximum atomic force 0.00130581 eV/A,
axial stress -0.00396726 kbar, relaxation wall time 2012.35 s (22.3595 core-hours).
Its unchanged transverse cell and atom order passed the geometry gate. The
56-stage ensemble plus reference was prepared and response worker PID 196133
launched on cu23. ABACUS PID 196222 was observed running the reference SCF.
BN(6,0) has meanwhile completed eight SCFs (reference plus seven displacements).
Sb2S3 remains in relaxation, with latest reported gradient about 0.0084 eV/A.

## Reference-force convergence

BN(6,0), same optimized geometry, tested on cu26: doubling axial k sampling
from 12 to 24 changes the maximum force component by 1.68e-8 eV/A; adding 10 A
to each transverse lattice length changes it by 2.41853e-5 eV/A. Extra cost:
1.2301 and 1.5110 core-hours. Native logs were hashed and comparison JSON saved
under remote `BN_6_0/reference-check` and local
`BN_6_0/reference_convergence.json`. This validates reference forces only, not
the entire BEC or Raman derivative convergence.

The relaxation audit additionally requires the exact positive ABACUS geometry
convergence message, so electronic SCF convergence and negative "not converged"
messages cannot accidentally pass. Ten targeted unit tests pass. The original
live Sb2S3 worker was not restarted; its final log will be checked by this
stricter audit before any production response preparation.

## Sb2S3 accepted relaxation and production response

The original PBE-D3(BJ) optimization finished with the explicit positive
`Relaxation is converged!` marker. The stricter geometry audit passed: maximum
atomic force norm 0.00341079 eV/A, axial stress 0.00092200 kbar, axial period
3.785715323 A. Optimization cost was 36.0525 core-hours (3244.73 s, 40 cores).
No HSE calculation was launched.

The final structure was recentered in xy before generating the reference and
20 symmetry-reduced response displacements. Transverse bounding-box vacuum
gaps are 20.1098 and 19.9962 A, both exceeding the production D3 pair cutoff
of 18 A. The nearest axial-image pair distance lies 0.1952 A from that cutoff,
well beyond the displacement amplitude. CN cutoff remains 15 A. These checks
do not constitute full derivative convergence tests; the production reference
forces are explicitly gated after changing the dispersion cutoff from the
relaxation settings.

Response worker PID 70238 was launched on cu25. BEC, force constants and spectra
are not yet accepted results. The literature reference uses B3LYP-D3(BJ), so
comparisons must retain the functional distinction rather than imply a matched
functional benchmark.

## First completed response ensemble and Raman launch

BN(6,0) completed all 21 SCFs and PYATB stages. The reconstruction has rank 3
at every representative site, condition numbers at most sqrt(2). Raw Born
acoustic-sum residual is 0.00231057 e; Hessian reciprocity relative Frobenius
residual is 1.41406e-4. Force-fit residuals reach 0.00919 eV/A (these include
finite-displacement nonlinear response and are retained, not silently removed).
The constraint projection changes the Hessian by 7.17139e-5 relatively.

Eigenvector overlaps identify three translations near zero and axial rigid
rotation at 5.41763 cm^-1 (rigid overlap 0.99999994). All remaining 68 modes
are positive, beginning at 99.2043 cm^-1. This establishes Gamma stability of
the sampled optical modes, not stability throughout the one-dimensional BZ.
IR outputs were generated; two 68-SCF Raman partitions were launched on cu20
(worker 80600) and cu26 (worker 63139). Both actual ABACUS processes were
observed running. Raman tensors and spectra remain pending.

Response cost: ABACUS 24.5900 core-hours, PYATB 2.4280 core-hours, separately
recorded preparation overhead 0.1060 allocated core-hours. Thus BEC plus Gamma
phonons cost 27.0180 ABACUS+PYATB core-hours, excluding relaxation and Raman.

Reference band gaps read from native gate records: BN(6,0) 2.79895286 eV,
BN(9,0) 3.81339684 eV, Sb2S3 1.50090512 eV. All passed the reference gate.

## Sb2S3 completed response and reference-mode caveat

Sb2S3 completed the reference plus 20 response displacements. Its rigid modes
are three translations near zero and an axial rotation at 1.51528 cm^-1 with
overlap 0.999719. The remaining 26 modes are positive, beginning at 39.3797,
41.1384, 45.6472 and 52.6260 cm^-1. IR was generated. A 52-SCF Raman worker
was launched on cu25 (84219). Response costs are ABACUS 17.9198 core-hours,
PYATB 1.0252, with preparation separately recorded at 0.0868 allocated core-hours.

The public CRYSTAL reference's 31.5762 cm^-1 mode has axial rigid-rotation
overlap 0.982962, computed from its printed classical displacements, source
geometry and atomic masses. This is a diagnostic based on rounded printed
eigenvectors, not a new corrected reference spectrum or proof of a code error.
It must not be treated as an ordinary internal mode in a naive frequency-error
metric. Original sampled reference curves are unchanged; comparisons must explain
this low-frequency feature and retain the different XC methods.

`extract_sb2s3_reference.py` now emits a separate reference rotation audit with
structure hash and no filtering. Twelve focused tests pass, including synthetic
reference mode numbering, overlaps and rejection of reordered components.

## Completed Raman calculations and compact evidence snapshots

BN(6,0): all 136 Raman SCFs and dielectric post-processing stages completed.
Raman costs: ABACUS 111.6676 core-hours, PYATB 8.1069 core-hours; preparation
overhead separately 0.5574 allocated core-hours. Sb2S3: all 52 Raman SCFs
completed, ABACUS 28.3936 and PYATB 1.6980 core-hours; preparation 0.1707.
Both tensor arrays and broadened spectra were collected by the native reader.

The first Sb2S3 two-panel comparison uses the original public sampled curves,
not reconstructed unit-weight peaks. IR main features correspond, but Raman
relative intensities differ substantially. It is a cross-functional comparison,
not accepted quantitative intensity validation. The figure, source hashes,
normalization and low-frequency caveat are recorded in the local campaign
`Sb2S3/comparison` folder. No frequency shifts or fitted intensities were used.

Compact native evidence archives downloaded and every member's size/SHA256
verified locally (no symlinks):

- BN_6_0: 1360 files, archive SHA256
  `3c84310ce2c138eb98408cff452d6d99c2c2830c3eba4e6266f5ff9c5c75a05c`.
- Sb2S3: 685 files, archive SHA256
  `c3c664c041b0c7d0c013fa149770b2571009eb2ea4aa2455763c547d89ea53bb`.

These are evidence snapshots under `.codex-tmp/one-dimensional-20260905`, not
yet the final public run/results examples. BN(9,0) remains in its response
calculation (40/57 successful SCFs at this checkpoint); it has not been archived
as completed. Literature-mode correspondence, tensor checks and public reproducible
case packaging remain part of the active task.

## BN(9,0) response completed; four-node Raman production

All 57 reference/displacement SCFs and response stages completed. The four
rigid motions comprise three near-zero translations and axial rotation at
2.05984 cm^-1 (overlap 0.99999938). All 104 remaining modes are positive,
beginning at 47.9194 and 48.3102 cm^-1. IR outputs were generated.
Response costs: ABACUS 109.4055 core-hours, PYATB 15.6297 core-hours;
preparation separately 0.2913 allocated core-hours.

The full 208-SCF Raman set was partitioned into four nonoverlapping workers:
cu20/112593, cu23/232580, cu25/106649, cu26/95064. Each node had no ABACUS
process before launch, and each actual new ABACUS process was subsequently
observed running. These Raman results remain pending; no completion claim
or final archive has been made for this case.

## BN(6,0) tabulated literature comparison

Erba, Ferrabone, Orlando, Dovesi and Rerat, DOI 10.1063/1.4788831, provide
explicit n=6 frequencies in Table I of the author manuscript, verified at
https://iris.unito.it/bitstream/2318/130911/4/paperbntubivib.pdf . The calculation
uses CRYSTAL/B3LYP with a modified 6-31G* basis, not PBE. Direct DOI resolution
through the browsing tool failed; the institutional full text explicitly gives
the DOI, title, authors, method and numerical table. A separate direct file
download was HTTP 403, so no local PDF is claimed for this reference.

`compare_bn6_reference.py` compares the seven explicitly IR-active branches by
frequency order within each band, multiplicity and polarization. It omits C6/C7
from that comparison because the text explicitly identifies them as IR-inactive.
The candidate branch frequencies differ by at most 3.0153%; the RBM is 408.4524
vs 414.41 cm^-1 and has radial overlap 0.996843. This is a frequency comparison
with different functionals, not absolute-intensity validation or a full reference
eigenvector match. Reference A/B/C labels are band enumeration, not irreps.

The older Wirtz2003 Table I RBM scaling constant was also visually checked:
it prints 515 cm^-1 A, but direct use appears inconsistent with its plotted
diameter/frequency scale. It is therefore not used to generate benchmark values;
this is an unresolved source-consistency observation, not a corrected literature
constant. Original figure data/explicit tabulated frequencies take precedence.

## Recovery from cu20 reboot

During BN(9,0) Raman part 1, cu20 rebooted (reported boot time
2026-09-05 14:19:34). Original worker 112593 was authoritatively absent from
the node process table, while the other three workers continued. The first two
SCFs had completed; the interrupted stage was mode-0005/minus PYATB.

The old worker lock, launch record and worker state were preserved with suffix
`.interrupted-cu20-reboot`, and a recovery JSON was written. Part 1 resumed
with worker 6619 using the native completion checks; completed SCFs were not
repeated. A new ABACUS process 6982 was observed running after the pending
PYATB step resumed. This was recovery from confirmed process loss, not a
restart based on an observation timeout.

Timing caveat: component records cannot recover the interrupted PYATB elapsed
time, so their sum is a completed-call cost, not the full billed total including
the interruption. Node and gateway timestamps also differ; do not infer exact
lost core-hours from subtracting their wall-clock timestamps.
