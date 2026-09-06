# One-dimensional publication update

## Scope and ordered acceptance checklist

- [x] Verify production routes: BN(9,0) and Sb2S3 use dimension=1,
  Phonopy displacements, common dipole/force observations and unified reconstruction.
- [x] Measure matched Cartesian BEC and independently executed force-only phonon
  controls, retaining the optimized geometry, XC, PP/ORB, k mesh and displacement.
- [x] Audit raw/projected BEC and Hessian agreement, tensor frames, sum rules,
  mode correspondence and separate successful/failed-call costs.
- [x] Export full BEC data and compact BN(9,0)/Sb2S3 presentation tables.
- [x] Present Sb2S3 IR/Raman alongside original public dataset curves, preserving
  disagreements and identifying the reference as a dataset, not a journal article.
- [x] Update runnable cases, bilingual manuals and agent-facing workflow guidance.
- [x] Update manuscript results, efficiency table, source index and appendices;
  retain existing user-edited figure layouts and structures.
- [x] Run focused and full tests, compile revised/clean PDFs and visually inspect.

## Cost contract

An SCF count means independently converged geometries, not electronic iterations.
Unified BEC and Gamma force constants share all reference/displacement SCFs; their
cost cannot be added twice or arbitrarily split into two independently measured jobs.
The separate baseline combines a Cartesian central BEC route and force-only Phonopy
displacements, sharing the reference already counted in the BEC route. Count and
report that reference convention explicitly. Report ABACUS and PYATB components and
their sum, excluding relaxation, Raman derivatives, and preparation from BEC+phonon
speedup. Keep failures separately. No time extrapolation is a measured benchmark.

Production unified costs: BN(9,0), 57 SCFs, 109.40550663 ABACUS + 15.62973637
PYATB core-hours; Sb2S3, 21 SCFs, 17.91983941 + 1.02522455 core-hours.
The BN(9,0) reboot interruption belongs to Raman, not to this response benchmark.

## Reference status

G. Ulian, DFT dataset on bulk and 1D stibnite Sb2S3 (2026),
https://doi.org/10.17632/6tntvw37tr.1, CC BY 4.0. No corresponding journal article
or preprint has been verified. Reference uses CRYSTAL/B3LYP-D3(BJ), production uses
ABACUS/PBE-D3(BJ). The original 31.5762 cm^-1 rotation-like reference mode remains
in the reference curve; Raman relative intensities disagree and must not be called
quantitatively validated. No peak shifts or fitted relative intensities are allowed.

## Execution

New remote root: /home/zhuxd/abacus/agent-runs/20260906-one-dimensional-benchmark.
Production source is read-only: /home/zhuxd/abacus/agent-runs/20260905-one-dimensional.
Reuse its frozen Python implementation for solver consistency; all new results go
to the new root. Input and source hashes are retained.

Live assignments: cu23 BN9 Cartesian (PID 258888), cu20 BN9 independent force
(31306), cu25 Sb2S3 Cartesian (132958), cu26 Sb2S3 independent force (121308).
Confirm live state, not these historical PIDs, before attempting recovery.
Prepared SCFs: BN9 61 BEC + 56 force = 117 versus 57 unified;
Sb2S3 31 BEC + 20 force = 51 versus 21 unified.

Completed local work: full BEC exports and species-preserving reference matching;
two manuscript BEC tables (Section 4.5), separate Sb2S3 three-panel figure (Fig. 8),
dataset bibliography entry [51], explicit Raman disagreement discussion, source
index entries, bilingual usage/default-unified/header corrections and example
tensor-convention correction. Existing main three-row spectra/structure figure
was untouched. Current clean PDF compiles (36 pages), inspected BEC and new
spectroscopy pages; no undefined references. A pre-existing 1.9-pt frontmatter
overfull box and author-bookmark warnings remain for final formatting review.
324 package tests pass with Python 3.10/Phonopy 2.21; 21 focused case/publication
tests passed before adding the timing-ledger test. README PDFs regenerated.

Intermediate-state tasks (completed below): complete timed controls and offline reconstruction checks, add final
cost rows to manuscript/abstract and both manuals, package benchmark evidence,
recompile clean/blue versions and recheck reference numbers/figures. Until then
the 20260906 PDF is an intermediate manuscript, not the final submission artifact.

