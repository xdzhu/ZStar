# VASP native response: separate structural and solver symmetry tolerances

Date: 2026-09-19

## Decision

- Keep the v2 spglib/Phonopy structural identification and atom-mapping
  tolerance at `symprec=1e-3 Angstrom`.
- Do not transfer that value to VASP's dimensionless `SYMPREC` tag.
- For native ionic response, keep VASP's default when the source omits
  `SYMPREC`, preserve explicit values at or below `1e-4`, and cap looser
  inherited values at `1e-4` in both the reference and response INCAR files.
- Record the source value, effective value, policy, and any override in
  `vasp_bec_manifest.json`.

## Reproduction

The exact serialized `eta_4=-0.005` GaN and ZnO structures were held fixed.
INCAR, KPOINTS, POSCAR, POTCAR, VASP 6.3.2, and `32 MPI x 1 OMP` were identical
except for `SYMPREC`.

| Material | `SYMPREC=1e-3` | `SYMPREC=1e-4` | HF jobs |
|---|---|---|---|
| ZnO | Failed during initialization: crystalline base-centered monoclinic versus reciprocal simple monoclinic | Passed lattice initialization and entered electronic SCF | failed `27723123`; control `27723238` |
| GaN | Same Bravais mismatch | Passed lattice initialization and entered electronic SCF | failed `27723146`; control `27723258` |

The control jobs were deliberately cancelled immediately after the relevant
initialization gate; they were diagnostics, not production relaxation results.
Their combined allocation was approximately 1.39 rank-wall core-hours.

The result means the former VASP value was too loose and admitted an
inconsistent approximate lattice classification. It does not alter the fixed
spglib/Phonopy structural tolerance.

## Regression coverage

`tests/test_vasp_native_response.py` checks loose-value capping, preservation
of VASP's absent/default setting and explicit tighter settings, manifest
provenance, and rejection of invalid values. The focused native VASP suite
passed `76` tests after this change.
