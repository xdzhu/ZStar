# Predicted Hamiltonians in a PYATB polarization calculation

ZStar prepares finite-displacement structures, and PYATB obtains the
polarization for each structure from H(R), S(R) and r(R). This example
prepares one PYATB stage from a Hamiltonian exported by HamGNN, DeepH, or
NextHAM. Repeat preparation for the reference and each displacement.

1. Predict H for the same cell, atom order, orbital order, and numerical orbital
   basis as S and r. Use the model version appropriate to that basis.
2. Export it as a nonmagnetic, real ABACUS text sparse matrix with H in Ry.
   Supply the prediction structure and the insulating Fermi energy in eV.
3. Prepare the input and execute PYATB.

       zstar response pyatb-hamiltonian --input stage/pyatb/Input \
         --structure stage/pyatb/STRU --prediction-structure prediction.vasp \
         --hamiltonian prediction-H.csr --model hamgnn \
         --fermi-energy ENERGY_IN_EV --output-dir prediction-pyatb
       cd prediction-pyatb
       pyatb

The preparation checks atom order, lattice, atom positions, and matrix
dimensions, and records the exact files. Keep the orbital ordering identical
when exporting model matrices. A matching matrix size cannot verify an
orbital ordering.

[HamGNN prediction guide](https://hamgnn.readthedocs.io/en/latest/user_guide/prediction.html)
documents its NumPy output. The older ZStar gen --input-mode hamgnn command
copies model configuration files into the displacement tree.
[DeepH](https://doi.org/10.1038/s43588-022-00265-6) and
[NextHAM](https://github.com/DavidYin94/NextHAM) also have model-specific output
formats. Convert the output of the selected predictor before using this
stage preparation.
