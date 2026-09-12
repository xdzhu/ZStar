# Experimental tetragonal BaTiO3 electromechanical smoke

This directory is a v2 research fixture for a non-centrosymmetric tetragonal
BaTiO3 structure. It is not a validated material benchmark or a stable CLI
example. The input structure is intentionally kept under `inputs/`; ABACUS
outputs and large pseudopotential/orbital files are not committed here.

The structure is used only to test the reference → Berry triplet → branch
matching → raw piezoelectric fit chain. Proper/improper corrections, relaxed-ion
contributions, convergence extrapolation, and independent-backend comparison
remain required before any scientific claim.

`run_relaxed_batch.sh` is an experimental fixed-cell ABACUS runner for the
relaxed-ion stages. It defaults to `40 MPI × 1 OpenMP`, writes per-stage timing
and convergence markers, and uses an atomic `.zstar-stage.lock` so a stage
cannot be started twice. Set `ZSTAR_V2_RUN_ROOT`, `ZSTAR_ABACUS`, and
`ZSTAR_MPI_LAUNCHER` when running outside the shared validation environment.
The runner is not a stable CLI and does not replace the v1 workflow.
