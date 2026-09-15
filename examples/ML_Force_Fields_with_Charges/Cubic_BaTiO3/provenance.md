# Provenance and availability

The local benchmark used ABACUS/PBEsol labels with one declared
pseudopotential/orbital/basis family and `kspacing = 0.1 A^-1`.  It contains
no public qNEP E/F labels in the archived multiphase trial datasets.

The full raw SCF directories, qNEP models, and train/test extxyz files are
intentionally excluded from Git because they are calculation artifacts rather
than a minimal software example.  A future public archive should provide:

- immutable dataset and model URLs;
- SHA-256 checksums;
- ABACUS, PYATB, GPUMD/qNEP, and Phonopy versions;
- GPU/resource logs; and
- exact DFT pseudopotential, orbital, functional, and k-point settings.

Relevant external references are the qNEP paper (DOI
10.1021/acs.jctc.6c00146), its Supporting Information, GPUMD charge-mode
documentation, and the qNEP Zenodo record 18335947.  They are reference
sources, not bundled data.
