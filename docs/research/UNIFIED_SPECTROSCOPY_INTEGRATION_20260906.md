# Unified spectroscopy integration plan

- [done] Promote validated rank-three response reconstruction, dimensional
  conventions and mode selection into the public package. Keep the canonical
  spectra lifecycle; support reusable BEC ensembles and explicit mode-FD fallback.
- [done] Complete a matched 40-core HfO2 mode-Raman control on cu23--cu26.
  Reuse MoS2/Sb2S3/CH4 evidence. Do not modify source matrices or density cubes.
- [done] Test preparation, resumable execution, input/source integrity,
  legacy/new PYATB static writers, status, postprocessing and job headers.
- [done] Add reproducible Unified spectra cases and English/Chinese manuals.
- [done] Extend the theory and implementation descriptions; move Efficiency
  benchmark of ZStar after spectroscopy and add the four-case spectroscopy cost table.
- [done] Restore Figure 2 from the retained pre-redraw original. Edit a copy
  of the specified Figure 1 PPTX, preserving its design and editable elements.
- [done] Rebuild clean/revised PDFs, check floats/citations/figure labels,
  run regression and packaged-case tests, and report residual limitations.

Final evidence: docs/research/unified_spectroscopy_20260906/QA.md and
integration_checksums.json. Current work is local; no new package/repository
release was performed. Measured IR+Raman speedups: HfO2 5.65, MoS2 3.39,
Sb2S3 3.68, CH4 8.35. Public CH4 execution and resume, four offline case
scripts, 388 tests and 66 subtests passed.

Scope: static nonresonant Placzek Raman and Gamma IR. Not resonant Raman or
full phonon dispersion. HfO2 supplementary controls are required for matching
the timing configuration, not a replacement for completed physical results.
