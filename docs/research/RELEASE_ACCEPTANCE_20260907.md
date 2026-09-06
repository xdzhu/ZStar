# ZStar 0.3.1 release acceptance

Date: 2026-09-07. This stable release incorporates the previously validated
Unified BEC/phonon/spectroscopy implementation and the September 7 manuscript
annotation review. No new DFT calculations were launched for this acceptance.

## Linux release gate

After the 0.3.0 upload, GitHub Linux CI found two example-layout failures:
the index stored `examples/3d_bulk` while the manifest specified `3D_Bulk`.
Windows accepted that spelling mismatch. Version 0.3.1 corrects the Git-index
directory name and adds a case-sensitive manifest/index regression test.
Runtime numerical code and retained results are unchanged. The original
0.3.0 tag and PyPI artifacts are not rewritten. The Windows and offline
checks below concern the 0.3.0 wheel; 0.3.1 receives a fresh Linux CI gate.

## Independent installation

- Python 3.10 environments were created without system site packages.
- Phonopy 4.4.0: 476 tests and 66 subtests pass, including repository tools.
- Phonopy 2.36.0: 383 runtime tests and 66 subtests pass.
- All 50 imported ZStar modules are verified to originate from the installed
  wheel, not the checkout. Thirty installed CLI checks pass; pip check passes.
- All 40 indexed example launchers pass their documented dry run in a separate
  source snapshot with Git Bash. The first Windows attempt selected WSL Bash,
  which could not see the Windows-installed executable; explicitly selecting
  Git Bash fixes this environment mismatch. Dry runs are not DFT validation.
- Earlier Linux execution, restart and retained-spectrum reproduction evidence
  remains in RELEASE_ACCEPTANCE_20260906.md; it is not relabeled as a new run.
- The installed 0.3.0 wheel reproduces the four retained Unified spectroscopy
  examples (HfO2, MoS2, Sb2S3, CH4) offline. All 14 comparable spectrum/response
  arrays agree exactly at the stored output precision; no DFT call is made.

## Manuscript and documentation

All 16 PDF comments are independently reconciled and closed in
ANNOTATED_REVISION_20260907.md. The approved abstract and benchmark data remain
unchanged. Both 35-page manuscript PDFs compile without unresolved references.
All 71 cited records have DOI/URL metadata; spectroscopy reference labels were
regenerated without changing approved structure images or plotting geometry.
English and Chinese README PDFs were regenerated. The PyPI description uses
public image URLs pinned to the release tag rather than local or private-repository paths.

## Distribution and publishing

GitHub carries the curated input/result examples and their run.sh launchers.
The wheel contains runtime modules and the Agent Skill; the source distribution
includes documentation but excludes examples. Neither distribution includes
dist build directories. Build products are kept outside the Git checkout.

The v0.3.1 tag triggers the tested GitHub release workflow. It builds wheel and
source archives and combines the versioned CHANGELOG entry with automatically
generated GitHub notes. PyPI publishing is a separate authenticated upload;
a local successful build alone does not establish remote publication.

Machine-local build hashes, test XML, import provenance, package membership and
remote publication receipts are retained under
`D:/Work/Zstar/release_acceptance_20260907/`. The tagged tree is the immutable
source reference. This document records acceptance scope rather than embedding
a self-referential commit hash.

## Author actions

The author retains final approval of Figure 1 and the journal/arXiv submission
forms. The Sb2S3 relative Raman-intensity difference remains explicitly reported;
publication does not imply agreement where the retained data do not show it.
