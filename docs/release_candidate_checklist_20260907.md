# ZStar Release-Candidate Checklist

This checklist records the coordinated close-out triggered by the annotated CPC manuscript dated 2026-09-07.

## Correction: acceptance is not complete

The previous completion claim is withdrawn. Re-reading the specified PDF found
26 highlights with 26 associated popups, not 27 independent comments. An audit
of the delivered manuscript found 12 requirements satisfied (three were already
satisfied), four partially satisfied, and ten incomplete or unverified.
The remaining work includes paragraph revisions, unbreakable command/software
names, figure placement, the uncaptioned Decision table, and a complete
bibliography rebuild and style check. Passing software tests does not close
these manuscript requirements.

## Priority 1: scientific consistency

- [ ] Finish reframing the program summary: the revision still foregrounds implementation-consistency details.
- [x] Replace `ensemble` language with `displaced-structure set` or `displacement set` outside statistical-mechanics contexts.
- [ ] Remove the remaining high-kappa qualifier from BEC collection; qNEP wording has been corrected.
- [ ] Verify and cite the DFPT and PAW-PBE method references; a VASP software citation alone does not close this item.
- [ ] Keep molecular APT and periodic BEC terminology distinct.

## Priority 2: manuscript structure and presentation

- [x] Remove manuscript-only software version numbers and version-pinned install commands.
- [ ] Keep Table 1 before the Theory section and tighten duplicate capability entries.
- [ ] Figure 1 is full-width; Figures 3, 4 and 9 still precede their subsection headings and need layout correction.
- [ ] Expand the short spectroscopy subsection into a coherent six-paragraph discussion.
- [ ] Add captions and context to the mode-activity decision table; reduce its width and avoid unexplained standalone output.
- [x] Rename the section to `Data availability` and update CRediT and acknowledgements exactly as annotated.

## Priority 3: repository and manuals

- [x] Put the approved Figure 1 PDF in the manual figure assets and update both README variants.
- [x] Quarantine superseded manual figure output with an archive note; retain source and historical workflow records.
- [ ] Audit all command examples for line wrapping and the current `zstar backend list` entry point.
- [x] Restore the repository name to zstar; use the manuscript title only in About. Restore the original links and remote URL.

## Priority 4: acceptance

- [ ] Existing-environment pytest passed 384 tests; this run did not prove clean-environment acceptance.
- [ ] Rebuild both manuscripts from the current bibliography and verify all annotation requirements against rendered pages.
- [ ] Finish manuscript/manual/repository consistency checks after the remaining revisions. No new PyPI release was made.
