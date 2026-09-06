# September 7 manuscript annotation revision

Source: `zstar_CPC-clean-0907-anooted.pdf`, 37 pages.
SHA256: `d4cc342469ec849dcf98f6725778b28bf3a4392b871d877f328ca8f56e58d61b`.
Extraction: 16 highlights with comments, 16 associated popup objects, and
287 navigation links. Popups are not additional comments.

## Locked conventions

- Separate names the old workflow; Unified names the new workflow.
- Cartesian retains its mathematical meaning, not a workflow name.
- Preserve the author-approved abstract verbatim and the approved figure layouts.
- PYATB is uppercase; atom indices use kappa; phonon response uses ph.
- No additional DFT studies or new capabilities are required by these annotations.

## Ordered Checklist

- [x] Extract all 16 annotations, selections, page numbers, and PDF object IDs.
- [x] Independently compare rich-text comments with the primary extraction.
- [x] A01: shorten the Table 1 family name to Dielectric.
- [x] A02-A05: cite Phonopy, ABACUS, PYATB, CP2K, and Quantum ESPRESSO where their roles are described; audit other named dependencies.
- [x] A06: condense independent/subsequent workflow instructions.
- [x] A07: condense numerical checks, preserving scientific applicability limits.
- [x] A08: name the old workflow Separate in prose and tables.
- [x] A09: cite every structure/physical-picture/dielectric subpanel in the body.
- [x] A10: widen the first column of the In2Se3 table (original Table 9).
- [x] A11: remove unnecessary caption implementation detail throughout.
- [x] A12: remove (cube) from molecular-table software names.
- [x] A13: exactly six spectroscopy paragraphs, ordered introduction, Bulk, Slab, Nanowire, Molecule, conclusion; cite panels a-l explicitly.
- [x] A14: condense efficiency discussion; retain measured-baseline limitations and verification.
- [x] A15: make both efficiency tables span the text width without changing data.
- [x] A16: cite all six potential panels explicitly.
- [x] Self-audit introduction, summary, current commands, output names, and appendix relevance.
- [x] Verify citation metadata and regenerate plot reference numbers from the final bibliography.
- [x] Compile revised and clean PDFs; inspect changed pages and whole-document layout.
- [x] Recheck approved abstract, numerical tables, references, and annotation closure.

## Release Follow-through

The author additionally requests GitHub and PyPI updates. Inspect existing
uncommitted work, current remote versions, tests, packaging boundaries, and
release credentials before publishing. GitHub includes curated examples;
PyPI excludes examples and build artifacts. Do not publish an untested package
or mistake the local 0.3.0rc6 snapshot for an already published release.

## Evidence Locations

Annotation JSON/Markdown and pre-edit backups are under
`D:/Work/Zstar/zstar-article/review_20260907/`.
The independent PDF-object check agrees with all 16 extracted comments. The
clean and revised manuscripts compile to 35 pages. The approved abstract and
both efficiency tables are unchanged; all required subpanels are cited in the
body and the spectroscopy section has the requested six paragraphs.

Five missing software references were added (CP2K, NumPy, SciPy, Matplotlib,
pymatgen); existing Phonopy, ABACUS, PYATB and QE papers are now cited where
used. All 71 cited records have DOI and URL fields. Crossref metadata was
retrieved for 70 records, with DataCite used for the Sb2S3 dataset. This is an
identity/metadata audit, not a claim to have newly read every full article.

Numerical and timing details displaced from the body are retained in Appendix
B, including the Separate-baseline limitations, Sb2S3 Raman-intensity mismatch,
and cross-backend comparison settings. No additional DFT calculations were
performed. Spectroscopy references were regenerated from bibliography keys;
the structure column is pixel-identical to the approved version.

The final manuscript audit reports no unresolved references or citations.
A non-clipping 1.9-pt elsarticle front-matter box warning remains in TeX Live
2023. The whole-document contact sheets and changed pages were visually checked.
Figure 1 remains subject to the author's previously planned final graphic review.
See RELEASE_ACCEPTANCE_20260907.md for package validation and publishing scope.
