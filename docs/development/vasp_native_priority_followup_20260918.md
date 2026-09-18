# VASP native-first follow-up acceptance

## Scope

Continue the validated native-response implementation on
`codex/vasp-native-response`, based on `0e7c177b`. Do not change the original
checkout, merge the concurrent v2 piezoelectric work, release to PyPI, or edit
the manuscript before the backend integration is agreed.

The design follows native VASP capabilities rather than imposing the
ABACUS + PYATB displacement reconstruction. A native solver remains a native
solver even when it internally uses finite differences.

## Implemented changes

- `zstar bec pre --calculator vasp ... --piezo` requests native relaxed-ion
  piezoelectric `e`, including the Gamma response required for ionic terms.
  It does not request elastic strain calculations. Existing `--phonons`
  continues to collect the same piezoelectric contributions when present.
- `--elastic` supplies complete native elastic response and derived `d`.
  Both options together still generate only reference and native-response
  stages, not two competing response ensembles.
- Native response JSON and common response quantities retain solver
  provenance. Derived `d` is labelled as algebraic conversion of native
  relaxed-ion `e` and `C`; IR is post-processing, and Raman requires additional
  mode-displaced dielectric calculations.
- Missing internal-strain force-balance data cannot silently pass the `d`
  gate. Both piezoelectric contributions are required; an explicitly printed
  total must close to their sum within 1e-4 C/m2. Existing mechanical stability,
  major symmetry and translational-residual checks remain in force.
- Native tensors survive a rejected derivative; the rejection reason is
  preserved. No projection, automatic solver substitution or extra DFT is
  triggered. The conversion solves the linear system rather than explicitly
  forming an inverse.
- English/Chinese native guides, BEC guides, READMEs, the AlN case guide and
  the packaged agent skill explain the native-first routing. Obsolete claims
  that `dfpt` is the default are replaced by the actual `auto` behavior.

## Checks

- 68 focused native-response, AlN and spectroscopy tests passed.
- Full suite: 452 passed, one existing example-layout failure. The failing
  path is `examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/run/input`.
  It was already present before this follow-up; no test was weakened or
  unrelated qNEP data moved to conceal it.
- Built the wheel and installed it without dependencies into the existing
  isolated clean-environment acceptance venv. Imports resolve to site-packages;
  CLI help exposes `--piezo`; the wheel contains neither examples nor POTCAR.
- Clean-wheel AlN selection-rule and SiC compact delivery verifiers passed.
- Packaged skill validation passed.
- On hf, the new parser was checked against the retained raw SiC elastic
  OUTCAR; the derived `d` agrees with the accepted record to 1e-10 pm/V.
- On hf, `--piezo` preparation from the actual relaxed AlN inputs succeeded.
  Both generated stages also passed the executor dry-run. This is a CLI/route
  smoke check, not an additional DFT validation claim.
- On hf, the entire AlN runner completed with `VASP_COMMAND=false` and
  `MPI_TASKS=64`. Reference, DFPT, elastic and all 18 Raman displacement stages
  were reused; response and selection-rule checks passed without a new VASP
  invocation. Refreshed native/common JSON records retain the accepted values:
  e31=-0.58162 and e33=1.46150 C/m2, d33=5.324396 pm/V. DFPT warnings remain.

## Capability boundaries

AlN and SiC PBE PAW provide bulk end-to-end evidence. The native DFPT
internal-strain warnings in those test settings remain visible; they do not
establish a general failure of native VASP piezoelectric calculations.
Hybrid/meta-GGA route selection is tested but is not equivalent to new
end-to-end functional validation. Low-dimensional tensors remain labelled as
periodic-supercell responses, with the existing 2D spectroscopy guard retained.
The current workflow does not automatically calculate a VASP LOPTICS curve;
the optical-constants command consumes supplied real/imaginary response data.
The new option does not claim a formal merged v2 piezoelectric command family.

## Primary sources

- [LEPSILON](https://vasp.at/wiki/LEPSILON): native electric dielectric, BEC
  and clamped-ion piezoelectric response.
- [DFPT phonons](https://vasp.at/wiki/Phonons_from_density-functional-perturbation_theory):
  Gamma response, internal strain, and absence of the clamped elastic strain
  perturbation.
- [Native finite differences](https://vasp.at/wiki/Phonons_from_finite_differences):
  `IBRION=6, ISIF>=3` complete elastic response.
