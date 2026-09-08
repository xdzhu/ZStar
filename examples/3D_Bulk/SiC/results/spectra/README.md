# Archived Unified IR and Raman results

These files were generated from the same two symmetry-adapted 3C-SiC
displacements used for the archived BEC and Gamma force constants in
`../shared/`. No additional ABACUS SCF calculation was performed: PYATB reused
the retained electronic Hamiltonian, overlap, and position matrices to obtain
the static dielectric derivatives required for Raman analysis.

The three optical modes are degenerate at 772.645 cm^-1. They have equal IR
intensities and equal normalized Raman activities, as required by the cubic
symmetry. The archive contains tabulated data, response tensors, and PNG, PDF,
and SVG plots. Large matrix copies and temporary PYATB workspaces are
excluded.

Run `bash run.sh --with-spectra` from the case root to repeat the complete
calculation under `work/`.
