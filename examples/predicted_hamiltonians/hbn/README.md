# hBN with HamGNN and DeepH

The test structures displace N along the layer normal by about
±0.01058 Å. HamGNN and DeepH predict changes from the equilibrium
ABACUS Hamiltonian. PYATB uses the ABACUS overlap and position matrices
of each test structure. Both models use six training displacements,
two validation displacements, and the same two held-out test structures.

| Hamiltonian | N out-of-plane BEC (e) |
| --- | ---: |
| ABACUS at the displaced geometries | −0.341 |
| HamGNN prediction | −0.335 |
| DeepH prediction | −0.433 |
| ABACUS equilibrium Hamiltonian at both geometries | −0.884 |

From this directory, reconstruct the charges from the archived
polarization outputs. The script writes the comparison to a new file.

```sh
python compare_berry.py results/berry-controls results/berry-hamgnn results/berry-deeph replay.json
```

To repeat a polarization calculation, unpack `pyatb_inputs.zip` into
a fresh directory and run `pyatb` in the selected displacement and method
directory, for example `disp-005/hamgnn`. Each `Input` uses a relative path
to its matched `common` matrices. Both frames use a 36 × 36 × 8 Berry mesh.
The matrices are from the actual predictions and ABACUS controls.
`results/hamgnn_training.json` and `results/deeph_training.json` record
the data split and selected checkpoints.
