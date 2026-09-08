# Point-Group IR and Raman Activity Validation

## Scope

ZStar classifies zone-center modes using the 32 crystallographic point groups.
This record documents the independent audit of the activity table implemented
in `zstar/group_modesDB.py` and reproduced in Table D.1 of the ZStar paper.

The table describes symmetry-allowed species, not the number of modes in a
particular structure. Mode multiplicities must first be obtained from the
mechanical representation of that structure.

## Authoritative basis

The primary reference is the
[POINT service of the Bilbao Crystallographic Server](https://www.cryst.ehu.eus/rep/point.html),
which publishes character tables, representation decompositions, and IR/Raman
selection rules for all 32 crystallographic point groups:

- M. I. Aroyo, A. Kirov, C. Capillas, J. M. Perez-Mato, and
  H. Wondratschek, *Bilbao Crystallographic Server. II. Representations of
  crystallographic point groups and space groups*, Acta Crystallographica A
  **62**, 115-128 (2006),
  [doi:10.1107/S0108767305040286](https://doi.org/10.1107/S0108767305040286).

The spectroscopic interpretation was checked against:

- D. L. Rousseau, R. P. Bauman, and S. P. S. Porto, *Normal mode
  determination in crystals*, Journal of Raman Spectroscopy **10**, 253-290
  (1981),
  [doi:10.1002/jrs.1250100152](https://doi.org/10.1002/jrs.1250100152).
- *International Tables for Crystallography*, Vol. D, Sec. 2.3.3,
  [First-order scattering by phonons](https://onlinelibrary.wiley.com/iucr/itc/Db/ch2o3v0001/sec2o3o3/).

## Selection rules used by ZStar

For electric-dipole infrared activity, the mode irrep must occur in the polar
vector representation `V`. For the static, nonresonant Raman treatment
implemented by ZStar, the mode irrep must occur in the symmetric square
`[V^2]`, corresponding to a symmetric polarizability derivative.

This scope does not include resonant or magnetic Raman processes in which
antisymmetric tensor components may contribute.

## Audit procedure and result

On 2026-09-08, the `V` and `[V^2]` decompositions were extracted independently
from every Bilbao POINT page and compared with the ZStar registry. The paper
table was then compared separately with the registry.

| Crystal system | Point groups checked | Bilbao vs. registry | Paper vs. registry |
| --- | ---: | ---: | ---: |
| Triclinic | 2 | 2/2 | 2/2 |
| Monoclinic | 3 | 3/3 | 3/3 |
| Orthorhombic | 3 | 3/3 | 3/3 |
| Tetragonal | 7 | 7/7 | 7/7 |
| Trigonal | 5 | 5/5 | 5/5 |
| Hexagonal | 7 | 7/7 | 7/7 |
| Cubic | 5 | 5/5 | 5/5 |
| **Total** | **32** | **32/32** | **32/32** |

No discrepancy was found in the listed IR-active or Raman-active species.

## Notation conventions

- Bilbao uses `C3i` for the crystallographic point group `-3`; `S6` is an
  equivalent Schoenflies name. Documentation should write `C3i (S6)` where
  both communities are addressed.
- Bilbao resolves complex-conjugate species such as `1E` and `2E`. ZStar
  combines each conjugate pair into the conventional real, doubly degenerate
  `E` notation used in vibrational spectroscopy.
- In centrosymmetric groups, electric-dipole IR-active species have odd parity
  and first-order symmetric Raman-active species have even parity. Parity is a
  necessary condition, not a statement that every `u` or `g` species is active.

## Runtime safeguards

Phonopy can emit a null `ir_label` when a mode manifold is not resolved at the
selected symmetry tolerance. ZStar reports such non-acoustic modes as
`Unresolved`; it does not infer that they are silent. A mode is reported as
`Silent` only when its recognized irrep belongs to the point group but occurs
in neither activity set.

The offline, source-anchored regression snapshot is tested with:

```bash
pytest tests/test_point_group_activity.py
```

This test checks all 32 point groups, retention of genuinely silent species,
and the null-label safeguard. The authoritative URLs and DOI are also exposed
as metadata in `zstar.group_modesDB`.
