# Native VASP BEC cross-check

This directory contains a compact VASP/PBE-D3(BJ) BEC calculation performed on
the deposited CRYSTAL/B3LYP-D3(BJ) geometry. It separates the effect of using a
common geometry from the remaining functional, basis, and implementation
differences. `BEC_tensors.csv` uses ZStar's displacement-first tensor convention.

The response was calculated with native VASP `LEPSILON`, a 500 eV cutoff, a
1x1x12 k-point mesh, `EDIFF=1e-8`, 28 MPI ranks, and `NCORE=4`. The maximum
acoustic-sum residual is `2e-5 e`. Symmetry-equivalent pairs are averaged only
for the compact diagonal comparison in the parent directory; the complete raw
tensors are retained here.

`POSCAR`, `INCAR`, and `KPOINTS` are sufficient to document the calculation.
The licensed `POTCAR` and large restart files are intentionally excluded.
