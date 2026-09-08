# Completed independent native DFPT check

VASP 6.3.2 ran with 40 MPI ranks x 1 OpenMP thread. Both stages completed
normally. OUTCAR wall times give 91.406 allocated core-hours including the
reference SCF. This is a BEC-only cross-check, not a full phonon benchmark.

| Software | B rr | B tt | B zz | N rr | N tt | N zz |
|---|---:|---:|---:|---:|---:|---:|
| ABACUS + PYATB/cube | 0.397 | 1.256 | 2.745 | -0.474 | -1.178 | -2.745 |
| VASP DFPT | 0.318 | 1.234 | 2.754 | -0.398 | -1.154 | -2.754 |

Units are e. These are species means in atom-local radial/tangential/axial
frames. Geometry agreement is better than 1e-7 angstrom. The axial values
differ by 0.3%, tangential values by about 2%, and radial values by about
0.08 e. Different basis/core treatments and transverse implementations are
not isolated by this comparison. No empirical matching or image correction
has been applied. Native VASP tensors have a maximum Cartesian charge-sum
residual of 2e-5 e. ABACUS projection changes are below 3.2e-4 e.

`comparison.json` retains full Cartesian tensors, local component ranges,
timings, conventions and source hashes. Reproduce the comparison from the
repository root:

```bash
python tools/shared_response/compare_bn9_vasp.py \
  --case examples/1D_Nanowire/BN_9_0 \
  --native examples/1D_Nanowire/BN_9_0/results/vasp_validation \
  --output comparison-reproduced.json
```

The original execution manifest records the former default dimensionality
3, describing the periodic solver cell. It is retained unchanged as native
provenance. The actual geometry is a nanotube periodic along z. The revised
runner preserves physical dimension 1 in new workflow metadata without
changing the solver input. The original misleading bulk-response exchange
file is not distributed; `vasp_bec.json` contains the native tensors, and
the dielectric tensor in `comparison.json` is explicitly a supercell value.

POTCAR, WAVECAR and charge-density scratch files are deliberately excluded.
`input_provenance.json` records the licensed potential hashes. The clean
`run/vasp/` inputs show the response-stage settings, while `run_vasp.sh`
prepares and executes the required reference-first workflow.
