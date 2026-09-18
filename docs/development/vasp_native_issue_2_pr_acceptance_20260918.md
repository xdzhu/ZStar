# VASP Native Response: Issue 2 PR Acceptance

## Scope

PR branch: `codex/vasp-native-issue-2`, based on `origin/main` at `6bc7b0d2`.
Only the native-response commits `0e7c177b` and `bbaf059a` were transplanted
from the development branch. The unrelated qNEP snapshot and the active v2
research worktree are not included or modified.

The implementation and retained 3C-SiC/AlN calculations address the native
interface and result-comparison items in [issue 2](https://github.com/xdzhu/ZStar/issues/2).
Slurm accounting is retained, but a matched cross-backend efficiency benchmark
is not claimed; this issue item remains a follow-up.

## Additional Review Fixes

- Reject incomplete or empty OUTCAR tensor blocks at their boundaries instead
  of borrowing rows from a following native-response block.
- Keep reused XML mode sources inside the new reference cache, using a
  workspace-relative path. A regression relocates both workspaces and collects
  IR without depending on the original response location.
- Check nonsymmetric off-diagonal BEC components in a triclinic structure,
  through both Phonopy's BORN reader and ZStar's internal tensor convention.
- Explain both `--response` and `--modes-xml` when a VASP mode source is missing.
- Test base and VASP-extra installations in CI for Phonopy 2.36.0 and 4.4.0.
  Optional XML tests skip only in the base profile; the VASP profile runs them.
- Locate existing NAC-test fixture data relative to the test file rather than
  the process working directory. Assertions and the phonon algorithm are unchanged.
- Replace branch-handoff wording in the bilingual user guides with source
  installation instructions and the actual validated scope.

## Local Verification

All environments were created on the E drive, without upgrading the user's
existing Python environment. Python 3.10, NumPy 2.2.6 and spglib 2.7.0 were used.

| Installation / dependency profile | Result |
| --- | --- |
| Source checkout, VASP extras, Phonopy 4.4.0 | 467 tests and 99 subtests passed |
| Independently installed wheel, VASP extras, Phonopy 4.4.0 | 467 tests and 99 subtests passed |
| Independently installed base wheel, Phonopy 4.5.0, no pymatgen | 460 tests passed, 7 optional tests skipped, 99 subtests passed |
| Independently installed wheel CLI smoke checks | 30 commands passed |
| Phonopy 2.36.0 compatibility run before final parser/CLI hardening | 464 tests and 99 subtests passed; final branch is covered by the CI matrix |
| Retained 3C-SiC response and Raman checks | Passed |
| Retained AlN spectral selection rules and mode numbering | Passed |

The installed-wheel suites ran outside the checkout using `python -I` and
`tools/release_acceptance.py`. Imported ZStar modules were verified to come
from the environment's `site-packages`, not the source directory; the native
response and spectroscopy modules also matched the final source text.
Remaining warnings are dependency deprecations, not failed scientific checks.

Both wheel and source distribution were built using the declared
`setuptools>=77` backend requirements. They include `zstar/vasp_response.py`
and exclude `examples/` and licensed POTCAR files. Distribution archives and
test logs are local acceptance artifacts, not Git inputs.

## Scientific Boundaries

Native electric DFPT is preferred for LDA/GGA. Complete elastic response uses
VASP's native strain finite differences; Raman still requires displaced-mode
dielectric derivatives. Failed native internal-strain checks retain raw tensors
and warnings, and prevent unsupported derived `d` from surviving recollection.
No symmetry projection is silently applied to the native electromechanical tensors.

The actual DFT calculations were already completed on hf and are documented in
the [original native acceptance record](vasp_native_response_validation_20260918.md)
and [AlN validation record](vasp_native_AlN_validation_20260918.md).
This PR review reused those results; it did not launch duplicate DFT jobs.
The two bulk PBE examples do not establish arbitrary-functional convergence,
intrinsic low-dimensional VASP conversion, or directional NAC validation.
The existing 2D spectroscopy guard is retained.

No automatic main merge, package-version bump, PyPI upload or manuscript edit
is part of this PR.
