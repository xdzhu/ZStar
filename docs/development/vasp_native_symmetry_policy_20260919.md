# VASP native-response symmetry policy correction

## Finding

VASP does not require `ISYM=-1` for native piezoelectric response. The official
`IBRION` documentation defines `IBRION=6` and `IBRION=8` as the finite-difference
and perturbative routes *with symmetry* and strongly recommends them over the
corresponding no-symmetry routes `IBRION=5` and `IBRION=7`. With `ISIF>=3`, the
finite-difference route also supplies elastic and internal-strain tensors; with
`LEPSILON` or `LCALCEPS`, it supplies the electric and piezoelectric response.

The previous development implementation hard-coded `ISYM=0` and `NCORE=4` in
both reference and response stages. That was an engineering workaround for a
VASP 6.3.2 k-point redistribution failure, not a physical or documented VASP
requirement. It disabled the symmetry reduction that the native solver was
intended to use.

Primary sources:

- [VASP IBRION](https://vasp.at/wiki/IBRION)
- [VASP ISYM](https://vasp.at/wiki/ISYM)
- [VASP finite-difference phonons and elastic response](https://vasp.at/wiki/Phonons_from_finite_differences)
- [VASP LEPSILON](https://vasp.at/wiki/LEPSILON)

## Corrected contract

- Native ionic response (`--phonons`, `--piezo`, or `--elastic`) preserves an
  input `ISYM=1/2/3`; otherwise it records an override and uses `ISYM=2`.
- Reference and response stages use the same enabled `ISYM` value.
- These stages use `NCORE=1` and remove `NPAR`, avoiding the observed VASP 6.3.2
  symmetry/k-point redistribution incompatibility without disabling symmetry.
- Pure electronic `LEPSILON`/`LCALCEPS` calculations do not require the ionic
  symmetry policy and retain the source or VASP-default settings.
- The manifest records source/selected `ISYM`, policy, and any symmetry or
  parallelization override.

## Verification

- Focused native/VASP tests: 93 passed.
- Full suite excluding the pre-existing example-layout regression: 456 passed,
  1 deselected.
- The unchanged pre-existing failure is
  `tests/test_examples_layout.py::test_legacy_case_layout_is_not_reintroduced`,
  caused by `examples/ML_Force_Fields_with_Charges/Cubic_BaTiO3/run/input`.

The input contract is now covered, but numerical acceptance still requires a
real VASP `IBRION=6, ISIF=3, LEPSILON=.TRUE., ISYM=2` comparison against the
retained no-symmetry result before the new route is promoted as production
validated.