## Completed Sb2S3 matched control

Separate BEC: 31 SCFs, 22.2883751263 ABACUS + 1.4541502750 PYATB core-hours.
Independent phonons: 20 SCFs, 17.9265606769 core-hours. Total 41.6690860783,
versus Unified 18.9450639514: 2.1994693-fold speedup, 54.5345% saving.
No failed calls in either response route. Maximum raw BEC difference 0.00103979 e;
raw Hessian relative difference 4.90762e-5; internal-frequency maximum difference
0.0184333 cm^-1. All-mode maximum 0.769037 cm^-1 is axial rigid rotation:
1.51528 versus 2.28432 cm^-1, each with overlap >0.9997. The 26 internal modes
are independently selected by eigenvectors; none are unstable.

Downloaded `Nanowire_Sb2S3/results/benchmark/` includes 282 hash-verified files
(new inputs, native logs, timing ledgers, tensor observations). The read-only
`verify_one_dimensional_example` command checks these costs against both the
new archive and the original unified ledger. It also reconstructed both production
cases and recalculated both spectra: Sb 685 original evidence files, BN9 2269;
largest tensor error below 3e-14, spectral error below 5e-16. Seven focused
publication tests now pass, including corrupt archive and numerical-shape checks.
At this checkpoint BN9 controls were still running; no extrapolated times entered the manuscript.

## Final measured results and acceptance

BN9 Cartesian BEC finished with 61 SCFs: ABACUS 122.8183901776 + PYATB
17.2331490873 = 140.0515392649 core-hours. Independent phonons finished with
56 SCFs and 130.3623845057 core-hours. Separate total is 270.4139237705,
Unified 125.0352430015: speedup 2.1627016294, successful-core-hour saving 53.7615%.
Its force worker disappeared during stage 43 on cu20, without recording elapsed
time for that call. After confirming no live worker, the partial stage was archived;
42 successes were retained and the remaining 14 completed on cu25. The unrecorded
interruption is disclosed; benchmark totals are not total billed usage.

BN9 maximum raw BEC difference is 0.0002080324 e, raw Hessian relative difference
1.1829184310e-5, internal-frequency maximum difference 0.5143159461 cm^-1. This
occurs on the lowest internal pair near 48 cm^-1. All 104 internal modes remain
positive. Its 624-file benchmark evidence archive passes SHA256 and independent
local reconstruction checks; Sb passes the corresponding 282-file audit.

Both cases include clean run inputs, PP/ORB, VASP-format structures, results,
full tensor exports, native evidence and matched benchmark records. Both have
English/Chinese READMEs and resumable run.sh. The new offline verifier checks
tensors, eigenvectors, spectra, hashes and timing without modifying those files.
The ten-system efficiency CSV/JSON is regenerated with `--include-one-dimensional`.
The command refuses missing/incomplete evidence instead of filling estimated costs.

355 package/research tests pass in a fresh Python 3.10 environment with Phonopy
4.4, numpy 2.2.6 and spglib 2.7; pip check reports no broken requirements. Additional
compatibility suites pass under Phonopy 2.36 and 2.44. A matrix-cache alias in older
Phonopy was handled by requesting the dynamical matrix without overwriting it with
new eigenvectors in the offline verifier. No production response kernel was changed.

Manuscript: Section 4.5, Tables 12/13 show the 1D BECs; Table 14 includes all ten
timed pairs; Figure 8 adds Sb2S3 spectra with dataset Ref. [51]; Appendix B.3
documents independent 1D reconstruction. The abstract range is 2.16--3.98.
Clean and blue revision PDFs compile to 36 pages, with no unresolved references.
New tables/figure, figure placement and appendix pages have been visually checked.
The isolated TeX source package also recompiles to 36 pages. README PDFs refreshed.

Scientific and release boundaries: Sb2S3 relative Raman-intensity agreement is not
claimed, and no associated journal paper is invented for its public dataset.
Gamma stability is not full-dispersion stability. Figure 1 remains unchanged as
reserved by the author; the packaging note flags that author-owned final artwork
check. No GitHub push or PyPI publication is implied by this local source update.
