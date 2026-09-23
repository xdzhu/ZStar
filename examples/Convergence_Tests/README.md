# Convergence tests

These examples keep numerical-convergence checks separate from the main
scientific demonstrations. They use the same public inputs and the canonical
Unified BEC/Gamma workflow as the production examples.

- `SiC_Displacement/` scans six finite-displacement magnitudes from 0.005 to
  0.030 Angstrom.
- `hBN_Vacuum/` scans monolayer hBN cell heights of 15, 20, 30, and 40
  Angstrom while keeping the layer centered.

Each directory contains a clean `run.sh`, an analysis script, and a `results/`
directory for compact tables and figures. Solver outputs are generated in a
separate `work/` directory and are not overwritten by the analysis step.

On a Torque/PBS cluster, `run_pbs.sh` submits the complete scan as one
single-node job. It defaults to the `gold5120` queue and 28 cores to match the
validation environment; set `ZSTAR_PBS_QUEUE` and `ZSTAR_PBS_PPN` for another
cluster.
