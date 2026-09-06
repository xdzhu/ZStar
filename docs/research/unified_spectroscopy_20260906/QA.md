# Integration verification record

- The four Unified and Cartesian static-response ensembles are complete.
- HfO2 matched direct control completed on cu23--cu26: 30 SCFs, 30 PYATB stages;
  all four workers report unchanged source hashes. Legacy 20-MPI costs are excluded.
- MoS2/CH4 matched controls and the Sb2S3 retained control were reused.
- Absolute tensor/activity comparisons and independent IR frequency checks pass;
  see summary.json for actual differences, not assumed identical results.
- Public reconstruction covers all 32 crystallographic point groups in tests.
- Public pre/run/post/stat completed on cu26 for CH4; a second invocation reused
  all completed static stages. Its atomic derivatives differ from the validated
  prototype by at most 3.47e-18 /angstrom.
- Four packaged run.sh --post-only checks completed on cu26 without DFT/PYATB.
  Their source observations are hash checked and outputs written outside results.
- Regression: 388 tests and 66 subtests passed, including four real-data public
  postprocessing cases, canonical preparation/job routing, source mutation,
  worker-lock cleanup, missing band gate and legacy/direct-static precision.
- Shell syntax checks passed for the common runner and Sb2S3 wrapper.
- Matrices and assets are private copies. No density cube symlink was introduced.
- Both clean and blue-revision manuscript PDFs compile (37 pages).
- Efficiency is Section 4.8, after spectroscopy; Tables 14 and 15 are adjacent.
- No undefined citations/references or body/table overfull boxes. The retained
  frontmatter output routine emits a 1.9-pt warning; visual body pages are clear.
- All 64 bibliography numbers match the figure citation map; no figure relabeling
  or changes to the accepted spectroscopy/structure layouts were required.
- Figure 2 is byte-identical to the retained pre-redraw PDF. Figure 1 edits the
  specified 20260905 PPTX; native PowerPoint export and editable-package checks pass.
- Theory, dimensions/units, benchmark counts and clean PDF pages were reviewed.
- Costs are assembled measured components, not a repeated-run timing distribution,
  nor total billed usage including failed trials and software-integration tests.
- Current work is a local source snapshot; no new GitHub/PyPI release was made.
