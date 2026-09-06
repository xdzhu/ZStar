# Annotated manuscript revision, 2026-09-04

This local source candidate is **0.3.0rc3**, based on commit
`8eba5cb645acbedcd093f964d1723ef44b202a5d`. It has not been committed, tagged,
or published. Older rc2 reports remain historical records, not the current
independent-workflow timing definition.

## Evidence added

- Thirty independent force SCFs completed on cu20/cu23/cu24/cu25 with one MPI
  rank and 40 OpenMP threads. The new archived results are under
  `examples/Shared_Response/independent_phonons/`, with 200 hashed source files.
- `separate_unified_efficiency.json` and `.csv` combine measured solver times
  for eight systems. Speedups range from 2.37 to 3.98. Seven retained BEC
  baselines already requested force output; this overhead was not subtracted.
  The separate force stages, not those old BEC forces, supply Separate phonons.
- `appendix_data_audit_20260904.json` records molecular APT tensors, actual
  In2Se3 layer ordering, hBN values, MoS2 offline response, and source hashes.
- The MoS2 spectroscopy case now retains the matching original BEC evidence,
  exact paper phonon inputs, and dielectric curves. It is distinct from the
  older `2d_materials/MoS2` quick-start result.

## Software and manuscript alignment

New files use `bec.dat`, `bec.raw.dat`, `bec.rep.dat`, `bec.rep.raw.dat`,
`response.json`, `response_fit.json`, `force_fit.json`, and `apt.json`.
`BORN` remains the Phonopy name; the redundant long BORN copy is no longer
written. Readers accept old archived names without modifying those archives.
Tensor orientation is unchanged and tested with nonsymmetric tensors.

The manuscript distinguishes production mode sums from research Hessian
cross-checks, clarifies response units, adds the PBE In2Se3 data, updates the
independent-workflow efficiency table and appendix, and redraws only Figure 8.
The other author-arranged figures are preserved. Figure 1 is still deferred
to the author and must be updated before actual submission.

## Verification

- 324 package tests pass with Phonopy 2.36 and independently with 4.4.
- 50 research-tool tests pass; 14 retained reconstruction variants pass the
  offline archive verifier.
- The installed wheel reproduces the archived MoS2 static sheet-response
  tensor from its documented offline command.
- The wheel and source distribution pass `twine check`; neither contains
  `examples/`. The separately supplied full-source snapshot does.
- English and Chinese README PDFs were regenerated. Clean and blue manuscript
  PDFs compile; the 25 annotation resolutions and appendix audit are retained
  with the manuscript, outside this software repository.

No new experimental spectra, altered reference frequencies, new software
physics claims, or public releases were introduced by this revision.
