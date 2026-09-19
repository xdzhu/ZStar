# Native VASP input decks

`reference/` generates the converged charge density and wavefunctions;
`response/` enables VASP's native `IBRION=6` and `LEPSILON` response. Both
decks use PBE, `NCORE=4`, and no `NPAR` setting.

VASP pseudopotentials are licensed and are therefore not redistributed. Build
the AlN `POTCAR` in each working directory from the PBE library configured at
your site, preserving the `Al N` order used by `POSCAR`. Run `reference` first,
then copy its `CHGCAR` and `WAVECAR` into `response` before launching VASP.
ZStar can collect the native dielectric, BEC, piezoelectric, internal-strain,
and elastic blocks from the completed `OUTCAR`.
