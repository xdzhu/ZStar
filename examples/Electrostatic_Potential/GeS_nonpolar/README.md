# GeS: fixed-ion nonpolar potential reference

This case complements the polar [GeS](../GeS/README.md) example. It removes
the relative armchair Ge/S offset at fixed cell and restores equal-species
inversion pairs. The supplied reference has Pmmn symmetry; the polar source
has Pmn2_1 symmetry. It is a nonpolar reference, not a demonstrated saddle
point. **Do not relax it before reproducing the potential comparison.**

The construction follows the zero-tilting reference in Fig. 1(b) of
[Fei, Kang and Yang (2016)](https://doi.org/10.1103/PhysRevLett.117.097601).
The cell and coordinates are those of our archived GeS example, not copied
from that paper. `results/reference_construction.json` records the mapping.

## Reproduce

Install ZStar in the current Python environment, then run:

```bash
bash run.sh --dry-run
bash run.sh
```

The default decompresses a private copy of the retained electrostatic cube
and regenerates plane maps and directional profiles under a new `work/`.
No DFT is required. The archive is never edited or symlinked.

For a fresh calculation, configure ABACUS and MPI/OMP with `zstar config`,
load your cluster environment, and use:

```bash
bash run.sh --calculate --work work-new-scf
```

`run/` contains only fixed-ion SCF inputs and the included DOJO NC
pseudopotentials/DZP 10-bohr orbitals. Settings match the polar example:
PBE-D3(0), 100 Ry, kspacing 0.05 0.05 1, SCF threshold 1e-8, Gaussian
smearing 0.001 Ry. The retained ABACUS 3.10.0 LTS run converged on 40 cores
in 39 s. `results/` contains the native log, structure mapping, compressed
cube and postprocessed data. Evidence hashes are recorded separately.

The plane map averages over the cell normal and is tiled **only for
plotting** (3x3), with the central cell outlined. The potential is not a
charge-density map. Both GeS panels use a common color range after removing
their arbitrary mean potential. The one-period mirror test along `a` gives
2.36e-8 for this reference, compared with 0.0983 for the polar structure.
This is a potential-symmetry diagnostic, not a polarization magnitude.
