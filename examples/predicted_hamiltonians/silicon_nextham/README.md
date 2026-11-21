# NextHAM polarization of 64-atom silicon

This example uses the 1664-dimensional spinor Hamiltonian from the
[released NextHAM silicon example](https://github.com/DavidYin94/NextHAM_V1_1_Inference/tree/e4ea9b7f17dd2854d6ea5be4fdd1fc2a25505a6b).
We average each predicted block with the conjugate transpose of its
opposite translation. The calculation uses the released overlap,
an ABACUS position matrix in the same basis, 256 occupied states, and
a 4 × 4 × 4 Berry mesh.

The predicted polarization on the nearest branch is
(−1.7, −2.0, −2.2) × 10⁻⁵ C/m². The initial Hamiltonian gives zero to
the output precision. The original and cached calculations produce
identical archived polarization files.

To check the archived results, copy `results` to a new directory and run
`python compare_polarization.py PATH_TO_COPY`. The script writes the
branch residual for each direction. For a full solver replay, place
the matching matrix files in a copy of `run` and check
`input_files.sha256`. Then run `python prepare_inputs.py` and run PYATB
from the generated `predicted` and `initial` directories.
