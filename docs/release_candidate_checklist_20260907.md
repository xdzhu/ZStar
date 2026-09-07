# ZStar Release-Candidate Checklist

This checklist records the coordinated close-out triggered by the annotated CPC manuscript dated 2026-09-07.

## Priority 1: scientific consistency

- [x] Reframe the program summary around the missing unified response workflow; present duplicate work only as a consequence.
- [x] Replace `ensemble` language with `displaced-structure set` or `displacement set` outside statistical-mechanics contexts.
- [x] Describe q-NEP export as BEC-data collection/export, not generic response-data export or high-kappa collection.
- [x] Verify the DFPT and PAW-PBE references used for the VASP benchmark.
- [ ] Keep molecular APT and periodic BEC terminology distinct.

## Priority 2: manuscript structure and presentation

- [x] Remove manuscript-only software version numbers and version-pinned install commands.
- [ ] Keep Table 1 before the Theory section and tighten duplicate capability entries.
- [x] Use full-width Figure 1 and keep figures/tables inside their owning subsections where practical.
- [ ] Expand the short spectroscopy subsection into a coherent six-paragraph discussion.
- [ ] Add captions and context to the mode-activity decision table; reduce its width and avoid unexplained standalone output.
- [x] Rename the section to `Data availability` and update CRediT and acknowledgements exactly as annotated.

## Priority 3: repository and manuals

- [x] Put the approved Figure 1 PDF in the manual figure assets and update both README variants.
- [x] Quarantine superseded manual figure output with an archive note; retain source and historical workflow records.
- [ ] Audit all command examples for line wrapping and the current `zstar backend list` entry point.
- [x] Rename the GitHub repository to match the manuscript title after the local tree is clean; update all links and release metadata. The rename and final push are complete.

## Priority 4: acceptance

- [x] Run the full test suite and clean-environment CLI smoke tests.
- [x] Compile clean and revision manuscripts, render representative pages, and check figures, references, captions, and cross-references.
- [x] Verify the repository tree, README PDFs, and example manifests locally; PyPI metadata remains unchanged because this task updates documentation and repository metadata only.
