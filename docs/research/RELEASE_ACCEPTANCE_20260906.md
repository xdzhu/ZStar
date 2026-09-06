# Release candidate acceptance

Scope: validate the existing Unified automation framework as a reviewer would
receive it. Do not add materials or research features. arXiv endorsement is
complete; author submission and final Figure 1 approval remain author actions.

## Ordered gates

- [complete] Independent wheel build and clean installation outside the
  checkout. Exercise all canonical CLI families and record dependency versions.
- [complete] Run retained-data reproductions, compare numerical outputs, and test
  preparation/restart/error handling from the distributed examples and manuals.
- [complete] Check every indexed example's reproduction level, assets and
  run/results contract. Correct claims that overstate end-to-end reproduction.
- [complete] Verify one short public workflow on the allocated cluster using the
  candidate package, without overwriting retained results or repeating benchmarks.
- [complete] Align bilingual documentation, skill, and manuscript around Unified
  efficient and accurate automation; keep backend interoperability secondary.
- [complete] Revise Figure 1 from the supplied editable deck and add a second page
  of editable optional scientific diagrams. Preserve accepted other figures.
- [complete] Rebuild matching packages, source/examples archive, manuals and clean
  manuscript. Check archive integrity, install from the final package, and repeat
  smoke tests before declaring acceptance.

## Evidence rules

- Separate current runs from historical verification records.
- Record exact test commands and environments, not an aggregate of unlike suites.
- Distinguish full DFT reruns, offline reconstruction and supplied-result viewing.
- Do not claim all backends implement the ABACUS + PYATB Unified ensemble.
- Benchmark speedups retain the measured baseline and accounting qualifications.
- Do not release incomplete artifacts or include licensed/private solver data.

## Working artifacts

Independent acceptance workspace: `D:/Work/Zstar/release_acceptance_20260906`.
The delivered archive includes per-file SHA256 verification and an outer checksum.
It is a local release candidate, not a published Git tag.

## Verified evidence

| Gate | Current evidence |
|---|---|
| Independent installation | Python 3.10.9 venvs with system site packages disabled; no editable ZStar installation |
| Installed package tests | 383 tests + 66 subtests with each of Phonopy 2.36.0 and 4.4.0; 50 imported ZStar modules verified under site-packages |
| Extended research tests | 476 tests + 66 subtests with Phonopy 4.4.0 after adding optional ASE; includes the package tests, not an additional 476 tests |
| CLI | 30 installed-package commands: lifecycle help, configuration, adapters and skill discovery |
| Public launchers | 40/40 indexed dry runs from a separate Linux archive with no source ZStar directory |
| Offline spectra | 16 arrays across HfO2, MoS2, Sb2S3 and CH4; maximum absolute difference 1.333e-15 against retained arrays |
| Actual DFT workflow | CH4 on cu23, ABACUS 3.10.0-LTS, PBE, scf_thr=1e-8; reference + 3 displacement SCFs; forces, polarization, Gamma modes, IR and static nonresonant Raman completed |
| Restart | All four SCF and polarization stages skipped on repeat; three displacements used the reference charge density |
| Independent CH4 result | Maximum internal-mode frequency difference 8.573e-7 cm^-1; maximum normalized powder Raman activity difference 3.864e-6 relative to the retained matched reference |
| Manuscript | Clean/revised PDF text matches; 64 bibliography entries; no unresolved citation/reference errors |
| Artwork | Figure 1 native editable PPTX has two slides; slide 2 provides symmetry, response, mode-projection and measured-cost assets; other accepted figure files preserved |
| Delivery isolation | Trial archive extracted, all 6475 payload hashes verified, its wheel reinstalled and 30 commands rerun; standalone manuscript compiled to identical 37-page text |

Offline roundoff-level agreement validates reconstruction from identical inputs,
not independent electronic-structure accuracy. The separate methane run provides
the end-to-end solver check. Degenerate-mode tensors may rotate within their
subspaces; powder activities, not individual tensor entries, are compared.

The remote environment installs this wheel privately but uses the configured
icu_copy solver dependencies. It is not claimed to be a clean dependency install;
the two Windows venvs provide that check. Research-only structure generators
add ASE through `tools/requirements-research-tests.txt`; ASE is not a core wheel
dependency or a requirement of the four offline spectroscopy reconstructions.

## Defects found and corrected

1. File-only spectrum exports attempted to initialize Tk. They now use explicit
   noninteractive Figure objects, with a regression that forbids GUI creation.
2. Matrix-export templates retained gamma_only=1, rejected by ABACUS. Generated
   PYATB SCF inputs now ensure gamma_only=0 and both required matrix exports;
   the source INPUT is unchanged.
3. A PYATB launcher using another interpreter imported that environment's older
   ZStar. It now executes the current installed standalone precision adapter.
4. Shell helper execution depended on archive execute bits. Helpers are invoked
   through bash explicitly; Linux extraction was tested without chmod fixes.
5. Some public 1D scripts preferred source PYTHONPATH over the installed wheel.
   Those overrides were removed; repository-only helper imports remain scoped.
6. CH4 spectroscopy rerun geometry differed from the matched Unified reference.
   The old inputs are preserved in legacy/; the active inputs now match.
7. Current validation documentation still used older version/test counts. Current
   evidence is now separated from historical records; the paper directory tree
   is kept together across page boundaries.

The first fresh CH4 PYATB attempt failed before the adapter repair. Its failure
record is retained; the successful continuation reused the completed reference
SCF. No earlier benchmark timings or scientific reference arrays were rewritten.

## Scope and author actions

- The primary validated Unified route is ABACUS + PYATB. Other backend parsing,
  routing and conventions have regression coverage and retained examples; this
  acceptance does not claim new full VASP/CP2K/QE DFT reruns.
- Example readiness has three levels: electronic-structure rerun, offline
  reconstruction, and supplied-result analysis. Potential cases requiring an
  external cube are identified explicitly; they are not full DFT reruns.
- The wheel/sdist exclude examples. The complete review delivery includes them.
  VASP POTCAR, private NbSe2 data and external solver binaries are excluded.
- Figure 1 awaits the author's final editing/approval. Confirm author metadata,
  final release tag and archive destination before public submission. arXiv
  endorsement is already complete. No tag, PyPI upload or submission is implied
  by the local candidate package.
- Numerical kernels, accepted literature peak positions and benchmark accounting
  were not changed to improve visual agreement. This is release acceptance, not
  a new convergence study or another complete DOI/full-text literature audit.
- TeX Live 2023 retains benign elsarticle frontmatter metadata warnings and a
  1.9-pt output-box warning. Inspected pages show no corresponding clipping;
  older Phonopy also emits spglib deprecation warnings without test failures.
- One expanded Windows test run encountered a temporary-file replacement
  PermissionError; the complete rerun passed 476 tests. Its cause was not
  established and no numerical code was changed in response. The separate
  native Linux solver run and both package-only test runs passed.

## Repeat the acceptance

Create a venv, install the supplied wheel plus pytest/pytest-subtests, and run
the following with that environment's Python. Use `-I` to exclude ambient
PYTHONPATH and verify the module provenance recorded by the harness.

```bash
python -I source/tools/release_acceptance.py smoke --output smoke
python -I source/tools/release_acceptance.py tests --repo source --output tests
python -m pip install -r source/tools/requirements-research-tests.txt
python -I source/tools/release_acceptance.py tests --repo source --include-tools --output extended-tests
```

The CI build and tag-release workflows now gate artifact publication on an
independent wheel installation. The local workflow files are prepared; no
remote Actions run is asserted until the source is committed and pushed.
