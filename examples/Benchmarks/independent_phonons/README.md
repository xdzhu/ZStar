# Independent phonons for the Separate/Unified benchmark

These are 30 newly calculated force-only SCFs, not duplicated timings or
forces relabeled from a BEC workflow. `results/` contains written inputs,
SCF logs, forces, successful-stage timings, validation and checksums.
`run/force_workflow.py` is the portable driver. Basis files are taken from
each sibling case's self-contained `run/` directory and copied into the work directory.

```bash
# Offline verification, no DFT and no changes to results/
bash run.sh

# Repeat the independent force SCFs for one material
bash run.sh --calculate t_HfO2 --command "mpirun -np 1 abacus" --omp 40
```

Add `--work /path/to/new-work` to select a new workspace. Each force input
starts from atomic charge, enables forces, and disables matrix/density exports.
The existing Cartesian reference supplies the force offset; there is no
additional reference SCF in this task count. BECs come from the separate
Cartesian archive. The original BEC timings included force output and were
not adjusted to estimate an unmeasured force-free implementation.

Successful solver wall times times 40 allocated cores define the added cost.
Failed initial asset-resolution attempts remain in the ledgers but are not
counted as completed solver work. This is a single timing measurement per
task, not an architecture-independent speedup guarantee.

The table is regenerated from the repository root with:

```bash
python tools/shared_response/build_separate_efficiency.py
```

Original joint Cartesian comparisons remain separate: their Hessians must
not be confused with these newly measured independent force calculations.
