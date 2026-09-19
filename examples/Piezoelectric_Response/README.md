# Piezoelectric response examples

These bulk examples exercise the finite-strain ABACUS + PYATB route and an
independent native VASP route under the same PBE functional.  The public set is
deliberately limited to the two clearest completed comparisons:

| Case | Role | ABACUS / VASP agreement |
| --- | --- | --- |
| [Wurtzite AlN](AlN) | Primary external benchmark against the de Jong PBE dataset | full `e`, `C`, and `d` tensors retained |
| [Wurtzite ZnO](ZnO) | Second polar 6mm benchmark with a larger strain response | full `e`, `C`, and `d` tensors retained |

Each directory contains clean ABACUS inputs and redistributable assets in
`run/`, native VASP input decks without licensed `POTCAR` files in `run/vasp/`,
archived machine-readable results in `results/`, a case-level README, and
`run.sh`.  The ABACUS calculation uses one reference plus explicit `+-0.5%`
engineering strains in six Voigt directions: 13 ABACUS calculations and 13
PYATB polarization evaluations.  The written cell matrices are used to recover
the actual strain vectors before fitting proper `e`, relaxed-ion `C`, and
`d = e C^-1`.

Run `./run.sh check` first to validate the archive without a DFT calculation.
`prepare`, `run`, `status`, and `collect` reproduce the ABACUS + PYATB route.
The direct runner honors `ZSTAR_MPI_RANKS`, `ZSTAR_OMP_THREADS`,
`ZSTAR_ABACUS`, `ZSTAR_MPI_LAUNCHER`, `ZSTAR_PYATB_INPUT`, and
`ZSTAR_PYTHON`; scheduler headers and module commands remain site-specific.

GaN is retained in the research audit because its completed cross-backend
tensor difference is larger.  Tetragonal PbTiO3 remains conditional because
the two completed VASP routes disagree in `d33` by 18.4%.  The incomplete PZT
ensemble is not promoted into this public example set.
