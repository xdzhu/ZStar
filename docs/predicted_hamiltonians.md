# Predicted Hamiltonians in a PYATB polarization calculation

ZStar prepares finite-displacement structures, and PYATB obtains the
polarization for each structure from H(R), S(R) and r(R). This example
prepares one PYATB stage from a Hamiltonian exported by HamGNN, DeepH, or
NextHAM. Repeat preparation for the reference and each displacement.

1. Predict H for the same cell, atom order, orbital order, and numerical orbital
   basis as S and r. Use the model version appropriate to that basis.
2. Export H as an ABACUS text sparse matrix in Ry. Use `nspin 1` for the
   DeepH and HamGNN converters. Use a matching `nspin 1` or `nspin 4` PYATB
   template for a native NextHAM export.
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

## Export predictions from each package

### DeepH-pack

Install the optional h5py dependency with pip install 'zstar[deeph]'. Use the real, nonmagnetic ABACUS-trained model output. Pass the matching
DeepH overlap and the orbital shell list emitted by the same workflow.

    zstar response convert-deeph --prediction hamiltonians_pred.h5 \
      --orbital-types orbital_types.dat --model-overlap overlaps.h5 \
      --reference-overlap stage/data-SR-sparse_SPIN0.csr --output prediction-H.csr

The command reverses DeepH's signed s/p/d/f orbital mapping, converts eV
to Ry, and compares each overlap block with the ABACUS overlap.
Both prediction converters enforce H(R) = H(-R)^T by averaging paired
blocks, equivalent to Hermitianizing the Fourier Hamiltonian.

### HamGNN

Use the ABACUS non-SOC predictor. Save the single structure's numeric graph
arrays in one NumPy archive:

- orbital_mask is the boolean atom-by-padded-orbital array from the same
  HamGNN basis definition used in band_cal.py.
- edge_index has shape (2, edges), and cell_shift has shape (edges, 3).
- Son and Soff contain padded onsite and inter-cell overlaps for atoms
  and edges in the prediction order. Reshape to (atoms, orbitals, orbitals)
  and (edges, orbitals, orbitals).

The converter reads numeric arrays without Python object deserialization.

    zstar response convert-hamgnn --prediction prediction_hamiltonian.npy \
      --graph prediction_graph.npz --reference-overlap stage/data-SR-sparse_SPIN0.csr \
      --output prediction-H.csr

### NextHAM

The official inference postprocessor writes predict_hr_tot as ABACUS
text CSR in Ry. Use that file as the Hamiltonian on the preparation
command. Match the original ABACUS basis and geometry used by NextHAM to
the overlap and position matrices already supplied to PYATB. For the
spin-orbit model, all three matrices must use the same spinor basis and
ordering, with `nspin 4` and the spinor occupied-band count in the template.

## Code validation

The native DeepH and HamGNN conversion was checked by encoding a real hBN
ABACUS Hamiltonian and its overlap in each model format and recovering
all 81 real-space blocks. The largest entrywise errors were 1.11e-16
Ry for DeepH and 2.30e-17 Ry for HamGNN. This checks conversion of the
basis and units. To evaluate a trained model, prepare its own predicted
Hamiltonian for every reference and displaced geometry.
